import datetime
import random
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import Site, Operator, Equipment, RentalLog, DemandForecast, WeeklyDemand

EQUIPMENT_TYPES = ["Excavator", "Crane", "Bulldozer", "Grader", "Wheel Loader", "Dump Truck", "Compactor", "Backhoe Loader"]
SITE_NAMES = ["Quarry Alpha", "Apex Mine North", "Titan Infrastructure", "Metro Expansion", "Granite Valley", "Iron Ore Site 4", "Copper Canyon", "Summit Highway", "Harbor Dredging", "Echo Dam"]
CITIES = ["Houston, TX", "Denver, CO", "Phoenix, AZ", "Chicago, IL", "Salt Lake City, UT", "Dallas, TX", "Seattle, WA", "Pittsburgh, PA", "Atlanta, GA", "Las Vegas, NV"]

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Sarah", "Emily", "Jessica", "Amanda", "Ashley"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

def get_monday_of_week(dt: datetime.date) -> datetime.date:
    """Returns the Monday of the week for a given date."""
    return dt - datetime.timedelta(days=dt.weekday())

def compile_weekly_demand_from_logs(db: Session):
    """
    Compiles rental logs into weekly_demand table per site and equipment_type per week.
    Calculates active equipment demand for each week.
    """
    db.query(WeeklyDemand).delete()
    db.commit()

    logs = db.query(RentalLog).all()
    weekly_counts = {}  # (week_start, site_id, equipment_type) -> count

    for log in logs:
        if not log.site_id or not log.check_in_date or not log.check_out_date:
            continue
        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        eq_type = eq.type if eq else "Excavator"

        start_mon = get_monday_of_week(log.check_in_date)
        # Cap end to current week's Monday so latest-week in DB = today's week
        # This ensures the ML model forecasts NEXT WEEK (Aug 3–Aug 10, 2026)
        current_week_mon = get_monday_of_week(datetime.date.today())
        end_mon = min(get_monday_of_week(log.check_out_date), current_week_mon)

        if end_mon < start_mon:
            # rental hasn't started yet relative to capped window; skip
            continue

        curr = start_mon
        while curr <= end_mon:
            key = (curr, log.site_id, eq_type)
            weekly_counts[key] = weekly_counts.get(key, 0) + 1
            curr += datetime.timedelta(days=7)

    weekly_records = []
    for (week_start, site_id, eq_type), demand in weekly_counts.items():
        wd = WeeklyDemand(
            week_start=week_start,
            site_id=site_id,
            equipment_type=eq_type,
            weekly_demand=demand
        )
        weekly_records.append(wd)

    db.add_all(weekly_records)
    db.commit()
    print(f"Compiled {len(weekly_records)} weekly demand records into database.")

