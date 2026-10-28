"""
Synthetic merchant generator CLI.

Usage:
    python -m evals.generate_merchants --count 10 --seed 42
    python -m evals.generate_merchants --count 5 --seed 1 --output merchants.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without the package installed
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sme_copilot.services.merchant_generator import MerchantGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic merchants with known true revenue and planted problems."
    )
    parser.add_argument("--count", type=int, default=10, help="Number of merchants to generate")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON to this file instead of stdout",
    )
    args = parser.parse_args()

    gen = MerchantGenerator(seed=args.seed)
    merchants = gen.generate(count=args.count)

    records = []
    for m in merchants:
        records.append(
            {
                "merchant_id": m.merchant_id,
                "name": m.name,
                "true_revenue": m.true_revenue,
                "planted_problems": [p.value for p in m.planted_problems],
            }
        )

    payload = json.dumps(records, indent=2)

    if args.output:
        Path(args.output).write_text(payload)
        print(f"Wrote {len(records)} merchants to {args.output}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
