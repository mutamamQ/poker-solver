import json
import subprocess
import sys

from poker_solver.cli import main


def spot_config():
    return {
        "version": 1,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2,
        "stack": 1,
        "bet": 1,
        "range0": [
            {"cards": ["As", "5s"], "weight": 1},
            {"cards": ["Qs", "Js"], "weight": 1},
        ],
        "range1": [
            {"cards": ["Kh", "Qh"], "weight": 1},
            {"cards": ["9h", "8h"], "weight": 1},
        ],
    }


def test_evaluate_json_and_error(capsys):
    assert main(["evaluate", "As", "Ks", "Qs", "Js", "Ts", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["category"] == "straight-flush"
    assert main(["evaluate", "As"]) == 2
    assert "error:" in capsys.readouterr().err


def test_equity_json_exact_counts_and_determinism(capsys):
    args = ["equity", "--hero", "As,Ah", "--villain", "Ks,Kh", "--board", "2c,3d,4h,8s,9c", "--json"]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out
    assert first == second
    assert json.loads(first)["total"] == 1


def test_solve_kuhn_json(capsys):
    assert main(["solve-kuhn", "--iterations", "1000", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["algorithm"] == "vanilla-cfr"
    assert data["nash_conv"] >= 0


def test_solve_spot_json(tmp_path, capsys):
    path = tmp_path / "spot.json"
    path.write_text(json.dumps(spot_config()))
    assert main(["solve-spot", str(path), "--iterations", "1000", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["nash_conv"] >= 0
    assert abs(sum(data["values"])) < 1e-10


def test_module_subprocess_smoke():
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "evaluate", "As", "Ks", "Qs", "Js", "Ts", "--json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["category"] == "straight-flush"


def test_spot_numeric_schema_is_strict(tmp_path, capsys):
    config = spot_config()
    config["stack"] = True
    path = tmp_path / "bad-number.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--iterations", "1", "--json"]) == 2
    assert "stack must be a JSON integer" in capsys.readouterr().err

    config = spot_config()
    config["range0"][0]["weight"] = "1.0"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--iterations", "1", "--json"]) == 2
    assert "combo weight must be a JSON number" in capsys.readouterr().err


def test_kuhn_cli_is_byte_deterministic(capsys):
    args = ["solve-kuhn", "--iterations", "100", "--json"]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out
    assert first == second
