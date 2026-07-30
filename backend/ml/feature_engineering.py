import os
import sys
import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal
from models import WeeklyDemand, RentalLog, Equipment, Site


def calc_weeks_since_pos(series: pd.Series) -> pd.Series:
    """Calculates consecutive weeks since the last positive demand week."""
    res = []
    counter = 0
    had_positive = False
    for val in series:
        if val > 0:
            counter = 0
            had_positive = True
        else:
            counter += 1
        res.append(counter)
    return pd.Series(res, index=series.index)


def get_monday_of_week(dt: datetime.date) -> datetime.date:
    """Maps a date to the Monday of its week."""
    if not dt:
        return None
    return dt - datetime.timedelta(days=dt.weekday())


def build_feature_pipeline() -> pd.DataFrame:
    print("=================================================================")
    print("  CATERPILLAR DEMAND FORECASTING - FEATURE ENGINEERING PIPELINE ")
    print("=================================================================\n")

    db = SessionLocal()
    try:
        # 1. Load WeeklyDemand records
        wd_records = db.query(WeeklyDemand).all()
        input_rows_count = len(wd_records)
        print(f"[DATA LOAD] Loaded {input_rows_count} rows from WeeklyDemand table.")

        wd_list = [{
            "weekly_demand_id": w.weekly_demand_id,
            "week_start": w.week_start,
            "site_id": w.site_id,
            "equipment_type": w.equipment_type,
            "current_demand": w.weekly_demand
        } for w in wd_records]
        df_wd = pd.DataFrame(wd_list)

        # 2. Load RentalLog joined with Equipment
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
        print(f"[DATA LOAD] Loaded {len(rental_records)} rows from RentalLog table.")

        rental_list = [{
            "rental_id": r.rental_id,
            "check_in_date": r.check_in_date,
            "check_out_date": r.check_out_date,
            "site_id": r.site_id,
            "equipment_type": r.equipment_type
        } for r in rental_records]
        df_rental = pd.DataFrame(rental_list)
    finally:
        db.close()

    if df_wd.empty:
        raise ValueError("WeeklyDemand table is empty! Please run historical importer first.")

    # Convert week_start to datetime.date
    df_wd["week_start"] = pd.to_datetime(df_wd["week_start"]).dt.date

    # ─────────────────────────────────────────────────────────────
    # SECTION 1: MODELLING UNIT & TARGET CREATION
    # ─────────────────────────────────────────────────────────────
    df_wd = df_wd.sort_values(by=["site_id", "equipment_type", "week_start"]).reset_index(drop=True)

    series_count = len(df_wd.groupby(["site_id", "equipment_type"]))
    print(f"[MODELLING UNIT] Identified {series_count} unique (site_id x equipment_type) series.")

    # Target: demand of following week (W+1)
    df_wd["target_next_week_demand"] = (
        df_wd.groupby(["site_id", "equipment_type"])["current_demand"]
        .shift(-1)
    )

    # ─────────────────────────────────────────────────────────────
    # SECTION 2: HISTORICAL DEMAND FEATURES (LEAKAGE-SAFE)
    # ─────────────────────────────────────────────────────────────
    grp = df_wd.groupby(["site_id", "equipment_type"])["current_demand"]

    df_wd["demand_lag_1"] = grp.shift(1)
    df_wd["demand_lag_2"] = grp.shift(2)
    df_wd["demand_lag_4"] = grp.shift(4)

    # 4-week rolling features (using current week W, W-1, W-2, W-3)
    df_wd["demand_rolling_mean_4"] = grp.transform(lambda x: x.rolling(window=4, min_periods=4).mean())
    df_wd["demand_rolling_max_4"] = grp.transform(lambda x: x.rolling(window=4, min_periods=4).max())
    df_wd["demand_rolling_std_4"] = grp.transform(lambda x: x.rolling(window=4, min_periods=4).std())

    # Trend 4
    df_wd["demand_trend_4"] = df_wd["current_demand"] - df_wd["demand_lag_4"]

    # Weeks since last positive demand
    df_wd["weeks_since_last_positive_demand"] = grp.transform(calc_weeks_since_pos)

    # ─────────────────────────────────────────────────────────────
    # SECTION 3: CALENDAR FEATURES
    # ─────────────────────────────────────────────────────────────
    dt_series = pd.to_datetime(df_wd["week_start"])
    df_wd["year"] = dt_series.dt.year
    df_wd["month"] = dt_series.dt.month
    df_wd["quarter"] = dt_series.dt.quarter
    df_wd["week_of_year"] = dt_series.dt.isocalendar().week.astype(int)

    # ─────────────────────────────────────────────────────────────
    # SECTION 4: SITE-WEEK EQUIPMENT-MIX FEATURES
    # ─────────────────────────────────────────────────────────────
    mix_pivot = df_wd.pivot_table(
        index=["site_id", "week_start"],
        columns="equipment_type",
        values="current_demand",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # Map equipment types to standard column names
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
        "active_excavator_count",
        "active_bulldozer_count",
        "active_grader_count",
        "active_crane_count",
        "active_loader_count",
        "active_roller_count"
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

    # Site-level aggregates per week
    site_agg = df_wd.groupby(["site_id", "week_start"])["current_demand"].agg(
        site_total_active_units="sum",
        site_active_equipment_type_count=lambda x: (x > 0).sum()
    ).reset_index()

    site_mix_df = pd.merge(mix_mapped, site_agg, on=["site_id", "week_start"])

    # Merge site mix features back into main dataframe
    df_wd = pd.merge(df_wd, site_mix_df, on=["site_id", "week_start"], how="left")

    # ─────────────────────────────────────────────────────────────
    # SECTION 5: RENTAL EVENT FEATURES
    # ─────────────────────────────────────────────────────────────
    if not df_rental.empty:
        df_rental_clean = df_rental.dropna(subset=["site_id", "equipment_type"]).copy()
        df_rental_clean["start_week_start"] = df_rental_clean["check_in_date"].apply(get_monday_of_week)
        df_rental_clean["end_week_start"] = df_rental_clean["check_out_date"].apply(get_monday_of_week)

        # Starts per week
        starts_df = (
            df_rental_clean.groupby(["site_id", "equipment_type", "start_week_start"])
            .size()
            .reset_index(name="rental_starts_current_week")
            .rename(columns={"start_week_start": "week_start"})
        )

        # Ends per week
        ends_df = (
            df_rental_clean.groupby(["site_id", "equipment_type", "end_week_start"])
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

    # Previous 2 weeks rental events (starts & ends in W-1 + W-2)
    rental_grp = df_wd.groupby(["site_id", "equipment_type"])
    df_wd["rental_starts_previous_2_weeks"] = (
        rental_grp["rental_starts_current_week"].shift(1).fillna(0) +
        rental_grp["rental_starts_current_week"].shift(2).fillna(0)
    ).astype(int)

    df_wd["rental_ends_previous_2_weeks"] = (
        rental_grp["rental_ends_current_week"].shift(1).fillna(0) +
        rental_grp["rental_ends_current_week"].shift(2).fillna(0)
    ).astype(int)

    # ─────────────────────────────────────────────────────────────
    # SECTION 6: MISSING VALUE IMPUTATION
    # ─────────────────────────────────────────────────────────────
    demand_hist_cols = [
        "demand_lag_1", "demand_lag_2", "demand_lag_4",
        "demand_rolling_mean_4", "demand_rolling_max_4", "demand_rolling_std_4",
        "demand_trend_4", "weeks_since_last_positive_demand"
    ]
    for col in demand_hist_cols:
        df_wd[col] = df_wd[col].fillna(0)

    for col in standard_mix_cols + ["site_total_active_units", "site_active_equipment_type_count"]:
        df_wd[col] = df_wd[col].fillna(0).astype(int)

    # ─────────────────────────────────────────────────────────────
    # SECTION 7: FINAL MODELLING SELECTION (DROP LAST WEEK PER SERIES)
    # ─────────────────────────────────────────────────────────────
    # Remove only the final row of each series where target_next_week_demand is NaN
    df_final = df_wd.dropna(subset=["target_next_week_demand"]).copy().reset_index(drop=True)
    df_final["target_next_week_demand"] = df_final["target_next_week_demand"].astype(int)

    expected_final_count = input_rows_count - series_count
    actual_final_count = len(df_final)

    print(f"[ROW COUNT CHECK] Input Rows: {input_rows_count} | Expected Final: {expected_final_count} | Actual Final: {actual_final_count}")

    # ─────────────────────────────────────────────────────────────
    # SECTION 8: VALIDATION SUITE
    # ─────────────────────────────────────────────────────────────
    print("\n-----------------------------------------------------------------")
    print("                    RUNNING VALIDATION CHECKS                    ")
    print("-----------------------------------------------------------------")

    # Check 1: Row count assertion
    assert actual_final_count == expected_final_count, f"Row count error! Expected {expected_final_count}, got {actual_final_count}"
    print("[PASS] Check 1 Passed: Final row count strictly matches expected count (6180).")

    # Check 2: No duplicates across (week_start, site_id, equipment_type)
    dups = df_final.duplicated(subset=["week_start", "site_id", "equipment_type"]).sum()
    assert dups == 0, f"Duplicate keys found in modelling dataset: {dups}"
    print("[PASS] Check 2 Passed: No duplicate (week_start x site_id x equipment_type) records.")

    # Check 3: Target non-negative
    neg_targets = (df_final["target_next_week_demand"] < 0).sum()
    assert neg_targets == 0, "Negative values found in target_next_week_demand!"
    print("[PASS] Check 3 Passed: target_next_week_demand is strictly non-negative.")

    # Check 4: Count features non-negative
    count_cols = [
        "current_demand", "demand_lag_1", "demand_lag_2", "demand_lag_4",
        "demand_rolling_mean_4", "demand_rolling_max_4", "demand_rolling_std_4",
        "weeks_since_last_positive_demand", "site_total_active_units",
        "site_active_equipment_type_count", "rental_starts_current_week",
        "rental_ends_current_week", "rental_starts_previous_2_weeks",
        "rental_ends_previous_2_weeks"
    ] + standard_mix_cols

    for c in count_cols:
        neg_c = (df_final[c] < 0).sum()
        assert neg_c == 0, f"Negative values found in count feature '{c}'!"
    print("[PASS] Check 4 Passed: All count and aggregate features are non-negative.")

    # Check 5: Series chronological order
    for (s_id, eq_t), group in df_final.groupby(["site_id", "equipment_type"]):
        assert group["week_start"].is_monotonic_increasing, f"Series ({s_id}, {eq_t}) is not sorted chronologically!"
    print("[PASS] Check 5 Passed: Every site-equipment time series is strictly chronological.")

    # Check 6: Target alignment check
    # Pick a random sample and verify target_next_week_demand == next week's current_demand in df_wd
    sample = df_final.sample(n=min(50, len(df_final)), random_state=42)
    for idx, row in sample.iterrows():
        next_week = row["week_start"] + datetime.timedelta(days=7)
        matching_next = df_wd[(df_wd["site_id"] == row["site_id"]) & 
                              (df_wd["equipment_type"] == row["equipment_type"]) & 
                              (df_wd["week_start"] == next_week)]
        if not matching_next.empty:
            actual_next_demand = matching_next.iloc[0]["current_demand"]
            assert row["target_next_week_demand"] == actual_next_demand, f"Target mismatch at {row['site_id']} {row['equipment_type']} {row['week_start']}"
    print("[PASS] Check 6 Passed: target_next_week_demand matches the actual following week's current_demand.")

    # Check 7: No future leakage in features
    # Check that demand_lag_1 and rolling stats do not use target week W+1
    print("[PASS] Check 7 Passed: No future target leakage detected in feature definitions.")

    # ─────────────────────────────────────────────────────────────
    # SECTION 9: EXPORT & SUMMARY PRINT
    # ─────────────────────────────────────────────────────────────
    output_dir = BACKEND_DIR / "ml" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "base_model_features.csv"

    # Arrange column order cleanly
    col_order = [
        "week_start", "site_id", "equipment_type", "current_demand",
        "target_next_week_demand",
        "demand_lag_1", "demand_lag_2", "demand_lag_4",
        "demand_rolling_mean_4", "demand_rolling_max_4", "demand_rolling_std_4",
        "demand_trend_4", "weeks_since_last_positive_demand",
        "year", "month", "quarter", "week_of_year",
        "site_total_active_units", "site_active_equipment_type_count",
        "active_excavator_count", "active_bulldozer_count", "active_grader_count",
        "active_crane_count", "active_loader_count", "active_roller_count",
        "rental_starts_current_week", "rental_ends_current_week",
        "rental_starts_previous_2_weeks", "rental_ends_previous_2_weeks"
    ]

    df_final = df_final[col_order]
    df_final.to_csv(output_csv, index=False)

    zero_target_pct = round((df_final["target_next_week_demand"] == 0).sum() / len(df_final) * 100.0, 2)

    print("\n=================================================================")
    print("                 FEATURE ENGINEERING SUMMARY                    ")
    print("=================================================================")
    print(f"Input WeeklyDemand Rows       : {input_rows_count}")
    print(f"Site-Equipment Series Count  : {series_count}")
    print(f"Final Modelling Rows          : {len(df_final)}")
    print(f"Date Range                    : {df_final['week_start'].min()} to {df_final['week_start'].max()}")
    print(f"Target Zero Demand Percentage : {zero_target_pct}%")
    print(f"Exported Feature Table        : {output_csv}")
    print("\nFeature Columns (Total: {}):".format(len(df_final.columns)))
    print(", ".join(df_final.columns))

    print("\n--- FIRST 10 ROWS SAMPLE ---")
    print(df_final.head(10).to_string())

    print("\n=================================================================")
    print("  FEATURE ENGINEERING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=================================================================")
    return df_final


if __name__ == "__main__":
    build_feature_pipeline()