def generate_100_seeds(db: Session):
    db.query(DemandForecast).delete()
    db.query(WeeklyDemand).delete()
    db.query(RentalLog).delete()
    db.query(Equipment).delete()
    db.query(Operator).delete()
    db.query(Site).delete()
    db.commit()

    print("Generating 100 rows per table with dynamic today's date & 2-week overdue equipment tracking...")

    today = datetime.date.today()

    # 1. Generate 100 SITES
    sites = [Site(site_id=f"S{i:03d}", site_name=f"{random.choice(SITE_NAMES)} #{i}", location=random.choice(CITIES)) for i in range(1, 101)]
    db.add_all(sites)
    db.commit()

    # 2. Generate 100 OPERATORS
    operators = [Operator(operator_id=f"OP{100+i}", name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}", contact_info=f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}") for i in range(1, 101)]
    db.add_all(operators)
    db.commit()

    equipments = []
    rental_logs = []

    # 3. Base Equipment Rows
    base_exact_equipment = [
        ("EQX1001", "Excavator", "RENTED", "S003", "OP101", today - datetime.timedelta(days=25), today - datetime.timedelta(days=10), 1.5, 10.0, 15),
        ("EQX1002", "Crane", "AVAILABLE", None, None, today - datetime.timedelta(days=40), today - datetime.timedelta(days=20), 0.0, 11.0, 20),
        ("EQX1003", "Bulldozer", "RENTED", "S002", "OP203", today - datetime.timedelta(days=30), today - datetime.timedelta(days=5), 7.5, 0.5, 25),
        ("EQX1004", "Excavator", "RENTED", "S004", "OP106", today - datetime.timedelta(days=18), today - datetime.timedelta(days=8), 2.0, 9.0, 10),
        ("EQX1005", "Bulldozer", "RENTED", "S005", "OP301", today - datetime.timedelta(days=42), today - datetime.timedelta(days=12), 8.0, 0.0, 30),
        ("EQX1006", "Grader", "RENTED", "S001", "OP114", today - datetime.timedelta(days=20), today - datetime.timedelta(days=2), 3.0, 6.0, 18),
        ("EQX1007", "Excavator", "AVAILABLE", None, None, today - datetime.timedelta(days=50), today - datetime.timedelta(days=38), 0.0, 12.0, 12),
    ]

    for eq_id, eq_type, status, site_id, op_id, c_in, c_out, eng, idle, days in base_exact_equipment:
        site_fk = site_id if site_id and int(site_id[1:]) <= 100 else None
        op_fk = f"OP{random.randint(101,200)}" if op_id else None

        eq = Equipment(equipment_id=eq_id, type=eq_type, status=status, current_site_id=site_fk, assigned_operator_id=op_fk)
        equipments.append(eq)

        tot = eng + idle
        idle_ratio = (idle / tot * 100.0) if tot > 0 else 0.0
        anomaly = "HIGH_IDLE_RATIO" if idle_ratio > 50.0 else ("UNASSIGNED_USAGE" if not op_fk else "OPTIMAL")

        r_log = RentalLog(
            rental_id=f"RNT{eq_id[3:]}",
            equipment_id=eq_id,
            site_id=site_fk,
            operator_id=op_fk,
            check_in_date=c_in,
            check_out_date=c_out,
            engine_hours_per_day=eng,
            idle_hours_per_day=idle,
            rental_days=days,
            is_overdue=True if c_out < today and status != "AVAILABLE" else False,
            anomaly_flag=anomaly
        )
        rental_logs.append(r_log)

    # 4. Generate 93 additional rental scenarios with last 2-week overdue items
    for i in range(8, 101):
        eq_id = f"EQX{1000+i}"
        eq_type = random.choice(EQUIPMENT_TYPES)

        scenario = random.choice([
            "OVERDUE_L1", "OVERDUE_L2", "OVERDUE_L3", "OVERDUE_L4", "OVERDUE_L5",
            "RETURN_TODAY", "RETURN_TOMORROW", "RETURN_FUTURE", "UNDERUTILIZED", "AVAILABLE"
        ])

        if scenario == "AVAILABLE":
            status = "AVAILABLE"
            site_fk = None
            op_fk = None
            check_in = today - datetime.timedelta(days=random.randint(20, 60))
            check_out = check_in + datetime.timedelta(days=random.randint(5, 14))
            eng, idle = 0.0, 0.0
            is_overdue = False
            anomaly = "OPTIMAL"
        else:
            status = "UNDERUTILIZED" if scenario == "UNDERUTILIZED" else "RENTED"
            site_fk = f"S{random.randint(1, 100):03d}"
            op_fk = f"OP{random.randint(101, 200)}"

            # Overdue scenarios targeting the last 2 weeks (1 to 14 days overdue)
            if scenario == "OVERDUE_L1":
                check_out = today - datetime.timedelta(days=1)
                is_overdue = True
            elif scenario == "OVERDUE_L2":
                check_out = today - datetime.timedelta(days=random.randint(2, 3))
                is_overdue = True
            elif scenario == "OVERDUE_L3":
                check_out = today - datetime.timedelta(days=random.randint(4, 6))
                is_overdue = True
            elif scenario == "OVERDUE_L4":
                check_out = today - datetime.timedelta(days=random.randint(7, 10))
                is_overdue = True
            elif scenario == "OVERDUE_L5":
                check_out = today - datetime.timedelta(days=random.randint(11, 14))
                is_overdue = True
            elif scenario == "RETURN_TODAY":
                check_out = today
                is_overdue = False
            elif scenario == "RETURN_TOMORROW":
                check_out = today + datetime.timedelta(days=1)
                is_overdue = False
            elif scenario == "RETURN_FUTURE":
                check_out = today + datetime.timedelta(days=random.randint(2, 10))
                is_overdue = False
            else: # UNDERUTILIZED
                check_out = today + datetime.timedelta(days=random.randint(1, 14))
                is_overdue = False

            rental_days = random.randint(7, 30)
            check_in = check_out - datetime.timedelta(days=rental_days)

            if scenario == "UNDERUTILIZED":
                eng = round(random.uniform(0.5, 2.5), 1)
                idle = round(random.uniform(7.0, 11.5), 1)
                anomaly = "HIGH_IDLE_RATIO"
            else:
                eng = round(random.uniform(5.0, 9.0), 1)
                idle = round(random.uniform(0.5, 3.0), 1)
                anomaly = "OVERDUE_BREACH" if is_overdue else "OPTIMAL"

        eq = Equipment(equipment_id=eq_id, type=eq_type, status=status, current_site_id=site_fk, assigned_operator_id=op_fk)
        equipments.append(eq)

        r_log = RentalLog(
            rental_id=f"RNT{1000+i}",
            equipment_id=eq_id,
            site_id=site_fk,
            operator_id=op_fk,
            check_in_date=check_in,
            check_out_date=check_out,
            engine_hours_per_day=eng,
            idle_hours_per_day=idle,
            rental_days=(check_out - check_in).days,
            is_overdue=is_overdue,
            anomaly_flag=anomaly
        )
        rental_logs.append(r_log)

    db.add_all(equipments)
    db.add_all(rental_logs)
    db.commit()

    # 5. Compile weekly demand from rental logs into weekly_demand table
    compile_weekly_demand_from_logs(db)

    # 6. Generate DEMAND FORECASTS for NEXT WEEK ALONE (August 3, 2026 to August 10, 2026)
    target_forecast_monday = datetime.date(2026, 8, 3)
    target_forecast_sunday = datetime.date(2026, 8, 10)

    forecasts = []
    for i in range(1, 101):
        site_id = f"S{((i - 1) % 100) + 1:03d}"
        eq_type = random.choice(EQUIPMENT_TYPES)
        pred = random.randint(2, 12)
        fct = DemandForecast(
            forecast_id=f"FCT_{site_id}_{eq_type}_{target_forecast_monday}",
            site_id=site_id,
            equipment_type=eq_type,
            predicted_demand=pred,
            forecast_date=target_forecast_monday
        )
        forecasts.append(fct)

    db.add_all(forecasts)
    db.commit()

    print(f"Database successfully seeded with overdue rentals for the last 2 weeks, weekly demand compilation, and NEXT WEEK demand forecasts for {target_forecast_monday} to {target_forecast_sunday}!")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    generate_100_seeds(db)
    db.close()
