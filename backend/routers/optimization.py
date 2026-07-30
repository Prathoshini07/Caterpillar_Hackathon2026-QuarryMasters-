"""
Financial & Fleet Optimization Router
====================================
1. Fuel & Maintenance Cost Penalties (Excess Idling Penalty Invoice)
2. Preventative Maintenance Scheduling based on Active Engine Hours (vs Calendar Days)

NOTE: Seeded/historical rental_logs store engine_hours_per_day and idle_hours_per_day
      as per-day averages. We use total_engine_hours (stored at checkout) when available,
      falling back to engine_hours_per_day × rental_days for older records.
      accumulated_idle_penalty_usd is stored directly at checkout for checked-out rentals;
      for open/seeded rentals we recompute from available data.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import RentalLog, Equipment, Site, Operator

router = APIRouter(prefix="/api/optimization", tags=["Financial & Fleet Optimization"])

# ── Standard financial & fleet parameters ────────────────────────────────────
IDLE_FUEL_CONSUMPTION_L_HR   = 3.5    # Liters/hour consumed while idling
FUEL_COST_PER_LITER          = 3.25   # USD per liter
HOURLY_IDLE_PENALTY_RATE     = 60.0   # USD per excess idle hour (operator charge)
MAX_HEALTHY_DAILY_IDLE_HRS   = 2.5    # Acceptable warm-up/cool-down threshold per day
CALENDAR_SERVICE_INTERVAL_DAYS = 90   # Traditional: service every 90 calendar days
ENGINE_HOUR_SERVICE_INTERVAL = 250    # Smart: service every 250 active engine hours
SERVICE_COST_USD             = 450.0  # Cost of one service run


@router.get("/data")
def get_optimization_data(db: Session = Depends(get_db)):
    logs = db.query(RentalLog).all()

    penalties_list      = []
    maintenance_list    = []
    seen_equipment_ids  = set()  # dedupe equipment in maintenance view

    total_wasted_fuel_liters     = 0.0
    total_penalties_levied       = 0.0
    total_calendar_service_cost  = 0.0
    total_engine_service_cost    = 0.0

    for log in logs:
        # ── Fetch relationships ───────────────────────────────────────────────
        eq   = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op   = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        eq_type   = eq.type      if eq   else "Machinery"
        site_name = site.site_name if site else "UNASSIGNED"
        op_name   = op.name      if op   else "UNASSIGNED"

        rental_days = log.rental_days or 1

        # ── Resolve total engine & idle hours ─────────────────────────────────
        # Priority: use stored total (from new checkout) → fall back to avg × days (seeded data)
        total_engine_hours = (
            log.total_engine_hours
            if log.total_engine_hours and log.total_engine_hours > 0
            else round((log.engine_hours_per_day or 0.0) * rental_days, 1)
        )
        # Idle total is always derived from per-day avg × days (stored as avg in DB)
        total_idle_hours = round((log.idle_hours_per_day or 0.0) * rental_days, 1)

        # Skip incomplete records (not checked out yet — engine hours still 0)
        if total_engine_hours <= 0:
            continue

        # ── 1. EXCESS IDLING PENALTY ──────────────────────────────────────────
        # Use stored penalty if it was computed at checkout, otherwise recompute.
        if log.accumulated_idle_penalty_usd and log.accumulated_idle_penalty_usd > 0:
            # Use the authoritative value saved at checkout
            total_penalty    = log.accumulated_idle_penalty_usd
            permissible_idle = round(MAX_HEALTHY_DAILY_IDLE_HRS * rental_days, 1)
            excess_idle_hrs  = round(max(0.0, total_idle_hours - permissible_idle), 2)
            wasted_fuel      = round(excess_idle_hrs * IDLE_FUEL_CONSUMPTION_L_HR, 2)
            fuel_cost        = round(wasted_fuel * FUEL_COST_PER_LITER, 2)
            penalty_charge   = round(excess_idle_hrs * HOURLY_IDLE_PENALTY_RATE, 2)
        else:
            # Recompute for seeded/legacy records
            # Formula: excess = total_idle - (2.5 hrs/day × days)
            permissible_idle = round(MAX_HEALTHY_DAILY_IDLE_HRS * rental_days, 1)
            excess_idle_hrs  = round(max(0.0, total_idle_hours - permissible_idle), 2)
            wasted_fuel      = round(excess_idle_hrs * IDLE_FUEL_CONSUMPTION_L_HR, 2)
            fuel_cost        = round(wasted_fuel * FUEL_COST_PER_LITER, 2)
            penalty_charge   = round(excess_idle_hrs * HOURLY_IDLE_PENALTY_RATE, 2)
            total_penalty    = round(fuel_cost + penalty_charge, 2)

        total_wasted_fuel_liters += wasted_fuel
        total_penalties_levied   += total_penalty

        if total_penalty > 0:
            penalties_list.append({
                "rental_id":         log.rental_id,
                "equipment_id":      log.equipment_id,
                "equipment_type":    eq_type,
                "site_name":         site_name,
                "operator_name":     op_name,
                "rental_days":       rental_days,
                "total_engine_hours":total_engine_hours,
                "total_idle_hours":  total_idle_hours,
                "permissible_idle_hrs": permissible_idle,
                "excess_idle_hours": excess_idle_hrs,
                "wasted_fuel_liters":wasted_fuel,
                "fuel_penalty_usd":  fuel_cost,
                "idle_penalty_usd":  penalty_charge,
                "total_penalty_usd": total_penalty,
            })

        # ── 2. PREVENTATIVE MAINTENANCE SCHEDULING ────────────────────────────
        # Only show each equipment once (latest rental determines state)
        if log.equipment_id in seen_equipment_ids:
            continue
        seen_equipment_ids.add(log.equipment_id)

        # Use cumulative active hours stored on the equipment row (most accurate)
        cumulative_active = (eq.cumulative_engine_hours or 0.0) if eq else 0.0

        # If equipment has no cumulative hours yet (seeded data), estimate from this rental
        if cumulative_active == 0.0:
            # Active hours = engine − idle for this rental only
            active_hours_this_rental = round(total_engine_hours - total_idle_hours, 1)
            cumulative_active = active_hours_this_rental

        hours_since_service = round(cumulative_active % ENGINE_HOUR_SERVICE_INTERVAL, 1)
        hours_until_service = round(ENGINE_HOUR_SERVICE_INTERVAL - hours_since_service, 1)
        life_consumed_pct   = round((hours_since_service / ENGINE_HOUR_SERVICE_INTERVAL) * 100.0, 1)

        if hours_until_service <= 30:
            maint_status = "URGENT SERVICE"
            status_color = "#EF4444"
        elif hours_until_service <= 75:
            maint_status = "SERVICE WARNING"
            status_color = "#F97316"
        else:
            maint_status = "OPTIMAL OPERATION"
            status_color = "#10B981"

        # ── Cost comparison: Calendar-based vs Engine-Hour-based ──────────────
        # Calendar Schedule: Services machine every 90 days regardless of usage ($450 / 90 days = $5.00 / calendar day)
        # Engine-Hour Schedule: Services machine every 250 ACTIVE hours ($450 / 250 hours = $1.80 / active hour)
        total_calendar_days = rental_days if rental_days > 0 else 1
        active_hours_worked = max(0.1, total_engine_hours - total_idle_hours)

        # Pro-rated accrued service expenditure
        calendar_cost = round(total_calendar_days * (SERVICE_COST_USD / CALENDAR_SERVICE_INTERVAL_DAYS), 2)
        engine_cost   = round(active_hours_worked * (SERVICE_COST_USD / ENGINE_HOUR_SERVICE_INTERVAL), 2)

        # Savings: Money saved on underutilized/heavily idling machines by NOT servicing based strictly on calendar age
        potential_savings = round(max(0.0, calendar_cost - engine_cost), 2)

        total_calendar_service_cost += calendar_cost
        total_engine_service_cost   += engine_cost

        maintenance_list.append({
            "equipment_id":           log.equipment_id,
            "equipment_type":         eq_type,
            "site_name":              site_name,
            "total_calendar_days":    total_calendar_days,
            "cumulative_active_hours":cumulative_active,
            "hours_since_last_service": hours_since_service,
            "hours_until_service":    hours_until_service,
            "life_consumed_pct":      life_consumed_pct,
            "maint_status":           maint_status,
            "status_color":           status_color,
            "calendar_cost_usd":      calendar_cost,
            "engine_cost_usd":        engine_cost,
            "potential_savings_usd":  potential_savings,
        })

    # Sort: highest penalty first, maintenance: most urgent first
    penalties_list.sort(key=lambda x: x["total_penalty_usd"], reverse=True)
    maintenance_list.sort(key=lambda x: x["hours_until_service"])

    # Total capital saved across underutilized machines by avoiding unnecessary calendar services
    total_savings = round(sum(m["potential_savings_usd"] for m in maintenance_list), 2)

    return {
        "summary": {
            "total_excess_idle_penalties_usd": round(total_penalties_levied, 2),
            "total_wasted_fuel_liters":        round(total_wasted_fuel_liters, 1),
            "maintenance_calendar_cost_usd":   round(total_calendar_service_cost, 2),
            "maintenance_engine_cost_usd":     round(total_engine_service_cost, 2),
            "net_maintenance_savings_usd":      total_savings,
            "penalty_records_count":            len(penalties_list),
            "maintenance_records_count":        len(maintenance_list),
        },
        "rates": {
            "hourly_idle_penalty_rate":       HOURLY_IDLE_PENALTY_RATE,
            "idle_fuel_consumption_l_hr":     IDLE_FUEL_CONSUMPTION_L_HR,
            "fuel_cost_per_liter":            FUEL_COST_PER_LITER,
            "max_healthy_daily_idle_hrs":     MAX_HEALTHY_DAILY_IDLE_HRS,
            "engine_service_interval_hrs":    ENGINE_HOUR_SERVICE_INTERVAL,
            "calendar_service_interval_days": CALENDAR_SERVICE_INTERVAL_DAYS,
            "service_cost_usd":               SERVICE_COST_USD,
        },
        "penalties":             penalties_list,
        "maintenance_schedules": maintenance_list,
    }
