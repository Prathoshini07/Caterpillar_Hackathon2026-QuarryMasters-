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

    ── WHAT USERS ENTER ─────────────────────────────────────────────────────────
      total_engine_hours : Total engine-ON hours accumulated over the ENTIRE rental period.
                           Example: machine was on for 8h on Day 1, 6h on Day 2, 7h on Day 3
                                    → enter 21 (the sum over the whole period)
      total_idle_hours   : Total idle hours accumulated over the ENTIRE rental period.
                           Idle time is a SUBSET of engine-on time (engine runs but no work done).
                           Must always be ≤ total_engine_hours.

    ── WHAT WE DERIVE ───────────────────────────────────────────────────────────
      engine_hrs_per_day  = total_engine_hours / actual_days     (daily average)
      idle_hrs_per_day    = total_idle_hours   / actual_days     (daily average)
      idle_ratio_pct      = (total_idle / total_engine) × 100   (% of engine time spent idling)
      total_active_hours  = total_engine - total_idle            (productive working hours)
      downtime_per_day    = 24 - engine_hrs_per_day              (hrs engine was fully OFF per day)
      utilization_pct     = active_hours / (24 × days) × 100   (% of calendar time productive)
    """
    # 1. Look up the rental log by rental_id
    log = db.query(RentalLog).filter(RentalLog.rental_id == payload.rental_id).first()
    if not log:
        raise HTTPException(status_code=404,
            detail=f"Rental ID '{payload.rental_id}' not found. Please enter the ID generated during check-in.")

    # 2. Check if already checked out — the reliable signal is equipment status = AVAILABLE,
    #    because a successful checkout always sets the equipment back to AVAILABLE.
    eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
    if eq and eq.status == "AVAILABLE":
        raise HTTPException(status_code=409,
            detail=f"Rental '{payload.rental_id}' has already been checked out. Equipment '{log.equipment_id}' is already marked AVAILABLE.")

    # 3. Validate hours — inputs are TOTALS for the whole rental period
    if payload.total_engine_hours <= 0:
        raise HTTPException(status_code=422, detail="Total engine hours must be greater than 0.")
    if payload.total_idle_hours < 0:
        raise HTTPException(status_code=422, detail="Total idle hours cannot be negative.")
    if payload.total_idle_hours > payload.total_engine_hours:
        raise HTTPException(status_code=422,
            detail="Total idle hours cannot exceed total engine hours (idle is a subset of engine-on time).")
    if payload.fuel_usage_liters < 0:
        raise HTTPException(status_code=422, detail="Fuel usage cannot be negative.")

    # 4. Equipment already fetched above (needed for maintenance tracker)

    # ── Step A: Actual rental duration ────────────────────────────────────────
    # The actual checkout date is exactly what the user provides — NOT the expected date.
    original_planned_checkout = log.check_out_date   # expected date stored at check-in
    actual_days = (payload.checkout_date - log.check_in_date).days
    if actual_days <= 0:
        actual_days = 1   # same-day rental: treat as at least 1 day to avoid division by zero

    # ── Step B: Derive per-day averages from entered totals ───────────────────
    #   Formula: average = total ÷ actual_rental_days
    engine_hrs_per_day = round(payload.total_engine_hours / actual_days, 2)
    idle_hrs_per_day   = round(payload.total_idle_hours   / actual_days, 2)

    # ── Step C: Usage analytics ───────────────────────────────────────────────
    #   idle_ratio: what fraction of engine-on time was spent idling
    #   Formula: (total_idle ÷ total_engine) × 100
    idle_ratio = round((payload.total_idle_hours / payload.total_engine_hours) * 100.0, 1)

    #   active_hours: hours the machine was genuinely working (engine on AND not idling)
    #   Formula: total_engine - total_idle
    total_active_hours = round(payload.total_engine_hours - payload.total_idle_hours, 1)

    #   downtime: calendar hours the engine was completely off (per day average)
    #   Formula: 24h - engine_hrs_per_day_avg
    downtime_per_day     = round(24.0 - engine_hrs_per_day, 2)
    total_downtime_hours = round(downtime_per_day * actual_days, 1)

    #   utilization: productive work as % of total calendar time
    #   Formula: active_hours ÷ (24 × days) × 100
    total_calendar_hours = 24.0 * actual_days
    utilization_pct      = round((total_active_hours / total_calendar_hours) * 100.0, 1)

    # ── Step D: Anomaly flag based on idle ratio ──────────────────────────────
    if idle_ratio > 75.0:
        anomaly_flag = "HIGH_IDLE"
    elif idle_ratio > 50.0:
        anomaly_flag = "UNDERUTILIZED"
    else:
        anomaly_flag = "OPTIMAL"

    # ── Step E: Financial Penalty (Excess Idling Billing) ────────────────────
    #   Policy: 2.5 hrs/day of idle is acceptable (warm-up + cool-down).
    #   Anything above that over the full rental period = "excess idling".
    #
    #   permissible_idle = 2.5 hrs/day × actual_days
    #   excess_idle      = total_idle_hours − permissible_idle   (floored at 0)
    #   wasted_fuel      = excess_idle × 3.5 L/hr
    #   fuel_penalty     = wasted_fuel × $3.25/L
    #   idle_penalty     = excess_idle × $60/hr   (operator/contractor charge)
    #   total_penalty    = fuel_penalty + idle_penalty
    IDLE_THRESHOLD_PER_DAY = 2.5          # hrs — acceptable warm-up/cool-down per day
    IDLE_PENALTY_RATE       = 60.0        # USD per excess idle hour
    IDLE_FUEL_RATE_L_HR     = 3.5         # liters burned per idle hour
    FUEL_COST_PER_LITER     = 3.25        # USD per liter

    permissible_idle_total = round(IDLE_THRESHOLD_PER_DAY * actual_days, 1)
    excess_idle_hours      = round(max(0.0, payload.total_idle_hours - permissible_idle_total), 2)
    wasted_fuel_liters     = round(excess_idle_hours * IDLE_FUEL_RATE_L_HR, 2)
    fuel_penalty_usd       = round(wasted_fuel_liters * FUEL_COST_PER_LITER, 2)
    idle_penalty_usd       = round(excess_idle_hours * IDLE_PENALTY_RATE, 2)
    total_penalty_usd      = round(fuel_penalty_usd + idle_penalty_usd, 2)

    # ── Step F: Engine-Hour Maintenance Tracker ───────────────────────────────
    #   Service is scheduled by ACTIVE working hours (not total engine-on time).
    #   This prevents idling machines from consuming service intervals unfairly.
    #   cumulative_engine_hours = running total of active hours across ALL rentals.
    SERVICE_INTERVAL_HRS = 250.0
    prev_cumulative      = (eq.cumulative_engine_hours or 0.0) if eq else 0.0
    new_cumulative       = round(prev_cumulative + total_active_hours, 1)
    hours_since_service  = round(new_cumulative % SERVICE_INTERVAL_HRS, 1)
    hours_until_service  = round(SERVICE_INTERVAL_HRS - hours_since_service, 1)
    service_life_pct     = round((hours_since_service / SERVICE_INTERVAL_HRS) * 100.0, 1)

    if hours_until_service <= 30:
        maint_status = "URGENT SERVICE REQUIRED"
        maint_color  = "#EF4444"
    elif hours_until_service <= 75:
        maint_status = "SERVICE WARNING"
        maint_color  = "#F97316"
    else:
        maint_status = "OPTIMAL OPERATION"
        maint_color  = "#10B981"

    # 5. Persist to DB — store derived per-day averages in legacy columns for history
    log.check_out_date               = payload.checkout_date
    log.engine_hours_per_day         = engine_hrs_per_day
    log.idle_hours_per_day           = idle_hrs_per_day
    log.operator_id                  = payload.operator_id
    log.rental_days                  = actual_days
    log.anomaly_flag                 = anomaly_flag
    log.fuel_usage_liters            = payload.fuel_usage_liters
    log.is_overdue                   = payload.checkout_date > original_planned_checkout
    log.total_engine_hours           = payload.total_engine_hours
    log.accumulated_idle_penalty_usd = total_penalty_usd

    # 6. Free the equipment & update cumulative active hours
    if eq:
        eq.status                  = "AVAILABLE"
        eq.current_site_id         = None
        eq.assigned_operator_id    = None
        eq.cumulative_engine_hours = new_cumulative

    db.commit()

    # 7. Fetch related info for summary
    site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
    op   = db.query(Operator).filter(Operator.operator_id == payload.operator_id).first()

    return {
        "success": True,
        "message": f"Equipment '{log.equipment_id}' successfully checked out.",
        # — Rental identity —
        "rental_id":       log.rental_id,
        "equipment_id":    log.equipment_id,
        "equipment_type":  eq.type if eq else "N/A",
        "site_id":         log.site_id,
        "site_name":       site.site_name if site else "N/A",
        "location":        log.location,
        "operator_id":     payload.operator_id,
        "operator_name":   op.name if op else "N/A",
        # — Dates —
        "check_in_date":   str(log.check_in_date),
        "check_out_date":  str(payload.checkout_date),
        "is_overdue":      log.is_overdue,
        # — Usage analytics (input totals + derived averages) —
        "actual_rental_days":       actual_days,
        "total_engine_hours":       payload.total_engine_hours,
        "total_idle_hours":         payload.total_idle_hours,
        "total_active_hours":       total_active_hours,
        "total_downtime_hours":     total_downtime_hours,
        "engine_hrs_per_day_avg":   engine_hrs_per_day,
        "idle_hrs_per_day_avg":     idle_hrs_per_day,
        "downtime_per_day_hrs":     downtime_per_day,
        "idle_ratio_pct":           idle_ratio,
        "utilization_pct":          utilization_pct,
        "fuel_usage_liters":        payload.fuel_usage_liters,
        "anomaly_flag":             anomaly_flag,
        # — Financial Penalty Invoice —
        "penalty_invoice": {
            "permissible_idle_total_hrs": permissible_idle_total,
            "total_idle_hours":           payload.total_idle_hours,
            "excess_idle_hours":          excess_idle_hours,
            "wasted_fuel_liters":         wasted_fuel_liters,
            "fuel_penalty_usd":           fuel_penalty_usd,
            "idle_penalty_usd":           idle_penalty_usd,
            "total_penalty_usd":          total_penalty_usd,
            "penalty_applied":            total_penalty_usd > 0,
        },
        # — Engine-Hour Maintenance Health —
        "maintenance_health": {
            "cumulative_active_hours":  new_cumulative,
            "hours_since_last_service": hours_since_service,
            "hours_until_service":      hours_until_service,
            "service_life_pct":         service_life_pct,
            "service_interval_hrs":     SERVICE_INTERVAL_HRS,
            "maint_status":             maint_status,
            "maint_color":              maint_color,
        },
    }


@router.get("/history")
def get_rental_history(db: Session = Depends(get_db)):
    """Fetch all historical rental logs for the User Portal."""
    logs = db.query(RentalLog).order_by(RentalLog.check_out_date.desc()).all()
    result = []

    for log in logs:
        eq   = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first()
        op   = db.query(Operator).filter(Operator.operator_id == log.operator_id).first()

        actual_days = log.rental_days if log.rental_days else 1
        # Use stored total if available, otherwise derive from per-day avg × days
        total_engine = log.total_engine_hours if log.total_engine_hours else round((log.engine_hours_per_day or 0) * actual_days, 1)
        total_idle   = round((log.idle_hours_per_day or 0) * actual_days, 1)
        total_active = round(total_engine - total_idle, 1)
        total_downtime = round((24.0 - (log.engine_hours_per_day or 0)) * actual_days, 1)

        result.append({
            "rental_id":           log.rental_id,
            "equipment_id":        log.equipment_id,
            "equipment_type":      eq.type if eq else "N/A",
            "site_id":             log.site_id,
            "site_name":           site.site_name if site else "N/A",
            "location":            log.location or "N/A",
            "operator_id":         log.operator_id,
            "operator_name":       op.name if op else "N/A",
            "check_in_date":       str(log.check_in_date),
            "check_out_date":      str(log.check_out_date),
            "rental_days":         actual_days,
            "engine_hrs_per_day":  log.engine_hours_per_day or 0,
            "idle_hrs_per_day":    log.idle_hours_per_day or 0,
            "total_engine_hrs":    total_engine,
            "total_idle_hrs":      total_idle,
            "total_active_hrs":    total_active,
            "total_downtime_hrs":  total_downtime,
            "fuel_usage_liters":   log.fuel_usage_liters or 0,
            "idle_penalty_usd":    log.accumulated_idle_penalty_usd or 0,
            "anomaly_flag":        log.anomaly_flag or "N/A",
            "is_overdue":          log.is_overdue,
        })

    return result


@router.get("/maintenance-status/{equipment_id}")
def get_maintenance_status(equipment_id: str, db: Session = Depends(get_db)):
    """
    Returns engine-hour maintenance health for a specific equipment.
    Scheduling is based strictly on cumulative ACTIVE hours, not calendar days.
    """
    eq = db.query(Equipment).filter(Equipment.equipment_id == equipment_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_id}' not found.")

    SERVICE_INTERVAL_HRS = 250.0
    cumulative           = eq.cumulative_engine_hours or 0.0
    hours_since_service  = round(cumulative % SERVICE_INTERVAL_HRS, 1)
    hours_until_service  = round(SERVICE_INTERVAL_HRS - hours_since_service, 1)
    service_life_pct     = round((hours_since_service / SERVICE_INTERVAL_HRS) * 100.0, 1)

    if hours_until_service <= 30:
        status = "URGENT SERVICE REQUIRED"
        color  = "#EF4444"
    elif hours_until_service <= 75:
        status = "SERVICE WARNING"
        color  = "#F97316"
    else:
        status = "OPTIMAL OPERATION"
        color  = "#10B981"

    return {
        "equipment_id":             equipment_id,
        "equipment_type":           eq.type,
        "cumulative_active_hours":  cumulative,
        "hours_since_last_service": hours_since_service,
        "hours_until_service":      hours_until_service,
        "service_life_pct":         service_life_pct,
        "service_interval_hrs":     SERVICE_INTERVAL_HRS,
        "maint_status":             status,
        "maint_color":              color,
    }
