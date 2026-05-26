# SMA Sunny Boy Inverter Scraper

A robust, self-healing Python scraper that connects directly to the local WebUI JSON API of modern SMA Sunny Boy inverters. It retrieves instantaneous values under **DC Measurements**, **Module Technology**, and **AC Side Measurements** and appends them to a CSV file.

## Features

- **Blazing Fast**: Directly scrapes raw JSON endpoints (`/dyn/getAllOnlValues.json`) instead of spinning up slow browser drivers.
- **Dynamic DHCP Discovery**: Automatically scans the local subnet (e.g. `192.168.1.0/24`) to find the inverter if its IP address changes.
- **Certificate Error Bypass**: Bypasses local SSL self-signed certificate warnings.
- **Cache-Optimized**: Caches large, static translation (`en-US.json`) and parameter metadata (`ObjectMetadata_User.json`) files locally on first run to optimize network overhead and keep subsequent scraper runs near-instantaneous.
- **Intelligent Value Translation**: Parses status tag structures like `[{'tag': 307}]` into clean status descriptions like `"Ok"`.
- **Wide Formatting (One Row Per Scrape)**: Saves each scrape as a single row in the CSV file with timestamps, making it extremely easy to read, import into pandas, or graph.
- **Self-Healing Dynamic Columns**: Automatically expands headers if new modular technology or panels are discovered, filling historical entries with empty values.
- **Built-in Polling Daemon**: Run natively in an infinite loop using the `--interval` flag to continuously poll data.
- **Graceful Session Release**: Performs a proper logout at the end of each run to prevent session lockout issues.

## Telemetry Captured

* **AC Side**: 
  - `PV generation power` (W)
  - `Total yield` (Wh)
  - `Daily yield` (Wh)
  - Operating time (s), Feed-in time (s)
* **DC Side**:
  - Input-level string measurements (`DC Measurements`: Voltage, Current, Power, Energy released)
* **Module Technology**:
  - Individual PV module/optimizer measurements (`Module Technology`: TS4 Voltage, Current, Power, Temperature, Signal Strength)
  - Modular technology commission and discovery status (`PV Module Control`)

## Setup

1. Make sure Python 3 is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run a single wide-format scrape using:

```bash
python scraper.py --ip 192.168.1.83 --password User!2345 --output sma_inverter_data.csv --format wide
```

### Options

- `--ip`: Specify the IP address of the inverter (default: `192.168.1.83`).
- `--password`: Specify the password for the "User" group (default: `User!2345`).
- `--output`: Specify the output CSV file path (default: `sma_inverter_data.csv`).
- `--format`: Specify CSV layout: `wide` (one row per scrape, ideal for graphing) or `long` (standard list format) (default: `wide`).
- `--interval`: Specify polling interval in minutes. If set, the script runs in a loop, polling and writing data dynamically.
- `--no-discover`: Disables subnet scanning if the target IP is down.
- `--clear-cache`: Clears the local static cache metadata files and forces a redownload.

### Running as a Polling Daemon (e.g. Every 5 Minutes)

To run the script in the background and poll the inverter every 5 minutes:

```bash
python scraper.py --ip 192.168.1.83 --password User!2345 --output sma_inverter_data.csv --format wide --interval 5
```
Press `Ctrl+C` in the terminal to stop the daemon gracefully.
