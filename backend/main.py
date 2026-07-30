from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from models import Site, Operator, Equipment, RentalLog, DemandForecast
from routers import dashboard, portal, anomaly, optimization
from seed_data import generate_100_seeds

app = FastAPI(
    title="Caterpillar Smart Rental Tracking API",
    description="Backend decision engine for Caterpillar asset tracking, overdue alerts, underutilization analysis, and return scheduling.",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(dashboard.router)
app.include_router(portal.router)
app.include_router(anomaly.router)
app.include_router(optimization.router)

@app.on_event("startup")
def startup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # SQLite migration: add new columns if they don't exist
        with engine.connect() as conn:
            # ── rental_logs column migrations ─────────────────────────────────
            existing_log_cols = [row[1] for row in conn.execute(
                __import__('sqlalchemy').text("PRAGMA table_info(rental_logs)")
            ).fetchall()]
            for col, ddl in [
                ("location",                   "ALTER TABLE rental_logs ADD COLUMN location TEXT"),
                ("fuel_usage_liters",          "ALTER TABLE rental_logs ADD COLUMN fuel_usage_liters REAL"),
                ("total_engine_hours",         "ALTER TABLE rental_logs ADD COLUMN total_engine_hours REAL"),
                ("accumulated_idle_penalty_usd","ALTER TABLE rental_logs ADD COLUMN accumulated_idle_penalty_usd REAL DEFAULT 0.0"),
                ("last_serviced_engine_hours", "ALTER TABLE rental_logs ADD COLUMN last_serviced_engine_hours REAL DEFAULT 0.0"),
            ]:
                if col not in existing_log_cols:
                    conn.execute(__import__('sqlalchemy').text(ddl))
                    conn.commit()

            # ── equipment column migrations ────────────────────────────────────
            existing_eq_cols = [row[1] for row in conn.execute(
                __import__('sqlalchemy').text("PRAGMA table_info(equipment)")
            ).fetchall()]
            if "cumulative_engine_hours" not in existing_eq_cols:
                conn.execute(__import__('sqlalchemy').text(
                    "ALTER TABLE equipment ADD COLUMN cumulative_engine_hours REAL DEFAULT 0.0"
                ))
                conn.commit()

        # Check if DB needs seeding (if sites table has less than 100 rows)
        sites_count = db.query(Site).count()
        if sites_count < 100:
            print("Seeding database with 100 rows per table...")
            generate_100_seeds(db)
        else:
            print(f"Database already populated with {sites_count} sites.")
    finally:
        db.close()

@app.get("/")
def root():
    return {
        "status": "Online",
        "system": "Caterpillar Smart Rental Tracking System",
        "docs": "/docs",
        "simulation_date": "2026-07-30"
    }
