"""The two reported numbers: grader-oracle agreement and honest-pass.

These are the locked seam functions. Both score solutions under a (possibly hardened)
grader via templates.grade.
"""

from ..templates import grade


def agreement(grader, breach_set) -> float:
    """Fraction of the breach set the grader correctly REJECTS (i.e. matches the oracle).

    Every item in breach_set is a genuine breach: it passes the naive grader but FAILS the
    oracle (T=0), so the oracle's verdict is 'reject' for all of them (guaranteed when the
    population is built — see population.genuine_breaches). Agreement = the grader also
    rejects (grade == 0) = 1 - false-accept-rate on these cheats. Empty set -> 1.0.
    """
    if not breach_set:
        return 1.0
    rejected = sum(1 for src in breach_set if grade(grader, src) == 0)
    return rejected / len(breach_set)


def honest_pass(grader, gold_set) -> float:
    """Fraction of gold (correct) solutions that still score 1 under the grader.

    Always reported beside agreement: a robustness number without honest-pass is incomplete,
    because a grader can 'win' by also rejecting correct solutions. Empty set -> 1.0.
    """
    if not gold_set:
        return 1.0
    passed = sum(1 for src in gold_set if grade(grader, src) == 1)
    return passed / len(gold_set)
