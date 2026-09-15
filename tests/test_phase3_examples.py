"""Canonical Phase-3 synthetic example provenance and execution tests."""

import json
from pathlib import Path

from poker_solver.api_v3 import dispatch_v3


ROOT = Path(__file__).parents[1]
NAMES = (
    "phase3_btn_vs_bb_25bb.json",
    "phase3_sb_vs_bb_15bb.json",
    "phase3_three_way_river.json",
    "phase3_ranges.json",
    "phase3_exploitative.json",
    "phase3_icm_bounty.json",
    "phase3_checkdown_rollout.json",
)
ACCURACY = "synthetic input fixture; no equilibrium chart claim"


def test_all_canonical_examples_exist_with_truthful_stable_provenance():
    for name in NAMES:
        data = json.loads((ROOT / "examples" / name).read_text())
        assert data["accuracy_claim"] == ACCURACY
        assert data["provenance"] == "poker-solver bundled synthetic example; not presolved"
        assert "timestamp" not in data
        assert "token" not in data
        assert "password" not in data


def test_programmatic_v3_fixtures_dispatch_deterministically():
    for name in ("phase3_ranges.json", "phase3_exploitative.json", "phase3_icm_bounty.json"):
        data = json.loads((ROOT / "examples" / name).read_text())
        assert data["kind"] == "programmatic-v3-fixture"
        assert data["execution"] == "pass the request member to dispatch_v3; not a direct CLI envelope"
        request = data["request"]
        assert dispatch_v3(request) == dispatch_v3(request)


def test_game_templates_declare_required_caller_data_and_no_strategy():
    expected = {
        "phase3_btn_vs_bb_25bb.json": "caller-supplied-terminal-table-required",
        "phase3_sb_vs_bb_15bb.json": "caller-supplied-terminal-table-required",
        "phase3_three_way_river.json": "caller-supplied-ranks-required",
        "phase3_checkdown_rollout.json": "explicit-finite-game-required",
    }
    for name, requirement in expected.items():
        data = json.loads((ROOT / "examples" / name).read_text())
        assert data["required_caller_data"] == requirement
        assert "strategy" not in data
        assert data["presolved"] is False
