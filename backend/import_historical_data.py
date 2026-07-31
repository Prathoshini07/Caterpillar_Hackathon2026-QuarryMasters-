import os
import sys
import csv
import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set

from database import SessionLocal, engine
from models import Site, Operator, Equipment, RentalLog, DemandForecast, WeeklyDemand

# ─────────────────────────────────────────────────────────────
# Normalization Mappings
# ─────────────────────────────────────────────────────────────

STATUS_MAP = {
    "Available": "AVAILABLE",
    "AVAILABLE": "AVAILABLE",
    "In Use": "RENTED",
    "RENTED": "RENTED",
    "Idle": "UNDERUTILIZED",
    "UNDERUTILIZED": "UNDERUTILIZED",
    "Under Maintenance": "MAINTENANCE",
    "MAINTENANCE": "MAINTENANCE"
}

ANOMALY_MAP = {
    "Missing Operator": "UNASSIGNED_USAGE",
    "High Idle Time": "HIGH_IDLE_RATIO",
    "Overdue Equipment": "OVERDUE_BREACH",
    "Under-utilised": "UNDERUTILIZED",
    "": "OPTIMAL",
    None: "OPTIMAL"
}


def normalize_rental_id(raw_id: Any) -> str:
    raw_str = str(raw_id).strip() if raw_id is not None else ""
    if raw_str.isdigit():
        return f"RNT{int(raw_str):06d}"
    return raw_str


def parse_date(date_str: Any) -> datetime.date:
    if not date_str or str(date_str).strip() in ("", "None", "null"):
        return None
    return datetime.date.fromisoformat(str(date_str).strip())


def parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "t", "y", "yes")

def calculate_total_engine_hours(
    engine_hours_per_day: float,
    rental_days: int,
) -> float:
    """Calculate total engine hours for an imported historical rental."""
    return round(
        max(0.0, engine_hours_per_day) * max(0, rental_days),
        2,
    )


