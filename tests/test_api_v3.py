"""Strict version-3 facade, preset, and CLI tests."""

import json

import pytest

from poker_solver.api_v3 import dispatch_v3
from poker_solver.cli import main
from poker_solver.presets import get_preset, list_presets


def request(operation, payload):
    return {"version": 3, "operation": operation, "payload": payload}


def test_capability_manifest_is_truthful_and_deterministic():
    result = dispatch_v3(request("capabilities", {}))
    assert result["version"] == 3
    assert result["features"]["fast-ddls"]["status"] == "unavailable"
    assert result["features"]["preflop"]["continuation"] == "terminal-table-only"
    assert result["features"]["multiway-postflop"]["players"] == 3
    assert result["features"]["n-player-cfr"]["deviation_certificate"] == "exhaustive-diagnostic-only"
    assert result["features"]["engine"]["modes"] == ["classic", "checkdown-equity"]
    assert result == dispatch_v3(request("capabilities", {}))
    result["features"]["fast-ddls"]["status"] = "implemented"
    assert dispatch_v3(request("capabilities", {}))["features"]["fast-ddls"]["status"] == "unavailable"


def test_presets_are_named_immutable_copies_and_have_example_files():
    names = list_presets()
    assert names == ("btn-vs-bb-25bb", "threeway-flop-demo")
    first = get_preset(names[0])
    first["starting_stacks"][0] = 999
    assert get_preset(names[0])["starting_stacks"][0] == 2500
    listed = dispatch_v3(request("list-presets", {}))
    assert [item["name"] for item in listed["presets"]] == list(names)


def test_icm_operation():
    result = dispatch_v3(request("icm", {"stacks": [3, 1], "payouts": [100, 0]}))
    assert result == {"operation": "icm", "equities": [75.0, 25.0], "scope": "bounded-small-field"}


def test_bounty_ko_operation_preserves_exact_rationals():
    result = dispatch_v3(request("bounty-ko", {
        "eliminated_bounty": "10",
        "recipient_shares": {"0": "1/3", "2": "2/3"},
    }))
    assert result["immediate_cash"] == {"0": "10/3", "2": "20/3"}
    assert result["scope"] == "immediate-one-hand-only"


def test_range_normalize_and_sizing_operations():
    normalized = dispatch_v3(request("range-normalize", {"text": "AsAh:0.5,KsKh"}))
    assert normalized["combo_count"] == 2
    assert normalized["text"] == "KhKs:1,AhAs:0.5"
    sized = dispatch_v3(request("size-convert", {
        "expression": {"unit": "big-blinds", "value": 3},
        "context": {"pot": 3, "own_commitment": 1, "highest_commitment": 2, "remaining_stack": 19, "big_blind": 2},
    }))
    assert sized["raise_to"] == 6


def test_exact_inference_operation():
    payload = {
        "hypotheses": [
            {"label": "tight", "prior": "1", "provenance": "fixture", "likelihoods": {"root": {"fold": "3/4", "call": "1/4"}}},
            {"label": "loose", "prior": "1", "provenance": "fixture", "likelihoods": {"root": {"fold": "1/4", "call": "3/4"}}},
        ],
        "observations": [{"public_key": "root", "action": "fold"}],
    }
    result = dispatch_v3(request("inference", payload))
    assert result["posterior"] == {"tight": "3/4", "loose": "1/4"}
    assert result["provenance"] == ["fixture", "fixture"]


def test_v3_rejects_unknown_missing_bool_and_nonfinite_fields():
    with pytest.raises(ValueError, match="unknown"):
        dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}, "extra": 1})
    with pytest.raises(ValueError):
        dispatch_v3({"version": True, "operation": "capabilities", "payload": {}})
    with pytest.raises(ValueError, match="unsupported"):
        dispatch_v3(request("solve-the-world", {}))
    with pytest.raises(ValueError):
        dispatch_v3(request("icm", {"stacks": [float("inf")], "payouts": [1]}))
    with pytest.raises(ValueError, match="too long"):
        dispatch_v3(request("bounty-ko", {
            "eliminated_bounty": "1" * 257,
            "recipient_shares": {"0": "1"},
        }))
    with pytest.raises(ValueError, match="too many hypotheses"):
        dispatch_v3(request("inference", {"hypotheses": [{}] * 65, "observations": []}))


def test_cli_phase3_json_file_stdin_and_error(tmp_path, monkeypatch, capsys):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request("list-presets", {})))
    assert main(["phase3", str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["operation"] == "list-presets"

    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(request("icm", {"stacks": [1], "payouts": [5]}))))
    assert main(["phase3", "-", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["equities"] == [5.0]

    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert main(["phase3", str(bad), "--json"]) == 2
    assert "error:" in capsys.readouterr().err
