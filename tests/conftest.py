"""Session-wide test isolation for practice mode (persistent cache + progress store)."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="practice-tests-")
os.environ.setdefault("POKER_PRACTICE_CACHE_DIR", os.path.join(_TMP, "cache"))
os.environ.setdefault("POKER_PRACTICE_DATA_DIR", os.path.join(_TMP, "data"))
