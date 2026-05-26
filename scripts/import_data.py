import csv
import sqlite3
import re
import sys

def import_csv_to_sqlite(csv_filepath, db_filepath, module_serial):
    conn = sqlite3.connect(db_filepath)
    cursor = conn.cursor()

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
    import argparse
    parser = argparse.ArgumentParser(description="Import SMA CSV data to SQLite")
    parser.add_argument("csv", help="Path to the CSV file")
    parser.add_argument("--db", default="sma_inverter_data.db", help="Path to the SQLite database")
    parser.add_argument("--serial", default="3014292153", help="Inverter serial number")
    args = parser.parse_args()

    import os
    if not os.path.exists(args.csv):
        print(f"Error: File {args.csv} not found.")
        sys.exit(1)

    import_csv_to_sqlite(args.csv, args.db, args.serial)
