import os
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CATEGORICAL_FEATURES = ["site_id", "equipment_type"]
EXCLUDED_FEATURES = ["target_next_week_demand", "week_start", "data_split"]


def load_and_prepare_datasets() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load base and enhanced feature datasets.
    Align data_split onto base dataset by matching (week_start, site_id, equipment_type).
    Validate row counts, keys, and target equality.
    """
    base_csv = BACKEND_DIR / "ml" / "generated" / "base_model_features.csv"
    enhanced_csv = BACKEND_DIR / "ml" / "generated" / "enhanced_model_features.csv"

    if not base_csv.exists():
        raise FileNotFoundError(f"Base feature table missing at {base_csv}")
    if not enhanced_csv.exists():
        raise FileNotFoundError(f"Enhanced feature table missing at {enhanced_csv}")

    df_base = pd.read_csv(base_csv)
    df_enhanced = pd.read_csv(enhanced_csv)

    # Ensure week_start is string or date formatted consistently
    df_base["week_start"] = pd.to_datetime(df_base["week_start"]).dt.strftime("%Y-%m-%d")
    df_enhanced["week_start"] = pd.to_datetime(df_enhanced["week_start"]).dt.strftime("%Y-%m-%d")

    # Match data_split onto base feature table if missing
    if "data_split" not in df_base.columns:
        split_map = df_enhanced.set_index(["week_start", "site_id", "equipment_type"])["data_split"].to_dict()
        df_base["data_split"] = df_base.set_index(["week_start", "site_id", "equipment_type"]).index.map(split_map)

    # Validation Checks
    assert len(df_base) == len(df_enhanced), f"Row count mismatch! Base={len(df_base)}, Enhanced={len(df_enhanced)}"
    assert len(df_base) == 6180, f"Expected 6,180 rows, got {len(df_base)}"

    base_keys = list(zip(df_base["week_start"], df_base["site_id"], df_base["equipment_type"]))
    enhanced_keys = list(zip(df_enhanced["week_start"], df_enhanced["site_id"], df_enhanced["equipment_type"]))
    assert base_keys == enhanced_keys, "Modelling keys order mismatch between base and enhanced datasets!"

    assert (df_base["target_next_week_demand"].values == df_enhanced["target_next_week_demand"].values).all(), \
        "Target values mismatch between base and enhanced datasets!"

    print("[MODEL UTILS] Datasets loaded and validated successfully.")
    print(f"  - Total Modelling Rows : {len(df_base)}")
    print(f"  - Base Features Count  : {len(get_feature_names(df_base))}")
    print(f"  - Enhanced Features Count: {len(get_feature_names(df_enhanced))}")

    return df_base, df_enhanced


def get_feature_names(df: pd.DataFrame) -> List[str]:
    """Get candidate model feature names excluding target, date, and split columns."""
    return [c for c in df.columns if c not in EXCLUDED_FEATURES]


def prepare_feature_matrix(
    df: pd.DataFrame,
    feature_names: List[str]
) -> Tuple[pd.DataFrame, np.ndarray, List[str], List[str]]:
    """
    Extract X, y, categorical feature names, and numeric feature names.
    Validate there are no unsupported object columns.
    """
    X = df[feature_names].copy()
    y = df["target_next_week_demand"].values.astype(int)

    cat_cols = [c for c in feature_names if c in CATEGORICAL_FEATURES]
    num_cols = [c for c in feature_names if c not in CATEGORICAL_FEATURES]

    # Ensure object dtypes exist only in declared categorical columns
    object_cols = X.select_dtypes(include=["object"]).columns.tolist()
    unsupported_obj_cols = [c for c in object_cols if c not in CATEGORICAL_FEATURES]
    assert len(unsupported_obj_cols) == 0, f"Unsupported object columns found in feature matrix: {unsupported_obj_cols}"

    # Convert numeric columns explicitly
    for c in num_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    for c in cat_cols:
        X[c] = X[c].astype(str)

    return X, y, cat_cols, num_cols
