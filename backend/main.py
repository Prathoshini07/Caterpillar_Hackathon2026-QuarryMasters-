from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base, SessionLocal
from models import Site, Equipment, RentalLog
from routers import dashboard, portal, forecast
from seed_data import generate_100_seeds
from ml.prediction_service import prediction_service
from startup_migrations import run_startup_migrations


app = FastAPI(
    title="Caterpillar Smart Rental Tracking API",
    description=(
        "Backend decision engine for Caterpillar asset tracking, "
        "overdue alerts, underutilization analysis, return scheduling, "
        "and demand forecasting."
    ),
    version="1.0.0",
)


# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(dashboard.router)
app.include_router(portal.router)
app.include_router(forecast.router)


def run_legacy_rental_log_migrations() -> None:
    """
    Preserve the existing lightweight SQLite migrations for older databases.

    These should eventually be moved into startup_migrations.py.
    """
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(rental_logs)")
            ).fetchall()
        }

        if "location" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE rental_logs "
                    "ADD COLUMN location TEXT"
                )
            )
            print("[MIGRATION] Added rental_logs.location")

        if "fuel_usage_liters" not in existing_columns:
            connection.execute(
                text(
                    "ALTER TABLE rental_logs "
                    "ADD COLUMN fuel_usage_liters REAL"
                )
            )
            print("[MIGRATION] Added rental_logs.fuel_usage_liters")


@app.on_event("startup")
def startup_db() -> None:
    # 1. Create tables that do not exist yet.
    Base.metadata.create_all(bind=engine)

    # 2. Upgrade existing tables before querying them.
    run_startup_migrations(engine)
    run_legacy_rental_log_migrations()

    # 3. Load the ML model only after the database schema is valid.
    try:
        prediction_service.load_model()
    except Exception as exc:
        print(
            "[WARNING] Failed to load ML prediction service model: "
            f"{exc}"
        )

    # 4. Check whether legacy seed data is required.
    db = SessionLocal()

    try:
        sites_count = db.query(Site).count()
        equipment_count = db.query(Equipment).count()
        rental_count = db.query(RentalLog).count()

        if (
            sites_count == 0
            and equipment_count == 0
            and rental_count == 0
        ):
            print(
                "Database is completely empty. "
                "Seeding database with 100 legacy rows per table..."
            )
            generate_100_seeds(db)
        else:
            print(
                "Database contains existing data "
                f"({sites_count} sites, "
                f"{equipment_count} equipment, "
                f"{rental_count} rental logs). "
                "Skipping auto-seeding."
            )
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "status": "Online",
        "system": "Caterpillar Smart Rental Tracking System",
        "docs": "/docs",
        "simulation_date": "2026-07-30",
    }