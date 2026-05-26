import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "sma_inverter_data.db"

def populate_mock_data():
    print("WARNING: This will DELETE all existing data in the database.")
    confirm = input("Are you sure you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM measurements")

    start_time = datetime.now() - timedelta(hours=2)

    # Categories from layout.json
    categories = ["AC Side > PV Generation", "DC Measurements", "Module Technology"]

    for i in range(60): # 60 minutes of data
        ts = (start_time + timedelta(minutes=i)).isoformat()

        # Inverter Power
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "AC Side > PV Generation", "PV generation power", str(4000 + random.random()*500), "W"))

        # String Data (AA, BB, CC)
        # String AA uses Ch 1 #1
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Power (Ch 1 #1)", str(1500 + random.random()*100), "W"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Voltage (Ch 1 #1)", str(400 + random.random()*10), "V"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Current (Ch 1 #1)", str(3.7 + random.random()*0.2), "A"))

        # String BB uses Ch 1 #2
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Power (Ch 1 #2)", str(1200 + random.random()*100), "W"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Voltage (Ch 1 #2)", str(380 + random.random()*10), "V"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Current (Ch 1 #2)", str(3.1 + random.random()*0.2), "A"))

        # String CC uses Ch 1 #3
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Power (Ch 1 #3)", str(1300 + random.random()*100), "W"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Voltage (Ch 1 #3)", str(390 + random.random()*10), "V"))
        cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                       (ts, "DC Measurements", "Current (Ch 1 #3)", str(3.3 + random.random()*0.2), "A"))

        # Module Level Data (26 modules)
        for m in range(1, 27):
            # Power
            cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                           (ts, "Module Technology", f"Power (Ch 1 #{m})", str(150 + random.random()*20), "W"))
            # Voltage
            cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                           (ts, "Module Technology", f"Voltage (Ch 1 #{m})", str(35 + random.random()*2), "V"))
            # Temp
            cursor.execute("INSERT INTO measurements (timestamp, category, parameter, value, unit) VALUES (?, ?, ?, ?, ?)",
                           (ts, "Module Technology", f"Temperature (Ch 1 #{m})", str(45 + random.random()*5), "°C"))

    conn.commit()
    conn.close()
    print("Mock data populated.")

if __name__ == "__main__":
    populate_mock_data()
