"""W6 re-audit UI repairs (N1 shortcut trap, N2 raw feedback tokens, N3 silent not-recorded)."""
from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")


def _onkey_body() -> str:
    start = APP.index("function onKey(ev)")
    return APP[start:APP.index("function init()", start)]


def test_n1_shortcuts_not_swallowed_in_size_box():
    body = _onkey_body()
    # The early return for typing targets must exempt shortcut keys inside #action-size,
    # otherwise B (which focuses #action-size) traps every later F/C/B press.
    assert "if (typing) return;" not in body
    assert 'ev.target.id === "action-size"' in body
    assert "KEY_KINDS, k" in body


def test_n2_feedback_tokens_humanized_display_only():
    i = APP.index('var fb = $("feedback-text");')
    seg = APP[i:i + 600]
    assert "score.feedback" in seg and ".replace(" in seg and "kindLabel(kind)" in seg
    assert "innerHTML" not in seg


def test_n3_not_recorded_notice_only_for_override_null_progress():
    i = APP.index("Not recorded in progress")
    seg = APP[i - 200:i]
    assert "override && res.progress === null" in seg
