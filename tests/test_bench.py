from rampart.bench.core import column, leaderboard, score_verifier
from rampart.rollout.dataset import Rollout


def _r(tid: str, rn: int, rh: int, to: int) -> Rollout:
    return Rollout(task_id=tid, model="m", completion="x", r_naive=rn, r_hardened=rh, t_oracle=to)


def test_naive_leaks_exploits_hardened_catches_them():
    rows = [
        _r("a", 1, 1, 1),  # honest solve
        _r("b", 1, 0, 0),  # cheat: naive accepts, hardened rejects
        _r("c", 1, 0, 0),  # cheat
        _r("d", 0, 0, 0),  # plain wrong: both reject
    ]
    naive, hardened = leaderboard(rows)
    assert naive.n_exploits == 3  # b, c, d are oracle-wrong
    assert abs(naive.catch_rate - 1 / 3) < 1e-9  # rejects only d
    assert naive.false_accept > hardened.false_accept
    assert hardened.catch_rate == 1.0  # rejects b, c, d
    assert naive.honest_pass == 1.0 and hardened.honest_pass == 1.0  # both keep the gold solve


def test_custom_verdict_plugs_in():
    rows = [_r("a", 1, 1, 1), _r("b", 1, 0, 0)]
    reject_all = score_verifier(rows, lambda r: 0, name="reject_all")
    assert reject_all.catch_rate == 1.0 and reject_all.honest_pass == 0.0
    accept_all = score_verifier(rows, lambda r: 1, name="accept_all")
    assert accept_all.catch_rate == 0.0 and accept_all.honest_pass == 1.0


def test_column_reads_reward():
    r = _r("a", 1, 0, 0)
    assert column("r_naive")(r) == 1 and column("r_hardened")(r) == 0
