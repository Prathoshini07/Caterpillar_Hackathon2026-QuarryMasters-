import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
import pandas as pd
import numpy as np

# mlxtend imports
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

VALID_EQUIPMENT_TYPES = {"Excavator", "Bulldozer", "Grader", "Crane", "Loader", "Roller"}


def mine_fp_growth_rules(
    df_base: pd.DataFrame,
    output_path: Path
) -> pd.DataFrame:
    """
    Mine FP-Growth rules using training-period site-week baskets only.
    """
    train_df = df_base[df_base["data_split"] == "train"].copy()

    # Active equipment types in current week where current_demand > 0
    active_rows = train_df[train_df["current_demand"] > 0]

    transactions_dict: Dict[Tuple[str, Any], Set[str]] = {}
    for _, row in active_rows.iterrows():
        key = (row["site_id"], row["week_start"])
        transactions_dict.setdefault(key, set()).add(row["equipment_type"])

    transactions = list(transactions_dict.values())
    if not transactions:
        print("[WARNING] No active transactions found in training data.")
        empty_rules = pd.DataFrame(columns=[
            "antecedents", "consequent", "support", "confidence", "lift",
            "antecedent_support", "consequent_support"
        ])
        empty_rules.to_csv(output_path, index=False)
        return empty_rules

    # One-hot transaction encoding
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_trans = pd.DataFrame(te_ary, columns=te.columns_)

    # FP-Growth frequent itemsets (min_support = 0.05)
    frequent_itemsets = fpgrowth(df_trans, min_support=0.05, use_colnames=True)
    if frequent_itemsets.empty:
        print("[WARNING] No frequent itemsets found with min_support=0.05.")
        empty_rules = pd.DataFrame(columns=[
            "antecedents", "consequent", "support", "confidence", "lift",
            "antecedent_support", "consequent_support"
        ])
        empty_rules.to_csv(output_path, index=False)
        return empty_rules

    # Association rules (metric="confidence", min_threshold=0.35)
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.35)
    if rules.empty:
        print("[WARNING] No rules generated with min_confidence=0.35.")
        empty_rules = pd.DataFrame(columns=[
            "antecedents", "consequent", "support", "confidence", "lift",
            "antecedent_support", "consequent_support"
        ])
        empty_rules.to_csv(output_path, index=False)
        return empty_rules

    retained_rows = []
    for _, r in rules.iterrows():
        ant_set = set(r["antecedents"])
        con_set = set(r["consequents"])
        lift_val = float(r["lift"])

        if lift_val < 1.15:
            continue
        if len(con_set) != 1:
            continue
        cons_item = list(con_set)[0]
        if cons_item not in VALID_EQUIPMENT_TYPES:
            continue
        if cons_item in ant_set:
            continue

        ant_str = "|".join(sorted(list(ant_set)))
        ant_sup = float(r["antecedent support"]) if "antecedent support" in r else float(r.get("antecedent_support", 0.0))
        cons_sup = float(r["consequent support"]) if "consequent support" in r else float(r.get("consequent_support", 0.0))

        retained_rows.append({
            "antecedents": ant_str,
            "consequent": cons_item,
            "support": float(r["support"]),
            "confidence": float(r["confidence"]),
            "lift": lift_val,
            "antecedent_support": ant_sup,
            "consequent_support": cons_sup
        })

    retained_df = pd.DataFrame(retained_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    retained_df.to_csv(output_path, index=False)
    print(f"[FP-GROWTH] Mined & retained {len(retained_df)} association rules -> {output_path}")
    return retained_df


def compute_row_association_features(
    df_base: pd.DataFrame,
    rules_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute row-level FP-Growth features for every row in base feature table.
    """
    active_baskets: Dict[Tuple[str, Any], Set[str]] = {}
    for _, row in df_base[df_base["current_demand"] > 0].iterrows():
        active_baskets.setdefault((row["site_id"], row["week_start"]), set()).add(row["equipment_type"])

    parsed_rules = []
    if not rules_df.empty:
        for _, r in rules_df.iterrows():
            ant_set = set(str(r["antecedents"]).split("|"))
            cons = str(r["consequent"])
            parsed_rules.append({
                "antecedent_set": ant_set,
                "consequent": cons,
                "support": float(r["support"]),
                "confidence": float(r["confidence"]),
                "lift": float(r["lift"])
            })

    results = []
    for _, row in df_base.iterrows():
        site_id = row["site_id"]
        w_start = row["week_start"]
        target_eq = row["equipment_type"]

        full_basket = active_baskets.get((site_id, w_start), set())
        basket_without_target = full_basket - {target_eq}

        matching_rules = [
            r for r in parsed_rules
            if r["consequent"] == target_eq and r["antecedent_set"].issubset(basket_without_target)
        ]

        if not matching_rules:
            results.append({
                "association_matching_rule_count": 0,
                "association_max_support": 0.0,
                "association_max_confidence": 0.0,
                "association_max_lift": 0.0,
                "association_mean_confidence": 0.0,
                "association_mean_lift": 0.0
            })
        else:
            supports = [r["support"] for r in matching_rules]
            confidences = [r["confidence"] for r in matching_rules]
            lifts = [r["lift"] for r in matching_rules]

            results.append({
                "association_matching_rule_count": len(matching_rules),
                "association_max_support": float(np.max(supports)),
                "association_max_confidence": float(np.max(confidences)),
                "association_max_lift": float(np.max(lifts)),
                "association_mean_confidence": float(np.mean(confidences)),
                "association_mean_lift": float(np.mean(lifts))
            })

    return pd.DataFrame(results, index=df_base.index)
