"""Command-line interface for the Smart Expense Tracker.
Same engine (database, ML categoriser, forecast, anomaly detection) as the Streamlit web app.
Run:  python cli.py
"""
import calendar
import csv
import getpass
import os
from datetime import date, datetime

import analysis as an
import db
import importer as imp
import ml

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")
CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
CATS = db.CATEGORIES + ["Income"]


# ---------------------------------------------------------------- safe input helpers (error handling)
def ask_float(prompt, minimum=0.0):
    while True:
        try:
            v = float(input(prompt).replace(",", "").strip())
            if v <= minimum:
                print(f"  ! Enter a number greater than {minimum:g}.")
                continue
            return v
        except ValueError:
            print("  ! Invalid number, try again (e.g. 250 or 99.50).")


def ask_date(prompt):
    while True:
        s = input(prompt).strip()
        if not s:
            return date.today()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        print("  ! Use YYYY-MM-DD or DD-MM-YYYY (or press Enter for today).")


def ask_choice(prompt, options):
    for i, o in enumerate(options, 1):
        print(f"   {i}. {o}")
    while True:
        s = input(prompt).strip()
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1]
        if s.title() in options:
            return s.title()
        print("  ! Pick a number from the list.")


def inr(x):
    return f"Rs {x:,.0f}"


def pick_month(df):
    today = date.today()
    s = input(f"Month (YYYY-MM, Enter = {today:%Y-%m}): ").strip()
    try:
        d = datetime.strptime(s, "%Y-%m") if s else today
        return d.year, d.month
    except ValueError:
        print("  ! Bad month, using current month.")
        return today.year, today.month


# ---------------------------------------------------------------- CSV persistence
def save_csv(uid):
    df = db.fetch_transactions(uid)
    out = df.drop(columns=["user_id"]) if not df.empty else df
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "amount", "type", "category", "description", "payment_mode"])
        for _, r in out.iterrows():
            w.writerow([r["date"].date(), r["amount"], r["type"], r["category"], r["description"], r["payment_mode"]])
    return len(out)


def load_csv(uid):
    n = 0
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            try:
                rows.append(dict(date=r["date"], amount=float(r["amount"]), type=r.get("type", "expense"),
                                 category=r.get("category", "Other"), description=r.get("description", ""),
                                 payment_mode=r.get("payment_mode", "UPI")))
            except (KeyError, ValueError):
                continue  # skip corrupted lines instead of crashing
        if rows:
            db.add_many(uid, rows)
            n = len(rows)
    return n


# ---------------------------------------------------------------- menu actions
def add_expense(uid):
    print("\nType naturally (e.g. 'Zomato 340', 'spent 250 on auto yesterday') or press Enter for guided entry.")
    text = input("> ").strip()
    if text:
        p = ml.parse_entry(text)
        if not p:
            print("  ! Couldn't find an amount. Try again.")
            return
        print(f"  Detected: {inr(p['amount'])} | {p['type']} | {p['category']} "
              f"({p['confidence'] * 100:.0f}% via {p['method']}) | {p['date']}")
        if input("  Save? [Y/n]: ").strip().lower() in ("", "y", "yes"):
            db.add_transaction(uid, p["date"], p["amount"], p["type"], p["category"], p["description"], "UPI")
            print("  Saved.")
        return
    ttype = ask_choice("Type: ", ["expense", "income"])
    amount = ask_float("Amount (Rs): ")
    cat = ask_choice("Category: ", CATS)
    dte = ask_date("Date (YYYY-MM-DD, Enter = today): ")
    desc = input("Description: ").strip()
    db.add_transaction(uid, dte, amount, ttype, cat, desc, "UPI")
    print("  Saved.")


