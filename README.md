# COMP 401 - Historical vs Real-Time Volatility Dashboard

## Overview

This project builds a live financial dashboard to analyze how real-time stock price movements compare to historical volatility expectations.

It ingests live market data, computes a 60-day annualized volatility baseline, and standardizes real-time price changes using a z-score framework to identify when movements are unusually large relative to historical behavior.

---

## Data Sources

- Finnhub API (free tier) — real-time stock quotes  
- Yahoo Finance (yfinance) — historical price data  

---

## Key Features

- Live stock price ingestion and storage (MariaDB)
- Real-time dashboard built with Dash + Plotly
- 60-day rolling annualized volatility
- Log return-based z-score for live price moves
- Session-aware live charts (resets after inactivity gaps)
- Multi-stock dashboard with drill-down detail views
- Caching layer for API efficiency and rate limit protection

---

## How It Works

1. Live ingestion (main.py)
   - Fetches real-time quotes at a fixed interval
   - Stores snapshots in the database

2. Dashboard (dashboard_app.py)
   - Reads recent snapshots
   - Computes live z-scores relative to historical volatility
   - Displays:
     - Live price
     - Live z-score (standardized move)
     - Historical 60D volatility

---

## Setup

### 1. Install dependencies

pip install -r requirements.txt

---

### 2. Configure environment variables

Create a .env file with:

FINNHUB_API_KEY=your_key_here

SNAPSHOT_SYMBOLS=AAPL,MSFT,TSLA,XOM,UNH

QUOTE_TTL_SECONDS=15

SNAPSHOT_EVERY_SECONDS=30

DB_HOST=localhost

DB_PORT=3306

DB_NAME=dashboarddb

DB_USER=appuser

DB_PASS=apppass

---

### 3. Run the project

Start live data ingestion:

python main.py

In a separate terminal, start the dashboard:

python dashboard_app.py

Then open your browser and go to:

http://127.0.0.1:8050/

(or the local address shown in your terminal)

---

## Interpreting the Dashboard

- Price chart — real-time price movement
- Z-score chart — standardized move relative to volatility
  - |z| < 2 → normal
  - 2 ≤ |z| < 3 → elevated
  - |z| ≥ 3 → extreme
- Historical volatility chart — 60-day rolling annualized volatility

---

## Notes

- Live charts reset after long inactivity periods (session-based view)
- Dashboard refresh rate and ingestion rate are displayed in the UI
- Designed to answer:
  “Is this current price move unusually large given historical risk?”

---

---

## Use of AI

AI tools were used as a development aid throughout this project, primarily to support structure, debugging, and front-end implementation.

- **Project structure & organization**: AI was used to help plan and organize the overall architecture of the project, including how components were separated across files and modules.

- **Backend development**: The majority of the backend logic (data ingestion, storage, and analytics) was implemented manually. AI was used selectively to assist with debugging and to help resolve specific roadblocks when they arose.

- **Frontend development**: The frontend (Dash/Plotly dashboard) was largely generated with the assistance of AI. However, all design decisions, layout, and functionality were directed and iterated on based on my intended user experience and project goals.

---

## Specific AI Prompt Flow for the Frontend 

The general process for designing the frotend was as follows:

1. **Starting from an existing baseline**
   - Initial prompts focused on taking my existing plotting/output code and adapting it into a web-based dashboard format in Dash/Plotly.

2. **High-level design direction**
   - Prompts were used to define the desired visual style and layout, such as:
     - “Make this resemble a Bloomberg-style terminal in terms of a professional appearance”
     - “Display multiple stocks in a clean grid of cards”
     - “Each card should contain live price and z-score charts”

3. **Component refinement**
   - Iterative prompts refined individual elements, including:
     - Chart styling (colors, thresholds, labeling)
     - Card layout and spacing
     - Consistent axes and formatting across components

4. **Functionality-driven iteration**
   - Prompts were used to introduce and refine specific behaviors, such as:
     - Live updating charts
     - Drill-down detail views per stock
     - Highlighting statistically significant moves

## Author

Parker Ellis  
Kenyon College