def resolve_data_dir(custom_path: str = None) -> Path:
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists() and p.is_dir():
            return p
        raise FileNotFoundError(f"Specified data directory '{custom_path}' does not exist.")

    candidates = [
        Path.cwd() / "synthetic_rental_output",
        Path.cwd().parent / "synthetic_rental_output",
        Path.cwd().parent.parent / "synthetic_rental_output",
        Path(__file__).resolve().parent / "synthetic_rental_output",
        Path(__file__).resolve().parent.parent / "synthetic_rental_output",
        Path(__file__).resolve().parent.parent.parent / "synthetic_rental_output",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()

    raise FileNotFoundError("Could not locate 'synthetic_rental_output' directory. Please specify with --data-dir.")


def read_csv_rows(file_path: Path) -> List[Dict[str, str]]:
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def validate_legacy_dataset(db) -> Tuple[bool, List[str]]:
    """Verify that the database currently contains only the legacy demonstration dataset."""
    reasons = []
    wd_count = db.query(WeeklyDemand).count()
    s_count = db.query(Site).count()
    o_count = db.query(Operator).count()
    e_count = db.query(Equipment).count()
    r_count = db.query(RentalLog).count()

    if wd_count != 0:
        reasons.append(f"WeeklyDemand count is {wd_count} (expected 0).")
    if s_count != 100:
        reasons.append(f"Site count is {s_count} (expected 100).")
    if o_count != 100:
        reasons.append(f"Operator count is {o_count} (expected 100).")
    if e_count != 100:
        reasons.append(f"Equipment count is {e_count} (expected 100).")
    if r_count != 100:
        reasons.append(f"RentalLog count is {r_count} (expected 100).")

    site_ids = {s.site_id for s in db.query(Site.site_id).all()}
    expected_site_ids = {f"S{i:03d}" for i in range(1, 101)}
    if site_ids != expected_site_ids:
        reasons.append("Site IDs do not match expected legacy pattern S001 to S100.")

    op_ids = {o.operator_id for o in db.query(Operator.operator_id).all()}
    expected_op_ids = {f"OP{100+i}" for i in range(1, 101)}
    if op_ids != expected_op_ids:
        reasons.append("Operator IDs do not match expected legacy pattern OP101 to OP200.")

    eq_ids = {e.equipment_id for e in db.query(Equipment.equipment_id).all()}
    expected_eq_ids = {f"EQX{1000+i}" for i in range(1, 101)}
    if eq_ids != expected_eq_ids:
        reasons.append("Equipment IDs do not match expected legacy pattern EQX1001 to EQX1100.")

    is_legacy = len(reasons) == 0
    return is_legacy, reasons


def verify_post_import(db, expected_counts: Dict[str, int]):
    """Comprehensive post-import verification logic."""
    print("\n=================================================================")
    print("                 POST-IMPORT INTEGRITY VERIFICATION              ")
    print("=================================================================")

    actual_sites = db.query(Site).count()
    actual_operators = db.query(Operator).count()
    actual_equipment = db.query(Equipment).count()
    actual_rental_logs = db.query(RentalLog).count()
    actual_weekly_demand = db.query(WeeklyDemand).count()
    actual_forecasts = db.query(DemandForecast).count()

    print(f"Sites            : {actual_sites} (expected {expected_counts['sites']})")
    print(f"Operators        : {actual_operators} (expected {expected_counts['operators']})")
    print(f"Equipment        : {actual_equipment} (expected {expected_counts['equipment']})")
    print(f"Rental Logs      : {actual_rental_logs} (expected {expected_counts['rental_logs']})")
    print(f"Weekly Demand    : {actual_weekly_demand} (expected {expected_counts['weekly_demand']})")
    print(f"Demand Forecasts : {actual_forecasts} (expected 0)")

    assert actual_sites == expected_counts['sites'], "Site count mismatch!"
    assert actual_operators == expected_counts['operators'], "Operator count mismatch!"
    assert actual_equipment == expected_counts['equipment'], "Equipment count mismatch!"
    assert actual_rental_logs == expected_counts['rental_logs'], "RentalLog count mismatch!"
    assert actual_weekly_demand == expected_counts['weekly_demand'], "WeeklyDemand count mismatch!"
    assert actual_forecasts == 0, "DemandForecast table must remain empty!"

    # Status Format Checks
    valid_statuses = {"AVAILABLE", "RENTED", "UNDERUTILIZED", "MAINTENANCE"}
    eq_statuses = set(e.status for e in db.query(Equipment.status).all())
    invalid_statuses = eq_statuses - valid_statuses
    assert len(invalid_statuses) == 0, f"Invalid equipment statuses found: {invalid_statuses}"

    # Unique Constraint Check on WeeklyDemand
    all_wd_keys = [(w.week_start, w.site_id, w.equipment_type) for w in db.query(WeeklyDemand.week_start, WeeklyDemand.site_id, WeeklyDemand.equipment_type).all()]
    assert len(all_wd_keys) == len(set(all_wd_keys)), "Duplicate WeeklyDemand unique key combinations found!"

    # FK Integrity Checks
    site_ids = set(s.site_id for s in db.query(Site.site_id).all())
    op_ids = set(o.operator_id for o in db.query(Operator.operator_id).all())
    eq_ids = set(e.equipment_id for e in db.query(Equipment.equipment_id).all())

    for eq in db.query(Equipment).all():
        if eq.current_site_id:
            assert eq.current_site_id in site_ids, f"Orphaned Equipment current_site_id '{eq.current_site_id}'"
        if eq.assigned_operator_id:
            assert eq.assigned_operator_id in op_ids, f"Orphaned Equipment assigned_operator_id '{eq.assigned_operator_id}'"

    for r in db.query(RentalLog).all():
        assert r.equipment_id in eq_ids, f"Orphaned RentalLog equipment_id '{r.equipment_id}'"
        if r.site_id:
            assert r.site_id in site_ids, f"Orphaned RentalLog site_id '{r.site_id}'"
        if r.operator_id:
            assert r.operator_id in op_ids, f"Orphaned RentalLog operator_id '{r.operator_id}'"

    for w in db.query(WeeklyDemand).all():
        assert w.site_id in site_ids, f"Orphaned WeeklyDemand site_id '{w.site_id}'"

    # Overlapping Rentals Check
    rentals_by_eq: Dict[str, List[Tuple[datetime.date, datetime.date, str]]] = {}
    for r in db.query(RentalLog).all():
        rentals_by_eq.setdefault(r.equipment_id, []).append((r.check_in_date, r.check_out_date, r.rental_id))

    overlap_count = 0
    for eq_id, ranges in rentals_by_eq.items():
        sorted_ranges = sorted(ranges, key=lambda x: x[0])
        for i in range(len(sorted_ranges) - 1):
            cur_in, cur_out, cur_id = sorted_ranges[i]
            next_in, next_out, next_id = sorted_ranges[i+1]
            if cur_out > next_in:
                overlap_count += 1

    print(f"Overlapping Rental Contracts : {overlap_count}")
    print("-----------------------------------------------------------------")
    print("✅ POST-IMPORT INTEGRITY VERIFICATION PASSED PERFECTLY!")
    print("=================================================================")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Historical dataset validator & importer for Caterpillar Smart Rental Tracking System.")
    parser.add_argument("--commit", action="store_true", help="Execute the database import in a single transaction. (Default is dry-run)")
    parser.add_argument("--replace-legacy", action="store_true", help="Safely replace existing demonstration legacy seed dataset with synthetic dataset.")
    parser.add_argument("--data-dir", type=str, help="Custom directory containing synthetic CSV files.")
    args = parser.parse_args()

    try:
        data_dir = resolve_data_dir(args.data_dir)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print("=================================================================")
    print("      CATERPILLAR HISTORICAL DATA IMPORTER & VALIDATOR          ")
    print("=================================================================")
    print(f"Data Directory : {data_dir}")
    print(f"Execution Mode : {'COMMIT MODE (Database will be updated)' if args.commit else 'DRY-RUN MODE (No database changes will be made)'}")
    print(f"Replace Legacy : {'YES (Legacy demonstration dataset replacement)' if args.replace_legacy else 'NO (Normal incremental validation)'}")
    print("=================================================================\n")

    db = SessionLocal()

    try:
        # Read CSV file rows
        sites_file = data_dir / "sites.csv"
        operators_file = data_dir / "operators.csv"
        equipment_file = data_dir / "equipment.csv"
        rental_logs_file = data_dir / "rental_logs.csv"
        weekly_demand_file = data_dir / "weekly_demand.csv"

        site_rows = read_csv_rows(sites_file)
        operator_rows = read_csv_rows(operators_file)
        equipment_rows = read_csv_rows(equipment_file)
        rental_log_rows = read_csv_rows(rental_logs_file)
        weekly_rows = read_csv_rows(weekly_demand_file)

        # ─────────────────────────────────────────────────────────────
        # REPLACEMENT MODE (--replace-legacy)
        # ─────────────────────────────────────────────────────────────
        if args.replace_legacy:
            is_legacy, reasons = validate_legacy_dataset(db)
            if not is_legacy:
                print("[ERROR] Database does NOT match expected legacy seed dataset!")
                print("Refusing to replace database contents. Reasons:")
                for r in reasons:
                    print(f"  - {r}")
                print("The database may contain non-legacy or user-created records.")
                sys.exit(1)

            print("LEGACY DATASET DETECTED")
            print("The following legacy records will be deleted:")
            print(f"  - Demand Forecasts : {db.query(DemandForecast).count()}")
            print(f"  - Weekly Demand    : {db.query(WeeklyDemand).count()}")
            print(f"  - Rental Logs      : {db.query(RentalLog).count()}")
            print(f"  - Equipment        : {db.query(Equipment).count()}")
            print(f"  - Operators        : {db.query(Operator).count()}")
            print(f"  - Sites            : {db.query(Site).count()}\n")

            # Parse synthetic records assuming clean target environment
            sites_to_insert: List[Site] = []
            operators_to_insert: List[Operator] = []
            equipment_to_insert: List[Equipment] = []
            rental_logs_to_insert: List[RentalLog] = []
            weekly_demand_to_insert: List[WeeklyDemand] = []

            valid_sites_set: Set[str] = set()
            valid_operators_set: Set[str] = set()
            valid_equipment_set: Set[str] = set()
            site_location_map: Dict[str, str] = {}

            # Sites
            for idx, row in enumerate(site_rows, start=2):
                s_id = row.get("site_id", "").strip()
                name = row.get("site_name", "").strip()
                loc = row.get("location", "").strip()
                if s_id and s_id not in valid_sites_set:
                    valid_sites_set.add(s_id)
                    site_location_map[s_id] = loc
                    sites_to_insert.append(Site(site_id=s_id, site_name=name, location=loc))

            # Operators
            for idx, row in enumerate(operator_rows, start=2):
                op_id = row.get("operator_id", "").strip()
                name = row.get("name", "").strip()
                contact = row.get("contact_info", "").strip()
                if op_id and op_id not in valid_operators_set:
                    valid_operators_set.add(op_id)
                    operators_to_insert.append(Operator(operator_id=op_id, name=name, contact_info=contact))

            # Equipment
            for idx, row in enumerate(equipment_rows, start=2):
                eq_id = row.get("equipment_id", "").strip()
                eq_type = row.get("type", "").strip()
                raw_status = row.get("status", "").strip()
                s_id = row.get("current_site_id", "").strip() or None
                op_id = row.get("assigned_operator_id", "").strip() or None

                norm_status = STATUS_MAP.get(raw_status)
                if not norm_status:
                    raise ValueError(f"[equipment.csv:Row {idx}] Invalid equipment status '{raw_status}'")

                if eq_id and eq_id not in valid_equipment_set:
                    valid_equipment_set.add(eq_id)
                    equipment_to_insert.append(Equipment(
                        equipment_id=eq_id,
                        type=eq_type,
                        status=norm_status,
                        current_site_id=s_id,
                        assigned_operator_id=op_id,
                        cumulative_engine_hours=0.0,
                    ))

            # Rental Logs
            seen_rentals: Set[str] = set()
            for idx, row in enumerate(rental_log_rows, start=2):
                r_id = normalize_rental_id(row.get("rental_id"))
                eq_id = row.get("equipment_id", "").strip()
                s_id = row.get("site_id", "").strip() or None
                op_id = row.get("operator_id", "").strip() or None
                c_in = parse_date(row.get("check_in_date"))
                c_out = parse_date(row.get("check_out_date"))
                eng_hrs = float(row.get("engine_hours_per_day", 0))
                idle_hrs = float(row.get("idle_hours_per_day", 0))
                r_days = int(row.get("rental_days", 0))
                total_engine_hours = calculate_total_engine_hours(
                    eng_hrs,
                    r_days,
                )

                is_overdue = parse_bool(row.get("is_overdue"))
                raw_anomaly = row.get("anomaly_flag", "").strip() if row.get("anomaly_flag") else ""
                norm_anomaly = ANOMALY_MAP.get(raw_anomaly, raw_anomaly or "OPTIMAL")

                if r_id and r_id not in seen_rentals:
                    seen_rentals.add(r_id)
                    rental_logs_to_insert.append(RentalLog(
                        rental_id=r_id,
                        equipment_id=eq_id,
                        site_id=s_id,
                        operator_id=op_id,
                        check_in_date=c_in,
                        check_out_date=c_out,
                        engine_hours_per_day=eng_hrs,
                        idle_hours_per_day=idle_hrs,
                        rental_days=r_days,
                        is_overdue=is_overdue,
                        anomaly_flag=norm_anomaly,
                        location=site_location_map.get(s_id) if s_id else None,
                        fuel_usage_liters=None,
                        total_engine_hours=total_engine_hours,
                        accumulated_idle_penalty_usd=0.0,
                        last_serviced_engine_hours=0.0,
                    ))

            # Weekly Demand
            seen_wd: Set[Tuple[datetime.date, str, str]] = set()
            for idx, row in enumerate(weekly_rows, start=2):
                w_start = parse_date(row.get("week_start"))
                s_id = row.get("site_id", "").strip()
                eq_type = row.get("equipment_type", "").strip()
                d_val = int(row.get("weekly_demand", 0))

                w_key = (w_start, s_id, eq_type)
                if w_key not in seen_wd:
                    seen_wd.add(w_key)
                    weekly_demand_to_insert.append(WeeklyDemand(
                        week_start=w_start,
                        site_id=s_id,
                        equipment_type=eq_type,
                        weekly_demand=d_val
                    ))

            print("The following synthetic records will be inserted:")
            print(f"  - Sites            : {len(sites_to_insert)}")
            print(f"  - Operators        : {len(operators_to_insert)}")
            print(f"  - Equipment        : {len(equipment_to_insert)}")
            print(f"  - Rental Logs      : {len(rental_logs_to_insert)}")
            print(f"  - Weekly Demand    : {len(weekly_demand_to_insert)}")
            print(f"  - Demand Forecasts : 0\n")

            if not args.commit:
                print("-----------------------------------------------------------------")
                print("  DRY-RUN COMPLETE: NO DATABASE CHANGES WERE MADE.              ")
                print("  To perform actual legacy replacement & import, execute:        ")
                print("    python import_historical_data.py --replace-legacy --commit  ")
                print("-----------------------------------------------------------------")
                return

            print("[COMMIT MODE] Executing legacy deletion and synthetic import in single transaction...")
            # 1. Delete in FK-safe order
            db.query(DemandForecast).delete()
            db.query(WeeklyDemand).delete()
            db.query(RentalLog).delete()
            db.query(Equipment).delete()
            db.query(Operator).delete()
            db.query(Site).delete()
            db.flush()

            # 2. Insert synthetic records in FK-safe order
            db.add_all(sites_to_insert)
            db.flush()
            db.add_all(operators_to_insert)
            db.flush()
            db.add_all(equipment_to_insert)
            db.flush()
            db.add_all(rental_logs_to_insert)
            db.flush()
            db.add_all(weekly_demand_to_insert)
            db.commit()

            print("\n=================================================================")
            print("  SUCCESS: Legacy dataset replaced with synthetic dataset!        ")
            print("=================================================================")

            verify_post_import(db, {
                "sites": len(sites_to_insert),
                "operators": len(operators_to_insert),
                "equipment": len(equipment_to_insert),
                "rental_logs": len(rental_logs_to_insert),
                "weekly_demand": len(weekly_demand_to_insert)
            })
            return

        # ─────────────────────────────────────────────────────────────
        # INCREMENTAL / NORMAL MODE (no --replace-legacy)
        # ─────────────────────────────────────────────────────────────
        db_sites = {s.site_id: s for s in db.query(Site).all()}
        db_operators = {o.operator_id: o for o in db.query(Operator).all()}
        db_equipment = {e.equipment_id: e for e in db.query(Equipment).all()}
        db_rental_logs = {r.rental_id: r for r in db.query(RentalLog).all()}
        db_weekly_demand = {(w.week_start, w.site_id, w.equipment_type): w for w in db.query(WeeklyDemand).all()}

        print("--- CURRENT DATABASE COUNTS BEFORE IMPORT ---")
        print(f"Sites            : {len(db_sites)}")
        print(f"Operators        : {len(db_operators)}")
        print(f"Equipment        : {len(db_equipment)}")
        print(f"Rental Logs      : {len(db_rental_logs)}")
        print(f"Weekly Demand    : {len(db_weekly_demand)}")
        print("---------------------------------------------\n")

        summary = {
            "Sites": {"INSERT": 0, "IDENTICAL": 0, "CONFLICT": 0, "REJECTED": 0},
            "Operators": {"INSERT": 0, "IDENTICAL": 0, "CONFLICT": 0, "REJECTED": 0},
            "Equipment": {"INSERT": 0, "IDENTICAL": 0, "CONFLICT": 0, "REJECTED": 0},
            "Rental Logs": {"INSERT": 0, "IDENTICAL": 0, "CONFLICT": 0, "REJECTED": 0},
            "Weekly Demand": {"INSERT": 0, "IDENTICAL": 0, "CONFLICT": 0, "REJECTED": 0},
        }

        rejections: List[str] = []
        conflicts: List[str] = []

        valid_sites_map: Dict[str, Site] = dict(db_sites)
        valid_operators_map: Dict[str, Operator] = dict(db_operators)
        valid_equipment_map: Dict[str, Equipment] = dict(db_equipment)

        sites_to_insert: List[Site] = []
        operators_to_insert: List[Operator] = []
        equipment_to_insert: List[Equipment] = []
        rental_logs_to_insert: List[RentalLog] = []
        weekly_demand_to_insert: List[WeeklyDemand] = []

        # Sites
        seen_sites_in_csv: Set[str] = set()
        for idx, row in enumerate(site_rows, start=2):
            site_id = row.get("site_id", "").strip()
            name = row.get("site_name", "").strip()
            location = row.get("location", "").strip()

            if not site_id or not name or not location:
                rejections.append(f"[sites.csv:Row {idx}] Missing required field(s): {row}")
                summary["Sites"]["REJECTED"] += 1
                continue

            if site_id in seen_sites_in_csv:
                continue
            seen_sites_in_csv.add(site_id)

            if site_id in db_sites:
                existing = db_sites[site_id]
                if existing.site_name == name and existing.location == location:
                    summary["Sites"]["IDENTICAL"] += 1
                else:
                    conflicts.append(f"[sites.csv:Row {idx}] Conflict for site_id '{site_id}'")
                    summary["Sites"]["CONFLICT"] += 1
            else:
                s_obj = Site(site_id=site_id, site_name=name, location=location)
                sites_to_insert.append(s_obj)
                valid_sites_map[site_id] = s_obj
                summary["Sites"]["INSERT"] += 1

        # Operators
        seen_operators_in_csv: Set[str] = set()
        for idx, row in enumerate(operator_rows, start=2):
            op_id = row.get("operator_id", "").strip()
            name = row.get("name", "").strip()
            contact = row.get("contact_info", "").strip()

            if not op_id or not name or not contact:
                rejections.append(f"[operators.csv:Row {idx}] Missing required field(s): {row}")
                summary["Operators"]["REJECTED"] += 1
                continue

            if op_id in seen_operators_in_csv:
                continue
            seen_operators_in_csv.add(op_id)

            if op_id in db_operators:
                existing = db_operators[op_id]
                if existing.name == name and existing.contact_info == contact:
                    summary["Operators"]["IDENTICAL"] += 1
                else:
                    conflicts.append(f"[operators.csv:Row {idx}] Conflict for operator_id '{op_id}'")
                    summary["Operators"]["CONFLICT"] += 1
            else:
                op_obj = Operator(operator_id=op_id, name=name, contact_info=contact)
                operators_to_insert.append(op_obj)
                valid_operators_map[op_id] = op_obj
                summary["Operators"]["INSERT"] += 1

        # Equipment
        seen_equipment_in_csv: Set[str] = set()
        for idx, row in enumerate(equipment_rows, start=2):
            eq_id = row.get("equipment_id", "").strip()
            eq_type = row.get("type", "").strip()
            raw_status = row.get("status", "").strip()
            site_id = row.get("current_site_id", "").strip() or None
            op_id = row.get("assigned_operator_id", "").strip() or None

            if not eq_id or not eq_type or not raw_status:
                rejections.append(f"[equipment.csv:Row {idx}] Missing required field(s)")
                summary["Equipment"]["REJECTED"] += 1
                continue

            if raw_status not in STATUS_MAP:
                rejections.append(f"[equipment.csv:Row {idx}] Unknown status '{raw_status}'")
                summary["Equipment"]["REJECTED"] += 1
                continue

            norm_status = STATUS_MAP[raw_status]

            if site_id and site_id not in valid_sites_map:
                rejections.append(f"[equipment.csv:Row {idx}] Invalid site_id '{site_id}'")
                summary["Equipment"]["REJECTED"] += 1
                continue

            if op_id and op_id not in valid_operators_map:
                rejections.append(f"[equipment.csv:Row {idx}] Invalid operator_id '{op_id}'")
                summary["Equipment"]["REJECTED"] += 1
                continue

            if eq_id in seen_equipment_in_csv:
                continue
            seen_equipment_in_csv.add(eq_id)

            if eq_id in db_equipment:
                existing = db_equipment[eq_id]
                if (existing.type == eq_type and
                    existing.status == norm_status and
                    existing.current_site_id == site_id and
                    existing.assigned_operator_id == op_id):
                    summary["Equipment"]["IDENTICAL"] += 1
                else:
                    conflicts.append(f"[equipment.csv:Row {idx}] Conflict for equipment_id '{eq_id}'")
                    summary["Equipment"]["CONFLICT"] += 1
            else:
                eq_obj = Equipment(
                    equipment_id=eq_id,
                    type=eq_type,
                    status=norm_status,
                    current_site_id=site_id,
                    assigned_operator_id=op_id
                )
                equipment_to_insert.append(eq_obj)
                valid_equipment_map[eq_id] = eq_obj
                summary["Equipment"]["INSERT"] += 1

        # Rental Logs
        seen_rentals_in_csv: Set[str] = set()
        for idx, row in enumerate(rental_log_rows, start=2):
            rental_id = normalize_rental_id(row.get("rental_id"))
            eq_id = row.get("equipment_id", "").strip()
            site_id = row.get("site_id", "").strip() or None
            op_id = row.get("operator_id", "").strip() or None
            c_in = parse_date(row.get("check_in_date"))
            c_out = parse_date(row.get("check_out_date"))

            try:
                eng_hrs = float(row.get("engine_hours_per_day", 0))
                idle_hrs = float(row.get("idle_hours_per_day", 0))
                r_days = int(row.get("rental_days", 0))
            except ValueError as ve:
                rejections.append(f"[rental_logs.csv:Row {idx}] Numeric parsing error: {ve}")
                summary["Rental Logs"]["REJECTED"] += 1
                continue

            is_overdue = parse_bool(row.get("is_overdue"))
            raw_anomaly = row.get("anomaly_flag", "").strip() if row.get("anomaly_flag") else ""
            norm_anomaly = ANOMALY_MAP.get(raw_anomaly, raw_anomaly or "OPTIMAL")

            if not rental_id or not eq_id or not c_in or not c_out or c_out < c_in or r_days <= 0:
                rejections.append(f"[rental_logs.csv:Row {idx}] Invalid rental record '{rental_id}'")
                summary["Rental Logs"]["REJECTED"] += 1
                continue

            if eng_hrs < 0 or idle_hrs < 0 or (eng_hrs + idle_hrs) > 24.0:
                rejections.append(f"[rental_logs.csv:Row {idx}] Invalid hours for rental '{rental_id}'")
                summary["Rental Logs"]["REJECTED"] += 1
                continue

            if eq_id not in valid_equipment_map or (site_id and site_id not in valid_sites_map) or (op_id and op_id not in valid_operators_map):
                rejections.append(f"[rental_logs.csv:Row {idx}] Foreign key error for rental '{rental_id}'")
                summary["Rental Logs"]["REJECTED"] += 1
                continue

            if rental_id in seen_rentals_in_csv:
                continue
            seen_rentals_in_csv.add(rental_id)

            derived_location = valid_sites_map[site_id].location if (site_id and site_id in valid_sites_map) else None

            if rental_id in db_rental_logs:
                existing = db_rental_logs[rental_id]
                if (existing.equipment_id == eq_id and
                    existing.site_id == site_id and
                    existing.operator_id == op_id and
                    existing.check_in_date == c_in and
                    existing.check_out_date == c_out and
                    abs(existing.engine_hours_per_day - eng_hrs) < 1e-4 and
                    abs(existing.idle_hours_per_day - idle_hrs) < 1e-4 and
                    existing.rental_days == r_days and
                    existing.is_overdue == is_overdue):
                    summary["Rental Logs"]["IDENTICAL"] += 1
                else:
                    conflicts.append(f"[rental_logs.csv:Row {idx}] Conflict for rental_id '{rental_id}'")
                    summary["Rental Logs"]["CONFLICT"] += 1
            else:
                r_obj = RentalLog(
                    rental_id=rental_id,
                    equipment_id=eq_id,
                    site_id=site_id,
                    operator_id=op_id,
                    check_in_date=c_in,
                    check_out_date=c_out,
                    engine_hours_per_day=eng_hrs,
                    idle_hours_per_day=idle_hrs,
                    rental_days=r_days,
                    is_overdue=is_overdue,
                    anomaly_flag=norm_anomaly,
                    location=derived_location,
                    fuel_usage_liters=None,
                )
                rental_logs_to_insert.append(r_obj)
                summary["Rental Logs"]["INSERT"] += 1

        # Weekly Demand
        seen_weekly_in_csv: Set[Tuple[datetime.date, str, str]] = set()
        for idx, row in enumerate(weekly_rows, start=2):
            w_start = parse_date(row.get("week_start"))
            site_id = row.get("site_id", "").strip()
            eq_type = row.get("equipment_type", "").strip()

            try:
                demand_val = int(row.get("weekly_demand", 0))
            except ValueError:
                rejections.append(f"[weekly_demand.csv:Row {idx}] Invalid weekly_demand")
                summary["Weekly Demand"]["REJECTED"] += 1
                continue

            if not w_start or not site_id or not eq_type or demand_val < 0 or site_id not in valid_sites_map:
                rejections.append(f"[weekly_demand.csv:Row {idx}] Invalid weekly demand row")
                summary["Weekly Demand"]["REJECTED"] += 1
                continue

            w_key = (w_start, site_id, eq_type)
            if w_key in seen_weekly_in_csv:
                continue
            seen_weekly_in_csv.add(w_key)

            if w_key in db_weekly_demand:
                existing = db_weekly_demand[w_key]
                if existing.weekly_demand == demand_val:
                    summary["Weekly Demand"]["IDENTICAL"] += 1
                else:
                    conflicts.append(f"[weekly_demand.csv:Row {idx}] Conflict for key {w_key}")
                    summary["Weekly Demand"]["CONFLICT"] += 1
            else:
                wd_obj = WeeklyDemand(
                    week_start=w_start,
                    site_id=site_id,
                    equipment_type=eq_type,
                    weekly_demand=demand_val
                )
                weekly_demand_to_insert.append(wd_obj)
                summary["Weekly Demand"]["INSERT"] += 1

        # Summary Report
        print("=================================================================")
        print("                     VALIDATION SUMMARY REPORT                   ")
        print("=================================================================")
        for table_name, counts in summary.items():
            print(f"\n{table_name}:")
            print(f"  - INSERT    : {counts['INSERT']}")
            print(f"  - IDENTICAL : {counts['IDENTICAL']}")
            print(f"  - CONFLICT  : {counts['CONFLICT']}")
            print(f"  - REJECTED  : {counts['REJECTED']}")
        print("\n=================================================================")

        if rejections:
            print(f"\n[REJECTIONS DETECTED] ({len(rejections)} invalid rows):")
            for r in rejections[:10]:
                print(f"  [REJECTED] {r}")

        if conflicts:
            print(f"\n[CONFLICTS DETECTED] ({len(conflicts)} conflicting records):")
            for c in conflicts[:10]:
                print(f"  [CONFLICT] {c}")

        if not args.commit:
            print("\n-----------------------------------------------------------------")
            print("  DRY-RUN COMPLETE: NO DATABASE CHANGES WERE MADE.              ")
            print("  To perform actual database import, execute:                   ")
            print("    python import_historical_data.py --commit                   ")
            print("-----------------------------------------------------------------")
            return

        if conflicts or rejections:
            print("\n[ABORTED] Cannot commit due to conflicts or rejections.")
            print("If you intend to replace the legacy demonstration dataset, run:")
            print("  python import_historical_data.py --replace-legacy --commit")
            sys.exit(1)

        db.add_all(sites_to_insert)
        db.flush()
        db.add_all(operators_to_insert)
        db.flush()
        db.add_all(equipment_to_insert)
        db.flush()
        db.add_all(rental_logs_to_insert)
        db.flush()
        db.add_all(weekly_demand_to_insert)
        db.commit()

        print("\nSUCCESS: Data committed to database!")

    except Exception as exc:
        db.rollback()
        print(f"\n[TRANSACTION ERROR] {exc}")
        print("Transaction rolled back cleanly.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
