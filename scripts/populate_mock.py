"""
Script to populate the SQLite database with mock PV system data for testing purposes.
This script generates:
- Inverter power (AC Side)
- String-level measurements (Power, Voltage, Current for Strings AA, BB, CC)
- Module-level measurements (Power, Voltage, Temperature for 26 modules)

Usage:
    python scripts/populate_mock.py [--force] [--days N]
"""

import sqlite3
from datetime import datetime, timedelta
import random
import sys

DB_PATH = "sma_inverter_data.db"

def populate_mock_data(force=False, days=1):
    """
    Populates the database with mock data.

    Args:
        force (bool): If True, skips confirmation before deleting existing data.
        days (int): Number of days of data to generate (default: 1).
    """
    if not force:
        print("WARNING: This will DELETE all existing data in the database.")
        confirm = input("Are you sure you want to proceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure table exists with correct schema matching main.py
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        category TEXT,
        parameter TEXT,
        value TEXT,
        unit TEXT,
        raw_value TEXT,
        scale REAL,
        key TEXT
    )
    """)

    cursor.execute("DELETE FROM measurements")

    now = datetime.now()
    # Align to the start of the current day or N days ago
    start_time = (now - timedelta(days=days-1)).replace(hour=6, minute=0, second=0, microsecond=0)

    # Generate data from 6 AM to 8 PM each day
    total_records = 0

    for day_offset in range(days):
        day_start = start_time + timedelta(days=day_offset)

        # 14 hours of data per day (6 AM to 8 PM), 5-minute intervals
        for i in range(0, 14 * 60, 5):
            ts_dt = day_start + timedelta(minutes=i)
            ts = ts_dt.isoformat()

            # Simple solar curve approximation (peak at noon)
            progress = i / (14 * 60) # 0 to 1
            solar_factor = max(0, 1 - 4 * (progress - 0.5)**2) # Parabolic curve

            # Inverter Power (max ~5000W)
            inv_p = (4500 * solar_factor) + random.random()*200
            cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (ts, "AC Side > PV Generation", "PV generation power", f"{inv_p:.2f}", "W", str(int(inv_p)), 1.0, "inv_p"))

            # String Data (AA, BB, CC)
            for string_name, channel, base_p, base_v, base_i in [("AA", "1", 1500, 380, 4.0), ("BB", "2", 1200, 370, 3.5), ("CC", "3", 1400, 375, 3.8)]:
                p = (base_p * solar_factor) + random.random()*50
                v = base_v + random.random()*20
                curr = (base_i * solar_factor) + random.random()*0.2

                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "DC Measurements", f"Power (Ch 1 #{channel})", f"{p:.2f}", "W", str(int(p)), 1.0, f"p_ch1_{channel}"))
                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "DC Measurements", f"Voltage (Ch 1 #{channel})", f"{v:.2f}", "V", str(int(v)), 1.0, f"v_ch1_{channel}"))
                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "DC Measurements", f"Current (Ch 1 #{channel})", f"{curr:.2f}", "A", str(int(curr*1000)), 0.001, f"i_ch1_{channel}"))

            # Module Level Data (26 modules)
            for m in range(1, 27):
                p = (160 * solar_factor) + random.random()*10
                v = 34 + random.random()*4
                t = 20 + (30 * solar_factor) + random.random()*5

                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "Module Technology", f"Power (Ch 1 #{m})", f"{p:.2f}", "W", str(int(p)), 1.0, f"m_p_{m}"))
                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "Module Technology", f"Voltage (Ch 1 #{m})", f"{v:.2f}", "V", str(int(v)), 1.0, f"m_v_{m}"))
                cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (ts, "Module Technology", f"Temperature (Ch 1 #{m})", f"{t:.2f}", "°C", str(int(t)), 1.0, f"m_t_{m}"))

            total_records += (1 + 3 + 3 + 3 + 26*3)

    conn.commit()
    conn.close()
    print(f"Mock data populated: {total_records} records over {days} day(s).")

if __name__ == "__main__":
    force = "--force" in sys.argv
    days = 1
    if "--days" in sys.argv:
        try:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            print("Invalid days argument, using default 1.")

    populate_mock_data(force=force, days=days)
