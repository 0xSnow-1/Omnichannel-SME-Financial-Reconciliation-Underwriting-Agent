import random

from sme_copilot.schemas.models import Merchant, ProblemType


class MerchantGenerator:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(
        self,
        count: int = 10,
        problem_types: list[ProblemType] | None = None,
        problems_per_merchant: tuple[int, int] = (1, 3),
    ) -> list[Merchant]:
        if problem_types is None:
            problem_types = list(ProblemType)

        merchants: list[Merchant] = []
        for i in range(count):
            name = f"Merchant-{i + 1:03d}"
            true_revenue = round(self._rng.uniform(50000, 500000), 2)
            n_problems = self._rng.randint(*problems_per_merchant)
            problems = self._rng.sample(problem_types, min(n_problems, len(problem_types)))
            merchants.append(
                Merchant(
                    name=name,
                    true_revenue=true_revenue,
                    planted_problems=problems,
                )
            )
        return merchants
