import csv
import sqlite3
import re

def import_csv_to_sqlite(csv_filepath, db_filepath, module_serial):
    conn = sqlite3.connect(db_filepath)
    cursor = conn.cursor()

    cursor.execute('''
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
    ''')
    # Clear existing data to avoid duplicates during testing
    cursor.execute("DELETE FROM measurements")

    with open(csv_filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp = row['Timestamp']
            for col, value in row.items():
                if col == 'Timestamp' or value is None or value == '':
                    continue

                # Category - Parameter (Unit)
                if " - " in col:
                    category, parameter = col.split(" - ", 1)
                else:
                    category = "Unknown"
                    parameter = col

                unit = ""
                if "(" in parameter and parameter.endswith(")"):
                    parameter, unit = parameter.rsplit("(", 1)
                    parameter = parameter.strip()
                    unit = unit[:-1]

                raw_value = value
                scale = 1.0
                key = module_serial

                cursor.execute('''
                    INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, category, parameter, value, unit, raw_value, scale, key))

    conn.commit()
    conn.close()
    print(f"Imported data from {csv_filepath} to {db_filepath}")

if __name__ == "__main__":
    import_csv_to_sqlite('sma_inverter_data_10hour_run.csv', 'sma_inverter_data.db', '3014292153')
