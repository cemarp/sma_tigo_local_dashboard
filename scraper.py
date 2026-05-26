#!/usr/bin/env python3
"""
SMA Sunny Boy Inverter Scraper
"""

import os
import sys
import json
import time
import socket
import sqlite3
import argparse
from datetime import datetime
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_IP = os.environ.get("INVERTER_IP", "")
DEFAULT_USER_GROUP = os.environ.get("INVERTER_USER_GROUP", "usr")
DEFAULT_PASSWORD = os.environ.get("INVERTER_PASSWORD", "")
DEFAULT_DB_FILE = os.environ.get("DATABASE_URL", "sma_inverter_data.db")

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
L10N_CACHE = os.path.join(CACHE_DIR, "en-US.json")
META_CACHE = os.path.join(CACHE_DIR, "ObjectMetadata_User.json")

def init_db(db_path):
    conn = sqlite3.connect(db_path)
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON measurements(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_key ON measurements(key)')
    conn.commit()
    return conn

def authenticate(session, base_url, password):
    url = f"{base_url}/dyn/login.json"
    payload = {"right": DEFAULT_USER_GROUP, "pass": password}
    try:
        r = session.post(url, json=payload, verify=False, timeout=5)
        r.raise_for_status()
        data = r.json()
        return data.get("result", {}).get("sid")
    except Exception:
        return None

def ensure_cached_files(session, base_url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    en_us = None
    metadata = None
    try:
        if os.path.exists(L10N_CACHE):
            with open(L10N_CACHE, "r") as f: en_us = json.load(f)
        if not en_us:
            r = session.get(f"{base_url}/data/l10n/en-US.json", verify=False, timeout=10)
            en_us = r.json()
            with open(L10N_CACHE, "w") as f: json.dump(en_us, f)
        if os.path.exists(META_CACHE):
            with open(META_CACHE, "r") as f: metadata = json.load(f)
        if not metadata:
            r = session.get(f"{base_url}/data/ObjectMetadata_User.json", verify=False, timeout=10)
            metadata = r.json()
            with open(META_CACHE, "w") as f: json.dump(metadata, f)
    except Exception:
        pass
    return en_us, metadata

def extract_telemetry(session, base_url, sid, metadata, en_us):
    url = f"{base_url}/dyn/getAllOnlValues.json?sid={sid}"
    try:
        r = session.post(url, json={"destDev": []}, verify=False, timeout=10)
        results = r.json().get("result", {})
    except Exception as e:
        print(f"Error fetching telemetry: {e}")
        return []

    if not results: return []
    device_id = list(results.keys())[0]
    device_telemetry = results[device_id]
    records = []
    timestamp = datetime.now().isoformat()

    for sensor_key, channels in device_telemetry.items():
        meta_entry = metadata.get(sensor_key)
        if not meta_entry: continue
        tag_hier = meta_entry.get("TagHier", [])
        category_path = [en_us.get(str(h_id), str(h_id)) for h_id in tag_hier]
        category_path_lower = [c.lower() for c in category_path]

        target_category = ""
        # Flexible but specific category mapping
        if "pv generation" in category_path_lower:
            target_category = "AC Side > PV Generation"
        elif "ac side" in category_path_lower:
            target_category = "AC Side"
        elif "pv module electronics" in category_path_lower or "module technology" in category_path_lower:
            target_category = "Module Technology"
        elif "dc side" in category_path_lower or "dc measurements" in category_path_lower:
            target_category = "DC Measurements"
        else:
            # Fallback to the first item in hierarchy if it exists
            target_category = category_path[0] if category_path else "Unknown"

        param_name = en_us.get(str(meta_entry.get("TagId")), sensor_key)
        scale = meta_entry.get("Scale", 1)
        unit = en_us.get(str(meta_entry.get("Unit")), "")

        for channel_id, val_list in channels.items():
            for idx, item in enumerate(val_list):
                if not isinstance(item, dict) or "val" not in item: continue
                raw_val = item["val"]
                if raw_val is None: continue
                val = raw_val * scale if isinstance(raw_val, (int, float)) else str(raw_val)
                full_name = f"{param_name} (Ch {channel_id} #{idx+1})" if len(channels)>1 or len(val_list)>1 else param_name
                records.append({
                    "timestamp": timestamp, "category": target_category, "parameter": full_name,
                    "value": str(val), "unit": unit, "raw_value": str(raw_val), "scale": scale, "key": sensor_key
                })
    return records

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=os.environ.get("INVERTER_IP", DEFAULT_IP))
    parser.add_argument("--password", default=os.environ.get("INVERTER_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--db", default=os.environ.get("DATABASE_URL", DEFAULT_DB_FILE))
    parser.add_argument("--interval", type=int, default=os.environ.get("SCRAPE_INTERVAL"))
    args = parser.parse_args()

    db_conn = init_db(args.db)
    session = requests.Session()
    base_url = f"https://{args.ip}"

    def run_cycle():
        if not args.ip or not args.password:
            print("Error: INVERTER_IP and INVERTER_PASSWORD must be set.")
            return
        sid = authenticate(session, base_url, args.password)
        if not sid:
            print(f"Authentication failed for {args.ip}")
            return
        en_us, metadata = ensure_cached_files(session, base_url)
        if not en_us or not metadata: return
        records = extract_telemetry(session, base_url, sid, metadata, en_us)
        cursor = db_conn.cursor()
        for r in records:
            cursor.execute('''
                INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (r['timestamp'], r['category'], r['parameter'], r['value'], r['unit'], r['raw_value'], r['scale'], r['key']))
        db_conn.commit()
        print(f"Scraped {len(records)} records.")
        # Logout
        session.post(f"{base_url}/dyn/logout.json?sid={sid}", json={}, verify=False, timeout=3)

    if args.interval:
        while True:
            try: run_cycle()
            except Exception as e: print(f"Error: {e}")
            time.sleep(args.interval * 60)
    else:
        run_cycle()

if __name__ == "__main__":
    main()
