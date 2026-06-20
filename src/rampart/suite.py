"""Score a solution against a set of gold-labeled (input -> expected) cases, sandboxed.

Builds a fresh dir with the solution and a generated case suite, then runs it through the
shared sandbox. Used to score solutions under a (possibly hardened) grader.
"""

import shutil
import tempfile
from pathlib import Path

from .sandbox import DEFAULT_MEM_MB, DEFAULT_TIMEOUT, run_suite


def score_solution(
    entry_point: str,
    solution_src: str,
    cases,
    timeout: float = DEFAULT_TIMEOUT,
    mem_mb: int = DEFAULT_MEM_MB,
) -> int:
    """Return 1 iff `solution_src` matches the expected output on every case (else 0)."""
    scoring_dir = Path(tempfile.mkdtemp(prefix="rampart_score_"))
    try:
        (scoring_dir / "solution.py").write_text(solution_src)
        (scoring_dir / "test_cases.py").write_text(_render_cases(entry_point, cases))
        return run_suite(scoring_dir, "test_cases.py", timeout, mem_mb)
    finally:
        shutil.rmtree(scoring_dir, ignore_errors=True)


def _render_cases(entry_point: str, cases) -> str:
    lines = [f"from solution import {entry_point} as _fn", "", "CASES = ["]
    for args, expected in cases:
        lines.append(f"    ({tuple(args)!r}, {expected!r}),")
    lines += [
        "]",
        "",
        "",
        "def test_cases():",
        "    for args, expected in CASES:",
        "        assert _fn(*args) == expected, args",
        "",
    ]
    return "\n".join(lines)
