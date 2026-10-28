from sme_copilot.services.merchant_generator import MerchantGenerator


def test_generates_correct_count():
    gen = MerchantGenerator(seed=42)
    merchants = gen.generate(count=10)
    assert len(merchants) == 10


def test_true_revenue_present():
    gen = MerchantGenerator(seed=42)
    merchants = gen.generate(count=5)
    for m in merchants:
        assert m.true_revenue > 0


def test_planted_problems_in_range():
    gen = MerchantGenerator(seed=42)
    merchants = gen.generate(count=5, problems_per_merchant=(1, 3))
    for m in merchants:
        assert 1 <= len(m.planted_problems) <= 3


def test_deterministic_with_seed():
    gen1 = MerchantGenerator(seed=42)
    gen2 = MerchantGenerator(seed=42)
    m1 = gen1.generate(count=5)
    m2 = gen2.generate(count=5)
    assert [m.true_revenue for m in m1] == [m.true_revenue for m in m2]
