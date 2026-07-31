"""
fix_old_rentals.py
------------------
Marks equipment as AVAILABLE if their rental checkout date
was in 2024 or 2025 (those rentals have already ended).

Also clears current_site_id and assigned_operator_id since
those rentals are complete.

Run from the backend directory:
    python fix_old_rentals.py
"""

import sqlite3
import datetime

DB_PATH = "rental_tracking.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# --- Step 1: Preview which equipment will be affected ---
print("=" * 60)
print("EQUIPMENT WITH RENTALS CHECKED OUT IN 2024 or 2025")
print("=" * 60)

rows = cur.execute("""
    SELECT rl.equipment_id, rl.check_out_date, e.status
    FROM rental_logs rl
    JOIN equipment e ON e.equipment_id = rl.equipment_id
    WHERE rl.check_out_date < '2026-01-01'
    ORDER BY rl.check_out_date DESC
""").fetchall()

affected_ids = set()
for row in rows:
    eq_id = row["equipment_id"]
    checkout = row["check_out_date"]
    status   = row["status"]
    print(f"  {eq_id:12s} | checkout: {checkout} | current status: {status}")
    affected_ids.add(eq_id)

print(f"\nTotal equipment to update: {len(affected_ids)}")
print()

if not affected_ids:
    print("Nothing to update. Exiting.")
    conn.close()
    exit()

# --- Step 2: Apply the fix ---
today = datetime.date.today().isoformat()
updated = 0

for eq_id in affected_ids:
    cur.execute("""
        UPDATE equipment
        SET status = 'AVAILABLE',
            current_site_id = NULL,
            assigned_operator_id = NULL
        WHERE equipment_id = ?
          AND status != 'AVAILABLE'
    """, (eq_id,))
    if cur.rowcount > 0:
        print(f"  [OK] {eq_id} -> marked AVAILABLE")
        updated += 1
    else:
        print(f"  [--] {eq_id} was already AVAILABLE, skipped")

# --- Step 3: Also mark rental_logs is_overdue = 0 for these completed rentals ---
cur.execute("""
    UPDATE rental_logs
    SET is_overdue = 0
    WHERE check_out_date < '2026-01-01'
      AND check_out_date IS NOT NULL
      AND engine_hours_per_day != 0.0
""")
logs_fixed = cur.rowcount
print(f"  [LOG] {logs_fixed} rental log(s) cleared of stale overdue flag")

conn.commit()
conn.close()

print()
print("=" * 60)
print(f"DONE. {updated} equipment record(s) updated to AVAILABLE.")
print("=" * 60)
