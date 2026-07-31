from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


MIGRATIONS = {
    "sqlite": [
        (
            "equipment",
            "cumulative_engine_hours",
            """
            ALTER TABLE equipment
            ADD COLUMN cumulative_engine_hours
            FLOAT NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "total_engine_hours",
            """
            ALTER TABLE rental_logs
            ADD COLUMN total_engine_hours
            FLOAT NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "accumulated_idle_penalty_usd",
            """
            ALTER TABLE rental_logs
            ADD COLUMN accumulated_idle_penalty_usd
            FLOAT NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "last_serviced_engine_hours",
            """
            ALTER TABLE rental_logs
            ADD COLUMN last_serviced_engine_hours
            FLOAT NOT NULL DEFAULT 0.0
            """,
        ),
    ],
    "postgresql": [
        (
            "equipment",
            "cumulative_engine_hours",
            """
            ALTER TABLE equipment
            ADD COLUMN cumulative_engine_hours
            DOUBLE PRECISION NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "total_engine_hours",
            """
            ALTER TABLE rental_logs
            ADD COLUMN total_engine_hours
            DOUBLE PRECISION NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "accumulated_idle_penalty_usd",
            """
            ALTER TABLE rental_logs
            ADD COLUMN accumulated_idle_penalty_usd
            DOUBLE PRECISION NOT NULL DEFAULT 0.0
            """,
        ),
        (
            "rental_logs",
            "last_serviced_engine_hours",
            """
            ALTER TABLE rental_logs
            ADD COLUMN last_serviced_engine_hours
            DOUBLE PRECISION NOT NULL DEFAULT 0.0
            """,
        ),
    ],
}


def column_exists(
    engine: Engine,
    table_name: str,
    column_name: str,
) -> bool:
    inspector = inspect(engine)

    if table_name not in inspector.get_table_names():
        return False

    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def run_startup_migrations(engine: Engine) -> None:
    dialect = engine.dialect.name
    print(f"[MIGRATION] Checking schema using dialect: {dialect}")

    if dialect not in MIGRATIONS:
        raise RuntimeError(
            f"Unsupported database dialect for startup migrations: {dialect}"
        )

    applied = 0

    for table_name, column_name, sql in MIGRATIONS[dialect]:
        if column_exists(engine, table_name, column_name):
            print(
                f"[MIGRATION] {table_name}.{column_name} already exists"
            )
            continue

        with engine.begin() as connection:
            connection.execute(text(sql))

        print(f"[MIGRATION] Added {table_name}.{column_name}")
        applied += 1

    if applied == 0:
        print("[MIGRATION] Database schema is already up to date")
    else:
        print(f"[MIGRATION] Applied {applied} migration(s)")