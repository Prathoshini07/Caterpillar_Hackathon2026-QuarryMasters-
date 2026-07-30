from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class SiteSchema(BaseModel):
    site_id: str
    site_name: str
    location: str

    class Config:
        from_attributes = True

class OperatorSchema(BaseModel):
    operator_id: str
    name: str
    contact_info: str

    class Config:
        from_attributes = True

class EquipmentSchema(BaseModel):
    equipment_id: str
    type: str
    status: str
    current_site_id: Optional[str] = None
    assigned_operator_id: Optional[str] = None

    class Config:
        from_attributes = True

class RentalLogSchema(BaseModel):
    rental_id: str
    equipment_id: str
    site_id: Optional[str] = None
    operator_id: Optional[str] = None
    check_in_date: date
    check_out_date: date
    engine_hours_per_day: float
    idle_hours_per_day: float
    rental_days: int
    is_overdue: bool
    anomaly_flag: Optional[str] = None

    class Config:
        orm_mode = True

class ActionItemSchema(BaseModel):
    id: str
    equipment_id: str
    equipment_type: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    operator_name: Optional[str] = None
    operator_contact: Optional[str] = None
    priority: str  # HIGH, MED, LOW
    action_type: str  # OVERDUE, UNDERUTILIZED, RETURN_TODAY, READY_TO_DEPLOY
    title: str
    description: str
    recommended_action: str
    due_date: str
    days_overdue: int

class OverdueAlertItem(BaseModel):
    equipment_id: str
    type: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    operator_name: Optional[str] = None
    operator_contact: Optional[str] = None
    check_out_date: str
    days_overdue: int
    alert_level: int  # 1 to 5
    alert_name: str  # Level 1 Info ... Level 5 Critical Breach
    recommended_action: str

class UnderutilizedItem(BaseModel):
    equipment_id: str
    type: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    operator_name: Optional[str] = None
    engine_hours: float
    idle_hours: float
    utilization_pct: float
    anomaly_flag: str
    recommendation: str

class DatewiseReturnItem(BaseModel):
    date: str
    total_returns: int
    items: List[dict]


# ──────────────────────────────────────────────
# User Portal Schemas  (single RentalLog table)
# ──────────────────────────────────────────────

class CheckInRequest(BaseModel):
    equipment_id: str
    equipment_type: str          # Excavator | Crane | Bulldozer | Grader
    site_id: str
    location: str                # Physical location of the site
    check_in_date: date
    expected_rental_days: int
    operator_id: str

class CheckOutRequest(BaseModel):
    rental_id: str               # Generated at check-in — must match
    checkout_date: date
    engine_hrs_per_day: float
    idle_hrs_per_day: float
    fuel_usage_liters: float     # Total fuel consumed during rental
    operator_id: str
