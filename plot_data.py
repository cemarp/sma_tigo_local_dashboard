#!/usr/bin/env python3
"""
SMA Sunny Boy Inverter Plotter
Reads the scraper wide CSV file, identifies DC power columns for Strings A, B, and C,
and generates a beautiful, publication-quality line graph.
"""

import os
import sys
import csv
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DEFAULT_CSV_FILE = "sma_inverter_data.csv"
DEFAULT_PLOT_FILE = "dc_power_plot.png"


def plot_dc_power(csv_path, output_path):
    if not os.path.exists(csv_path):
        print(f"[Error] CSV file not found: {csv_path}")
        return False
        
    print(f"[Plotter] Reading data from {csv_path}...")
    
    timestamps = []
    # Dict mapping column name to list of values
    dc_power_data = {}
    
    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames if reader.fieldnames else []
            
            # Find all DC Power columns
            dc_power_cols = []
            for h in headers:
                h_lower = h.lower()
                if "dc measurements - power" in h_lower:
                    dc_power_cols.append(h)
                    dc_power_data[h] = []
                    
            if not dc_power_cols:
                print("[Error] No DC Power measurement columns found in the CSV!")
                print("Available columns were:", headers)
                return False
                
            print(f"[Plotter] Identified target columns to plot: {dc_power_cols}")
            
            for row in reader:
                # Parse timestamp
                ts_str = row.get("Timestamp")
                if not ts_str:
                    continue
                try:
                    # Handle ISO timestamp (e.g. 2026-05-24T09:25:11.869482)
                    ts = datetime.fromisoformat(ts_str)
                except ValueError:
                    try:
                        # Fallback for other formats
                        ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
                    except ValueError:
                        continue
                        
                timestamps.append(ts)
                
                # Extract values
                for col in dc_power_cols:
                    val_str = row.get(col)
                    try:
                        val = float(val_str) if val_str else 0.0
                    except ValueError:
                        val = 0.0
                    dc_power_data[col].append(val)
                    
    except Exception as e:
        print(f"[Error] Failed to parse CSV file: {e}")
        return False
        
    if not timestamps:
        print("[Error] No valid data points found in CSV.")
        return False
        
    print(f"[Plotter] Plotting {len(timestamps)} data points...")
    
    # Modern styling theme
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    
    fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
    
    # Vibrant, cohesive color palette
    colors = ["#00b4d8", "#ffb703", "#fb8500", "#e63946", "#457b9d"]
    
    # Plot each string
    for idx, col in enumerate(sorted(dc_power_cols)):
        # Simplify label name for the legend (e.g. extract "Power (Ch 1 #1)" or map to String A/B/C)
        string_name = f"String {chr(65 + idx)}" # maps 0 -> A, 1 -> B, 2 -> C
        label_text = f"{string_name} ({col.split(' - ')[-1]})"
        
        ax.plot(
            timestamps,
            dc_power_data[col],
            label=label_text,
            color=colors[idx % len(colors)],
            linewidth=2.5,
            marker='o',
            markersize=4,
            alpha=0.85
        )
        
    # Title & Labels
    ax.set_title("SMA Sunny Boy Inverter - DC String Power Inputs", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("Time (Local Time)", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_ylabel("Power Input (Watts)", fontsize=11, fontweight="bold", labelpad=10)
    
    # Formatting x-axis to be clean and readable
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    # Automatically locate best time ticks
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate() # rotate labels if crowded
    
    # Legend custom styling
    legend = ax.legend(frameon=True, facecolor="white", edgecolor="#e0e0e0", fontsize=10)
    legend.get_frame().set_linewidth(1.0)
    
    # Grid lines custom styling
    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
    
    # Spine styling
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
        spine.set_linewidth(0.8)
        
    # Soft background accent
    ax.set_facecolor("#fafafa")
    
    plt.tight_layout()
    
    # Save the output image
    try:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close()
        print(f"[Plotter] Successfully saved graph image to {output_path}")
        return True
    except Exception as e:
        print(f"[Error] Failed to save plot image: {e}")
        return False


if __name__ == "__main__":
    csv_file = DEFAULT_CSV_FILE
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        
    plot_file = DEFAULT_PLOT_FILE
    if len(sys.argv) > 2:
        plot_file = sys.argv[2]
        
    plot_dc_power(csv_file, plot_file)
