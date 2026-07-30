import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_score, recall_score, f1_score

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def compute_comprehensive_metrics(
    y_true: np.ndarray,
    y_pred_raw: np.ndarray,
    current_demand: np.ndarray,
    y_pred_occ: np.ndarray = None
) -> Dict[str, float]:
    """
    Compute comprehensive evaluation metrics:
    - Regression/Count: MAE, RMSE, exact_count_accuracy, within_one_unit_accuracy
    - Demand Occurrence: precision, recall, f1, occurrence_accuracy
    - Business: underprediction_rate, overprediction_rate, mean_shortage_error, additional_equip (precision, recall, f1)
    """
    y_true = np.array(y_true, dtype=float)
    y_pred_raw = np.clip(np.array(y_pred_raw, dtype=float), 0, None)
    current_demand = np.array(current_demand, dtype=float)

    # Rounded non-negative integer predictions for count metrics
    y_pred_rounded = np.round(y_pred_raw).astype(int)

    if y_pred_occ is None:
        y_pred_occ = (y_pred_rounded > 0).astype(int)
    else:
        y_pred_occ = np.array(y_pred_occ, dtype=int)

    actual_occ = (y_true > 0).astype(int)

    # 1. Regression / Count Metrics
    mae = float(mean_absolute_error(y_true, y_pred_raw))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred_raw)))
    exact_acc = float(np.mean(y_true.astype(int) == y_pred_rounded))
    within_one_acc = float(np.mean(np.abs(y_true.astype(int) - y_pred_rounded) <= 1))

    # 2. Demand Occurrence Metrics
    occ_acc = float(np.mean(actual_occ == y_pred_occ))
    occ_prec = float(precision_score(actual_occ, y_pred_occ, zero_division=0))
    occ_rec = float(recall_score(actual_occ, y_pred_occ, zero_division=0))
    occ_f1 = float(f1_score(actual_occ, y_pred_occ, zero_division=0))

    # 3. Business Metrics
    n = len(y_true)
    underpred_rate = float(np.sum(y_pred_rounded < y_true.astype(int)) / n * 100.0)
    overpred_rate = float(np.sum(y_pred_rounded > y_true.astype(int)) / n * 100.0)

    # Mean Shortage Error
    actual_add_need = np.maximum(0, y_true - current_demand)
    pred_add_need = np.maximum(0, y_pred_rounded - current_demand)
    mean_shortage_err = float(mean_absolute_error(actual_add_need, pred_add_need))

    # Additional Equipment Detection
    actual_add_cond = (y_true > current_demand).astype(int)
    pred_add_cond = (y_pred_rounded > current_demand).astype(int)

    add_prec = float(precision_score(actual_add_cond, pred_add_cond, zero_division=0))
    add_rec = float(recall_score(actual_add_cond, pred_add_cond, zero_division=0))
    add_f1 = float(f1_score(actual_add_cond, pred_add_cond, zero_division=0))

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "exact_count_accuracy": round(exact_acc, 4),
        "within_one_unit_accuracy": round(within_one_acc, 4),
        "demand_occurrence_accuracy": round(occ_acc, 4),
        "precision": round(occ_prec, 4),
        "recall": round(occ_rec, 4),
        "F1": round(occ_f1, 4),
        "underprediction_rate": round(underpred_rate, 2),
        "overprediction_rate": round(overpred_rate, 2),
        "mean_shortage_error": round(mean_shortage_err, 4),
        "add_equip_precision": round(add_prec, 4),
        "add_equip_recall": round(add_rec, 4),
        "add_equip_f1": round(add_f1, 4),
    }


def evaluate_baselines(df_base: pd.DataFrame) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Evaluate Baseline A (Persistence), Baseline B (4-week rolling mean), and Baseline C (Historical Mean).
    Returns nested dict: baselines[model_name][split] -> metrics dict
    """
    train_df = df_base[df_base["data_split"] == "train"].copy()
    val_df = df_base[df_base["data_split"] == "validation"].copy()
    test_df = df_base[df_base["data_split"] == "test"].copy()

    # Compute Historical Site-Equipment Mean on TRAIN SET ONLY
    hist_mean_map = train_df.groupby(["site_id", "equipment_type"])["target_next_week_demand"].mean().to_dict()
    global_train_mean = train_df["target_next_week_demand"].mean()

    results = {}

    for name in ["Baseline A - Persistence", "Baseline B - Rolling Mean 4", "Baseline C - Historical Mean"]:
        results[name] = {}
        for split_name, df_split in [("validation", val_df), ("test", test_df)]:
            y_true = df_split["target_next_week_demand"].values
            current_demand = df_split["current_demand"].values

            if name == "Baseline A - Persistence":
                y_pred = current_demand.copy().astype(float)
            elif name == "Baseline B - Rolling Mean 4":
                y_pred = df_split["demand_rolling_mean_4"].values.astype(float)
            else: # Baseline C
                keys = list(zip(df_split["site_id"], df_split["equipment_type"]))
                y_pred = np.array([hist_mean_map.get(k, global_train_mean) for k in keys], dtype=float)

            results[name][split_name] = compute_comprehensive_metrics(y_true, y_pred, current_demand)

    return results
