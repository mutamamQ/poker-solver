"""Validation, immutability and identity tests for practice.models."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from types import MappingProxyType

import pytest

from poker_solver.cards import format_card, parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.model import Action
from poker_solver.practice.models import (
    PracticeSpot,
    SolveParams,
    SolveProvenance,
    action_from_json,
    action_to_json,
)

BOARD = parse_cards(["Td", "8h", "As", "6s", "7s"])
R0 = (WeightedCombo(parse_cards(["Ac", "Ah"]), 1.0), WeightedCombo(parse_cards(["5d", "4d"]), 0.5))
R1 = (WeightedCombo(parse_cards(["Qc", "Qd"]), 1.0), WeightedCombo(parse_cards(["Jc", "Jd"]), 1.0))


def river(**overrides):
    kwargs = dict(
        family="river-oop-bet-or-check",
        backend="river",
        game_type="heads-up",
        street="river",
        board=BOARD,
        hero_seat=0,
        villain_seats=(1,),
        ranges=(R0, R1),
        pot=100,
        stacks=(200, 200),
        action_history=(),
        bet_sizes=(75,),
        hero_hand=parse_cards(["Ah", "Ac"]),
        solve=SolveParams(),
        backend_extra={},
    )
    kwargs.update(overrides)
    return PracticeSpot(**kwargs)


def kuhn(card="J", hero=0, history=(), **overrides):
    kwargs = dict(
        family="kuhn-intro", backend="kuhn", game_type="heads-up", street="preflop", board=(),
        hero_seat=hero, villain_seats=(1 - hero,), ranges=((), ()), pot=2, stacks=(1, 1),
        action_history=history, bet_sizes=(1,), hero_hand=None, solve=SolveParams(),
        backend_extra={"kuhn_card": card},
    )
    kwargs.update(overrides)
    return PracticeSpot(**kwargs)


def test_solve_params_validation():
    assert SolveParams() == SolveParams("vanilla-cfr", 200, None)
    for bad in (dict(iterations=0), dict(iterations=True), dict(iterations=1.0), dict(algorithm="x"),
                dict(seed=3), dict(algorithm="external-sampling-mccfr"),
                dict(algorithm="external-sampling-mccfr", seed=True)):
        with pytest.raises(ValueError):
            SolveParams(**bad)
    assert SolveParams("external-sampling-mccfr", 5, 7).seed == 7
    assert SolveParams.from_json(SolveParams(iterations=9).canonical()) == SolveParams(iterations=9)
    with pytest.raises(ValueError):
        SolveParams.from_json({"iterations": 3, "bogus": 1})


@pytest.mark.parametrize(
    "overrides",
    [
        dict(family="Bad Family"),
        dict(backend="nope"),
        dict(street="flop"),
        dict(board=BOARD[:4]),
        dict(board=BOARD[:4] + (BOARD[0],)),
        dict(board=BOARD[:4] + (True,)),
        dict(hero_seat=True),
        dict(hero_seat=2),
        dict(villain_seats=(0,)),
        dict(pot=True),
        dict(pot=0),
        dict(pot=float("nan")),
        dict(stacks=(200, 100)),
        dict(stacks=(200, True)),
        dict(bet_sizes=(75, 50)),
        dict(bet_sizes=(500,)),
        dict(bet_sizes=(25, 75)),
        dict(bet_sizes=(True,)),
        dict(action_history=(Action("call"),)),
        dict(action_history=(Action("bet", 75),)),  # wrong actor for hero 0
        dict(hero_hand=parse_cards(["Qc", "Qd"])),  # not in hero range
        dict(hero_hand=None),
        dict(hero_hand=(BOARD[0], 1)),
        dict(backend_extra={"unknown": 1}),
        dict(backend_extra={"kuhn_card": "J"}),
        dict(backend_extra={"spr": float("inf")}),
        dict(ranges=(R0,)),
        dict(ranges=(R0, R1 + (R1[0],))),
        dict(ranges=(R0, (WeightedCombo(parse_cards(["Qc", "Qd"]), 0.0),))),
        dict(ranges=(R0, ((40, 41),))),
        dict(solve={"iterations": 5}),
        dict(game_type="3-max"),
    ],
)
def test_river_spot_rejects_invalid(overrides):
    with pytest.raises(ValueError):
        river(**overrides)


def test_kuhn_validation():
    assert kuhn().hero_hand_str == ["J"]
    with pytest.raises(ValueError):
        kuhn(card="A")
    with pytest.raises(ValueError):
        kuhn(hero=1)  # P0 acts at the root
    with pytest.raises(ValueError):
        kuhn(history=(Action("check"), Action("check")))  # terminal
    with pytest.raises(ValueError):
        kuhn(pot=3)
    with pytest.raises(ValueError):
        kuhn(hero_hand=(0, 1))
    assert kuhn(hero=1, history=(Action("bet"),)).hero_seat == 1


def test_allstreet_turn_is_partial():
    with pytest.raises(ValueError, match="turn"):
        river(backend="allstreet", street="turn", board=BOARD[:4])


def test_frozen_and_defensive_copies():
    extra = {"spr": 2, "range_shape": "x"}
    ranges = [list(R0), list(R1)]
    spot = river(ranges=ranges, backend_extra=extra)
    before = spot.params_hash()
    extra["spr"] = 9
    ranges[0].append(WeightedCombo((0, 1), 1.0))
    assert spot.params_hash() == before
    assert isinstance(spot.backend_extra, MappingProxyType)
    assert isinstance(spot.ranges, tuple) and isinstance(spot.ranges[0], tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        spot.pot = 5.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        spot.backend_extra["spr"] = 1  # type: ignore[index]
    canonical = spot.canonical()
    canonical["pot"] = 1
    assert spot.canonical()["pot"] == 100.0


def test_hash_and_spot_id_definition():
    spot = river()
    canonical = spot.canonical()
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    assert spot.params_hash() == hashlib.sha256(text.encode()).hexdigest()
    canonical.pop("solve")
    no_solve = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    assert spot.spot_id == spot.family + "/" + hashlib.sha256(no_solve.encode()).hexdigest()[:12]
    other = spot.with_solve(SolveParams(iterations=7))
    assert other.spot_id == spot.spot_id
    assert other.params_hash() != spot.params_hash()
    assert other.solve.iterations == 7


def test_hash_stability_and_normalization():
    assert river().params_hash() == river().params_hash()
    assert river(pot=100).params_hash() == river(pot=100.0).params_hash()
    assert river(ranges=(tuple(reversed(R0)), R1)).params_hash() == river().params_hash()
    assert river(hero_hand=parse_cards(["Ac", "Ah"])).params_hash() == river().params_hash()
    base = river()
    for changed in (river(pot=150), river(stacks=(300, 300)), river(bet_sizes=(50,)),
                    river(ranges=(R0[:1], R1)), river(backend_extra={"spr": 2})):
        assert changed.params_hash() != base.params_hash()
        assert changed.spot_id != base.spot_id


def test_to_json_shape():
    data = river(action_history=(Action("bet", 75),), hero_seat=1, villain_seats=(0,),
                 hero_hand=parse_cards(["Qc", "Qd"])).to_json()
    assert data["board_str"] == [format_card(c) for c in BOARD]
    assert data["hero_hand_str"] == ["Qc", "Qd"]
    assert data["action_history"] == [{"kind": "bet", "amount": 75}]
    assert data["spot_id"].startswith("river-oop-bet-or-check/")
    assert len(data["params_hash"]) == 64
    assert isinstance(data["label"], str) and "Qc" in data["label"]
    json.dumps(data, allow_nan=False)
    k = kuhn("Q").to_json()
    assert k["hero_hand_str"] == ["Q"] and k["hero_hand"] is None


def test_action_json_roundtrip():
    for action in (Action("check"), Action("bet", 75)):
        assert action_from_json(action_to_json(action)) == action
    assert action_from_json({"kind": "fold"}) == Action("fold")
    for bad in ({"kind": ""}, {"kind": "bet", "amount": True}, {"kind": "bet", "amount": -1},
                {"kind": "bet", "x": 1}, "bet"):
        with pytest.raises(ValueError):
            action_from_json(bad)


def test_provenance_validation():
    spot = river()
    good = dict(backend="river", entrypoint="e", params=spot.canonical(), params_hash=spot.params_hash(),
                algorithm="vanilla-cfr", iterations=1, seed=None, nash_conv=0.1, wall_time_s=0.0,
                solver_version="0.1.0")
    prov = SolveProvenance(**good)
    assert prov.to_json()["params"] == spot.canonical()
    for key, value in (("params_hash", "abc"), ("iterations", True), ("nash_conv", float("nan")),
                       ("wall_time_s", -1.0), ("backend", "x")):
        with pytest.raises(ValueError):
            SolveProvenance(**{**good, key: value})
