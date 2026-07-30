import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models import Site, Operator, Equipment, RentalLog, DemandForecast
from seed_data import generate_100_seeds

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

SIMULATED_TODAY = datetime.date(2026, 7, 30)

def compute_live_status(eq, log, today=SIMULATED_TODAY):
    if eq.status == "AVAILABLE" or log is None:
        return "Available"
    
    days_diff = (today - log.check_out_date).days
    if days_diff > 0:
        return "Overdue"
    elif days_diff == 0:
        return "Returning Today"
        
    eng = log.engine_hours_per_day or 0.0
    idle = log.idle_hours_per_day or 0.0
    tot = eng + idle
    idle_ratio = (idle / tot * 100.0) if tot > 0 else 0.0
    
    if idle_ratio >= 50.0:
        return "Idle"
        
    return "In Use"

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_equipment = db.query(Equipment).count()
    
    # Compute counts dynamically based on the 5-state logic
    counts = {
        "Available": 0,
        "In Use": 0,
        "Idle": 0,
        "Returning Today": 0,
        "Overdue": 0
    }
    
    equipments = db.query(Equipment).all()
    for eq in equipments:
        last_log = db.query(RentalLog).filter(RentalLog.equipment_id == eq.equipment_id).order_by(RentalLog.check_out_date.desc()).first()
        status = compute_live_status(eq, last_log, SIMULATED_TODAY)
        counts[status] += 1

    # Overall Idle Ratio logic (keeping for metrics)
    all_logs = db.query(RentalLog).all()
    total_idle_ratio = 0.0
    valid_count = 0

    for log in all_logs:
        if log.engine_hours_per_day > 0:
            idle_ratio = (log.idle_hours_per_day / (log.engine_hours_per_day + log.idle_hours_per_day)) * 100.0
            total_idle_ratio += idle_ratio
            valid_count += 1

    avg_idle_ratio = round(total_idle_ratio / valid_count, 1) if valid_count > 0 else 0.0
    avg_utilization = round(100.0 - avg_idle_ratio, 1)

    return {
        "simulation_date": str(SIMULATED_TODAY),
        "total_equipment": total_equipment,
        "available_count": counts["Available"],
        "in_use_count": counts["In Use"],
        "idle_count": counts["Idle"],
        "returning_today_count": counts["Returning Today"],
        "overdue_count": counts["Overdue"],
        "avg_idle_ratio_pct": avg_idle_ratio,
        "avg_utilization_pct": avg_utilization,
        "total_sites": db.query(Site).count(),
        "total_operators": db.query(Operator).count()
    }


