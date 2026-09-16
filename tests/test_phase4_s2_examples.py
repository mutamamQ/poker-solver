"""Permanent S2-I2 examples and generic CLI RED suite.

I203 exclusive owner. Tests canonical synthetic 4/5/9-player direct-request JSON examples
and generic CLI file/stdin/error behavior through existing `phase4 REQUEST --json` path.

Credible RED: absent examples at examples/phase4/nplayer_{4p,5p,9p}_flop.json.
Not malformed schema, placeholders, skips, or caught exceptions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

def test_phase4_nplayer_4p_example_file():
    """4-player canonical example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_4p_flop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-nplayer-postflop"
    assert data["game_version"] == "nplayer-postflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 4
    assert "metadata" in data


def test_phase4_nplayer_5p_example_file():
    """5-player canonical example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_5p_flop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-nplayer-postflop"
    assert data["game_version"] == "nplayer-postflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 5
    assert "metadata" in data


def test_phase4_nplayer_9p_example_file():
    """9-player canonical example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_9p_flop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-nplayer-postflop"
    assert data["game_version"] == "nplayer-postflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 9
    assert "metadata" in data


def test_phase4_stdin_execution():
    """Generic stdin path `phase4 - --json` executes 4p example."""
    example_path = Path("examples/phase4/nplayer_4p_flop.json")
    request_json = example_path.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "-", "--json"],
        input=request_json,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-nplayer-postflop"
    assert len(data["values"]) == 4


def test_phase4_missing_file_error():
    """Missing file path returns exit code 2 with error message."""
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "nonexistent.json", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_phase4_malformed_json_error():
    """Malformed JSON returns exit code 2 with error message."""
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "-", "--json"],
        input="{invalid json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_phase4_s1_control_stays_green():
    """Existing S1 phase4 request remains operational (green control)."""
    example_path = Path("examples/phase4_s1_flop.json")
    assert example_path.is_file(), "tracked S1 compatibility fixture must remain present"
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"phase4 S1 control failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-allstreet-postflop"
