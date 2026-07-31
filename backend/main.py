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
app.include_router(anomaly.router)
app.include_router(optimization.router)

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
        # SQLite migration: add new columns if they don't exist
        with engine.connect() as conn:
            existing_log_cols = [row[1] for row in conn.execute(
                __import__('sqlalchemy').text("PRAGMA table_info(rental_logs)")
            ).fetchall()]
            for col, ddl in [
                ("location",                    "ALTER TABLE rental_logs ADD COLUMN location TEXT"),
                ("fuel_usage_liters",           "ALTER TABLE rental_logs ADD COLUMN fuel_usage_liters REAL"),
                ("total_engine_hours",          "ALTER TABLE rental_logs ADD COLUMN total_engine_hours REAL"),
                ("accumulated_idle_penalty_usd","ALTER TABLE rental_logs ADD COLUMN accumulated_idle_penalty_usd REAL DEFAULT 0.0"),
                ("last_serviced_engine_hours",  "ALTER TABLE rental_logs ADD COLUMN last_serviced_engine_hours REAL DEFAULT 0.0"),
            ]:
                if col not in existing_log_cols:
                    conn.execute(__import__('sqlalchemy').text(ddl))
                    conn.commit()

            existing_eq_cols = [row[1] for row in conn.execute(
                __import__('sqlalchemy').text("PRAGMA table_info(equipment)")
            ).fetchall()]
            if "cumulative_engine_hours" not in existing_eq_cols:
                conn.execute(__import__('sqlalchemy').text(
                    "ALTER TABLE equipment ADD COLUMN cumulative_engine_hours REAL DEFAULT 0.0"
                ))
                conn.commit()

        # Check if DB needs legacy seeding (only when all core operational tables are completely empty)
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
        "simulation_date": str(__import__('datetime').date.today())
    }