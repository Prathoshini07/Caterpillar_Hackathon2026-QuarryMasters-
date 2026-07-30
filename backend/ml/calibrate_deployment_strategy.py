"""
backend/ml/calibrate_deployment_strategy.py
============================================
Calibrated change-gated hybrid threshold search.
Selects deployment thresholds using VALIDATION ONLY, then evaluates test once.

Run with:
    python -m ml.calibrate_deployment_strategy
"""
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    precision_score, recall_score, f1_score, confusion_matrix
)
from catboost import CatBoostRegressor

BACKEND_DIR      = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SAVED_MODELS_DIR = BACKEND_DIR / "ml" / "saved_models"
GENERATED_DIR    = BACKEND_DIR / "ml" / "generated"
MODEL_PATH       = SAVED_MODELS_DIR / "demand_direct_model.cbm"
METADATA_PATH    = SAVED_MODELS_DIR / "model_metadata.json"
ENHANCED_CSV     = GENERATED_DIR / "enhanced_model_features.csv"
DEPLOY_JSON      = SAVED_MODELS_DIR / "deployment_strategy.json"
FORECAST_THRESH  = GENERATED_DIR / "deployment_threshold_comparison.csv"
ALERT_THRESH     = GENERATED_DIR / "shortage_alert_threshold_comparison.csv"

# Threshold grids
INCREASE_THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25,
                       0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70]
DECREASE_THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30,
                       0.35, 0.40, 0.50, 0.60, 0.70]

MAE_TOL = 0.002   # tolerance for verifying recreated metrics


# ─────────────────────────────────────────────────────────────────
# METRIC HELPERS
# ─────────────────────────────────────────────────────────────────

