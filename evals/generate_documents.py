"""
Synthetic document generator for SME underwriting evaluation.
Generates realistic CSV bank statements, e-wallet transaction exports, and platform sales reports
with ground-truth labels and planted discrepancies.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sme_copilot.schemas.models import ProblemType


def generate_merchant_dataset(
    merchant_id: str,
    name: str,
    true_revenue: float,
    planted_problems: list[ProblemType],
    output_dir: Path,
    seed: int | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_date = datetime(2024, 1, 1)
    num_txns = rng.randint(8, 15)

    # 1. Bank Statement
    bank_csv = output_dir / "bank_statement.csv"
    balance = round(rng.uniform(10000, 30000), 2)
    bank_rows = [["Date", "Description", "Amount", "Balance"]]
    txns_data = []

    mismatch_injected = False
    for i in range(num_txns):
        dt = (base_date + timedelta(days=i * 2)).strftime("%Y-%m-%d")
        is_deposit = rng.random() > 0.35
        amt = round(rng.uniform(1000, 15000), 2)
        if not is_deposit:
            amt = -amt

        # Check planted discrepancies
        if ProblemType.DEPOSIT_SPIKE in planted_problems and i == num_txns // 2:
            amt = 250000.0  # Massive spike
            desc = "Unusual Cash Infusion"
        elif ProblemType.INFLATED_REVENUE in planted_problems and i == 3:
            amt = round(true_revenue * 0.8, 2)
            desc = "Bulk Inventory Advance"
        elif is_deposit:
            desc = rng.choice(["Customer Direct Deposit", "Merchant Payout", "Store Inflow"])
        else:
            desc = rng.choice(["Supplier Payment", "Utility Bill", "Commercial Lease"])

        balance = round(balance + amt, 2)

        # Plant running balance arithmetic tampering if specified
        if ProblemType.HIDDEN_FEE in planted_problems and not mismatch_injected and i == 4:
            # Plant mismatch (tampered ending balance)
            balance = round(balance - 500.0, 2)
            mismatch_injected = True

        bank_rows.append([dt, desc, f"{amt:.2f}", f"{balance:.2f}"])
        txns_data.append({"date": dt, "description": desc, "amount": amt, "balance": balance})

    with open(bank_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(bank_rows)

    # 2. E-Wallet Export (GCash / Maya)
    ewallet_csv = output_dir / "ewallet_export.csv"
    ewallet_rows = [["Date", "Reference_ID", "Type", "Amount", "Fee", "Balance"]]
    ewallet_bal = 5000.0
    for j in range(5):
        dt = (base_date + timedelta(days=j * 3)).strftime("%Y-%m-%d")
        ref = f"GC-{rng.randint(100000, 999999)}"
        amt = round(rng.uniform(200, 3000), 2)
        fee = 15.0 if amt > 1000 else 0.0
        ewallet_bal = round(ewallet_bal + amt - fee, 2)
        ewallet_rows.append(
            [dt, ref, "QR Payment", f"{amt:.2f}", f"{fee:.2f}", f"{ewallet_bal:.2f}"]
        )

    with open(ewallet_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(ewallet_rows)

    # 3. Ground truth JSON
    ground_truth = {
        "merchant_id": merchant_id,
        "name": name,
        "true_revenue": true_revenue,
        "planted_problems": [p.value for p in planted_problems],
        "total_bank_transactions": len(txns_data),
        "bank_ending_balance": balance,
        "has_arithmetic_mismatch": mismatch_injected,
    }

    gt_file = output_dir / "ground_truth.json"
    gt_file.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")

    return ground_truth
