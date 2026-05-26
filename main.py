from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import json
import os
from datetime import datetime

app = FastAPI()

DB_PATH = os.environ.get("DATABASE_URL", "sma_inverter_data.db")
CONFIG_PATH = os.environ.get("LAYOUT_CONFIG", "layout.json")

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

init_db()

@app.get("/config")
async def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

@app.get("/data/latest")
async def get_latest_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(timestamp) FROM measurements")
    latest_ts = cursor.fetchone()[0]
    if not latest_ts:
        return []
    cursor.execute("SELECT * FROM measurements WHERE timestamp = ?", (latest_ts,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/data/daily")
async def get_daily_data(date: str = Query(None), days: int = Query(1)):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if days == 1:
        cursor.execute("SELECT * FROM measurements WHERE timestamp LIKE ? ORDER BY timestamp ASC", (f"{date}%",))
    else:
        # Calculate end date
        from datetime import timedelta
        start_dt = datetime.strptime(date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=days-1)
        end_date = end_dt.strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM measurements WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC",
                       (f"{date}T00:00:00", f"{end_date}T23:59:59"))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# Serve static files (HTML, JS, CSS)
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
