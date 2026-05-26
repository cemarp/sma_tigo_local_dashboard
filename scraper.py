#!/usr/bin/env python3
"""
SMA Sunny Boy Inverter Scraper
Fetches real-time instantaneous values under "DC Measurements" and "Module Technology"
directly from the SMA JSON-RPC local WebUI API and saves them into a CSV file.

Auto-discovers the inverter's IP if it changes due to DHCP.
Bypasses SSL/certificate warnings.
Uses local caching for translation and metadata files to keep scraping fast.
"""

import os
import sys
import json
import time
import socket
import csv
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3

# Suppress insecure SSL/certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_IP = "192.168.1.83"
DEFAULT_USER_GROUP = "usr"  # User role in SMA is 'usr'
DEFAULT_PASSWORD = "User!2345"
DEFAULT_CSV_FILE = "sma_inverter_data.csv"

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
L10N_CACHE = os.path.join(CACHE_DIR, "en-US.json")
META_CACHE = os.path.join(CACHE_DIR, "ObjectMetadata_User.json")
CACHE_EXPIRY_SECONDS = 86400  # 24 hours


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape DC Measurements and Module Technology from SMA Sunny Boy Inverter."
    )
    parser.add_argument(
        "--ip",
        default=DEFAULT_IP,
        help=f"Inverter IP address (default: {DEFAULT_IP})"
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Inverter User password"
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_CSV_FILE,
        help=f"Output CSV file path (default: {DEFAULT_CSV_FILE})"
    )
    parser.add_argument(
        "--db",
        default="sma_inverter_data.db",
        help="SQLite database path for the dashboard backend"
    )
    parser.add_argument(
        "--no-discover",
        action="store_true",
        help="Disable automatic subnet discovery if target IP is down"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear local metadata and translation cache files"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Polling interval in minutes. If specified, script runs in an infinite loop."
    )
    parser.add_argument(
        "--format",
        choices=["wide", "long"],
        default="wide",
        help="Output CSV format: 'wide' (one row per scrape, perfect for graphing) or 'long' (default: 'wide')"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Total duration to run in minutes when in loop mode. If set, loop stops after this time."
    )
    return parser.parse_args()


