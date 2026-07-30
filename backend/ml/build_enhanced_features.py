import os
import sys
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.association_features import mine_fp_growth_rules, compute_row_association_features
from ml.transition_features import learn_transition_probabilities, compute_row_transition_features


def build_enhanced_feature_dataset():
    print("=================================================================")
    print("  CATERPILLAR DEMAND FORECASTING - ENHANCED FEATURE GENERATOR   ")
    print("=================================================================\n")

    base_csv = BACKEND_DIR / "ml" / "generated" / "base_model_features.csv"
    if not base_csv.exists():
        raise FileNotFoundError(f"Base feature table not found at {base_csv}. Run 'python -m ml.feature_engineering' first.")

    df_base = pd.read_csv(base_csv)
    df_base["week_start"] = pd.to_datetime(df_base["week_start"]).dt.date

    # ─────────────────────────────────────────────────────────────
    # 1. CHRONOLOGICAL DATA SPLIT (70% train / 15% val / 15% test)
    # ─────────────────────────────────────────────────────────────
    distinct_weeks = sorted(list(set(df_base["week_start"])))
    n_weeks = len(distinct_weeks)

    n_train = int(n_weeks * 0.70)
    n_val = int(n_weeks * 0.15)
    n_test = n_weeks - n_train - n_val

    train_weeks = set(distinct_weeks[:n_train])
    val_weeks = set(distinct_weeks[n_train:n_train + n_val])
    test_weeks = set(distinct_weeks[n_train + n_val:])

    def get_split(w):
        if w in train_weeks:
            return "train"
        elif w in val_weeks:
            return "validation"
        else:
            return "test"

    df_base["data_split"] = df_base["week_start"].apply(get_split)

    print("--- CHRONOLOGICAL DATASET SPLIT ---")
    print(f"Total Distinct Weeks : {n_weeks}")
    print(f"Train Weeks          : {len(train_weeks)} ({min(train_weeks)} to {max(train_weeks)}) | Rows: {(df_base['data_split'] == 'train').sum()}")
    print(f"Validation Weeks     : {len(val_weeks)} ({min(val_weeks)} to {max(val_weeks)}) | Rows: {(df_base['data_split'] == 'validation').sum()}")
    print(f"Test Weeks           : {len(test_weeks)} ({min(test_weeks)} to {max(test_weeks)}) | Rows: {(df_base['data_split'] == 'test').sum()}\n")

    # ─────────────────────────────────────────────────────────────
    # 2. FP-GROWTH RULE MINING & ROW FEATURES
    # ─────────────────────────────────────────────────────────────
    rules_csv = BACKEND_DIR / "ml" / "generated" / "fp_growth_rules.csv"
    rules_df = mine_fp_growth_rules(df_base, rules_csv)

    print("[FP-GROWTH] Computing row-level association features for 6,180 rows...")
    df_assoc = compute_row_association_features(df_base, rules_df)

    # ─────────────────────────────────────────────────────────────
    # 3. TRANSITION PROBABILITIES & ROW FEATURES
    # ─────────────────────────────────────────────────────────────
    trans_csv = BACKEND_DIR / "ml" / "generated" / "transition_probabilities.csv"
    trans_df = learn_transition_probabilities(train_weeks, trans_csv)

    print("[TRANSITION] Computing row-level transition features for 6,180 rows...")
    df_trans = compute_row_transition_features(df_base, trans_df)

    # ─────────────────────────────────────────────────────────────
    # 4. MERGE ENHANCED FEATURES
    # ─────────────────────────────────────────────────────────────
    df_enhanced = pd.concat([df_base, df_assoc, df_trans], axis=1)

    enhanced_csv = BACKEND_DIR / "ml" / "generated" / "enhanced_model_features.csv"
    df_enhanced.to_csv(enhanced_csv, index=False)
    print(f"\n[EXPORT] Enhanced feature dataset saved to -> {enhanced_csv}")

    # ─────────────────────────────────────────────────────────────
    # 5. VALIDATION CHECKS
    # ─────────────────────────────────────────────────────────────
    print("\n-----------------------------------------------------------------")
    print("                    RUNNING VALIDATION CHECKS                    ")
    print("-----------------------------------------------------------------")

    # 1. Enhanced row count == 6,180
    assert len(df_enhanced) == 6180, f"Row count error! Expected 6,180, got {len(df_enhanced)}"
    print("[PASS] Check 1 Passed: Enhanced row count remains exactly 6,180.")

    # 2. No duplicates
    dups = df_enhanced.duplicated(subset=["week_start", "site_id", "equipment_type"]).sum()
    assert dups == 0, f"Duplicate keys found: {dups}"
    print("[PASS] Check 2 Passed: No duplicate week_start/site_id/equipment_type rows.")

    # 3. All base feature columns present
    for col in df_base.columns:
        assert col in df_enhanced.columns, f"Base feature column '{col}' missing from enhanced output!"
    print("[PASS] Check 3 Passed: All original base feature columns preserved.")

    # 4. Non-negative features
    non_neg_cols = [
        "association_matching_rule_count", "association_max_support",
        "association_max_confidence", "association_max_lift",
        "association_mean_confidence", "association_mean_lift",
        "transition_recent_start_trigger_count", "transition_max_start_probability",
        "transition_mean_start_probability", "transition_recent_end_trigger_count",
        "transition_max_end_probability", "transition_mean_end_probability"
    ]
    for c in non_neg_cols:
        neg_vals = (df_enhanced[c] < 0).sum()
        assert neg_vals == 0, f"Negative values found in feature '{c}'!"
    print("[PASS] Check 4 Passed: All association and transition features are non-negative.")

    # 5. Rule metrics non-negative
    if not rules_df.empty:
        for metric in ["support", "confidence", "lift"]:
            assert (rules_df[metric] < 0).sum() == 0, f"Negative values found in FP-Growth rule metric '{metric}'!"
    print("[PASS] Check 5 Passed: FP-Growth rule support, confidence, and lift are non-negative.")

    # 6. Transition probabilities between 0 and 1
    if not trans_df.empty:
        for prob_col in ["raw_probability", "smoothed_probability"]:
            invalid_probs = ((trans_df[prob_col] < 0.0) | (trans_df[prob_col] > 1.0)).sum()
            assert invalid_probs == 0, f"Transition probabilities out of range [0, 1] in '{prob_col}'!"
    print("[PASS] Check 6 Passed: All transition probabilities lie strictly between 0 and 1.")

    # 7. Same week_start -> same data_split
    split_check = df_enhanced.groupby("week_start")["data_split"].nunique()
    assert (split_check > 1).sum() == 0, "Inconsistent data_split within same week_start!"
    print("[PASS] Check 7 Passed: All rows belonging to the same week_start have identical data_split.")

    # 8. Train < Validation < Test chronology
    train_max_date = df_enhanced[df_enhanced["data_split"] == "train"]["week_start"].max()
    val_min_date = df_enhanced[df_enhanced["data_split"] == "validation"]["week_start"].min()
    val_max_date = df_enhanced[df_enhanced["data_split"] == "validation"]["week_start"].max()
    test_min_date = df_enhanced[df_enhanced["data_split"] == "test"]["week_start"].min()

    assert train_max_date < val_min_date, "Train weeks overlap with Validation weeks!"
    assert val_max_date < test_min_date, "Validation weeks overlap with Test weeks!"
    print("[PASS] Check 8 Passed: Chronological ordering strictly enforced (Train < Validation < Test).")

    # ─────────────────────────────────────────────────────────────
    # 6. REPORTING SUMMARY
    # ─────────────────────────────────────────────────────────────
    assoc_match_pct = round((df_enhanced["association_matching_rule_count"] > 0).sum() / len(df_enhanced) * 100.0, 2)
    trans_trigger_pct = round(
        ((df_enhanced["transition_recent_start_trigger_count"] > 0) | (df_enhanced["transition_recent_end_trigger_count"] > 0)).sum() / len(df_enhanced) * 100.0, 2
    )

    print("\n=================================================================")
    print("                 ENHANCED FEATURE GENERATION SUMMARY            ")
    print("=================================================================")
    print(f"Retained FP-Growth Rules         : {len(rules_df)}")
    print(f"Retained Transition Relationships: {len(trans_df)}")
    print(f"Enhanced Output Rows             : {len(df_enhanced)}")
    print(f"Total Feature Columns            : {len(df_enhanced.columns)}")
    print(f"Rows with Matching Assoc Rules   : {assoc_match_pct}%")
    print(f"Rows with Transition Triggers    : {trans_trigger_pct}%")

    if not rules_df.empty:
        print("\n--- TOP 10 FP-GROWTH RULES BY LIFT ---")
        top_rules = rules_df.sort_values(by="lift", ascending=False).head(10)
        print(top_rules.to_string(index=False))

    if not trans_df.empty:
        print("\n--- TOP 10 TRANSITION RELATIONSHIPS BY SMOOTHED PROBABILITY ---")
        top_trans = trans_df.sort_values(by="smoothed_probability", ascending=False).head(10)
        print(top_trans.to_string(index=False))

    print("\n=================================================================")
    print("  ENHANCED FEATURE PIPELINE COMPLETED SUCCESSFULLY!")
    print("=================================================================")


if __name__ == "__main__":
    build_enhanced_feature_dataset()
