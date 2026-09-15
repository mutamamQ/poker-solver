"""Exact bounded Bayesian inference from explicit public action likelihoods."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence


class ImpossibleEvidenceError(ValueError):
    """Raised when an observation sequence has zero probability."""


def _fraction(value: object, label: str) -> Fraction:
    if isinstance(value, bool):
        raise TypeError(f"{label} must not be boolean")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{label} must be finite")
        return Fraction.from_float(value)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{label} must be rational text") from exc
    raise TypeError(f"{label} must be an int, float, Fraction, or rational text")


def _public_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty text")
    lowered = value.lower()
    if any(token in lowered for token in ("private", "hidden", "hole_card", "hole-card")):
        raise ValueError(f"{label} must identify public information only")
    return value


@dataclass(frozen=True, slots=True)
class Observation:
    public_key: str
    action: str

    def __post_init__(self) -> None:
        _public_text(self.public_key, "observation public key")
        if not isinstance(self.action, str) or not self.action:
            raise ValueError("observation action must be non-empty text")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    label: str
    prior: Fraction
    likelihoods: Mapping[str, Mapping[str, Fraction]]
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("hypothesis label must be non-empty text")
        if not isinstance(self.provenance, str) or not self.provenance:
            raise ValueError("hypothesis provenance must be non-empty text")
        prior = _fraction(self.prior, "prior")
        if prior < 0:
            raise ValueError("prior must be non-negative")
        if not isinstance(self.likelihoods, Mapping) or not self.likelihoods:
            raise ValueError("likelihoods must contain public observations")
        copied: dict[str, Mapping[str, Fraction]] = {}
        for public_key, row in self.likelihoods.items():
            _public_text(public_key, "likelihood public key")
            if not isinstance(row, Mapping) or not row:
                raise ValueError("likelihood action row must be non-empty")
            converted: dict[str, Fraction] = {}
            for action, probability in row.items():
                if not isinstance(action, str) or not action:
                    raise ValueError("likelihood action must be non-empty text")
                probability = _fraction(probability, "likelihood")
                if probability < 0:
                    raise ValueError("likelihood must be non-negative")
                converted[action] = probability
            if sum(converted.values(), Fraction()) != 1:
                raise ValueError("likelihood action row must sum to 1")
            copied[public_key] = MappingProxyType(converted)
        object.__setattr__(self, "prior", prior)
        object.__setattr__(self, "likelihoods", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class InferenceResult:
    hypotheses: tuple[Hypothesis, ...]
    posterior: Mapping[str, Fraction]
    observations: tuple[Observation, ...]
    provenance: tuple[str, ...]

    def update(self, observation: Observation) -> "InferenceResult":
        return _update(self.hypotheses, self.posterior, self.observations + (observation,))

    def predictive(self, public_key: str) -> Mapping[str, Fraction]:
        _public_text(public_key, "predictive public key")
        actions = _action_signature(self.hypotheses, public_key)
        result = {
            action: sum(
                self.posterior[hypothesis.label]
                * hypothesis.likelihoods[public_key][action]
                for hypothesis in self.hypotheses
            )
            for action in actions
        }
        return MappingProxyType(result)


class OpponentInference:
    """Validated finite hypothesis model with exact sequential Bayes updates."""

    def __init__(self, hypotheses: Sequence[Hypothesis]) -> None:
        if isinstance(hypotheses, (str, bytes)) or not isinstance(hypotheses, Sequence):
            raise TypeError("hypotheses must be a finite sequence")
        copied = tuple(hypotheses)
        if not copied or any(not isinstance(item, Hypothesis) for item in copied):
            raise ValueError("hypotheses must contain Hypothesis values")
        labels = tuple(item.label for item in copied)
        if len(set(labels)) != len(labels):
            raise ValueError("duplicate hypothesis labels")
        prior_total = sum((item.prior for item in copied), Fraction())
        if prior_total <= 0:
            raise ValueError("total prior must be positive")
        observation_keys = tuple(copied[0].likelihoods)
        if any(tuple(item.likelihoods) != observation_keys for item in copied[1:]):
            raise ValueError("hypotheses must have identical observation coverage and order")
        for public_key in observation_keys:
            _action_signature(copied, public_key)
        self.hypotheses = copied
        self._prior = MappingProxyType({
            item.label: item.prior / prior_total for item in copied
        })

    def update(self, observations: Sequence[Observation]) -> InferenceResult:
        if isinstance(observations, (str, bytes)) or not isinstance(observations, Sequence):
            raise TypeError("observations must be a finite sequence")
        observations = tuple(observations)
        if any(not isinstance(item, Observation) for item in observations):
            raise TypeError("observations must contain Observation values")
        result = _update(self.hypotheses, self._prior, ())
        for observation in observations:
            result = result.update(observation)
        return result


def _action_signature(hypotheses: tuple[Hypothesis, ...], public_key: str) -> tuple[str, ...]:
    if public_key not in hypotheses[0].likelihoods:
        raise ValueError(f"unknown observation {public_key!r}")
    actions = tuple(hypotheses[0].likelihoods[public_key])
    for hypothesis in hypotheses[1:]:
        if public_key not in hypothesis.likelihoods:
            raise ValueError("hypotheses have missing observation coverage")
        if tuple(hypothesis.likelihoods[public_key]) != actions:
            raise ValueError("hypothesis action coverage/order mismatch")
    return actions


def _update(
    hypotheses: tuple[Hypothesis, ...],
    current: Mapping[str, Fraction],
    observations: tuple[Observation, ...],
) -> InferenceResult:
    if observations:
        observation = observations[-1]
        actions = _action_signature(hypotheses, observation.public_key)
        if observation.action not in actions:
            raise ValueError(f"unknown action {observation.action!r}")
        masses = {
            hypothesis.label:
                current[hypothesis.label]
                * hypothesis.likelihoods[observation.public_key][observation.action]
            for hypothesis in hypotheses
        }
        evidence = sum(masses.values(), Fraction())
        if evidence == 0:
            raise ImpossibleEvidenceError("observation sequence has zero evidence")
        posterior = {label: mass / evidence for label, mass in masses.items()}
    else:
        posterior = dict(current)
    return InferenceResult(
        hypotheses=hypotheses,
        posterior=MappingProxyType(posterior),
        observations=observations,
        provenance=tuple(item.provenance for item in hypotheses),
    )