def view_expenses(uid):
    df = db.fetch_transactions(uid)
    if df.empty:
        print("\nNo transactions yet.")
        return
    c = input("Filter by category (Enter = all): ").strip().title()
    if c:
        df = df[df["category"] == c]
    n = input("How many recent rows? (Enter = 20): ").strip()
    n = int(n) if n.isdigit() else 20
    print(f"\n{'Date':<12}{'Type':<9}{'Category':<19}{'Amount':>10}  Description")
    print("-" * 70)
    for _, r in df.head(n).iterrows():
        print(f"{r['date']:%Y-%m-%d}  {r['type']:<9}{r['category']:<19}{r['amount']:>10,.0f}  {r['description'][:28]}")
    print(f"\nShowing {min(n, len(df))} of {len(df)} rows.")


def report(uid):
    df = db.fetch_transactions(uid)
    y, m = pick_month(df)
    k = an.kpis(df, y, m)
    cs = an.category_spend(df, y, m)
    print(f"\n===== Report: {calendar.month_name[m]} {y} =====")
    print(f"Income: {inr(k['income'])}   Spent: {inr(k['spent'])}   Saved: {inr(k['saved'])} "
          f"({k['savings_rate']:.0f}%)")
    if cs.empty:
        print("No expenses this month.")
        return
    days = calendar.monthrange(y, m)[1]
    print(f"Average per day: {inr(k['spent'] / days)}")
    mm = an.month_slice(df, y, m)
    top = mm[mm["type"] == "expense"].nlargest(1, "amount").iloc[0]
    print(f"Highest expense: {inr(top['amount'])} - {top['description']} ({top['category']}, {top['date']:%d %b})")
    print("\nSpending by category:")
    for cat, v in cs.items():
        bar = "#" * int(v / cs.sum() * 40)
        print(f"  {cat:<18}{v:>9,.0f}  {v / cs.sum() * 100:>4.0f}%  {bar}")
    bs = an.budget_status(df, db.get_budgets(uid), y, m)
    for _, r in bs.iterrows():
        if r["status"] != "ok":
            icon = "OVER" if r["status"] == "over" else "WARN"
            print(f"  [{icon}] {r['category']}: {r['pct']:.0f}% of budget ({inr(r['spent'])}/{inr(r['budget'])})")
    proj, total = an.forecast_month_end(df, y, m)
    if (y, m) == (date.today().year, date.today().month):
        print(f"\nForecast month-end spending: {inr(total)}")


def charts(uid):
    import matplotlib
    if not os.environ.get("DISPLAY") and os.name != "nt" and os.uname().sysname != "Darwin":
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    df = db.fetch_transactions(uid)
    y, m = pick_month(df)
    cs = an.category_spend(df, y, m)
    if cs.empty:
        print("No expenses to chart.")
        return
    os.makedirs(CHART_DIR, exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].pie(cs.values, labels=cs.index, autopct="%1.0f%%", startangle=90)
    ax[0].set_title(f"Spending by category - {calendar.month_name[m]} {y}")
    exp = an.month_slice(df, y, m)
    exp = exp[exp["type"] == "expense"]
    daily = exp.groupby(exp["date"].dt.day)["amount"].sum()
    ax[1].bar(daily.index, daily.values)
    ax[1].set_title("Daily spending")
    ax[1].set_xlabel("Day of month")
    ax[1].set_ylabel("Rs")
    fig.tight_layout()
    path = os.path.join(CHART_DIR, f"report_{y}_{m:02d}.png")
    fig.savefig(path, dpi=120)
    print(f"Chart saved: {path}")
    try:
        plt.show()
    except Exception:
        pass


def insights(uid):
    df = db.fetch_transactions(uid)
    y, m = pick_month(df)
    print("\n--- Smart tips ---")
    for level, msg in an.insights(df, db.get_budgets(uid), y, m):
        print(f"  [{level.upper()}] {msg}")
    a = an.detect_anomalies(df)
    print("\n--- Unusual transactions ---")
    if a.empty:
        print("  None found.")
    for _, r in a.head(5).iterrows():
        print(f"  {r['date']:%Y-%m-%d} {r['description']} {inr(r['amount'])} (usual ~{inr(r['typical'])})")