@router.get("/action-queue")
def get_action_queue(db: Session = Depends(get_db)):
    actions = []
    logs = db.query(RentalLog).all()

    for log in logs:
        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        days_diff = (SIMULATED_TODAY - log.check_out_date).days
        
        eng = log.engine_hours_per_day
        idle = log.idle_hours_per_day
        idle_ratio = round((idle / (eng + idle) * 100.0), 1) if (eng + idle) > 0 else 0.0

        site_name = site.site_name if site else "Unassigned Location"
        op_name = op.name if op else "Unassigned Operator"
        op_contact = op.contact_info if op else "N/A"

        # 1. Overdue / Today Return Actions
        if days_diff == 0:  # Scheduled Return Today
            actions.append({
                "id": f"ACT-TODAY-{log.rental_id}",
                "equipment_id": log.equipment_id,
                "equipment_type": eq.type if eq else "Equipment",
                "site_id": log.site_id,
                "site_name": site_name,
                "operator_name": op_name,
                "operator_contact": op_contact,
                "priority": "HIGH",
                "action_type": "RETURN_TODAY",
                "title": f"Return Today: {log.equipment_id} ({eq.type if eq else ''})",
                "description": f"Contract due today at {site_name}. Verify machine check-in.",
                "recommended_action": "Contact operator for check-in confirmation & dispatch flatbed haulage.",
                "due_date": str(log.check_out_date),
                "days_overdue": 0
            })
        elif days_diff > 0:  # Overdue Return
            actions.append({
                "id": f"ACT-OVD-{log.rental_id}",
                "equipment_id": log.equipment_id,
                "equipment_type": eq.type if eq else "Equipment",
                "site_id": log.site_id,
                "site_name": site_name,
                "operator_name": op_name,
                "operator_contact": op_contact,
                "priority": "HIGH",
                "action_type": "OVERDUE",
                "title": f"OVERDUE ({days_diff} Days Late) - {log.equipment_id}",
                "description": f"Rental passed return date ({log.check_out_date}). Level {min(5, (days_diff // 3) + 1)} Alert active for site {site_name}.",
                "recommended_action": f"Issue Level {min(5, (days_diff // 3) + 1)} Penalty Notice & initiate machine recovery protocol.",
                "due_date": str(log.check_out_date),
                "days_overdue": days_diff
            })

        # 2. Underutilized Actions (Idle Efficiency Ratio > 50%)
        if idle_ratio > 50.0:
            actions.append({
                "id": f"ACT-IDLE-{log.rental_id}",
                "equipment_id": log.equipment_id,
                "equipment_type": eq.type if eq else "Equipment",
                "site_id": log.site_id,
                "site_name": site_name,
                "operator_name": op_name,
                "operator_contact": op_contact,
                "priority": "HIGH" if idle_ratio >= 75.0 else "MED",
                "action_type": "UNDERUTILIZED",
                "title": f"Underutilized Asset: {log.equipment_id} (Idle Ratio: {idle_ratio}%)",
                "description": f"Machine idle for {idle} hrs of {eng} total engine runtime ({idle_ratio}% idle ratio > 50% threshold) at {site_name}.",
                "recommended_action": "Reallocate asset to high-demand Quarry site or execute remote telematics power-down.",
                "due_date": str(log.check_out_date),
                "days_overdue": max(0, days_diff)
            })

    priority_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    actions.sort(key=lambda x: (priority_order.get(x["priority"], 9), -x["days_overdue"]))

    return {
        "total_actions": len(actions),
        "actions": actions
    }


@router.get("/available-equipment")
def get_available_equipment(db: Session = Depends(get_db)):
    available_items = db.query(Equipment).filter(Equipment.status == "AVAILABLE").all()
    result = []
    
    for eq in available_items:
        last_log = db.query(RentalLog).filter(RentalLog.equipment_id == eq.equipment_id).order_by(RentalLog.check_out_date.desc()).first()
        last_site = db.query(Site).filter(Site.site_id == last_log.site_id).first() if last_log and last_log.site_id else None
        
        result.append({
            "equipment_id": eq.equipment_id,
            "type": eq.type,
            "status": eq.status,
            "last_site_id": last_log.site_id if last_log else None,
            "last_site_name": last_site.site_name if last_site else "CAT Central Yard",
            "last_location": last_site.location if last_site else "Peoria Depot",
            "readiness": "100% Ready for Rental",
            "fuel_level": "95% Diesel Tank",
            "telematics_health": "Optimal"
        })
        
    return {
        "count": len(result),
        "available_equipments": result
    }


@router.get("/equipment")
def get_all_equipment_details(db: Session = Depends(get_db)):
    equipments = db.query(Equipment).all()
    result = []
    
    for eq in equipments:
        last_log = db.query(RentalLog).filter(RentalLog.equipment_id == eq.equipment_id).order_by(RentalLog.check_out_date.desc()).first()
        site = db.query(Site).filter(Site.site_id == last_log.site_id).first() if last_log and last_log.site_id else None
        op = db.query(Operator).filter(Operator.operator_id == last_log.operator_id).first() if last_log and last_log.operator_id else None
        
        live_status = compute_live_status(eq, last_log, SIMULATED_TODAY)
        
        # Calculate some extra telemetry data for the view
        idle_ratio = 0.0
        days_remaining = 0
        days_overdue = 0
        if last_log and live_status != "Available":
            eng = last_log.engine_hours_per_day or 0.0
            idle = last_log.idle_hours_per_day or 0.0
            tot = eng + idle
            idle_ratio = round((idle / tot * 100.0), 1) if tot > 0 else 0.0
            
            diff = (SIMULATED_TODAY - last_log.check_out_date).days
            if diff > 0:
                days_overdue = diff
            else:
                days_remaining = -diff
        
        result.append({
            "equipment_id": eq.equipment_id,
            "type": eq.type,
            "live_status": live_status,
            "site_name": site.site_name if site else "N/A",
            "location": site.location if site else "N/A",
            "operator_name": op.name if op else "N/A",
            "idle_ratio": idle_ratio,
            "days_remaining": days_remaining,
            "days_overdue": days_overdue,
            "check_out_date": str(last_log.check_out_date) if last_log else None
        })
        
    return {
        "count": len(result),
        "equipments": result
    }

