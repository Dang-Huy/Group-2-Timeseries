"""
Transform all quantile tail columns from _10/_90 -> _5/_95 for ALL variables,
plus the existing d_GoldDemand* / dlog_GoldDemand* handling.

OUTPUT COLUMNS (per variable that has tail cols):
  <var>_5   : base value where base <= rolling q5,  else 0
  <var>_95  : base value where base >= rolling q95 AND base > 0, else 0

GoldDemand is special: its base dlog is recomputed from raw Excel.
All other variables: base value is taken directly from the CSV base column.

Rolling parameters: window=252, min_periods=50, q_low=0.05, q_high=0.95

Source of truth for GoldDemand level:
  raw_data/Copy-of-Data-V0R2.xlsx  (Quaterly sheet, "Consumer demand_VN")
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────
EXCEL_PATH   = Path("raw_data/Copy-of-Data-V0R2.xlsx")
EXCEL_SHEET  = "Quaterly"
LEVEL_COL    = "Consumer demand_VN"

CSV_FILES = [
    "g2data_final.csv",
    "g2data_asymmetric_final.csv",
    "g2data_quantile_final.csv",
]

ROLLING_WINDOW      = 252
ROLLING_MIN_PERIODS = 50
QUANTILE_LOW        = 0.05
QUANTILE_HIGH       = 0.95

# ──────────────────────────────────────────────────────────────────
# COLUMN_RENAME_MAP
# Maps lowercased input column name -> canonical output name.
#
# Pattern for non-GoldDemand variables:
#   <var>_10  -> <var>_5
#   <var>_90  -> <var>_95
#
# Pattern for GoldDemand (base recomputed from Excel):
#   d_GoldDemand / dlog_GoldDemand         -> dlog_GoldDemand
#   d/dlog_GoldDemand_5  / _10             -> dlog_GoldDemand_5
#   d/dlog_GoldDemand_95 / _90             -> dlog_GoldDemand_95
#   d/dlog_GoldDemand_pos                  -> dlog_GoldDemand_pos
#   d/dlog_GoldDemand_neg                  -> dlog_GoldDemand_neg
# ──────────────────────────────────────────────────────────────────
COLUMN_RENAME_MAP = {
    # ── GoldDemand base ──────────────────────────────────────────
    "d_golddemand":            "dlog_GoldDemand",
    "dlog_golddemand":         "dlog_GoldDemand",

    # ── GoldDemand tail (accept old _10/_90 names too) ───────────
    "d_golddemand_5":          "dlog_GoldDemand_5",
    "dlog_golddemand_5":       "dlog_GoldDemand_5",
    "d_golddemand_10":         "dlog_GoldDemand_5",    # old alias
    "dlog_golddemand_10":      "dlog_GoldDemand_5",    # old alias

    "d_golddemand_95":         "dlog_GoldDemand_95",
    "dlog_golddemand_95":      "dlog_GoldDemand_95",
    "d_golddemand_90":         "dlog_GoldDemand_95",   # old alias
    "dlog_golddemand_90":      "dlog_GoldDemand_95",   # old alias

    # ── GoldDemand asymmetric ────────────────────────────────────
    "d_golddemand_pos":        "dlog_GoldDemand_pos",
    "dlog_golddemand_pos":     "dlog_GoldDemand_pos",
    "d_golddemand_neg":        "dlog_GoldDemand_neg",
    "dlog_golddemand_neg":     "dlog_GoldDemand_neg",

    # ── VNIndex ──────────────────────────────────────────────────
    "dlog_vnindex_10":         "dlog_VNIndex_5",
    "dlog_vnindex_90":         "dlog_VNIndex_95",
    "dlog_vnindex_5":          "dlog_VNIndex_5",        # idempotent
    "dlog_vnindex_95":         "dlog_VNIndex_95",       # idempotent

    # ── OilPrice ─────────────────────────────────────────────────
    "dlog_oilprice_10":        "dlog_OilPrice_5",
    "dlog_oilprice_90":        "dlog_OilPrice_95",
    "dlog_oilprice_5":         "dlog_OilPrice_5",
    "dlog_oilprice_95":        "dlog_OilPrice_95",

    # ── ExchangeRate ─────────────────────────────────────────────
    "dlog_exchangerate_10":    "dlog_ExchangeRate_5",
    "dlog_exchangerate_90":    "dlog_ExchangeRate_95",
    "dlog_exchangerate_5":     "dlog_ExchangeRate_5",
    "dlog_exchangerate_95":    "dlog_ExchangeRate_95",

    # ── CPI ──────────────────────────────────────────────────────
    "d_cpi_10":                "d_CPI_5",
    "d_cpi_90":                "d_CPI_95",
    "d_cpi_5":                 "d_CPI_5",
    "d_cpi_95":                "d_CPI_95",

    # ── Interest Rate ────────────────────────────────────────────
    "d_ir_10":                 "d_IR_5",
    "d_ir_90":                 "d_IR_95",
    "d_ir_5":                  "d_IR_5",
    "d_ir_95":                 "d_IR_95",

    # ── M2 ───────────────────────────────────────────────────────
    "dlog_m2_10":              "dlog_M2_5",
    "dlog_m2_90":              "dlog_M2_95",
    "dlog_m2_5":               "dlog_M2_5",
    "dlog_m2_95":              "dlog_M2_95",

    # ── GoldReserve ──────────────────────────────────────────────
    "dlog_goldreserve_10":     "dlog_GoldReserve_5",
    "dlog_goldreserve_90":     "dlog_GoldReserve_95",
    "dlog_goldreserve_5":      "dlog_GoldReserve_5",
    "dlog_goldreserve_95":     "dlog_GoldReserve_95",
}

# Which output names belong to the GoldDemand family
# (these columns need the Excel-recomputed dlog as base,
#  NOT the CSV's dlog_GoldDemand column)
GOLD_DEMAND_OUTPUT_NAMES = {
    "dlog_GoldDemand",
    "dlog_GoldDemand_5",
    "dlog_GoldDemand_95",
    "dlog_GoldDemand_pos",
    "dlog_GoldDemand_neg",
}


# ──────────────────────────────────────────────────────────────────
# Step 1 – Load GoldDemand level data from Excel, compute dlog
# ──────────────────────────────────────────────────────────────────
def load_dlog_from_excel(excel_path: Path, sheet: str) -> pd.Series:
    """
    Read quarterly GoldDemand levels, compute log-diff.
    Returns a Series indexed by quarter-start Timestamp.
    """
    q = pd.read_excel(excel_path, sheet_name=sheet)
    q = q.dropna(subset=["Period"])
    q = q.iloc[::-1].reset_index(drop=True)   # newest-first -> chronological

    level = q[LEVEL_COL].astype(float)
    if (level <= 0).any():
        bad = level[level <= 0]
        raise ValueError(
            f"'{LEVEL_COL}' has non-positive values at rows "
            f"{bad.index.tolist()} -> {bad.tolist()}"
        )

    dlog = np.log(level).diff()   # first entry is NaN by construction

    def _parse_quarter(s: str) -> pd.Timestamp:
        qtr, year = s.split("-")
        q_num = int(qtr[1])
        month = (q_num - 1) * 3 + 1
        return pd.Timestamp(int(year), month, 1)

    q["quarter_start"] = q["Period"].apply(_parse_quarter)
    return pd.Series(dlog.values, index=q["quarter_start"], name="dlog_GoldDemand")


# ──────────────────────────────────────────────────────────────────
# Step 2 – Compute rolling quantile arrays for ONE base series
# ──────────────────────────────────────────────────────────────────
def _rolling_quantiles(base_series: pd.Series):
    """Return (q5_array, q95_array) as numpy arrays."""
    q5 = base_series.rolling(
        window=ROLLING_WINDOW, min_periods=ROLLING_MIN_PERIODS
    ).quantile(QUANTILE_LOW).values
    q95 = base_series.rolling(
        window=ROLLING_WINDOW, min_periods=ROLLING_MIN_PERIODS
    ).quantile(QUANTILE_HIGH).values
    return q5, q95


# ──────────────────────────────────────────────────────────────────
# Step 3 – Compute final column values given base and output name
# ──────────────────────────────────────────────────────────────────
def _compute_values(
    new_name: str,
    base_dlog: np.ndarray,
    q5: np.ndarray,
    q95: np.ndarray,
) -> np.ndarray:
    """
    Apply the tail/asymmetric filter to produce the final array.

    Rules (same for ALL variables):
      _pos : base where base > 0,  else 0
      _neg : base where base < 0,  else 0
      _5   : base where base <= q5, else 0
      _95  : base where base >= q95 AND base > 0, else 0
      plain: base as-is
    """
    if new_name.endswith("_pos"):
        return np.where(base_dlog > 0, base_dlog, 0.0)
    elif new_name.endswith("_neg"):
        return np.where(base_dlog < 0, base_dlog, 0.0)
    elif new_name.endswith("_5"):
        return np.where(base_dlog <= q5, base_dlog, 0.0)
    elif new_name.endswith("_95"):
        return np.where((base_dlog >= q95) & (base_dlog > 0), base_dlog, 0.0)
    else:
        return base_dlog


# ──────────────────────────────────────────────────────────────────
# Step 4 – Transform one CSV file
# ──────────────────────────────────────────────────────────────────
def transform_csv(csv_path: str, dlog_quarterly: pd.Series) -> None:
    df = pd.read_csv(csv_path)
    dates = pd.to_datetime(df["date"])

    # ── Find columns to process ────────────────────────────────
    cols_to_process = [
        col for col in df.columns
        if col.strip().lower() in COLUMN_RENAME_MAP
    ]
    if not cols_to_process:
        print(f"[SKIP] {csv_path} — no matching columns found.")
        return

    # ── Align GoldDemand dlog to CSV dates (quarterly mapping) ─
    quarter_starts = dates.dt.to_period("Q").dt.to_timestamp()
    gold_base_dlog = quarter_starts.map(dlog_quarterly).values  # shape (N,)

    # ── Pre-compute rolling quantiles for GoldDemand once ──────
    gold_q5, gold_q95 = _rolling_quantiles(
        pd.Series(gold_base_dlog, index=dates)
    )

    # ── Cache of (q5, q95) per non-Gold base column ────────────
    # Keyed by the base column name (without suffix).
    _quantile_cache: dict[str, tuple] = {}

    def _get_non_gold_base(new_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        For non-GoldDemand columns, infer the base column name and return
        (base_dlog, q5, q95).
        """
        # Strip suffix to find base column: e.g. "dlog_VNIndex_5" -> "dlog_VNIndex"
        for suffix in ("_pos", "_neg", "_5", "_95"):
            if new_name.endswith(suffix):
                base_col_name = new_name[: -len(suffix)]
                break
        else:
            base_col_name = new_name   # plain column

        if base_col_name not in df.columns:
            raise KeyError(
                f"Cannot find base column '{base_col_name}' in CSV for '{new_name}'. "
                f"Available columns: {list(df.columns)}"
            )

        base_arr = df[base_col_name].values.astype(float)

        if base_col_name not in _quantile_cache:
            q5, q95 = _rolling_quantiles(pd.Series(base_arr, index=dates))
            _quantile_cache[base_col_name] = (q5, q95)

        q5, q95 = _quantile_cache[base_col_name]
        return base_arr, q5, q95

    # ── Process each column in-place (preserve order) ──────────
    replacements = []

    for col in cols_to_process:
        new_name = COLUMN_RENAME_MAP[col.strip().lower()]
        col_pos  = list(df.columns).index(col)

        # Choose base series
        if new_name in GOLD_DEMAND_OUTPUT_NAMES:
            base_dlog = gold_base_dlog
            q5, q95   = gold_q5, gold_q95
        else:
            base_dlog, q5, q95 = _get_non_gold_base(new_name)

        final_values = _compute_values(new_name, base_dlog, q5, q95)

        df = df.drop(columns=[col])
        df.insert(col_pos, new_name, final_values)
        replacements.append((col, new_name))

    # ── Drop rows where ANY GoldDemand column is NaN ───────────
    gold_cols   = [c for c in df.columns if c.startswith("dlog_GoldDemand")]
    before_drop = len(df)
    df = df.dropna(subset=gold_cols, how="any")
    dropped = before_drop - len(df)
    if dropped:
        print(f"  Dropped {dropped} row(s) with NaN in GoldDemand columns.")

    # ── Sanity checks ──────────────────────────────────────────
    _sanity_check(df, csv_path)

    df.to_csv(csv_path, index=False)

    print(f"[OK] {csv_path}")
    for old, new in replacements:
        print(f"     {old!r:35s} -> {new!r}")
    print("-" * 60)


