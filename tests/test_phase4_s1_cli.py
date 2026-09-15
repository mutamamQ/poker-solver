"""Additive Phase-4 CLI contract tests."""

from __future__ import annotations

import io
import json

from poker_solver.cli import build_parser, main


def _request(*, algorithm: str = "vanilla-cfr", seed: int | None = None) -> dict:
    return {
        "version": 4,
        "operation": "solve-allstreet-postflop",
        "payload": {
            "version": "allstreet-postflop-v1",
            "starting_board": [0, 1, 2],
            "initial_dead_pot": 2,
            "effective_stack": 1,
            "player0_combos": [{"cards": [3, 4], "weight": 1.0}],
            "player1_combos": [{"cards": [5, 6], "weight": 1.0}],
            "allowed_runouts": [[7, 8]],
            "betting_mode": "no-limit",
            "wager_targets": [0],
            "algorithm": algorithm,
            "iterations": 2,
            "seed": seed,
            "max_nodes": 5_000,
            "max_depth": 64,
        },
    }


def _write_request(tmp_path, request: dict, name: str = "request.json"):
    path = tmp_path / name
    path.write_text(json.dumps(request), encoding="utf-8")
    return path


def test_phase4_command_registered_in_parser():
    args = build_parser().parse_args(["phase4", "request.json", "--json"])
    assert args.command == "phase4"
    assert args.request == "request.json"
    assert args.json is True


def test_phase4_file_input_emits_compact_v4_json(tmp_path, capsys):
    path = _write_request(tmp_path, _request())
    assert main(["phase4", str(path), "--json"]) == 0
    text = capsys.readouterr().out
    result = json.loads(text)
    assert text == json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) + "\n"
    assert result["version"] == 4
    assert result["operation"] == "solve-allstreet-postflop"
    assert result["config_version"] == 4
    assert result["game_version"] == "allstreet-postflop-v1"
    assert result["starting_street"] == "flop"
    assert result["continuation"] == "automatic-natural-terminal"


def test_phase4_accepts_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_request())))
    assert main(["phase4", "-", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["version"] == 4


def test_phase4_vanilla_output_is_byte_deterministic(tmp_path, capsys):
    path = _write_request(tmp_path, _request())
    argv = ["phase4", str(path), "--json"]
    assert main(argv) == 0
    first = capsys.readouterr().out
    assert main(argv) == 0
    second = capsys.readouterr().out
    assert first == second


def test_phase4_seeded_mccfr_output_is_byte_deterministic(tmp_path, capsys):
    path = _write_request(
        tmp_path, _request(algorithm="external-sampling-mccfr", seed=17)
    )
    argv = ["phase4", str(path), "--json"]
    assert main(argv) == 0
    first = capsys.readouterr().out
    assert main(argv) == 0
    second = capsys.readouterr().out
    assert first == second


def test_phase4_malformed_json_exits_2(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{not-json}", encoding="utf-8")
    assert main(["phase4", str(path), "--json"]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_phase4_validation_error_exits_2(tmp_path, capsys):
    request = _request()
    request["payload"]["iterations"] = 0
    path = _write_request(tmp_path, request)
    assert main(["phase4", str(path), "--json"]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_phase4_missing_file_exits_2(capsys):
    assert main(["phase4", "/definitely/missing/request.json", "--json"]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_phase3_command_remains_compatible(tmp_path, capsys):
    request = {"version": 3, "operation": "capabilities", "payload": {}}
    path = _write_request(tmp_path, request, "phase3.json")
    assert main(["phase3", str(path), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["version"] == 3
    assert "features" in result


def test_phase4_canonical_example_executes(capsys):
    assert main(["phase4", "examples/phase4_s1_flop.json", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["config_version"] == 4
    assert result["game_version"] == "allstreet-postflop-v1"
    assert result["continuation"] == "automatic-natural-terminal"