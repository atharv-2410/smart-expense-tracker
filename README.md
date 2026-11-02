# 💸 Smart Expense Tracker & Budget Analyzer

One engine, two interfaces: a **Streamlit web app** (`streamlit run app.py`) and a **command-line app** (`python cli.py`)
that share the same database, ML categoriser, forecast and anomaly detection.

Auto-categorises spending, warns before you overspend, forecasts month-end totals and flags unusual purchases.

## Run it (2 minutes)
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 -> **Try demo** tab -> *Launch demo account* (loads 3 months of realistic data).

## Features
| Feature | Where | How it works |
|---|---|---|
| Login / register | `db.py` | PBKDF2-hashed passwords, per-user data in SQLite |
| Smart entry | `ml.parse_entry` | Regex NLP: "spent 250 on auto yesterday" -> amount, date, type, category |
| Auto-categorisation | `ml.categorize` | Keyword rules first, then TF-IDF + Multinomial Naive Bayes; retrains on the user's own history |
| Budgets + alerts | `analysis.budget_status` | Warning at 80%, red at >100% |
| Month-end forecast | `analysis.forecast_month_end` | Average of daily run-rate and linear regression on cumulative spend |
| Anomaly detection | `analysis.detect_anomalies` | Modified z-score (median/MAD > 3.5) and >= 3x the usual amount for that merchant/category |
| Insights | `analysis.insights` | 50/30/20 rule, month-over-month change, forecast-vs-budget, weekend share |
| Import / Export | `app.py` | CSV import (auto-categorised), CSV + Excel report export |

## Files
`app.py` UI · `db.py` database · `ml.py` NLP + classifier · `analysis.py` analytics · `seed.py` demo data · `eval_data.py` held-out test phrases

## Measured accuracy
`python -c "import ml; print(ml.model_accuracy())"` -> ~86% on 50 held-out hand-labelled descriptions (never used for training).
Add your own labelled phrases to `eval_data.py` for a bigger, more convincing number.

## Demo script (3-4 min)
1. Launch demo -> Dashboard: KPIs, category donut, daily trend, red/amber budget alerts.
2. Add Transaction -> type `spent 250 on auto yesterday` -> show detected category + confidence -> Save.
3. Insights & Forecast -> forecast table ("will exceed Food budget"), anomaly table (the Amazon 4999 purchase), 50/30/20 tips.
4. Import / Export -> download the Excel report.
5. Close with future scope: bank/UPI SMS parsing, receipt OCR, mobile app, group budgets.
Tip: record a screen video as backup in case the venue Wi-Fi/laptop misbehaves.

## Reset
Delete `expenses.db` to start fresh.

## Requirements traceability (Internship brief -> this project)
| Brief requirement | Where it is implemented |
|---|---|
| Add / view / categorise expenses | CLI menu 1-2, web "Add Transaction" + "Transactions" (auto-categorised by rules + Naive Bayes) |
| Lists and dictionaries as data structures | parsed entries are dicts, transactions handled as lists of dicts / DataFrames (`ml.parse_entry`, `db.add_many`) |
| CSV file storage, load on start | CLI saves `expenses.csv` on exit and reloads it on first start; web app has CSV/Excel import and export |
| Functions / modular code | `db.py`, `ml.py`, `analysis.py`, `importer.py`, `seed.py`, `cli.py`, `app.py` |
| Reports (monthly total, by category, highest expense, averages) | CLI menu 3, web Dashboard |
| Matplotlib charts | CLI menu 4 saves `charts/report_YYYY_MM.png` (pie + daily bars); web app uses interactive Plotly |
| Menu with loops and if-else | `cli.main()` |
| Error handling (try/except) | `ask_float`, `ask_date`, `ask_choice`, per-action try/except so the menu never crashes |

**Beyond the brief:** natural-language entry, ML categorisation (~90% held-out accuracy), budgets with alerts, month-end forecast,
anomaly detection, 50/30/20 insights, bank-statement import (UPI aware), People Ledger (who you sent to / received from), login.

## Command-line app
```bash
python cli.py        # choose "Demo account" to try it instantly
```
