"""Export processed financial data to CSV files.

This script uses src.data_loader, which already normalizes monetary fields to USD
for income statements and cash flows.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import (
    load_income_statements,
    load_cash_flows,
    load_ratios,
    load_stock_prices,
)


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "income_statements_usd.csv": load_income_statements.__wrapped__(),
        "cash_flows_usd.csv": load_cash_flows.__wrapped__(),
        "ratios.csv": load_ratios.__wrapped__(),
        "stock_prices.csv": load_stock_prices.__wrapped__(),
    }

    for filename, df in datasets.items():
        path = output_dir / filename
        df.to_csv(path, index=False)
        print(f"Wrote {path} ({len(df)} rows)")

    print("Done.")


if __name__ == "__main__":
    main()
