from sqlalchemy import Column, String, Integer, Float, Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Site(Base):
    __tablename__ = "sites"

    site_id = Column(String, primary_key=True, index=True)
    site_name = Column(String, nullable=False)
    location = Column(String, nullable=False)

    equipments = relationship("Equipment", back_populates="current_site")
    rental_logs = relationship("RentalLog", back_populates="site")
    demand_forecasts = relationship("DemandForecast", back_populates="site")
    weekly_demands = relationship("WeeklyDemand", back_populates="site")


class Operator(Base):
    __tablename__ = "operators"

    operator_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_info = Column(String, nullable=False)

    assigned_equipments = relationship("Equipment", back_populates="assigned_operator")
    rental_logs = relationship("RentalLog", back_populates="operator")


class Equipment(Base):
    __tablename__ = "equipment"

    equipment_id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False)  # Excavator, Crane, Bulldozer, Grader, Loader, Dump Truck, Wheel Loader
    status = Column(String, nullable=False)  # RENTED, AVAILABLE, MAINTENANCE, UNDERUTILIZED
    current_site_id = Column(String, ForeignKey("sites.site_id"), nullable=True)
    assigned_operator_id = Column(String, ForeignKey("operators.operator_id"), nullable=True)

    current_site = relationship("Site", back_populates="equipments")
    assigned_operator = relationship("Operator", back_populates="assigned_equipments")
    rental_logs = relationship("RentalLog", back_populates="equipment")


class RentalLog(Base):
    __tablename__ = "rental_logs"

    rental_id = Column(String, primary_key=True, index=True)
    equipment_id = Column(String, ForeignKey("equipment.equipment_id"), nullable=False)
    site_id = Column(String, ForeignKey("sites.site_id"), nullable=True)
    operator_id = Column(String, ForeignKey("operators.operator_id"), nullable=True)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    engine_hours_per_day = Column(Float, nullable=False)
    idle_hours_per_day = Column(Float, nullable=False)
    rental_days = Column(Integer, nullable=False)
    is_overdue = Column(Boolean, default=False)
    anomaly_flag = Column(String, nullable=True)  # HIGH_IDLE, UNASSIGNED_USAGE, OVERDUE_BREACH, OPTIMAL
    location = Column(String, nullable=True)            # Site location captured at check-in
    fuel_usage_liters = Column(Float, nullable=True)    # Fuel consumed, captured at check-out

    equipment = relationship("Equipment", back_populates="rental_logs")
    site = relationship("Site", back_populates="rental_logs")
    operator = relationship("Operator", back_populates="rental_logs")


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    forecast_id = Column(String, primary_key=True, index=True)
    site_id = Column(String, ForeignKey("sites.site_id"), nullable=False)
    equipment_type = Column(String, nullable=False)
    predicted_demand = Column(Integer, nullable=False)
    forecast_date = Column(Date, nullable=False)

    site = relationship("Site", back_populates="demand_forecasts")


class WeeklyDemand(Base):
    __tablename__ = "weekly_demand"

    weekly_demand_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    week_start = Column(Date, nullable=False, index=True)
    site_id = Column(String, ForeignKey("sites.site_id"), nullable=False, index=True)
    equipment_type = Column(String, nullable=False, index=True)
    weekly_demand = Column(Integer, nullable=False)

    site = relationship("Site", back_populates="weekly_demands")

    __table_args__ = (
        UniqueConstraint("week_start", "site_id", "equipment_type", name="uix_weekly_demand_week_site_type"),
    )

