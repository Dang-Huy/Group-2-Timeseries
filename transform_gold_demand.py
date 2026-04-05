"""
Transform all d_GoldDemand* columns -> dlog_GoldDemand* across CSV datasets.

Source of truth: raw_data/Copy-of-Data-V0R2.xlsx (Quaterly sheet, "Consumer demand_VN")
Computes: dlog_GoldDemand = log(GoldDemand).diff()

Handles:
  d_GoldDemand       -> dlog_GoldDemand
  d_GoldDemand_10    -> dlog_GoldDemand_10   (same dlog values)
  d_GoldDemand_90    -> dlog_GoldDemand_90   (same dlog values)
  d_GoldDemand_pos   -> dlog_GoldDemand_pos  (same dlog values)
  d_GoldDemand_neg   -> dlog_GoldDemand_neg  (same dlog values)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────
EXCEL_PATH = Path("raw_data/Copy-of-Data-V0R2.xlsx")
EXCEL_SHEET = "Quaterly"

CSV_FILES = [
    "g2data_final.csv",
    "g2data_asymmetric_final.csv",
    "g2data_quantile_final.csv",
]

# Case-insensitive aliases for finding the GoldDemand level column in Excel
GOLD_DEMAND_ALIASES = {
    "golddemand", "gold_demand", "consumer demand_vn",
    "consumerdemand_vn", "consumer_demand_vn",
}

# Mapping: old column name (case-insensitive) -> new column name
# All suffixed variants get the SAME dlog values, just different names.
COLUMN_RENAME_MAP = {
    "d_golddemand":     "dlog_GoldDemand",
    "d_golddemand_10":  "dlog_GoldDemand_10",
    "d_golddemand_90":  "dlog_GoldDemand_90",
    "d_golddemand_pos": "dlog_GoldDemand_pos",
    "d_golddemand_neg": "dlog_GoldDemand_neg",
}


# ──────────────────────────────────────────────────────────────────
# Helper: find column by case-insensitive alias set
# ──────────────────────────────────────────────────────────────────
def find_column(columns: pd.Index, aliases: set) -> str:
    """Return the original column name matching any alias (case-insensitive)."""
    for col in columns:
        normalised = col.strip().lower().replace(" ", "_")
        if normalised in aliases:
            return col
    raise KeyError(
        f"None of the expected aliases {aliases} found in columns: {list(columns)}"
    )


# ──────────────────────────────────────────────────────────────────
# Step 1 - Load level data from Excel and compute dlog diff
# ──────────────────────────────────────────────────────────────────
def load_dlog_from_excel(excel_path: Path, sheet: str) -> pd.Series:
    """
    Read quarterly GoldDemand level data, compute log-diff,
    return a Series indexed by quarter-start timestamp.
    """
    q = pd.read_excel(excel_path, sheet_name=sheet)
    q = q.dropna(subset=["Period"])

    # Data is newest-first; reverse to chronological
    q = q.iloc[::-1].reset_index(drop=True)

    # Find the GoldDemand level column
    level_col = find_column(q.columns, GOLD_DEMAND_ALIASES)
    level = q[level_col].astype(float)

    # Validate: all values must be > 0 for log
    if (level <= 0).any():
        bad = level[level <= 0]
        raise ValueError(
            f"GoldDemand contains non-positive values at rows: "
            f"{bad.index.tolist()} -> {bad.tolist()}"
        )

    # Vectorised: dlog = log(level).diff()
    dlog = np.log(level).diff()

    # Parse quarter periods -> quarter-start timestamps
    def _parse_quarter(s: str) -> pd.Timestamp:
        qtr, year = s.split("-")
        q_num = int(qtr[1])
        month = (q_num - 1) * 3 + 1
        return pd.Timestamp(int(year), month, 1)

    q["quarter_start"] = q["Period"].apply(_parse_quarter)

    result = pd.Series(dlog.values, index=q["quarter_start"], name="dlog_GoldDemand")
    return result


# ──────────────────────────────────────────────────────────────────
# Step 2 - Transform each CSV
# ──────────────────────────────────────────────────────────────────
def transform_csv(csv_path: str, dlog_quarterly: pd.Series) -> None:
    """
    Load CSV, replace all d_GoldDemand* columns with dlog_GoldDemand*,
    and save back in-place.
    """
    df = pd.read_csv(csv_path)
    original_rows = len(df)

    # Build daily dlog series by mapping dates -> quarters
    dates = pd.to_datetime(df["date"])
    quarter_starts = dates.dt.to_period("Q").dt.to_timestamp()
    dlog_daily = quarter_starts.map(dlog_quarterly).values

    # Find all d_GoldDemand* columns and replace them
    replacements = []
    for col in list(df.columns):
        col_lower = col.strip().lower()
        if col_lower in COLUMN_RENAME_MAP:
            new_name = COLUMN_RENAME_MAP[col_lower]
            col_pos = list(df.columns).index(col)

            # Drop old column, insert new at same position
            df = df.drop(columns=[col])
            df.insert(col_pos, new_name, dlog_daily)

            replacements.append((col, new_name))

    if not replacements:
        print(f"File: {csv_path}")
        print("  No d_GoldDemand* columns found, skipping.")
        print()
        return

    # Validations
    assert len(df) == original_rows, f"Row count changed in {csv_path}!"

    # No inf values in any new column
    for _, new_name in replacements:
        series = df[new_name]
        assert not np.isinf(series.dropna()).any(), f"inf in {new_name} of {csv_path}!"

    # No old d_GoldDemand* columns remain
    for col in df.columns:
        assert col.strip().lower() not in COLUMN_RENAME_MAP, (
            f"Old column {col} still present in {csv_path}!"
        )

    # Save
    df.to_csv(csv_path, index=False)

    # Summary
    print(f"File: {csv_path}")
    print("Replaced:")
    for old, new in replacements:
        print(f"  * {old} -> {new}")
    nan_count = df[replacements[0][1]].isna().sum()
    print(f"Rows: {len(df)}")
    print(f"NaNs: {nan_count}")
    print()


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Loading GoldDemand level data from Excel...")
    print("=" * 60)

    dlog_quarterly = load_dlog_from_excel(EXCEL_PATH, EXCEL_SHEET)

    print(f"Quarterly periods loaded: {len(dlog_quarterly)}")
    print(f"Range: {dlog_quarterly.index.min()} -> {dlog_quarterly.index.max()}")
    print(f"dlog NaN count (first value): {dlog_quarterly.isna().sum()}")
    print()

    for csv_file in CSV_FILES:
        csv_path = Path(csv_file)
        if not csv_path.exists():
            print(f"WARNING: {csv_file} not found, skipping.")
            continue
        transform_csv(str(csv_path), dlog_quarterly)

    print("=" * 60)
    print("All files transformed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
