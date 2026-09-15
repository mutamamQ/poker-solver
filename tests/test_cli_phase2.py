"""Phase 2 CLI integration and round-trip tests."""

import io
import json

from poker_solver.cli import main


def _config():
    return {
        "version": 2,
        "starting_street": "river",
        "starting_board": ["2c", "3d", "4h", "9s", "Kc"],
        "initial_dead_pot": 2,
        "effective_stack": 1,
        "player0_combos": [{"cards": ["As", "5s"], "weight": 1.7}],
        "player1_combos": [{"cards": ["Kh", "Qh"], "weight": 2.3}],
        "allowed_runouts": [],
        "betting_mode": "pot-limit",
        "wager_targets": [1],
    }


def test_solve_multistreet_and_exploitability_roundtrip(tmp_path, capsys):
    config_path = tmp_path / "spot.json"
    config_path.write_text(json.dumps(_config()))
    assert main(["solve-multistreet", str(config_path), "--algorithm", "vanilla-cfr", "--iterations", "50", "--json"]) == 0
    solved = json.loads(capsys.readouterr().out)
    assert solved["metadata"]["config_version"] == 2
    assert solved["exploitability_half_nash_conv"] == solved["nash_conv"] / 2
    strategy_path = tmp_path / "strategy.json"
    strategy_path.write_text(json.dumps(solved))
    assert main(["exploitability", str(config_path), str(strategy_path), "--json"]) == 0
    measured = json.loads(capsys.readouterr().out)
    assert measured["nash_conv"] == solved["nash_conv"]
    assert measured["best_response_values"]


def test_solve_multistreet_reads_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_config())))
    code = main(["solve-multistreet", "-", "--algorithm", "vanilla-cfr", "--iterations", "5", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["algorithm"] == "vanilla-cfr"


def test_mccfr_cli_is_same_seed_deterministic(tmp_path, capsys):
    path = tmp_path / "spot.json"
    path.write_text(json.dumps(_config()))
    argv = ["solve-multistreet", str(path), "--algorithm", "external-sampling-mccfr", "--iterations", "100", "--seed", "42", "--json"]
    assert main(argv) == 0
    first = capsys.readouterr().out
    assert main(argv) == 0
    second = capsys.readouterr().out
    assert first == second


def test_v2_rejects_bool_integer_with_exit_two(tmp_path, capsys):
    data = _config()
    data["effective_stack"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    code = main(["solve-multistreet", str(path), "--algorithm", "vanilla-cfr", "--iterations", "5", "--json"])
    assert code == 2
    assert "JSON integer" in capsys.readouterr().err


def test_v2_rejects_old_internal_version(tmp_path, capsys):
    data = _config()
    data["version"] = "multistreet-v1"
    path = tmp_path / "bad-version.json"
    path.write_text(json.dumps(data))
    code = main(["solve-multistreet", str(path), "--algorithm", "vanilla-cfr", "--iterations", "5", "--json"])
    assert code == 2
    captured = capsys.readouterr()
    assert "version must be a JSON integer" in captured.err
