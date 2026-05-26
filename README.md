# SMA PV System Dashboard

A local replacement for the SMA Sunny Portal, providing real-time and historical visualization of PV system performance, including module-level data and string analysis.

## Features

- **Inverter & Module Level Data:** Scrapes detailed metrics (Power, Voltage, Temperature) directly from your SMA inverter.
- **Physical Layout Visualization:** Custom grid layout for Strings AA, BB, and CC.
- **Advanced Charting:**
    - **Power Analysis:** Compares Inverter AC Output, Total Module DC Sum, and individual String DC Power.
    - **String Voltages:** Real-time tracking of DC voltages across all strings.
    - **String Currents:** Real-time tracking of DC currents across all strings.
    - **Module History:** Comparative graphs for individual module Power, Voltage, and Temperature.
    - **Resizable Graphs:** All charts can be resized by the user for detailed analysis.
- **Multi-Day Analysis:** Select up to 5 days of data for side-by-side performance comparison.
- **Time Scrubber:** Historical playback of any day's or multi-day performance.
- **Live Mode:** Automatic data refresh for real-time monitoring.
- **SQLite Storage:** Persistent local storage of all collected data.

## Deployment Instructions

### Prerequisites
- Docker and Docker Compose installed.
- Access to the SMA Inverter on the local network.

### Quick Start

1. **Clone the repository** (if you haven't already).
2. **Configure your system:**
   Edit `layout.json` if your string or module configuration differs.
3. **Build and Start the Dashboard:**
   ```bash
   docker-compose up -d --build
   ```
4. **Access the Dashboard:**
   Open your browser and go to `http://localhost:8000`.

### Scraper Configuration

The scraper runs inside the `scraper` container. You can adjust its behavior in `docker-compose.yml` or by passing environment variables:

- `INVERTER_IP`: The local IP of your SMA inverter (default: `192.168.1.83`).
- `INVERTER_PASSWORD`: Your inverter's User password (default: `User!2345`).
- `SCRAPE_INTERVAL`: How often to poll the inverter (in minutes).

## Technical Details

- **Backend:** FastAPI (Python)
- **Frontend:** Tailwind CSS, Chart.js
- **Database:** SQLite
- **Data Collection:** JSON-RPC Scraper with auto-discovery and session management.

## File Structure

- `main.py`: FastAPI backend and data API.
- `scraper.py`: Local network scraper for SMA inverters.
- `static/index.html`: Dashboard frontend.
- `layout.json`: System configuration (strings, modules, metrics).
- `sma_inverter_data.db`: SQLite database (auto-generated).