def get_local_ip_subnet():
    """Gets the active local IP address and determines the /24 subnet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public IP to find the preferred local route
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "192.168.1.1"
    finally:
        s.close()
    
    parts = local_ip.split(".")
    if len(parts) == 4:
        # Return prefix, e.g. "192.168.1"
        return ".".join(parts[:3])
    return "192.168.1"


def test_ip_for_inverter(ip):
    """Tests if a given IP hosts an SMA inverter by trying to fetch en-US.json or login.json."""
    url = f"https://{ip}/data/l10n/en-US.json"
    try:
        # Very short timeout for subnet scan
        response = requests.get(url, verify=False, timeout=0.4)
        if response.status_code == 200:
            return ip
    except requests.RequestException:
        pass
    
    # Try backup check on login.json
    url_login = f"https://{ip}/dyn/login.json"
    try:
        response = requests.post(url_login, json={}, verify=False, timeout=0.4)
        # Even if login fails (e.g. 400 bad payload), receiving a response confirms an active SMA endpoint
        if response.status_code in (200, 400, 405):
            return ip
    except requests.RequestException:
        pass
    
    return None


def discover_inverter_ip():
    """Concurrently scans the local /24 subnet for active SMA inverters."""
    subnet = get_local_ip_subnet()
    print(f"[Discovery] Target IP is down. Scanning subnet {subnet}.0/24 for SMA Inverters...")
    
    ips_to_scan = [f"{subnet}.{i}" for i in range(1, 255)]
    discovered_ip = None
    
    with ThreadPoolExecutor(max_workers=60) as executor:
        futures = {executor.submit(test_ip_for_inverter, ip): ip for ip in ips_to_scan}
        for future in as_completed(futures):
            result = future.result()
            if result:
                discovered_ip = result
                # Cancel remaining tasks
                print(f"[Discovery] Found active SMA Inverter at: {discovered_ip}")
                break
                
    return discovered_ip


def ensure_cached_files(session, base_url, clear_cache=False):
    """Fetches and caches static localization and metadata files from the inverter."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    if clear_cache:
        if os.path.exists(L10N_CACHE):
            os.remove(L10N_CACHE)
        if os.path.exists(META_CACHE):
            os.remove(META_CACHE)
        print("[Cache] Cleared local cache files.")
        
    en_us = None
    metadata = None
    
    # 1. English Localization dictionary
    if os.path.exists(L10N_CACHE) and (time.time() - os.path.getmtime(L10N_CACHE)) < CACHE_EXPIRY_SECONDS:
        try:
            with open(L10N_CACHE, "r", encoding="utf-8") as f:
                en_us = json.load(f)
            print("[Cache] Loaded localization dictionary (en-US.json) from cache.")
        except Exception:
            pass
            
    if not en_us:
        print("[HTTP] Fetching localization dictionary (en-US.json) from inverter...")
        try:
            r = session.get(f"{base_url}/data/l10n/en-US.json", verify=False, timeout=10)
            r.raise_for_status()
            en_us = r.json()
            with open(L10N_CACHE, "w", encoding="utf-8") as f:
                json.dump(en_us, f, ensure_ascii=False, indent=2)
            print("[Cache] Localization dictionary cached successfully.")
        except Exception as e:
            print(f"[Warning] Failed to fetch en-US.json from inverter: {e}")
            en_us = {}

    # 2. Object Metadata dictionary
    if os.path.exists(META_CACHE) and (time.time() - os.path.getmtime(META_CACHE)) < CACHE_EXPIRY_SECONDS:
        try:
            with open(META_CACHE, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            print("[Cache] Loaded parameter metadata (ObjectMetadata_User.json) from cache.")
        except Exception:
            pass
            
    if not metadata:
        print("[HTTP] Fetching parameter metadata (ObjectMetadata_User.json) from inverter...")
        # Note: We try ObjectMetadata_User.json since we are logging in as User
        try:
            r = session.get(f"{base_url}/data/ObjectMetadata_User.json", verify=False, timeout=15)
            r.raise_for_status()
            metadata = r.json()
            with open(META_CACHE, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            print("[Cache] Parameter metadata cached successfully.")
        except Exception as e:
            print(f"[Warning] Failed to fetch ObjectMetadata_User.json: {e}. Trying fallback ObjectMetadata_Istl.json...")
            try:
                r = session.get(f"{base_url}/data/ObjectMetadata_Istl.json", verify=False, timeout=15)
                r.raise_for_status()
                metadata = r.json()
                with open(META_CACHE, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                print("[Cache] Fallback parameter metadata cached successfully.")
            except Exception as e2:
                print(f"[Error] Failed to fetch metadata: {e2}")
                metadata = {}
                
    return en_us, metadata


def authenticate(session, base_url, password):
    """Authenticates against login.json and returns the session ID (sid)."""
    url = f"{base_url}/dyn/login.json"
    payload = {"right": DEFAULT_USER_GROUP, "pass": password}
    
    print(f"[HTTP] Authenticating as User at {url}...")
    try:
        r = session.post(url, json=payload, verify=False, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        # Check error or missing result
        if "err" in data:
            print(f"[Error] Authentication rejected by inverter: Error code {data['err']}")
            # In some firmwares, 401/error code 503 means session limit reached
            if data["err"] == 401:
                print("[Error] Inverter reports: Unauthorized. Please check User password.")
            elif data["err"] == 503:
                print("[Error] Inverter reports: Max concurrent sessions limit reached. Please wait or log out other devices.")
            return None
            
        sid = data.get("result", {}).get("sid")
        if sid:
            print(f"[HTTP] Authentication successful. Session ID (sid): {sid}")
            return sid
        else:
            print(f"[Error] No Session ID (sid) returned in response: {data}")
            return None
    except Exception as e:
        print(f"[Error] Failed to connect during authentication: {e}")
        return None


def logout(session, base_url, sid):
    """Gracefully terminates the session on the inverter."""
    url = f"{base_url}/dyn/logout.json?sid={sid}"
    print("[HTTP] Logging out to release inverter session...")
    try:
        r = session.post(url, json={}, verify=False, timeout=3)
        if r.status_code == 200:
            print("[HTTP] Session successfully released.")
        else:
            print(f"[Warning] Logout returned status code {r.status_code}")
    except Exception as e:
        print(f"[Warning] Failed to logout cleanly: {e}")


def extract_telemetry(session, base_url, sid, metadata, en_us):
    """Fetches all values, filters by category, maps units/scales/names, and returns records."""
    url = f"{base_url}/dyn/getAllOnlValues.json?sid={sid}"
    payload = {"destDev": []}
    
    print("[HTTP] Fetching instantaneous measurements...")
    try:
        r = session.post(url, json=payload, verify=False, timeout=10)
        r.raise_for_status()
        raw_data = r.json()
    except Exception as e:
        print(f"[Error] Failed to retrieve instantaneous values: {e}")
        return []
        
    results = raw_data.get("result", {})
    if not results:
        print(f"[Warning] Empty or invalid results returned: {raw_data}")
        return []
        
    # Get the device ID (usually a single device key)
    device_ids = list(results.keys())
    if not device_ids:
        print("[Warning] No devices found in telemetry response.")
        return []
    
    device_id = device_ids[0]
    device_telemetry = results[device_id]
    
    records = []
    timestamp = datetime.now().isoformat()
    
    # We want categories: ["Instantaneous values", "DC Measurements"] and ["Instantaneous values", "Module Technology"]
    targets = [
        ["instantaneous values", "dc measurements"],
        ["instantaneous values", "module technology"]
    ]
    
    match_count = 0
    
    for sensor_key, channels in device_telemetry.items():
        # Look up sensor in metadata
        meta_entry = metadata.get(sensor_key)
        if not meta_entry:
            continue
            
        # Parse hierarchy path
        tag_hier = meta_entry.get("TagHier", [])
        category_path = [en_us.get(str(h_id), str(h_id)) for h_id in tag_hier]
        category_path_lower = [c.lower() for c in category_path]
        
        # Check if matches our targets
        is_target = False
        target_category = ""
        
        # 1. DC Measurements
        if len(category_path_lower) >= 2 and category_path_lower[0] == "dc side" and category_path_lower[1] == "dc measurements":
            is_target = True
            if len(category_path_lower) >= 3 and category_path_lower[2] == "pv module electronics":
                target_category = "Module Technology"
            elif len(category_path_lower) >= 3 and category_path_lower[2] == "pv module control":
                target_category = "PV Module Control"
            else:
                target_category = "DC Measurements"
        # 2. AC Side Measurements
        elif len(category_path_lower) >= 2 and category_path_lower[0] == "ac side":
            if category_path_lower[1] == "pv generation":
                is_target = True
                target_category = "AC Side > PV Generation"
            elif category_path_lower[1] == "measured values":
                is_target = True
                if len(category_path_lower) >= 3:
                    target_category = f"AC Side > Measured values > {category_path[2]}"
                else:
                    target_category = "AC Side > Measured values"
        # 3. Fallbacks
        elif len(category_path_lower) >= 2 and category_path_lower[0] == "instantaneous values":
            if category_path_lower[1] == "dc measurements":
                is_target = True
                target_category = "DC Measurements"
            elif category_path_lower[1] == "module technology":
                is_target = True
                target_category = "Module Technology"
                
        if not is_target:
            continue
            
        # Translate sensor name
        tag_id = meta_entry.get("TagId")
        param_name = en_us.get(str(tag_id), sensor_key)
        
        # Scale and unit mapping
        scale = meta_entry.get("Scale", 1)
        unit_id = meta_entry.get("Unit")
        unit_name = en_us.get(str(unit_id), "") if unit_id else ""
        
        # Process channels (e.g. different strings/phases "1", "2")
        for channel_id, val_list in channels.items():
            if not isinstance(val_list, list):
                continue
                
            for idx, item in enumerate(val_list):
                if not isinstance(item, dict) or "val" not in item:
                    continue
                    
                raw_val = item["val"]
                if raw_val is None:
                    continue
                    
                # Check if it is a tag status (e.g. [{"tag": 307}] or {"tag": 307})
                is_status = False
                tag_num = None
                
                if isinstance(raw_val, list):
                    if len(raw_val) > 0 and isinstance(raw_val[0], dict) and "tag" in raw_val[0]:
                        is_status = True
                        tag_num = raw_val[0]["tag"]
                elif isinstance(raw_val, dict) and "tag" in raw_val:
                    is_status = True
                    tag_num = raw_val["tag"]
                
                if is_status:
                    # Translate status tag
                    translated_val = en_us.get(str(tag_num), str(tag_num))
                    scaled_val = tag_num
                else:
                    # Numerical or string measurement
                    if isinstance(raw_val, (int, float)):
                        scaled_val = raw_val * scale
                        if isinstance(scaled_val, float):
                            # Format floats cleanly to avoid trailing zeros or floating point representation errors
                            translated_val = f"{scaled_val:.3f}".rstrip('0').rstrip('.')
                        else:
                            translated_val = str(scaled_val)
                    else:
                        scaled_val = raw_val
                        translated_val = str(raw_val)
                    
                # Append channel identifier to name if multiple exist
                full_param_name = param_name
                if len(channels) > 1 or len(val_list) > 1:
                    full_param_name = f"{param_name} (Ch {channel_id} #{idx+1})"
                    
                records.append({
                    "Timestamp": timestamp,
                    "Category": target_category,
                    "Parameter": full_param_name,
                    "Value": translated_val,
                    "Unit": unit_name,
                    "Raw Value": raw_val,
                    "Scale": scale,
                    "Key": sensor_key
                })
                match_count += 1
                
    print(f"[Parser] Extracted {match_count} measurements from target categories.")
    return records


def write_to_csv(records, output_file):
    """Appends records to the specified CSV file in long format, creating headers if new."""
    if not records:
        print("[CSV] No records to write.")
        return
        
    file_exists = os.path.exists(output_file)
    headers = ["Timestamp", "Category", "Parameter", "Value", "Unit", "Raw Value", "Scale", "Key"]
    
    try:
        with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            if not file_exists or os.path.getsize(output_file) == 0:
                writer.writeheader()
            writer.writerows(records)
        print(f"[CSV] Successfully appended {len(records)} records in long format to {output_file}")
    except Exception as e:
        print(f"[Error] Failed to write long format data to CSV: {e}")


def write_to_csv_wide(records, output_file):
    """Writes/appends records in wide format (one row per scrape timestamp, dynamic self-healing columns)."""
    if not records:
        print("[CSV] No records to write.")
        return
        
    timestamp = records[0]["Timestamp"]
    
    # Create the row dictionary mapping unique column names to values
    row_data = {"Timestamp": timestamp}
    for r in records:
        col_name = f"{r['Category']} - {r['Parameter']}"
        if r['Unit']:
            col_name = f"{col_name} ({r['Unit']})"
        row_data[col_name] = r["Value"]
        
    headers = ["Timestamp"]
    existing_rows = []
    
    # Check if file exists and read its content/headers
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                headers = reader.fieldnames if reader.fieldnames else ["Timestamp"]
                for row in reader:
                    existing_rows.append(row)
        except Exception as e:
            print(f"[Warning] Failed to read existing CSV headers: {e}")
            headers = ["Timestamp"]
            
    # Check if there are any new columns in the current scrape
    new_cols = [col for col in row_data.keys() if col not in headers]
    
    if new_cols:
        print(f"[CSV] Found {len(new_cols)} new columns. Dynamically extending CSV headers...")
        # Add new columns to the end of headers
        headers.extend(sorted(new_cols))
        
        # Rewrite the entire file with updated headers and existing rows (to keep them aligned)
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                if existing_rows:
                    writer.writerows(existing_rows)
        except Exception as e:
            print(f"[Error] Failed to rewrite CSV with updated headers: {e}")
            return
            
    # If file doesn't exist and we didn't add new cols, initialize headers
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        headers = ["Timestamp"] + sorted([col for col in row_data.keys() if col != "Timestamp"])
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
        except Exception as e:
            print(f"[Error] Failed to initialize new CSV: {e}")
            return
            
    # Append the current row
    try:
        with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writerow(row_data)
        print(f"[CSV] Successfully saved scrape as one row in {output_file} ({len(headers)} columns total).")
    except Exception as e:
        print(f"[Error] Failed to append wide format row to CSV: {e}")


def write_to_sqlite(records, db_path):
    """Writes/appends records to the SQLite database for the local dashboard backend."""
    if not records:
        return
    import sqlite3
    try:
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
        
        # Insert records
        for r in records:
            cursor.execute('''
                INSERT INTO measurements (timestamp, category, parameter, value, unit, raw_value, scale, key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r['Timestamp'], 
                r['Category'], 
                r['Parameter'], 
                r['Value'], 
                r['Unit'], 
                str(r['Raw Value']), 
                r['Scale'], 
                r['Key']
            ))
        conn.commit()
        conn.close()
        print(f"[SQLite] Successfully appended {len(records)} records to {db_path}.")
    except Exception as e:
        print(f"[Error] Failed to write data to SQLite: {e}")


def run_scrape(args):
    """Executes a single scrape cycle: discovers IP, authenticates, fetches telemetry, writes to CSV, and logs out."""
    # Establish base Session with connection pooling
    session = requests.Session()
    target_ip = args.ip
    base_url = f"https://{target_ip}"
    
    # Try connecting to the default IP
    print(f"[Network] Testing connectivity to target IP: {target_ip}...")
    try:
        # Check standard HTTPS port
        socket.create_connection((target_ip, 443), timeout=2.0)
    except Exception:
        print(f"[Warning] Inverter is unreachable at {target_ip}.")
        if args.no_discover:
            print("[Error] Subnet discovery disabled. Aborting current cycle.")
            return False
            
        # Attempt subnet auto-discovery
        discovered_ip = discover_inverter_ip()
        if discovered_ip:
            target_ip = discovered_ip
            base_url = f"https://{target_ip}"
        else:
            print("[Error] Failed to locate SMA Inverter on the local subnet. Aborting current cycle.")
            return False
            
    # Authenticate to get session ID
    sid = authenticate(session, base_url, args.password)
    if not sid:
        return False
        
    try:
        # Cache metadata and translation files
        en_us, metadata = ensure_cached_files(session, base_url, args.clear_cache)
        
        # Scrape and extract data
        records = extract_telemetry(session, base_url, sid, metadata, en_us)
        
        # Output to CSV based on requested format
        if args.format == "wide":
            write_to_csv_wide(records, args.output)
        else:
            write_to_csv(records, args.output)
            
        # Also save to SQLite database if configured
        if args.db:
            write_to_sqlite(records, args.db)
        
    finally:
        # Graceful logout to prevent inverter session locking
        logout(session, base_url, sid)
        
    print("[Done] Scraping cycle completed successfully.")
    return True


def main():
    args = parse_args()
    
    if args.interval:
        print(f"[Main] Starting SMA Scraper in loop mode. Polling every {args.interval} minutes.")
        if args.duration:
            print(f"[Main] Run limit configured: scraper will stop automatically after {args.duration} minutes.")
        print("[Main] Press Ctrl+C to terminate the daemon loop gracefully.")
        
        loop_start_time = time.time()
        while True:
            cycle_start_time = time.time()
            try:
                run_scrape(args)
            except Exception as e:
                print(f"[Error] Scraper encountered an exception during execution cycle: {e}")
                
            # Check if total duration limit has been reached
            if args.duration:
                total_elapsed_min = (time.time() - loop_start_time) / 60.0
                if total_elapsed_min >= args.duration:
                    print(f"[Main] Total configured run duration of {args.duration} minutes reached. Exiting.")
                    break
                    
            # Calculate sleep time to maintain accuracy
            elapsed = (time.time() - cycle_start_time) / 60.0
            sleep_time = max(0.1, (args.interval - elapsed) * 60.0)
            
            # Recheck if sleeping would push us beyond total duration
            if args.duration:
                total_elapsed_sec = time.time() - loop_start_time
                remaining_sec = (args.duration * 60.0) - total_elapsed_sec
                if remaining_sec <= 0:
                    print(f"[Main] Total configured run duration of {args.duration} minutes reached. Exiting.")
                    break
                # Truncate sleep if it exceeds the remaining run duration
                if sleep_time > remaining_sec:
                    sleep_time = remaining_sec
            
            print(f"[Main] Next scrape in {args.interval} minutes. Sleeping for {sleep_time:.1f} seconds...")
            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                print("\n[Main] Polling daemon terminated by user. Exiting.")
                break
    else:
        run_scrape(args)


if __name__ == "__main__":
    main()