@router.get("/overdue-alerts")
def get_overdue_alerts(db: Session = Depends(get_db)):
    overdue_logs = db.query(RentalLog).filter(RentalLog.check_out_date <= SIMULATED_TODAY).all()
    
    levels = {
        1: {"level": 1, "name": "Level 1: Gentle Reminder", "color": "#3B82F6", "badge": "INFO", "count": 0, "items": []},
        2: {"level": 2, "name": "Level 2: Caution Notice", "color": "#EAB308", "badge": "WARNING", "count": 0, "items": []},
        3: {"level": 3, "name": "Level 3: Escalated Surcharge", "color": "#F97316", "badge": "ESCALATED", "count": 0, "items": []},
        4: {"level": 4, "name": "Level 4: High Risk Penalty", "color": "#EF4444", "badge": "HIGH RISK", "count": 0, "items": []},
        5: {"level": 5, "name": "Level 5: Critical Contract Breach", "color": "#A855F7", "badge": "CRITICAL LOCK", "count": 0, "items": []},
    }

    for log in overdue_logs:
        days_late = (SIMULATED_TODAY - log.check_out_date).days
        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        if days_late <= 1:
            lvl = 1
            action = "Send SMS/Email reminder to operator for return confirmation."
        elif days_late <= 3:
            lvl = 2
            action = "Notify site manager of potential rental extension charges."
        elif days_late <= 6:
            lvl = 3
            action = "Apply $250/day late penalty fee and dispatch field supervisor."
        elif days_late <= 10:
            lvl = 4
            action = "Issue formal contract default notice and pause further equipment leases."
        else:
            lvl = 5
            action = "TRIGGER REMOTE TELEMATICS ENGINE LOCK & DISPATCH RECOVERY TOW."

        item = {
            "equipment_id": log.equipment_id,
            "type": eq.type if eq else "Machinery",
            "site_id": log.site_id,
            "site_name": site.site_name if site else "N/A",
            "operator_id": log.operator_id,
            "operator_name": op.name if op else "Unassigned",
            "operator_contact": op.contact_info if op else "N/A",
            "check_out_date": str(log.check_out_date),
            "days_overdue": days_late,
            "alert_level": lvl,
            "alert_name": levels[lvl]["name"],
            "recommended_action": action
        }

        levels[lvl]["count"] += 1
        levels[lvl]["items"].append(item)

    return {
        "simulation_date": str(SIMULATED_TODAY),
        "total_overdue": len(overdue_logs),
        "levels": levels
    }


