"""Exact bounded Bayesian opponent-inference tests."""

from fractions import Fraction
from types import MappingProxyType

import pytest

from poker_solver.inference import (
    Hypothesis,
    ImpossibleEvidenceError,
    Observation,
    OpponentInference,
)


def _hypotheses():
    return (
        Hypothesis(
            "tight",
            Fraction(2, 3),
            {
                "root": {"fold": Fraction(3, 4), "call": Fraction(1, 4)},
                "turn": {"fold": Fraction(1, 2), "call": Fraction(1, 2)},
            },
            provenance="solver-A",
        ),
        Hypothesis(
            "loose",
            Fraction(1, 3),
            {
                "root": {"fold": Fraction(1, 4), "call": Fraction(3, 4)},
                "turn": {"fold": Fraction(1, 4), "call": Fraction(3, 4)},
            },
            provenance="solver-B",
        ),
    )


def test_manual_fraction_bayes_and_sequential_batch_identity():
    model = OpponentInference(_hypotheses())
    first = model.update((Observation("root", "call"),))
    assert first.posterior == {"tight": Fraction(2, 5), "loose": Fraction(3, 5)}
    sequential = first.update(Observation("turn", "fold"))
    batch = model.update((Observation("root", "call"), Observation("turn", "fold")))
    assert sequential.posterior == batch.posterior == {
        "tight": Fraction(4, 7), "loose": Fraction(3, 7)
    }
    assert sequential.observations == batch.observations


def test_posterior_predictive_is_exact_and_deterministic():
    result = OpponentInference(_hypotheses()).update((Observation("root", "call"),))
    assert result.predictive("turn") == {
        "call": Fraction(13, 20), "fold": Fraction(7, 20)
    }
    assert tuple(result.posterior) == ("tight", "loose")
    assert result.provenance == ("solver-A", "solver-B")
    assert isinstance(result.posterior, MappingProxyType)


def test_prior_scale_invariance_and_caller_mutation_isolation():
    table = {"root": {"fold": Fraction(1, 2), "call": Fraction(1, 2)}}
    hypothesis = Hypothesis("h", 7, table, provenance="caller")
    table["root"]["fold"] = Fraction(1)
    model = OpponentInference((hypothesis,))
    assert model.update((Observation("root", "call"),)).posterior["h"] == 1
    assert hypothesis.likelihoods["root"]["fold"] == Fraction(1, 2)
    with pytest.raises(TypeError):
        hypothesis.likelihoods["root"]["fold"] = Fraction(1)  # type: ignore[index]


def test_zero_evidence_fails_closed_without_smoothing():
    hypotheses = (
        Hypothesis("a", 1, {"root": {"fold": 1, "call": 0}}, provenance="a"),
        Hypothesis("b", 1, {"root": {"fold": 1, "call": 0}}, provenance="b"),
    )
    with pytest.raises(ImpossibleEvidenceError):
        OpponentInference(hypotheses).update((Observation("root", "call"),))


@pytest.mark.parametrize("bad", [True, -1, float("nan"), float("inf")])
def test_rejects_invalid_prior_and_likelihood_values(bad):
    with pytest.raises((TypeError, ValueError)):
        Hypothesis("bad", bad, {"root": {"fold": 1}}, provenance="x")
    with pytest.raises((TypeError, ValueError)):
        Hypothesis("bad", 1, {"root": {"fold": bad}}, provenance="x")


def test_rejects_duplicate_labels_and_nonunit_or_mismatched_rows():
    valid = Hypothesis("same", 1, {"root": {"fold": 1}}, provenance="x")
    with pytest.raises(ValueError, match="duplicate"):
        OpponentInference((valid, valid))
    with pytest.raises(ValueError, match="sum"):
        Hypothesis("bad", 1, {"root": {"fold": Fraction(1, 2)}}, provenance="x")
    other = Hypothesis("other", 1, {"root": {"call": 1}}, provenance="y")
    with pytest.raises(ValueError, match="action coverage"):
        OpponentInference((valid, other))


def test_missing_observation_action_and_private_keys_fail_closed():
    model = OpponentInference(_hypotheses())
    with pytest.raises(ValueError, match="unknown observation"):
        model.update((Observation("river", "call"),))
    with pytest.raises(ValueError, match="unknown action"):
        model.update((Observation("root", "raise"),))
    with pytest.raises(ValueError, match="public"):
        Observation("private_cards:AsKs", "call")
    with pytest.raises(ValueError, match="public"):
        Observation("hidden/villain", "call")


def test_observation_and_hypothesis_schema_are_strict():
    with pytest.raises(ValueError, match="label"):
        Hypothesis("", 1, {"root": {"fold": 1}}, provenance="x")
    with pytest.raises(ValueError, match="provenance"):
        Hypothesis("x", 1, {"root": {"fold": 1}}, provenance="")
    with pytest.raises(ValueError, match="observation"):
        Observation("", "call")
    with pytest.raises(ValueError, match="action"):
        Observation("root", "")
