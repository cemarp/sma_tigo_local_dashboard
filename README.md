# SMA PV System Dashboard & Inverter Scraper

A comprehensive local monitoring solution that replaces the SMA Sunny Portal. It includes a high-performance, self-healing Python scraper that connects directly to the local WebUI JSON API of modern SMA Sunny Boy inverters, saving telemetry in real-time to both SQLite (for active dashboard querying) and CSV (for deep data analysis and plotting).

---

## 🌟 Features

- **Dashboard Visualizations (FastAPI + Chart.js)**:
  - **Inverter & Module Level Data:** Visualizes Power, Voltage, and Temperature from the inverter and individual TS4 panel optimizers.
  - **Physical Layout Visualization:** Custom grid layout mapping Strings A, B, and C.
  - **Advanced Charting:** Real-time and historical comparison of Inverter AC Output, Total Module DC Sum, and individual String DC Power, Voltage, and Current.
  - **Time Scrubber:** Play back historical performance from any recorded day.
  - **Live Mode:** Real-time data updates via clean HTTP polling.
- **Robust Scraper Daemon (`scraper.py`)**:
  - **Blazing Fast**: Directly scrapes raw JSON endpoints (`/dyn/getAllOnlValues.json`) instead of spinning up slow browser drivers.
  - **Dynamic DHCP Discovery**: Automatically scans the local subnet (e.g. `192.168.1.0/24`) to find the inverter if its IP address changes.
  - **Certificate Error Bypass**: Gracefully handles and bypasses local self-signed SSL warnings.
  - **Cache-Optimized**: Caches large translation and parameter metadata files locally on the first run, making subsequent runs near-instantaneous.
  - **Wide CSV Formatting (One Row Per Scrape)**: Saves each scrape as a single wide row with timestamps, making it extremely easy to read, import into pandas, or graph.
  - **Self-Healing Dynamic Columns**: Automatically expands CSV headers if new modular technology or panels are discovered, filling historical entries with empty values.
  - **SQLite Persistent Storage**: Automatically populates `sma_inverter_data.db` to feed the FastAPI dashboard backend.

---

## 🛠️ Setup & Deployment

### Option 1: Docker Compose (Dashboard + Scraper Together)

This is the recommended deployment method for running the complete stack.

1. **Configure your system:**
   Edit `layout.json` if your string or module configuration differs from default.
2. **Build and Start:**
   ```bash
   docker-compose up -d --build
   ```
3. **Access the Dashboard:**
   Open your browser and navigate to `http://localhost:8000`.

### Option 2: Running the Scraper Natively (Standalone)

If you only want to scrape data to CSV or SQLite without running the web dashboard:

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run a Single Scrape:**
   ```bash
   python scraper.py --ip 192.168.1.83 --password User!2345 --output sma_inverter_data.csv --format wide
   ```
3. **Run as a Polling Daemon (e.g., Every 5 Minutes for 8 Hours):**
   ```bash
   python scraper.py --ip 192.168.1.83 --password User!2345 --output sma_inverter_data.csv --format wide --interval 5 --duration 480
   ```

---

## 📋 Scraper Command-Line Options

- `--ip`: Specify the IP address of the inverter (default: `192.168.1.83`).
- `--password`: Specify the password for the "User" group (default: `User!2345`).
- `--output`: Specify the output CSV file path (default: `sma_inverter_data.csv`).
- `--db`: Specify the SQLite database path (default: `sma_inverter_data.db`).
- `--format`: Specify CSV layout: `wide` (one row per scrape, ideal for graphing) or `long` (standard list format) (default: `wide`).
- `--interval`: Polling interval in minutes. If specified, runs in an infinite daemon loop.
- `--duration`: Total duration to run in minutes when in loop mode.
- `--no-discover`: Disables automatic local network subnet discovery.
- `--clear-cache`: Clears the local static cache metadata files and forces a redownload.

---

## 📂 File Structure

- `scraper.py`: Core local network scraper for SMA inverters (populates SQLite and CSV).
- `main.py`: FastAPI backend and data API.
- `static/index.html`: Dashboard frontend.
- `layout.json`: System configuration (strings, modules, metrics).
- `plot_data.py`: CLI plotting utility to generate DC Power input comparison line graphs.
- `get_cert.py`: SSL utility to fetch and save the inverter's SSL certificate locally.
- `sma_inverter_data.db`: SQLite database for the dashboard (auto-generated).
- `sma_inverter_data.csv`: CSV database for manual analysis (auto-generated).
