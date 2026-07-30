import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Equipment, RentalLog, Site, Operator
from schemas import CheckInRequest, CheckOutRequest

router = APIRouter(prefix="/api/portal", tags=["User Portal"])


@router.get("/equipment/{equipment_id}/status")
def get_equipment_status(equipment_id: str, db: Session = Depends(get_db)):
    """Check real-time equipment status for pre-validation."""
    eq = db.query(Equipment).filter(Equipment.equipment_id == equipment_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_id}' not found.")

    site = db.query(Site).filter(Site.site_id == eq.current_site_id).first() if eq.current_site_id else None
    op = db.query(Operator).filter(Operator.operator_id == eq.assigned_operator_id).first() if eq.assigned_operator_id else None

    return {
        "equipment_id": eq.equipment_id,
        "type": eq.type,
        "status": eq.status,
        "current_site_id": eq.current_site_id,
        "current_site_name": site.site_name if site else None,
        "assigned_operator_id": eq.assigned_operator_id,
        "assigned_operator_name": op.name if op else None,
    }


@router.post("/checkin")
def checkin_equipment(payload: CheckInRequest, db: Session = Depends(get_db)):
    """
    Check in an equipment to a site.
    - Creates one row in rental_logs with all check-in data.
    - engine_hours_per_day / idle_hours_per_day default 0 (filled on checkout).
    - Returns the generated rental_id — user must keep it for checkout.
    """
    # 1. Validate equipment exists
    eq = db.query(Equipment).filter(Equipment.equipment_id == payload.equipment_id).first()
    if not eq:
        raise HTTPException(status_code=404,
            detail=f"Equipment '{payload.equipment_id}' not found in the system.")

    # 2. Duplicate allocation guard
    if eq.status != "AVAILABLE":
        current_site = db.query(Site).filter(Site.site_id == eq.current_site_id).first() if eq.current_site_id else None
        site_info = f"Site {eq.current_site_id}" + (f" ({current_site.site_name})" if current_site else "")
        raise HTTPException(status_code=409,
            detail=(
                f"Equipment '{payload.equipment_id}' is currently '{eq.status}' "
                f"and assigned to {site_info}. It cannot be re-allocated until returned."
            ))

    # 3. Validate site exists
    site = db.query(Site).filter(Site.site_id == payload.site_id).first()
    if not site:
        raise HTTPException(status_code=404,
            detail=f"Site '{payload.site_id}' not found in the system.")

    # 4. Validate operator exists
    operator = db.query(Operator).filter(Operator.operator_id == payload.operator_id).first()
    if not operator:
        raise HTTPException(status_code=404,
            detail=f"Operator '{payload.operator_id}' not found in the system.")

    # 5. Generate rental_id and expected checkout date
    rental_id = f"RL-{str(uuid.uuid4())[:8].upper()}"
    expected_checkout = payload.check_in_date + datetime.timedelta(days=payload.expected_rental_days)

    # 6. Create single RentalLog row (hours filled in on checkout)
    new_log = RentalLog(
        rental_id=rental_id,
        equipment_id=payload.equipment_id,
        site_id=payload.site_id,
        operator_id=payload.operator_id,
        check_in_date=payload.check_in_date,
        check_out_date=expected_checkout,         # expected; overwritten on checkout
        engine_hours_per_day=0.0,                 # placeholder
        idle_hours_per_day=0.0,                   # placeholder
        rental_days=payload.expected_rental_days,
        is_overdue=False,
        anomaly_flag=None,
        location=payload.location,
        fuel_usage_liters=None,                   # filled on checkout
    )
    db.add(new_log)

    # 7. Update equipment status
    eq.status = "RENTED"
    eq.current_site_id = payload.site_id
    eq.assigned_operator_id = payload.operator_id

    db.commit()
    db.refresh(new_log)

    return {
        "success": True,
        "message": f"Equipment '{payload.equipment_id}' checked in to Site '{payload.site_id}'. Save your Rental ID for checkout.",
        "rental_id": rental_id,
        "equipment_id": payload.equipment_id,
        "equipment_type": payload.equipment_type,
        "site_id": payload.site_id,
        "site_name": site.site_name,
        "location": payload.location,
        "operator_id": payload.operator_id,
        "operator_name": operator.name,
        "check_in_date": str(payload.check_in_date),
        "expected_checkout_date": str(expected_checkout),
        "expected_rental_days": payload.expected_rental_days,
    }


