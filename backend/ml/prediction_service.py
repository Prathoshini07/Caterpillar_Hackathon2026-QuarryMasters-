"""
backend/ml/prediction_service.py
=================================
Singleton ML Prediction Service for Caterpillar Demand Forecasting.
Loads trained CatBoost model, metadata, and deployment strategy once.
Builds current inference feature rows from database and runs model predictions.
"""
import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sqlalchemy.orm import Session
from sqlalchemy import func

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import WeeklyDemand, RentalLog, Equipment, Site, DemandForecast
from ml.association_features import compute_row_association_features
from ml.transition_features import compute_row_transition_features

SAVED_MODELS_DIR = BACKEND_DIR / "ml" / "saved_models"
GENERATED_DIR    = BACKEND_DIR / "ml" / "generated"

MODEL_PATH       = SAVED_MODELS_DIR / "demand_direct_model.cbm"
METADATA_PATH    = SAVED_MODELS_DIR / "model_metadata.json"
STRATEGY_PATH    = SAVED_MODELS_DIR / "deployment_strategy.json"
RULES_PATH       = GENERATED_DIR / "fp_growth_rules.csv"
TRANS_PATH       = GENERATED_DIR / "transition_probabilities.csv"


def calc_weeks_since_pos(series: pd.Series) -> pd.Series:
    """Calculates consecutive weeks since the last positive demand week."""
    res = []
    counter = 0
    for val in series:
        if val > 0:
            counter = 0
        else:
            counter += 1
        res.append(counter)
    return pd.Series(res, index=series.index)


def get_monday_of_week(dt: datetime.date) -> datetime.date:
    """Maps a date to the Monday of its week."""
    if not dt:
        return None
    if isinstance(dt, pd.Timestamp):
        dt = dt.date()
    return dt - datetime.timedelta(days=dt.weekday())