def people(uid):
    df = db.fetch_transactions(uid)
    led = an.people_ledger(df)
    if led.empty:
        print("\nNo person-to-person transactions found.")
        return
    print(f"\n{'Person':<22}{'Sent':>10}{'Received':>11}{'Net':>10}  Txns")
    print("-" * 58)
    for _, r in led.head(15).iterrows():
        print(f"{r['person'][:21]:<22}{r['sent']:>10,.0f}{r['received']:>11,.0f}{r['net']:>+10,.0f}  {r['txns']}")
    print(f"\nTotal sent {inr(led['sent'].sum())} | received {inr(led['received'].sum())} | {len(led)} people")


def budgets(uid):
    cur = db.get_budgets(uid)
    print("\nCurrent budgets:", ", ".join(f"{k}: {inr(v)}" for k, v in cur.items()) or "none")
    cat = ask_choice("Category to set: ", db.CATEGORIES)
    db.set_budget(uid, cat, ask_float("Monthly limit (Rs): "))
    print("  Budget saved.")


def import_statement(uid):
    path = input("Path to bank statement (CSV/XLSX): ").strip().strip('"')
    if not os.path.isfile(path):
        print("  ! File not found.")
        return
    try:
        with open(path, "rb") as f:
            parsed, notes = imp.parse_statement(f, path)
    except Exception as ex:
        print(f"  ! Could not read statement: {ex}")
        return
    for n in notes:
        print("  note:", n)
    rows = [dict(date=r["date"], amount=r["amount"], type=r["type"],
                 category="Income" if r["type"] == "income" else ml.categorize(r["description"] or r["description_raw"])[0],
                 description=r["description"], payment_mode="UPI") for _, r in parsed.iterrows()]
    print(f"  Parsed {len(rows)} transactions.")
    if input("  Import them? [Y/n]: ").strip().lower() in ("", "y", "yes"):
        db.add_many(uid, rows)
        print("  Imported.")


# ---------------------------------------------------------------- start-up / main loop
def login():
    print("1. Login   2. Register   3. Demo account")
    c = input("Choice: ").strip()
    if c == "3":
        u = db.login("demo@demo.com", "demo1234")
        if not u:
            import seed
            uid, _ = db.register("Demo Student", "demo@demo.com", "demo1234")
            seed.seed(uid)
            u = db.login("demo@demo.com", "demo1234")
        return u
    email = input("Email: ")
    pw = getpass.getpass("Password: ")
    if c == "2":
        uid, err = db.register(input("Name: "), email, pw)
        if err:
            print("  !", err)
            return None
    u = db.login(email, pw)
    if not u:
        print("  ! Invalid credentials.")
    return u


def main():
    db.init_db()
    print("=" * 46 + "\n  Welcome to Smart Expense Tracker (CLI)\n" + "=" * 46)
    user = None
    while not user:
        user = login()
    uid = user["id"]
    if db.fetch_transactions(uid).empty and os.path.isfile(CSV_FILE):
        print(f"Loaded {load_csv(uid)} saved expenses from expenses.csv")
    actions = {"1": add_expense, "2": view_expenses, "3": report, "4": charts, "5": insights,
               "6": budgets, "7": import_statement, "8": people}
    while True:
        df = db.fetch_transactions(uid)
        ml.train(list(zip(df["description"].str.lower(), df["category"])) if not df.empty else None)
        print(f"\nHi {user['name']}!\n 1. Add an expense\n 2. View expenses\n 3. Generate report\n 4. Charts (matplotlib)\n"
              " 5. Insights & anomalies\n 6. Set budgets\n 7. Import bank statement\n 8. People ledger (UPI)\n 9. Save and Exit")
        c = input("Enter your choice: ").strip()
        if c == "9":
            print(f"Saved {save_csv(uid)} transactions to {CSV_FILE}. Goodbye!")
            break
        fn = actions.get(c)
        if not fn:
            print("  ! Invalid choice.")
            continue
        try:
            fn(uid)
        except (KeyboardInterrupt, EOFError):
            print("\n  (cancelled)")
        except Exception as ex:  # never crash the menu
            print(f"  ! Something went wrong: {ex}")


if __name__ == "__main__":
    main()