@router.post("/checkout")
def checkout_equipment(payload: CheckOutRequest, db: Session = Depends(get_db)):
    """
    Check out an equipment using its Rental ID.
    - Looks up the RentalLog by rental_id.
    - Validates it's still open (engine_hours_per_day == 0).
    - Fills in hours, fuel, checkout date.
    - Returns a rich summary with computed analytics.
    """
    # 1. Look up the rental log by rental_id
    log = db.query(RentalLog).filter(RentalLog.rental_id == payload.rental_id).first()
    if not log:
        raise HTTPException(status_code=404,
            detail=f"Rental ID '{payload.rental_id}' not found. Please enter the ID generated during check-in.")

    # 2. Check if already checked out
    if log.engine_hours_per_day != 0.0 or log.idle_hours_per_day != 0.0:
        raise HTTPException(status_code=409,
            detail=f"Rental '{payload.rental_id}' has already been checked out.")

    # 3. Validate hours
    if payload.engine_hrs_per_day <= 0:
        raise HTTPException(status_code=422, detail="Engine hours/day must be greater than 0.")
    if payload.idle_hrs_per_day < 0:
        raise HTTPException(status_code=422, detail="Idle hours/day cannot be negative.")
    if payload.idle_hrs_per_day > payload.engine_hrs_per_day:
        raise HTTPException(status_code=422,
            detail="Idle hours/day cannot exceed engine hours/day.")
    if payload.fuel_usage_liters < 0:
        raise HTTPException(status_code=422, detail="Fuel usage cannot be negative.")

    # 4. Compute analytics
    original_planned_checkout = log.check_out_date
    actual_days = (payload.checkout_date - log.check_in_date).days or log.rental_days
    idle_ratio = round((payload.idle_hrs_per_day / payload.engine_hrs_per_day) * 100.0, 1)

    if idle_ratio > 75.0:
        anomaly_flag = "HIGH_IDLE"
    elif idle_ratio > 50.0:
        anomaly_flag = "UNDERUTILIZED"
    else:
        anomaly_flag = "OPTIMAL"

    eng = payload.engine_hrs_per_day
    idle = payload.idle_hrs_per_day
    total_runtime_hours = round(eng, 1)
    total_idle_hours = round(idle, 1)
    total_engine_hours = round(eng, 1)
    downtime_per_day = max(0.0, round(24.0 - eng, 1))
    total_downtime_hours = downtime_per_day
    utilization_pct = round((eng / 24.0) * 100.0, 1)

    # 5. Update the RentalLog row
    log.check_out_date = payload.checkout_date
    log.engine_hours_per_day = payload.engine_hrs_per_day
    log.idle_hours_per_day = payload.idle_hrs_per_day
    log.operator_id = payload.operator_id
    log.rental_days = actual_days
    log.anomaly_flag = anomaly_flag
    log.fuel_usage_liters = payload.fuel_usage_liters
    log.is_overdue = payload.checkout_date > original_planned_checkout

    # 6. Free the equipment
    eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
    if eq:
        eq.status = "AVAILABLE"
        eq.current_site_id = None
        eq.assigned_operator_id = None

    db.commit()

    # 7. Fetch related info for summary
    site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
    op = db.query(Operator).filter(Operator.operator_id == payload.operator_id).first()

    return {
        "success": True,
        "message": f"Equipment '{log.equipment_id}' successfully checked out.",
        # — Rental identity —
        "rental_id": log.rental_id,
        "equipment_id": log.equipment_id,
        "equipment_type": eq.type if eq else "N/A",
        "site_id": log.site_id,
        "site_name": site.site_name if site else "N/A",
        "location": log.location,
        "operator_id": payload.operator_id,
        "operator_name": op.name if op else "N/A",
        # — Dates —
        "check_in_date": str(log.check_in_date),
        "check_out_date": str(payload.checkout_date),
        "is_overdue": log.is_overdue,
        # — Usage analytics —
        "actual_rental_days": actual_days,
        "engine_hrs_per_day": payload.engine_hrs_per_day,
        "idle_hrs_per_day": payload.idle_hrs_per_day,
        "total_engine_hours": total_engine_hours,
        "total_idle_hours": total_idle_hours,
        "total_runtime_hours": total_runtime_hours,
        "downtime_per_day_hrs": downtime_per_day,
        "total_downtime_hours": total_downtime_hours,
        "idle_ratio_pct": idle_ratio,
        "utilization_pct": utilization_pct,
        "fuel_usage_liters": payload.fuel_usage_liters,
        "anomaly_flag": anomaly_flag,
    }


@router.get("/history")
def get_rental_history(db: Session = Depends(get_db)):
    """Fetch all historical rental logs for the User Portal."""
    logs = db.query(RentalLog).order_by(RentalLog.check_out_date.desc()).all()
    result = []
    
    # Pre-fetch for performance could be done, but simple loop is fine for now
    for log in logs:
        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first()
        op = db.query(Operator).filter(Operator.operator_id == log.operator_id).first()
        
        actual_days = log.rental_days if log.rental_days else 1
        eng = log.engine_hours_per_day or 0.0
        idle = log.idle_hours_per_day or 0.0
        
        # Per-day average values (strictly <= 24.0 hrs/day):
        # eng = average engine runtime hrs/day (<= 24)
        # idle = average idle hrs/day (<= eng)
        # downtime = 24.0 - eng (<= 24)
        runtime_per_day = round(eng, 1)
        idle_per_day = round(idle, 1)
        downtime_per_day = max(0.0, round(24.0 - eng, 1))
        
        result.append({
            "rental_id": log.rental_id,
            "equipment_id": log.equipment_id,
            "equipment_type": eq.type if eq else "N/A",
            "site_id": log.site_id,
            "site_name": site.site_name if site else "N/A",
            "location": log.location or "N/A",
            "operator_id": log.operator_id,
            "operator_name": op.name if op else "N/A",
            "check_in_date": str(log.check_in_date),
            "check_out_date": str(log.check_out_date),
            "rental_days": actual_days,
            "engine_hrs_per_day": runtime_per_day,
            "idle_hrs_per_day": idle_per_day,
            "total_engine_hrs": runtime_per_day,
            "total_idle_hrs": idle_per_day,
            "total_runtime_hrs": runtime_per_day,
            "total_downtime_hrs": downtime_per_day,
            "fuel_usage_liters": log.fuel_usage_liters or 0,
            "anomaly_flag": log.anomaly_flag or "N/A",
            "is_overdue": log.is_overdue
        })
        
    return result

