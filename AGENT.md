# Agent History

## Prompt History
1. **Initial Request**: Recreate the SMA Sunny Portal 'PV System Overview' dashboard using local telemetry data stored in SQLite.
2. **Interactive Dashboard Enhancements**: Add a draggable and resizable UI (GridStack.js) for charts, supporting multi-day analysis and a time scrubber.
3. **Feature Restoration**: Restore lost features from a previous iteration: hierarchical sidebars for module selection, shift-click range selection, and trace highlighting/thickening on hover (both in sidebar and legend).

## Summary of Changes

### Backend (main.py)
- Implemented FastAPI backend to serve system configuration and telemetry data.
- Added endpoints for latest data and multi-day historical data.
- Automatic SQLite database initialization.

### Frontend (static/index.html)
- **GridStack Integration**: Implemented a draggable and resizable grid for all performance charts.
- **Hierarchical Sidebars**: Added scrollable sidebars next to module history charts for fine-grained trace selection.
- **Trace Highlighting**: Implemented trace thickening on hover for sidebar modules, string group headers, and chart legends.
- **Shift-Click Selection**: Supported range selection of module checkboxes.
- **Time Scrubber**: Interactive historical playback of system performance.
- **Responsive Layout**: Built with Tailwind CSS for a modern, dashboard-like feel.
- **Jitter Prevention**: Guarded `ResizeObserver` logic to ensure smooth UI interactions during resizing.

### Infrastructure & Tools
- **Containerization**: Added `Dockerfile` and `docker-compose.yml` for easy deployment.
- **Data Scraper**: Included `scraper.py` for direct JSON-RPC polling of SMA inverters.
- **Environment Config**: Provided `.env.example` for secure credential management.
- **Utility Scripts**: Added `scripts/import_data.py` (CSV import) and `scripts/populate_mock.py` (mock data generation).

## Technical Learnings
- **Chart.js Performance**: Using `chart.update('none')` is essential for responsive hover effects in high-density datasets.
- **Resize Stability**: Hierarchical layouts with flex-grow and overflow-y-auto can trigger infinite ResizeObserver loops; a 1px delta guard effectively stabilizes this.
- **State Management**: Client-side state for hidden/visible traces is managed directly through the Chart.js dataset visibility API and synced with sidebar checkbox states.