# ──────────────────────────────────────────────────────────────────
# Sanity checks
# ──────────────────────────────────────────────────────────────────
def _sanity_check(df: pd.DataFrame, label: str) -> None:
    """
    For every (base, tail) pair in the dataframe:
      - non-zero values of tail must equal base exactly
      - sign constraint for _pos / _neg
      - pos/neg correlation guard for GoldDemand
    """
    # Collect all (base_col, tail_col, suffix) triples
    pairs = []
    for col in df.columns:
        for suffix in ("_pos", "_neg", "_5", "_95"):
            if col.endswith(suffix):
                base_name = col[: -len(suffix)]
                if base_name in df.columns:
                    pairs.append((base_name, col, suffix))

    for base_name, tail_col, suffix in pairs:
        base = df[base_name].values
        tail = df[tail_col].values
        nonzero_mask = tail != 0
        nonzero_tail = tail[nonzero_mask]
        nonzero_base = base[nonzero_mask]

        if len(nonzero_tail) == 0:
            print(f"  [WARN] {tail_col}: all zeros — check rolling window / data range!")
            continue

        if not np.allclose(nonzero_tail, nonzero_base):
            print(f"  [WARN] {tail_col}: non-zero values do not match base '{base_name}'!")

        if suffix == "_pos" and (nonzero_tail < 0).any():
            print(f"  [WARN] {tail_col}: contains negative values!")
        if suffix == "_neg" and (nonzero_tail > 0).any():
            print(f"  [WARN] {tail_col}: contains positive values!")

    # pos/neg correlation guard (GoldDemand)
    pos_col = "dlog_GoldDemand_pos"
    neg_col = "dlog_GoldDemand_neg"
    if pos_col in df.columns and neg_col in df.columns:
        corr = df[pos_col].corr(df[neg_col])
        tag  = "OK" if abs(corr) <= 0.9 else "too high!"
        print(f"  [INFO] GoldDemand pos/neg corr = {corr:.4f} ({tag})")


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("Loading GoldDemand level data from Excel...")
    dlog_quarterly = load_dlog_from_excel(EXCEL_PATH, EXCEL_SHEET)
    print(f"  Quarters loaded : {len(dlog_quarterly)}")
    print(f"  Range           : {dlog_quarterly.index.min().date()} -> "
          f"{dlog_quarterly.index.max().date()}")
    print(f"  NaN count       : {dlog_quarterly.isna().sum()} (first row expected)")
    print("=" * 60)
    print()

    for csv_file in CSV_FILES:
        csv_path = Path(csv_file)
        if not csv_path.exists():
            print(f"[WARN] {csv_file} not found, skipping.")
            continue
        transform_csv(str(csv_path), dlog_quarterly)

    print()
    print("=" * 60)
    print("Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()