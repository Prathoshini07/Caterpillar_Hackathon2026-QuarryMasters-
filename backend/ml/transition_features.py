import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import pandas as pd
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal
from models import RentalLog, Equipment


def get_monday_of_week(dt: datetime.date) -> datetime.date:
    if not dt:
        return None
    return dt - datetime.timedelta(days=dt.weekday())


def learn_transition_probabilities(
    train_weeks: Set[datetime.date],
    output_path: Path
) -> pd.DataFrame:
    """
    Learn transition probabilities using training-period events only.
    """
    db = SessionLocal()
    try:
        query = (
            db.query(
                RentalLog.rental_id,
                RentalLog.check_in_date,
                RentalLog.check_out_date,
                RentalLog.site_id,
                Equipment.type.label("equipment_type")
            )
            .join(Equipment, RentalLog.equipment_id == Equipment.equipment_id)
            .filter(RentalLog.site_id.isnot(None))
            .all()
        )
        events_data = [{
            "rental_id": r.rental_id,
            "check_in_date": r.check_in_date,
            "check_out_date": r.check_out_date,
            "site_id": r.site_id,
            "equipment_type": r.equipment_type
        } for r in query]
    finally:
        db.close()

    if not events_data:
        print("[WARNING] No rental events found in database.")
        empty_trans = pd.DataFrame(columns=[
            "source_equipment_type", "source_event_type", "target_equipment_type",
            "source_count", "success_count", "raw_probability", "smoothed_probability"
        ])
        empty_trans.to_csv(output_path, index=False)
        return empty_trans

    df_events = pd.DataFrame(events_data)
    df_events["check_in_date"] = pd.to_datetime(df_events["check_in_date"]).dt.date
    df_events["check_out_date"] = pd.to_datetime(df_events["check_out_date"]).dt.date

    # Align to week_start Monday
    df_events["start_week_start"] = df_events["check_in_date"].apply(get_monday_of_week)
    df_events["end_week_start"] = df_events["check_out_date"].apply(get_monday_of_week)

    # Filter training-period events
    start_events_train = df_events[df_events["start_week_start"].isin(train_weeks)].copy()
    end_events_train = df_events[df_events["end_week_start"].isin(train_weeks)].copy()

    # Pre-group target starts by site_id and equipment_type
    target_starts_by_site_type: Dict[Tuple[str, str], List[datetime.date]] = {}
    for _, r in df_events.iterrows():
        target_starts_by_site_type.setdefault((r["site_id"], r["equipment_type"]), []).append(r["check_in_date"])

    unique_eq_types = sorted(list(set(df_events["equipment_type"].dropna())))
    transition_rows = []

    # 1. Start-to-Start transitions
    for src_type in unique_eq_types:
        src_starts = start_events_train[start_events_train["equipment_type"] == src_type]
        source_count = len(src_starts)

        for tgt_type in unique_eq_types:
            if src_type == tgt_type:
                continue

            success_count = 0
            for _, s_row in src_starts.iterrows():
                site = s_row["site_id"]
                s_date = s_row["check_in_date"]
                tgt_dates = target_starts_by_site_type.get((site, tgt_type), [])
                # Match target starts at same site within 14 days after s_date
                has_match = any(0 < (t_date - s_date).days <= 14 for t_date in tgt_dates)
                if has_match:
                    success_count += 1

            if source_count >= 10:
                raw_prob = success_count / source_count
                smooth_prob = (success_count + 1) / (source_count + 2)
                transition_rows.append({
                    "source_equipment_type": src_type,
                    "source_event_type": "Rental Start",
                    "target_equipment_type": tgt_type,
                    "source_count": source_count,
                    "success_count": success_count,
                    "raw_probability": raw_prob,
                    "smoothed_probability": smooth_prob
                })

    # 2. End-to-Start transitions
    for src_type in unique_eq_types:
        src_ends = end_events_train[end_events_train["equipment_type"] == src_type]
        source_count = len(src_ends)

        for tgt_type in unique_eq_types:
            if src_type == tgt_type:
                continue

            success_count = 0
            for _, e_row in src_ends.iterrows():
                site = e_row["site_id"]
                e_date = e_row["check_out_date"]
                tgt_dates = target_starts_by_site_type.get((site, tgt_type), [])
                has_match = any(0 < (t_date - e_date).days <= 14 for t_date in tgt_dates)
                if has_match:
                    success_count += 1

            if source_count >= 10:
                raw_prob = success_count / source_count
                smooth_prob = (success_count + 1) / (source_count + 2)
                transition_rows.append({
                    "source_equipment_type": src_type,
                    "source_event_type": "Rental End",
                    "target_equipment_type": tgt_type,
                    "source_count": source_count,
                    "success_count": success_count,
                    "raw_probability": raw_prob,
                    "smoothed_probability": smooth_prob
                })

    trans_df = pd.DataFrame(transition_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trans_df.to_csv(output_path, index=False)
    print(f"[TRANSITION] Learned & retained {len(trans_df)} transition relationships -> {output_path}")
    return trans_df


def compute_row_transition_features(
    df_base: pd.DataFrame,
    trans_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute row-level transition features for every row in base feature table.
    """
    db = SessionLocal()
    try:
        query = (
            db.query(
                RentalLog.check_in_date,
                RentalLog.check_out_date,
                RentalLog.site_id,
                Equipment.type.label("equipment_type")
            )
            .join(Equipment, RentalLog.equipment_id == Equipment.equipment_id)
            .filter(RentalLog.site_id.isnot(None))
            .all()
        )
        events_data = [{
            "check_in_date": r.check_in_date,
            "check_out_date": r.check_out_date,
            "site_id": r.site_id,
            "equipment_type": r.equipment_type
        } for r in query]
    finally:
        db.close()

    df_events = pd.DataFrame(events_data)

    # Pre-index events by site_id and week_start for lightning fast lookup
    start_events_by_site_week: Dict[Tuple[str, datetime.date], List[str]] = {}
    end_events_by_site_week: Dict[Tuple[str, datetime.date], List[str]] = {}

    if not df_events.empty:
        df_events["check_in_date"] = pd.to_datetime(df_events["check_in_date"]).dt.date
        df_events["check_out_date"] = pd.to_datetime(df_events["check_out_date"]).dt.date
        df_events["start_week_start"] = df_events["check_in_date"].apply(get_monday_of_week)
        df_events["end_week_start"] = df_events["check_out_date"].apply(get_monday_of_week)

        for _, r in df_events.iterrows():
            if pd.notna(r["start_week_start"]):
                start_events_by_site_week.setdefault((r["site_id"], r["start_week_start"]), []).append(r["equipment_type"])
            if pd.notna(r["end_week_start"]):
                end_events_by_site_week.setdefault((r["site_id"], r["end_week_start"]), []).append(r["equipment_type"])

    start_trans_by_target: Dict[str, Dict[str, float]] = {}
    end_trans_by_target: Dict[str, Dict[str, float]] = {}

    if not trans_df.empty:
        for _, r in trans_df.iterrows():
            src = str(r["source_equipment_type"])
            ev_type = str(r["source_event_type"])
            tgt = str(r["target_equipment_type"])
            prob = float(r["smoothed_probability"])

            if ev_type == "Rental Start":
                start_trans_by_target.setdefault(tgt, {})[src] = prob
            elif ev_type == "Rental End":
                end_trans_by_target.setdefault(tgt, {})[src] = prob

    results = []
    for _, row in df_base.iterrows():
        site_id = row["site_id"]
        w_start = row["week_start"]
        prev_w_start = w_start - datetime.timedelta(days=7)
        target_eq = row["equipment_type"]

        # Starts in W or W-1 at site_id
        starts_in_window = (
            start_events_by_site_week.get((site_id, w_start), []) +
            start_events_by_site_week.get((site_id, prev_w_start), [])
        )
        # Ends in W or W-1 at site_id
        ends_in_window = (
            end_events_by_site_week.get((site_id, w_start), []) +
            end_events_by_site_week.get((site_id, prev_w_start), [])
        )

        start_map = start_trans_by_target.get(target_eq, {})
        start_trigger_probs = [start_map[src] for src in starts_in_window if src in start_map]

        end_map = end_trans_by_target.get(target_eq, {})
        end_trigger_probs = [end_map[src] for src in ends_in_window if src in end_map]

        if not start_trigger_probs:
            n_start = 0
            max_start_prob = 0.0
            mean_start_prob = 0.0
        else:
            n_start = len(start_trigger_probs)
            max_start_prob = float(np.max(start_trigger_probs))
            mean_start_prob = float(np.mean(start_trigger_probs))

        if not end_trigger_probs:
            n_end = 0
            max_end_prob = 0.0
            mean_end_prob = 0.0
        else:
            n_end = len(end_trigger_probs)
            max_end_prob = float(np.max(end_trigger_probs))
            mean_end_prob = float(np.mean(end_trigger_probs))

        results.append({
            "transition_recent_start_trigger_count": n_start,
            "transition_max_start_probability": max_start_prob,
            "transition_mean_start_probability": mean_start_prob,
            "transition_recent_end_trigger_count": n_end,
            "transition_max_end_probability": max_end_prob,
            "transition_mean_end_probability": mean_end_prob
        })

    return pd.DataFrame(results, index=df_base.index)
