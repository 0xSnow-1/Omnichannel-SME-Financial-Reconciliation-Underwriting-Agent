import math


def calculate_pass_at_k(n: int, c: int, k: int) -> float:
    """Calculate pass@k using the unbiased estimator from HumanEval / Anthropic evals.

    Formula: 1 - comb(n - c, k) / comb(n, k)
    If n - c < k, returns 1.0.
    """
    if n <= 0 or k <= 0 or k > n:
        return 1.0 if c > 0 else 0.0
    if n - c < k:
        return 1.0
    try:
        prob_all_fail = math.comb(n - c, k) / math.comb(n, k)
        return round(1.0 - prob_all_fail, 4)
    except Exception:
        return round(c / n, 4)


def calculate_pass_pow_k(single_run_pass_rate: float, k: int) -> float:
    """Calculate pass^k (probability of passing all k consecutive attempts).

    Formula: (pass_rate) ** k
    """
    if k <= 0:
        return 1.0
    clamped = max(0.0, min(1.0, single_run_pass_rate))
    return round(clamped**k, 4)
