from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from models import Site, Operator, Equipment, RentalLog, DemandForecast
from routers import dashboard, portal
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

@app.on_event("startup")
def startup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # SQLite migration: add new columns if they don't exist
        with engine.connect() as conn:
            existing = [row[1] for row in conn.execute(
                __import__('sqlalchemy').text("PRAGMA table_info(rental_logs)")
            ).fetchall()]
            if "location" not in existing:
                conn.execute(__import__('sqlalchemy').text(
                    "ALTER TABLE rental_logs ADD COLUMN location TEXT"
                ))
                conn.commit()
            if "fuel_usage_liters" not in existing:
                conn.execute(__import__('sqlalchemy').text(
                    "ALTER TABLE rental_logs ADD COLUMN fuel_usage_liters REAL"
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