@router.get("/underutilized")
def get_underutilized(
    threshold_pct: float = Query(50.0, description="Idle Efficiency Ratio threshold %"),
    db: Session = Depends(get_db)
):
    """
    Idle Efficiency Ratio % = (idle_hours / engine_hours) * 100%
    Note: Engine hours is total engine runtime, so Engine Hours >= Idle Hours ALWAYS.
    Flagged as underutilized if Idle Efficiency Ratio > threshold (50%).
    Sorted descending by Idle Efficiency Ratio (worst underutilization first).
    """
    logs = db.query(RentalLog).all()
    results = []

    for log in logs:
        eng = log.engine_hours_per_day
        idle = log.idle_hours_per_day

        idle_efficiency_ratio = round((idle / (eng + idle) * 100.0), 1) if (eng + idle) > 0 else 0.0
        productive_hours = round(max(0.0, eng - idle), 1)

        is_underutilized = idle_efficiency_ratio > threshold_pct

        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        recommendation = "Optimal Machine Efficiency"
        if idle_efficiency_ratio > 75.0:
            recommendation = "Severe Engine Idling (>75% Idle Ratio). Immediate Reallocation or Telematics Shutdown!"
        elif is_underutilized:
            recommendation = "Underutilized (>50% Idle Ratio). Review Site Operating Hours & Transfer Asset."

        results.append({
            "rental_id": log.rental_id,
            "equipment_id": log.equipment_id,
            "type": eq.type if eq else "Heavy Equipment",
            "site_id": log.site_id,
            "site_name": site.site_name if site else "N/A",
            "operator_name": op.name if op else "Unassigned",
            "engine_hours": eng,
            "idle_hours": idle,
            "productive_hours": productive_hours,
            "idle_efficiency_ratio": idle_efficiency_ratio,
            "is_underutilized": is_underutilized,
            "anomaly_flag": log.anomaly_flag or ("HIGH_IDLE_RATIO" if is_underutilized else "OPTIMAL"),
            "recommendation": recommendation
        })

    results.sort(key=lambda x: x["idle_efficiency_ratio"], reverse=True)

    return {
        "idle_ratio_threshold_pct": threshold_pct,
        "total_analyzed": len(results),
        "underutilized_count": sum(1 for r in results if r["is_underutilized"]),
        "equipments": results
    }


@router.get("/datewise-returns")
def get_datewise_returns(db: Session = Depends(get_db)):
    """
    Organized into 3 distinct sections for neat tabular presentation:
    1. overdue_returns: check_out_date < SIMULATED_TODAY
    2. today_returns: check_out_date == SIMULATED_TODAY
    3. upcoming_returns: check_out_date > SIMULATED_TODAY
    """
    logs = db.query(RentalLog).order_by(RentalLog.check_out_date.asc()).all()

    overdue_items = []
    today_items = []
    upcoming_items = []

    for log in logs:
        eq = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        days_overdue = (SIMULATED_TODAY - log.check_out_date).days
        days_remaining = (log.check_out_date - SIMULATED_TODAY).days

        item = {
            "rental_id": log.rental_id,
            "equipment_id": log.equipment_id,
            "type": eq.type if eq else "Equipment",
            "site_id": log.site_id,
            "site_name": site.site_name if site else "N/A",
            "location": site.location if site else "N/A",
            "operator_name": op.name if op else "Unassigned",
            "operator_contact": op.contact_info if op else "N/A",
            "check_in_date": str(log.check_in_date),
            "check_out_date": str(log.check_out_date),
            "days_overdue": max(0, days_overdue),
            "days_remaining": max(0, days_remaining),
            "engine_hours": log.engine_hours_per_day,
            "idle_hours": log.idle_hours_per_day
        }

        if log.check_out_date < SIMULATED_TODAY:
            item["status_label"] = f"OVERDUE ({days_overdue} days)"
            item["alert_level"] = min(5, (days_overdue // 3) + 1)
            overdue_items.append(item)
        elif log.check_out_date == SIMULATED_TODAY:
            item["status_label"] = "DUE TODAY"
            today_items.append(item)
        else:
            item["status_label"] = f"UPCOMING ({days_remaining} days left)"
            upcoming_items.append(item)

    overdue_items.sort(key=lambda x: x["days_overdue"], reverse=True)
    upcoming_items.sort(key=lambda x: x["check_out_date"])

    return {
        "simulation_date": str(SIMULATED_TODAY),
        "overdue_count": len(overdue_items),
        "today_count": len(today_items),
        "upcoming_count": len(upcoming_items),
        "overdue_returns": overdue_items,
        "today_returns": today_items,
        "upcoming_returns": upcoming_items
    }


@router.post("/reseed")
def reseed_database(db: Session = Depends(get_db)):
    generate_100_seeds(db)
    return {"message": "Database reseeded successfully with 100 rows per table and corrected engine/idle ratios!"}