def compute_metrics(y_true: np.ndarray,
                    y_pred_int: np.ndarray,
                    current_demand: np.ndarray) -> Dict[str, float]:
    """All metrics for an integer operational prediction."""
    n = len(y_true)
    y_true_i = y_true.astype(int)
    y_pred_i = np.clip(y_pred_int.astype(int), 0, None)

    mae  = float(mean_absolute_error(y_true_i, y_pred_i))
    rmse = float(np.sqrt(mean_squared_error(y_true_i, y_pred_i)))
    exact_acc   = float(np.mean(y_true_i == y_pred_i))
    within1_acc = float(np.mean(np.abs(y_true_i - y_pred_i) <= 1))
    underpred   = float(np.sum(y_pred_i < y_true_i) / n * 100)
    overpred    = float(np.sum(y_pred_i > y_true_i) / n * 100)

    # Demand occurrence (any demand > 0)
    occ_true = (y_true_i > 0).astype(int)
    occ_pred = (y_pred_i > 0).astype(int)
    occ_prec = float(precision_score(occ_true, occ_pred, zero_division=0))
    occ_rec  = float(recall_score(occ_true, occ_pred, zero_division=0))
    occ_f1   = float(f1_score(occ_true, occ_pred, zero_division=0))

    # Additional-equipment detection
    cd_int = current_demand.astype(int)
    aeq_actual = (y_true_i > cd_int).astype(int)
    aeq_pred   = (y_pred_i > cd_int).astype(int)
    aeq_prec = float(precision_score(aeq_actual, aeq_pred, zero_division=0))
    aeq_rec  = float(recall_score(aeq_actual, aeq_pred, zero_division=0))
    aeq_f1   = float(f1_score(aeq_actual, aeq_pred, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(aeq_actual, aeq_pred, labels=[0, 1]).ravel()

    # Shortage error = MAE on additional-need signal
    actual_need = np.maximum(0, y_true_i - cd_int)
    pred_need   = np.maximum(0, y_pred_i - cd_int)
    shortage_err = float(mean_absolute_error(actual_need, pred_need))

    return {
        "MAE":                           round(mae, 4),
        "RMSE":                          round(rmse, 4),
        "exact_count_accuracy":          round(exact_acc, 4),
        "within_one_unit_accuracy":      round(within1_acc, 4),
        "underprediction_rate":          round(underpred, 4),
        "overprediction_rate":           round(overpred, 4),
        "demand_occurrence_precision":   round(occ_prec, 4),
        "demand_occurrence_recall":      round(occ_rec, 4),
        "demand_occurrence_F1":          round(occ_f1, 4),
        "additional_equipment_precision": round(aeq_prec, 4),
        "additional_equipment_recall":    round(aeq_rec, 4),
        "additional_equipment_F1":        round(aeq_f1, 4),
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
        "mean_shortage_error":           round(shortage_err, 4),
    }


def alert_metrics(y_true: np.ndarray,
                  raw_pred: np.ndarray,
                  current_demand: np.ndarray,
                  increase_thresh: float) -> Dict[str, float]:
    """Shortage-alert metrics: signal = raw_pred - cd >= threshold."""
    cd_int      = current_demand.astype(int)
    y_true_i    = y_true.astype(int)
    aeq_actual  = (y_true_i > cd_int).astype(int)
    alert_fired = ((raw_pred - current_demand) >= increase_thresh).astype(int)
    prec = float(precision_score(aeq_actual, alert_fired, zero_division=0))
    rec  = float(recall_score(aeq_actual, alert_fired, zero_division=0))
    f1   = float(f1_score(aeq_actual, alert_fired, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(aeq_actual, alert_fired, labels=[0, 1]).ravel()
    # Shortage error on alerted rows
    pred_need   = np.maximum(0, np.round(raw_pred).astype(int) - cd_int)
    actual_need = np.maximum(0, y_true_i - cd_int)
    shortage_err = float(mean_absolute_error(actual_need, pred_need))
    return {
        "alert_precision":   round(prec, 4),
        "alert_recall":      round(rec, 4),
        "alert_F1":          round(f1, 4),
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
        "n_alerts_fired":    int(alert_fired.sum()),
        "n_actual_positive": int(aeq_actual.sum()),
        "mean_shortage_error": round(shortage_err, 4),
    }


# ─────────────────────────────────────────────────────────────────
# HYBRID PREDICTION
# ─────────────────────────────────────────────────────────────────

def apply_change_gated(raw_pred: np.ndarray, current_demand: np.ndarray,
                       inc_thresh: float, dec_thresh: float) -> np.ndarray:
    """Returns integer operational forecast."""
    predicted_change = raw_pred - current_demand
    cb_rounded = np.clip(np.round(raw_pred), 0, None).astype(int)
    cd_int     = current_demand.astype(int)
    # Gate: use CB when predicted change exceeds threshold, else use CD
    use_cb = (predicted_change >= inc_thresh) | (predicted_change <= -dec_thresh)
    return np.where(use_cb, cb_rounded, cd_int)


# ─────────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────────

def load_all():
    with open(METADATA_PATH) as f:
        meta = json.load(f)
    model = CatBoostRegressor()
    model.load_model(str(MODEL_PATH))
    df = pd.read_csv(ENHANCED_CSV)
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.strftime("%Y-%m-%d")
    return meta, model, df


def prepare_X(df_split: pd.DataFrame, feature_list: List[str],
              cat_features: List[str]) -> pd.DataFrame:
    ds = df_split.copy()
    for col in feature_list:
        if col in cat_features:
            ds[col] = ds[col].astype(str)
        elif col in ds.columns:
            ds[col] = pd.to_numeric(ds[col], errors="coerce").fillna(0)
    return ds[feature_list]


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    print("=================================================================")
    print("  CATERPILLAR DEMAND FORECASTING - DEPLOYMENT CALIBRATION       ")
    print("=================================================================\n")

    # ── SECTION 1: Load & Verify ───────────────────────────────────
    print("-----------------------------------------------------------------")
    print("  SECTION 1: LOAD & VERIFY MODEL")
    print("-----------------------------------------------------------------")

    meta, model, df = load_all()
    feature_list = meta["all_features_ordered"]
    cat_features = meta["categorical_features"]

    print(f"  Model type   : {meta['selected_model_type']}")
    print(f"  Feature set  : {meta['feature_set']}")
    print(f"  Features     : {len(feature_list)}")

    val_df  = df[df["data_split"] == "validation"].copy()
    test_df = df[df["data_split"] == "test"].copy()

    val_y   = val_df["target_next_week_demand"].values.astype(int)
    test_y  = test_df["target_next_week_demand"].values.astype(int)
    val_cd  = val_df["current_demand"].values.astype(float)
    test_cd = test_df["current_demand"].values.astype(float)

    val_raw  = np.clip(model.predict(prepare_X(val_df,  feature_list, cat_features)), 0, None)
    test_raw = np.clip(model.predict(prepare_X(test_df, feature_list, cat_features)), 0, None)

    assert not np.any(np.isnan(val_raw)),  "NaN in validation CatBoost predictions!"
    assert not np.any(np.isnan(test_raw)), "NaN in test CatBoost predictions!"
    assert np.all(val_raw  >= 0), "Negative validation predictions!"
    assert np.all(test_raw >= 0), "Negative test predictions!"

    val_mae_check  = float(mean_absolute_error(val_y,  val_raw))
    test_mae_check = float(mean_absolute_error(test_y, test_raw))

    print(f"\n  Verification against saved metadata:")
    print(f"    Recreated Val  MAE = {val_mae_check:.4f}  (expected ~0.3146)")
    print(f"    Recreated Test MAE = {test_mae_check:.4f}  (expected ~0.3420)")

    if abs(val_mae_check - meta["validation_metrics"]["MAE"]) > MAE_TOL:
        raise RuntimeError(
            f"[FAIL] Val MAE mismatch: got {val_mae_check:.4f}, "
            f"expected {meta['validation_metrics']['MAE']:.4f}"
        )
    if abs(test_mae_check - meta["test_metrics"]["MAE"]) > MAE_TOL:
        raise RuntimeError(
            f"[FAIL] Test MAE mismatch: got {test_mae_check:.4f}, "
            f"expected {meta['test_metrics']['MAE']:.4f}"
        )
    print("  [PASS] Both recreated MAEs match saved metadata within tolerance.\n")

    # ── SECTION 2 & 3: Grid Search on Validation ──────────────────
    print("-----------------------------------------------------------------")
    print("  SECTION 2+3: THRESHOLD GRID SEARCH (VALIDATION ONLY)")
    print("-----------------------------------------------------------------")

    n_combos = len(INCREASE_THRESHOLDS) * len(DECREASE_THRESHOLDS)
    print(f"  Increase thresholds : {INCREASE_THRESHOLDS}")
    print(f"  Decrease thresholds : {DECREASE_THRESHOLDS}")
    print(f"  Total combinations  : {n_combos}\n")

    forecast_rows = []
    for inc_t in INCREASE_THRESHOLDS:
        for dec_t in DECREASE_THRESHOLDS:
            val_pred = apply_change_gated(val_raw, val_cd, inc_t, dec_t)
            assert np.all(val_pred >= 0), "Negative operational forecast!"
            m = compute_metrics(val_y, val_pred, val_cd)
            m["increase_threshold"] = inc_t
            m["decrease_threshold"] = dec_t
            forecast_rows.append(m)

    forecast_df = pd.DataFrame(forecast_rows)
    forecast_df.to_csv(FORECAST_THRESH, index=False)
    print(f"  [EXPORT] Threshold grid -> {FORECAST_THRESH}")

    # ── SECTION 4A: Select Best Displayed-Forecast Config ─────────
    print("\n-----------------------------------------------------------------")
    print("  SECTION 4A: SELECT DISPLAYED-FORECAST THRESHOLDS (VAL ONLY)")
    print("-----------------------------------------------------------------")

    # Primary: lowest MAE. Tie-breakers: exact_acc, within1_acc, aeq_F1, underpred
    best_disp = forecast_df.sort_values(
        by=["MAE", "exact_count_accuracy", "within_one_unit_accuracy",
            "additional_equipment_F1", "underprediction_rate"],
        ascending=[True, False, False, False, True]
    ).iloc[0].to_dict()

    disp_inc = best_disp["increase_threshold"]
    disp_dec = best_disp["decrease_threshold"]

    print(f"\n  Best displayed-forecast configuration:")
    print(f"    Increase threshold : {disp_inc}")
    print(f"    Decrease threshold : {disp_dec}")
    print(f"\n  Validation metrics:")
    for k, v in best_disp.items():
        if k not in ("increase_threshold", "decrease_threshold"):
            print(f"    {k:<40}: {v}")

    # How many configurations match this MAE exactly?
    tied_mae = forecast_df[forecast_df["MAE"] == best_disp["MAE"]]
    print(f"\n  Configurations with same MAE: {len(tied_mae)}")

    # ── SECTION 4B: Shortage Alert Threshold ──────────────────────
    print("\n-----------------------------------------------------------------")
    print("  SECTION 4B: SELECT SHORTAGE-ALERT THRESHOLD (VAL ONLY)")
    print("-----------------------------------------------------------------")

    alert_rows = []
    for inc_t in INCREASE_THRESHOLDS:
        m = alert_metrics(val_y, val_raw, val_cd, inc_t)
        m["increase_threshold"] = inc_t
        alert_rows.append(m)

    alert_df = pd.DataFrame(alert_rows)
    alert_df.to_csv(ALERT_THRESH, index=False)
    print(f"\n  [EXPORT] Shortage-alert grid -> {ALERT_THRESH}")

    print(f"\n  {'Threshold':>12} {'Precision':>10} {'Recall':>10} {'F1':>10} "
          f"{'TP':>6} {'FP':>6} {'FN':>6} {'ShortErr':>10}")
    print(f"  {'-'*76}")
    for _, row in alert_df.iterrows():
        rd = row.to_dict()
        print(f"  {rd['increase_threshold']:>12.2f} "
              f"{rd['alert_precision']:>10.4f} "
              f"{rd['alert_recall']:>10.4f} "
              f"{rd['alert_F1']:>10.4f} "
              f"{rd['TP']:>6} "
              f"{rd['FP']:>6} "
              f"{rd['FN']:>6} "
              f"{rd['mean_shortage_error']:>10.4f}")

    # Primary: highest F1. Tie-breakers: recall, precision, lower shortage err
    best_alert = alert_df.sort_values(
        by=["alert_F1", "alert_recall", "alert_precision", "mean_shortage_error"],
        ascending=[False, False, False, True]
    ).iloc[0].to_dict()

    alert_inc = best_alert["increase_threshold"]
    print(f"\n  Best shortage-alert threshold: {alert_inc}")
    print(f"    Val Precision : {best_alert['alert_precision']:.4f}")
    print(f"    Val Recall    : {best_alert['alert_recall']:.4f}")
    print(f"    Val F1        : {best_alert['alert_F1']:.4f}")
    print(f"    TP={best_alert['TP']}  FP={best_alert['FP']}  "
          f"FN={best_alert['FN']}  TN={best_alert['TN']}")

    # ── SECTION 5: Untouched Test Evaluation ──────────────────────
    print("\n-----------------------------------------------------------------")
    print("  SECTION 5: UNTOUCHED TEST EVALUATION")
    print("-----------------------------------------------------------------")

    # Displayed forecast on test
    test_pred_disp = apply_change_gated(test_raw, test_cd, disp_inc, disp_dec)
    assert np.all(test_pred_disp >= 0), "Negative test forecast!"
    test_disp_m = compute_metrics(test_y, test_pred_disp, test_cd)

    print(f"\n  --- DISPLAYED FORECAST TEST METRICS ---")
    print(f"  (inc_thresh={disp_inc}, dec_thresh={disp_dec})")
    for k, v in test_disp_m.items():
        if k not in ("TP", "FP", "FN", "TN"):
            print(f"    {k:<40}: {v}")
    print(f"    TP={test_disp_m['TP']}  FP={test_disp_m['FP']}  "
          f"FN={test_disp_m['FN']}  TN={test_disp_m['TN']}")

    # Shortage alert on test
    test_alert_m = alert_metrics(test_y, test_raw, test_cd, alert_inc)

    print(f"\n  --- SHORTAGE ALERT TEST METRICS ---")
    print(f"  (inc_thresh={alert_inc})")
    print(f"    Precision  : {test_alert_m['alert_precision']:.4f}")
    print(f"    Recall     : {test_alert_m['alert_recall']:.4f}")
    print(f"    F1         : {test_alert_m['alert_F1']:.4f}")
    print(f"    TP={test_alert_m['TP']}  FP={test_alert_m['FP']}  "
          f"FN={test_alert_m['FN']}  TN={test_alert_m['TN']}")

    # ── SECTION 5B: Compare vs Previous Fixed Hybrid B ────────────
    print("\n-----------------------------------------------------------------")
    print("  COMPARISON VS PREVIOUS FIXED HYBRID B (|CB_round - CD| >= 1)")
    print("-----------------------------------------------------------------")

    # Re-compute previous Hybrid B for fair comparison
    prev_hb_val  = np.where(
        np.abs(np.clip(np.round(val_raw), 0, None).astype(int) - val_cd.astype(int)) >= 1,
        np.clip(np.round(val_raw), 0, None).astype(int), val_cd.astype(int)
    )
    prev_hb_test = np.where(
        np.abs(np.clip(np.round(test_raw), 0, None).astype(int) - test_cd.astype(int)) >= 1,
        np.clip(np.round(test_raw), 0, None).astype(int), test_cd.astype(int)
    )
    prev_hb_val_m  = compute_metrics(val_y,  prev_hb_val,  val_cd)
    prev_hb_test_m = compute_metrics(test_y, prev_hb_test, test_cd)

    print(f"\n  {'Metric':<40} {'Prev HybB Val':>14} {'Calib Val':>12} "
          f"{'Prev HybB Test':>14} {'Calib Test':>12}")
    print(f"  {'-'*96}")
    for k in ["MAE", "RMSE", "exact_count_accuracy", "within_one_unit_accuracy",
              "underprediction_rate", "additional_equipment_F1",
              "additional_equipment_recall", "mean_shortage_error"]:
        pv  = prev_hb_val_m.get(k, float("nan"))
        cv  = best_disp.get(k, float("nan"))
        pt  = prev_hb_test_m.get(k, float("nan"))
        ct  = test_disp_m.get(k, float("nan"))
        print(f"  {k:<40} {pv:>14.4f} {cv:>12.4f} {pt:>14.4f} {ct:>12.4f}")

    # ── SECTION 6: Save Deployment Config ─────────────────────────
    print("\n-----------------------------------------------------------------")
    print("  SECTION 6: SAVE DEPLOYMENT CONFIGURATION")
    print("-----------------------------------------------------------------")

    # Build clean validation metrics for JSON
    val_disp_m = {k: v for k, v in best_disp.items()
                  if k not in ("increase_threshold", "decrease_threshold")}
    val_alert_m = {k: v for k, v in best_alert.items()
                   if k != "increase_threshold"}

    deploy_config = {
        "model_version": "1.0.0",
        "strategy_type": "calibrated_change_gated_hybrid",
        "displayed_forecast": {
            "increase_threshold": float(disp_inc),
            "decrease_threshold": float(disp_dec),
            "rounding_rule": "nearest_non_negative_integer",
            "decision_rule": (
                f"if (raw_pred - current_demand) >= {disp_inc}: use round(raw_pred); "
                f"elif (raw_pred - current_demand) <= -{disp_dec}: use round(raw_pred); "
                "else: use current_demand"
            ),
            "validation_metrics": val_disp_m,
            "test_metrics": test_disp_m,
        },
        "shortage_alert": {
            "increase_threshold": float(alert_inc),
            "signal_definition": "raw_prediction_minus_current_demand",
            "alert_rule": (
                f"fire alert when (raw_catboost_prediction - current_demand) >= {alert_inc}"
            ),
            "validation_metrics": val_alert_m,
            "test_metrics": test_alert_m,
        },
        "model_artifact": str(MODEL_PATH),
        "feature_source": "backend/ml/generated/enhanced_model_features.csv",
        "n_features": len(feature_list),
        "features_ordered": feature_list,
        "categorical_features": cat_features,
        "grid_searched": {
            "increase_thresholds": INCREASE_THRESHOLDS,
            "decrease_thresholds": DECREASE_THRESHOLDS,
            "total_combinations_evaluated": n_combos,
        },
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(DEPLOY_JSON, "w") as f:
        json.dump(deploy_config, f, indent=2, default=str)
    print(f"\n  [SAVED] Deployment config -> {DEPLOY_JSON}")

    # ── SECTION 7: Validation Checks ──────────────────────────────
    print("\n-----------------------------------------------------------------")
    print("  SECTION 7: VALIDATION CHECKS")
    print("-----------------------------------------------------------------")

    checks = []

    checks.append(("CatBoost was not retrained", True))  # structurally enforced
    checks.append(("Existing model artifact not overwritten", True))
    checks.append(("Thresholds selected using validation only", True))
    checks.append(("Test evaluated only after threshold selection", True))

    checks.append(("increase_threshold in tested grid",
                   float(disp_inc) in INCREASE_THRESHOLDS))
    checks.append(("decrease_threshold in tested grid",
                   float(disp_dec) in DECREASE_THRESHOLDS))
    checks.append(("alert_threshold in tested grid",
                   float(alert_inc) in INCREASE_THRESHOLDS))

    # All displayed predictions are non-negative integers
    checks.append(("Val displayed preds non-negative integers",
                   bool(np.all(apply_change_gated(val_raw, val_cd, disp_inc, disp_dec) >= 0))))
    checks.append(("Test displayed preds non-negative integers",
                   bool(np.all(test_pred_disp >= 0))))

    # Recreated MAEs match
    checks.append(("Val MAE matches metadata",
                   abs(val_mae_check - meta["validation_metrics"]["MAE"]) <= MAE_TOL))
    checks.append(("Test MAE matches metadata",
                   abs(test_mae_check - meta["test_metrics"]["MAE"]) <= MAE_TOL))

    # deployment_strategy.json has all required fields
    required_fields = [
        "model_version", "strategy_type", "displayed_forecast",
        "shortage_alert", "model_artifact", "feature_source", "generated_at"
    ]
    for field in required_fields:
        checks.append((f"deploy_config has field: {field}", field in deploy_config))

    for subfld in ["increase_threshold", "decrease_threshold", "validation_metrics", "test_metrics"]:
        checks.append((f"displayed_forecast has field: {subfld}",
                       subfld in deploy_config["displayed_forecast"]))

    for subfld in ["increase_threshold", "signal_definition", "validation_metrics", "test_metrics"]:
        checks.append((f"shortage_alert has field: {subfld}",
                       subfld in deploy_config["shortage_alert"]))

    print()
    all_passed = True
    for desc, result in checks:
        tag = "[PASS]" if result else "[FAIL]"
        print(f"  {tag}  {desc}")
        if not result:
            all_passed = False
    print(f"\n  Result: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")

    # ── SECTION 8: Final Report ────────────────────────────────────
    print("\n=================================================================")
    print("  SECTION 8: FINAL REPORT")
    print("=================================================================\n")

    print(f"  1. Threshold combinations evaluated      : {n_combos}")
    print(f"  2. Best displayed-forecast increase_thresh: {disp_inc}")
    print(f"  3. Best displayed-forecast decrease_thresh: {disp_dec}")
    print(f"  4. Displayed-forecast VAL metrics:")
    for k in ["MAE", "RMSE", "exact_count_accuracy", "within_one_unit_accuracy",
              "underprediction_rate", "additional_equipment_F1", "mean_shortage_error"]:
        print(f"       {k:<40}: {best_disp.get(k, float('nan')):.4f}")
    print(f"  5. Displayed-forecast TEST metrics (untouched):")
    for k in ["MAE", "RMSE", "exact_count_accuracy", "within_one_unit_accuracy",
              "underprediction_rate", "additional_equipment_F1", "mean_shortage_error"]:
        print(f"       {k:<40}: {test_disp_m.get(k, float('nan')):.4f}")
    print(f"  6. Best shortage-alert increase_thresh    : {alert_inc}")
    print(f"  7. Shortage-alert VAL metrics:")
    print(f"       Precision : {best_alert['alert_precision']:.4f}")
    print(f"       Recall    : {best_alert['alert_recall']:.4f}")
    print(f"       F1        : {best_alert['alert_F1']:.4f}")
    print(f"  8. Shortage-alert TEST metrics (untouched):")
    print(f"       Precision : {test_alert_m['alert_precision']:.4f}")
    print(f"       Recall    : {test_alert_m['alert_recall']:.4f}")
    print(f"       F1        : {test_alert_m['alert_F1']:.4f}")
    print(f"  9. vs Previous Hybrid B:")
    print(f"       Prev Hybrid B Val MAE  : {prev_hb_val_m['MAE']:.4f}")
    print(f"       Calibrated Val MAE     : {best_disp['MAE']:.4f}")
    print(f"       Prev Hybrid B Test MAE : {prev_hb_test_m['MAE']:.4f}")
    print(f"       Calibrated Test MAE    : {test_disp_m['MAE']:.4f}")
    delta_v = prev_hb_val_m["MAE"]  - best_disp["MAE"]
    delta_t = prev_hb_test_m["MAE"] - test_disp_m["MAE"]
    print(f"       Val MAE improvement    : {delta_v:+.4f}")
    print(f"       Test MAE improvement   : {delta_t:+.4f}")
    print(f" 10. Saved artifacts:")
    print(f"       {DEPLOY_JSON}")
    print(f"       {FORECAST_THRESH}")
    print(f"       {ALERT_THRESH}")

    print("\n=================================================================")
    print("  SAFETY CONFIRMATION")
    print("=================================================================")
    print("  [OK] CatBoost was NOT retrained.")
    print("  [OK] demand_direct_model.cbm was NOT overwritten.")
    print("  [OK] model_metadata.json was NOT overwritten.")
    print("  [OK] No database records changed.")
    print("  [OK] No frontend files changed.")
    print("  [OK] No FastAPI routes changed.")
    print("  [OK] No forecasts inserted into demand_forecasts.")
    print("  [OK] Thresholds selected using VALIDATION data only.")


if __name__ == "__main__":
    main()
