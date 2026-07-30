import datetime
import random
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import Site, Operator, Equipment, RentalLog, DemandForecast

EQUIPMENT_TYPES = ["Excavator", "Crane", "Bulldozer", "Grader", "Wheel Loader", "Dump Truck", "Compactor", "Backhoe Loader"]
SITE_NAMES = ["Quarry Alpha", "Apex Mine North", "Titan Infrastructure", "Metro Expansion", "Granite Valley", "Iron Ore Site 4", "Copper Canyon", "Summit Highway", "Harbor Dredging", "Echo Dam"]
CITIES = ["Houston, TX", "Denver, CO", "Phoenix, AZ", "Chicago, IL", "Salt Lake City, UT", "Dallas, TX", "Seattle, WA", "Pittsburgh, PA", "Atlanta, GA", "Las Vegas, NV"]

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Sarah", "Emily", "Jessica", "Amanda", "Ashley"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

def generate_100_seeds(db: Session):
    db.query(DemandForecast).delete()
    db.query(RentalLog).delete()
    db.query(Equipment).delete()
    db.query(Operator).delete()
    db.query(Site).delete()
    db.commit()

    print("Generating 100 rows per table with Idle Efficiency Ratio = idle_hr / (engine_hrs + idle_hrs) * 100%...")

    # 1. Generate 100 SITES
    sites = [Site(site_id=f"S{i:03d}", site_name=f"{random.choice(SITE_NAMES)} #{i}", location=random.choice(CITIES)) for i in range(1, 101)]
    db.add_all(sites)
    db.commit()

    # 2. Generate 100 OPERATORS
    operators = [Operator(operator_id=f"OP{100+i}", name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}", contact_info=f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}") for i in range(1, 101)]
    db.add_all(operators)
    db.commit()

    # Base exact dataset rows from prompt Image 1 & 2
    # Formula: Idle Efficiency Ratio % = idle_hr / (engine_hr + idle_hr) * 100%
    base_exact_equipment = [
        ("EQX1001", "Excavator", "RENTED", "S003", "OP101", "2025-04-01", "2025-04-16", 11.5, 10.0, 15), # 10 / (11.5+10) = 46.5% / idle < eng
        ("EQX1002", "Crane", "AVAILABLE", None, None, "2025-03-10", "2025-03-30", 0.0, 0.0, 20),      
        ("EQX1003", "Bulldozer", "RENTED", "S002", "OP203", "2025-02-15", "2025-03-11", 8.0, 0.5, 25),   # 0.5 / (8+0.5) = 5.8% (Optimal)
        ("EQX1004", "Excavator", "RENTED", "S004", "OP106", "2025-05-05", "2025-05-15", 11.0, 9.0, 10),  # 9 / (11+9) = 45% / idle < eng
        ("EQX1005", "Bulldozer", "RENTED", "S005", "OP301", "2025-01-01", "2025-01-31", 8.0, 0.0, 30),   # 0 / (8+0) = 0% (Optimal)
        ("EQX1006", "Grader", "RENTED", "S001", "OP114", "2025-04-05", "2025-04-23", 9.0, 6.0, 18),     # 6 / (9+6) = 40% / idle < eng
        ("EQX1007", "Excavator", "AVAILABLE", None, None, "2025-03-20", "2025-04-01", 0.0, 0.0, 12),  
    ]

    today = datetime.date(2026, 7, 30)
    equipments = []
    rental_logs = []

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
            check_in_date=datetime.date.fromisoformat(c_in),
            check_out_date=datetime.date.fromisoformat(c_out),
            engine_hours_per_day=eng,
            idle_hours_per_day=idle,
            rental_days=days,
            is_overdue=True if datetime.date.fromisoformat(c_out) < today else False,
            anomaly_flag=anomaly
        )
        rental_logs.append(r_log)

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
            check_in = today - datetime.timedelta(days=random.randint(15, 60))
            check_out = check_in + datetime.timedelta(days=random.randint(5, 14))
            eng, idle = 0.0, 0.0
            is_overdue = False
            anomaly = "UNASSIGNED_IDLE"
        else:
            status = "UNDERUTILIZED" if scenario == "UNDERUTILIZED" else "RENTED"
            site_fk = f"S{random.randint(1, 100):03d}"
            op_fk = f"OP{random.randint(101, 200)}"
            
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
                check_out = today - datetime.timedelta(days=random.randint(11, 20))
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
                eng = round(random.uniform(8.0, 14.0), 1)
                idle = round(random.uniform(eng * 0.55, min(eng - 0.5, 12.0)), 1) # idle/eng >= 55% & idle < eng
                anomaly = "HIGH_IDLE_RATIO"
            else:
                eng = round(random.uniform(6.0, 12.0), 1)
                idle = round(random.uniform(0.5, min(eng * 0.3, 3.0)), 1)  # idle/eng < 30% & idle < eng
                anomaly = "OVERDUE_BREACH" if is_overdue else "OPTIMAL"

        eq = Equipment(equipment_id=eq_id, type=eq_type, status=status, current_site_id=site_fk, assigned_operator_id=op_fk)
        equipments.append(eq)

        idle_ratio = (idle / eng * 100.0) if eng > 0 else 0.0

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

    # 5. Generate 100 DEMAND FORECASTS
    forecasts = [DemandForecast(forecast_id=f"FCT{1000+i}", site_id=f"S{random.randint(1, 100):03d}", equipment_type=random.choice(EQUIPMENT_TYPES), predicted_demand=random.randint(1, 15), forecast_date=today + datetime.timedelta(days=random.randint(1, 30))) for i in range(1, 101)]
    db.add_all(forecasts)
    db.commit()

    print("Database seeded! Formula: Idle Efficiency Ratio % = idle_hr / (engine_hrs + idle_hrs) * 100%.")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    generate_100_seeds(db)
    db.close()