class PredictionService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictionService, cls).__new__(cls)
            cls._instance.is_loaded = False
            cls._instance.model = None
            cls._instance.metadata = {}
            cls._instance.strategy = {}
            cls._instance.rules_df = pd.DataFrame()
            cls._instance.trans_df = pd.DataFrame()
        return cls._instance

    def load_model(self):
        """Loads and validates model artifacts at startup. Fails if invalid."""
        if not MODEL_PATH.exists():
            raise RuntimeError(f"Model artifact missing: {MODEL_PATH}")
        if not METADATA_PATH.exists():
            raise RuntimeError(f"Model metadata missing: {METADATA_PATH}")
        if not STRATEGY_PATH.exists():
            raise RuntimeError(f"Deployment strategy missing: {STRATEGY_PATH}")

        with open(METADATA_PATH, "r") as f:
            self.metadata = json.load(f)
        with open(STRATEGY_PATH, "r") as f:
            self.strategy = json.load(f)

        # Artifact validations
        if self.metadata.get("selected_model_type") != "direct":
            raise RuntimeError("Selected model type in metadata is not 'direct'")
        if self.metadata.get("feature_set") != "Enhanced Features":
            raise RuntimeError("Feature set in metadata is not 'Enhanced Features'")
        if not self.metadata.get("all_features_ordered"):
            raise RuntimeError("Metadata feature list 'all_features_ordered' missing")

        disp = self.strategy.get("displayed_forecast", {})
        alert = self.strategy.get("shortage_alert", {})

        inc_t = disp.get("increase_threshold")
        dec_t = disp.get("decrease_threshold")
        alt_t = alert.get("increase_threshold")

        if inc_t is None or abs(float(inc_t) - 0.05) > 1e-4:
            raise RuntimeError(f"Displayed forecast increase_threshold must be 0.05, got {inc_t}")
        if dec_t is None or abs(float(dec_t) - 0.10) > 1e-4:
            raise RuntimeError(f"Displayed forecast decrease_threshold must be 0.10, got {dec_t}")
        if alt_t is None or abs(float(alt_t) - 0.20) > 1e-4:
            raise RuntimeError(f"Shortage alert increase_threshold must be 0.20, got {alt_t}")

        # Load CatBoost Model
        self.model = CatBoostRegressor()
        self.model.load_model(str(MODEL_PATH))

        # Load FP-Growth & Transition rules
        if RULES_PATH.exists():
            self.rules_df = pd.read_csv(RULES_PATH)
        else:
            self.rules_df = pd.DataFrame()

        if TRANS_PATH.exists():
            self.trans_df = pd.read_csv(TRANS_PATH)
        else:
            self.trans_df = pd.DataFrame()

        self.is_loaded = True
        print(f"[PREDICTION SERVICE] Loaded CatBoost Direct Model ({len(self.metadata['all_features_ordered'])} features)")

    def build_latest_feature_rows(self, db: Session) -> Tuple[pd.DataFrame, datetime.date]:
        """Builds feature engineering dataframe for the latest complete week in DB."""
        wd_records = db.query(WeeklyDemand).all()
        if not wd_records:
            raise ValueError("WeeklyDemand table is empty!")

        wd_list = [{
            "weekly_demand_id": w.weekly_demand_id,
            "week_start": w.week_start,
            "site_id": w.site_id,
            "equipment_type": w.equipment_type,
            "current_demand": w.weekly_demand
        } for w in wd_records]
        df_wd = pd.DataFrame(wd_list)
        df_wd["week_start"] = pd.to_datetime(df_wd["week_start"]).dt.date
        df_wd = df_wd.sort_values(by=["site_id", "equipment_type", "week_start"]).reset_index(drop=True)

        # Historical lag and rolling features
        grp = df_wd.groupby(["site_id", "equipment_type"])["current_demand"]
        df_wd["demand_lag_1"] = grp.shift(1).fillna(0)
        df_wd["demand_lag_2"] = grp.shift(2).fillna(0)
        df_wd["demand_lag_4"] = grp.shift(4).fillna(0)
        df_wd["demand_rolling_mean_4"] = grp.transform(lambda x: x.rolling(4, min_periods=1).mean()).fillna(0)
        df_wd["demand_rolling_max_4"] = grp.transform(lambda x: x.rolling(4, min_periods=1).max()).fillna(0)
        df_wd["demand_rolling_std_4"] = grp.transform(lambda x: x.rolling(4, min_periods=1).std()).fillna(0)
        df_wd["demand_trend_4"] = (df_wd["current_demand"] - df_wd["demand_lag_4"]).fillna(0)
        df_wd["weeks_since_last_positive_demand"] = grp.transform(calc_weeks_since_pos).fillna(0)

        # Calendar features
        dt_series = pd.to_datetime(df_wd["week_start"])
        df_wd["year"] = dt_series.dt.year
        df_wd["month"] = dt_series.dt.month
        df_wd["quarter"] = dt_series.dt.quarter
        df_wd["week_of_year"] = dt_series.dt.isocalendar().week.astype(int)

        # Site equipment-mix features
        mix_pivot = df_wd.pivot_table(
            index=["site_id", "week_start"],
            columns="equipment_type",
            values="current_demand",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        req_types = {
            "Excavator": "active_excavator_count",
            "Bulldozer": "active_bulldozer_count",
            "Grader": "active_grader_count",
            "Crane": "active_crane_count",
            "Loader": "active_loader_count",
            "Wheel Loader": "active_loader_count",
            "Roller": "active_roller_count",
            "Compactor": "active_roller_count"
        }
        mix_mapped = mix_pivot[["site_id", "week_start"]].copy()
        standard_mix_cols = [
            "active_excavator_count", "active_bulldozer_count",
            "active_grader_count", "active_crane_count",
            "active_loader_count", "active_roller_count"
        ]
        for col in standard_mix_cols:
            mix_mapped[col] = 0

        for eq_col in mix_pivot.columns:
            if eq_col in ["site_id", "week_start"]:
                continue
            target_col = req_types.get(eq_col, f"active_{eq_col.lower().replace(' ', '_')}_count")
            if target_col not in mix_mapped.columns:
                mix_mapped[target_col] = 0
            mix_mapped[target_col] += mix_pivot[eq_col]

        site_agg = df_wd.groupby(["site_id", "week_start"])["current_demand"].agg(
            site_total_active_units="sum",
            site_active_equipment_type_count=lambda x: (x > 0).sum()
        ).reset_index()

        site_mix_df = pd.merge(mix_mapped, site_agg, on=["site_id", "week_start"])
        df_wd = pd.merge(df_wd, site_mix_df, on=["site_id", "week_start"], how="left")

        # Rental event features
        rental_records = (
            db.query(
                RentalLog.rental_id,
                RentalLog.check_in_date,
                RentalLog.check_out_date,
                RentalLog.site_id,
                Equipment.type.label("equipment_type")
            )
            .join(Equipment, RentalLog.equipment_id == Equipment.equipment_id)
            .all()
        )

        if rental_records:
            df_rental = pd.DataFrame([{
                "rental_id": r.rental_id,
                "check_in_date": r.check_in_date,
                "check_out_date": r.check_out_date,
                "site_id": r.site_id,
                "equipment_type": r.equipment_type
            } for r in rental_records]).dropna(subset=["site_id", "equipment_type"])

            df_rental["start_week_start"] = df_rental["check_in_date"].apply(get_monday_of_week)
            df_rental["end_week_start"] = df_rental["check_out_date"].apply(get_monday_of_week)

            starts_df = (
                df_rental.groupby(["site_id", "equipment_type", "start_week_start"])
                .size()
                .reset_index(name="rental_starts_current_week")
                .rename(columns={"start_week_start": "week_start"})
            )
            ends_df = (
                df_rental.groupby(["site_id", "equipment_type", "end_week_start"])
                .size()
                .reset_index(name="rental_ends_current_week")
                .rename(columns={"end_week_start": "week_start"})
            )
            df_wd = pd.merge(df_wd, starts_df, on=["site_id", "equipment_type", "week_start"], how="left")
            df_wd = pd.merge(df_wd, ends_df, on=["site_id", "equipment_type", "week_start"], how="left")
        else:
            df_wd["rental_starts_current_week"] = 0
            df_wd["rental_ends_current_week"] = 0

        df_wd["rental_starts_current_week"] = df_wd["rental_starts_current_week"].fillna(0).astype(int)
        df_wd["rental_ends_current_week"] = df_wd["rental_ends_current_week"].fillna(0).astype(int)

        rental_grp = df_wd.groupby(["site_id", "equipment_type"])
        df_wd["rental_starts_previous_2_weeks"] = (
            rental_grp["rental_starts_current_week"].shift(1).fillna(0) +
            rental_grp["rental_starts_current_week"].shift(2).fillna(0)
        ).astype(int)

        df_wd["rental_ends_previous_2_weeks"] = (
            rental_grp["rental_ends_current_week"].shift(1).fillna(0) +
            rental_grp["rental_ends_current_week"].shift(2).fillna(0)
        ).astype(int)

        # Impute missing values
        for col in ["demand_lag_1", "demand_lag_2", "demand_lag_4",
                    "demand_rolling_mean_4", "demand_rolling_max_4", "demand_rolling_std_4",
                    "demand_trend_4", "weeks_since_last_positive_demand"]:
            df_wd[col] = df_wd[col].fillna(0)

        for col in standard_mix_cols + ["site_total_active_units", "site_active_equipment_type_count"]:
            df_wd[col] = df_wd[col].fillna(0).astype(int)

        # Select latest week start
        latest_week_start = df_wd["week_start"].max()
        df_latest = df_wd[df_wd["week_start"] == latest_week_start].copy().reset_index(drop=True)

        # Association & transition features
        df_assoc = compute_row_association_features(df_latest, self.rules_df)
        df_trans = compute_row_transition_features(df_latest, self.trans_df)

        df_enhanced_latest = pd.concat([df_latest, df_assoc, df_trans], axis=1)
        return df_enhanced_latest, latest_week_start

    def predict_all_sites(self, db: Session) -> List[Dict[str, Any]]:
        """Generates demand forecasts for all site-equipment series."""
        if not self.is_loaded:
            self.load_model()

        df_features, latest_week = self.build_latest_feature_rows(db)

        ordered_features = self.metadata["all_features_ordered"]
        cat_features = set(self.metadata.get("categorical_features", ["site_id", "equipment_type"]))

        # Feature validation
        for col in ordered_features:
            if col not in df_features.columns:
                raise ValueError(f"Required feature '{col}' missing from inference features")

        X = df_features[ordered_features].copy()

        for col in ordered_features:
            if col in cat_features:
                X[col] = X[col].astype(str)
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)
                if np.any(np.isnan(X[col])) or np.any(np.isinf(X[col])):
                    raise ValueError(f"Feature '{col}' contains NaN or Inf values")

        # Run CatBoost Prediction
        raw_preds = np.clip(self.model.predict(X), 0.0, None)

        disp_inc = float(self.strategy["displayed_forecast"]["increase_threshold"])  # 0.05
        disp_dec = float(self.strategy["displayed_forecast"]["decrease_threshold"])  # 0.10
        alert_inc = float(self.strategy["shortage_alert"]["increase_threshold"])       # 0.20

        # Query site names for enriched output
        site_map = {s.site_id: s.site_name for s in db.query(Site).all()}

        results = []
        for idx, row in df_features.iterrows():
            s_id = str(row["site_id"])
            s_name = site_map.get(s_id, f"Site {s_id}")
            eq_type = str(row["equipment_type"])
            curr_d = int(row["current_demand"])
            r_pred = float(raw_preds[idx])

            r_change = r_pred - curr_d

            if r_change >= disp_inc:
                pred_d = max(0, int(round(r_pred)))
            elif r_change <= -disp_dec:
                pred_d = max(0, int(round(r_pred)))
            else:
                pred_d = curr_d

            shortage_risk = bool(r_change >= alert_inc)
            pred_change = int(pred_d - curr_d)
            add_units = max(0, int(pred_d - curr_d))

            if r_change >= 0.50:
                risk_level = "HIGH"
            elif r_change >= alert_inc:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            forecast_week_date = latest_week + datetime.timedelta(days=7)

            results.append({
                "site_id": s_id,
                "site_name": s_name,
                "equipment_type": eq_type,
                "source_week": latest_week.strftime("%Y-%m-%d"),
                "forecast_week": forecast_week_date.strftime("%Y-%m-%d"),
                "current_demand": curr_d,
                "raw_model_prediction": round(r_pred, 4),
                "predicted_demand": pred_d,
                "predicted_change": pred_change,
                "additional_units_needed": add_units,
                "shortage_risk": shortage_risk,
                "shortage_risk_level": risk_level,
                "model_version": self.metadata.get("model_version", "1.0.0"),
                "strategy_type": self.strategy.get("strategy_type", "calibrated_change_gated_hybrid")
            })

        return results

    def predict_site(self, site_id: str, db: Session) -> List[Dict[str, Any]]:
        """Returns demand forecasts for all equipment types at one site."""
        all_forecasts = self.predict_all_sites(db)
        site_forecasts = [f for f in all_forecasts if f["site_id"] == site_id]
        if not site_forecasts:
            raise KeyError(f"Site '{site_id}' not found")
        return site_forecasts

    def predict_single(self, site_id: str, equipment_type: str, db: Session) -> Dict[str, Any]:
        """Returns single forecast for specified site and equipment type."""
        all_forecasts = self.predict_all_sites(db)
        for f in all_forecasts:
            if f["site_id"] == site_id and f["equipment_type"] == equipment_type:
                return f
        raise KeyError(f"Forecast for site '{site_id}' and equipment '{equipment_type}' not found")

    def get_shortages(self, db: Session) -> List[Dict[str, Any]]:
        """Returns only forecasts where shortage_risk is True."""
        all_forecasts = self.predict_all_sites(db)
        return [f for f in all_forecasts if f["shortage_risk"]]

    def get_status(self, db: Session) -> Dict[str, Any]:
        """Returns forecast model service status."""
        if not self.is_loaded:
            try:
                self.load_model()
            except Exception as e:
                return {
                    "model_loaded": False,
                    "error": str(e)
                }

        forecasts = self.predict_all_sites(db)
        sites = set(f["site_id"] for f in forecasts)
        eq_types = set(f["equipment_type"] for f in forecasts)
        src_week = forecasts[0]["source_week"] if forecasts else ""
        f_week = forecasts[0]["forecast_week"] if forecasts else ""

        return {
            "model_loaded": True,
            "model_version": self.metadata.get("model_version", "1.0.0"),
            "selected_model_type": self.metadata.get("selected_model_type", "direct"),
            "strategy_type": self.strategy.get("strategy_type", "calibrated_change_gated_hybrid"),
            "source_latest_week": src_week,
            "forecast_week": f_week,
            "number_of_sites": len(sites),
            "number_of_equipment_types": len(eq_types)
        }


# Singleton instance
prediction_service = PredictionService()
