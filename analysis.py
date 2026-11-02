"""Analytics: KPIs, budget status, month-end forecast, anomaly detection, plain-English insights."""
import calendar
from datetime import date

import numpy as np
import pandas as pd


def month_slice(df, year, month):
    if df.empty:
        return df
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df[(df["date"].dt.year == year) & (df["date"].dt.month == month)]


def kpis(df, year, month):
    m = month_slice(df, year, month)
    exp = m.loc[m["type"] == "expense", "amount"].sum()
    inc = m.loc[m["type"] == "income", "amount"].sum()
    rate = (inc - exp) / inc * 100 if inc > 0 else 0.0
    return {"spent": float(exp), "income": float(inc), "saved": float(inc - exp), "savings_rate": float(rate)}


def category_spend(df, year, month):
    m = month_slice(df, year, month)
    m = m[m["type"] == "expense"]
    return m.groupby("category")["amount"].sum().sort_values(ascending=False)


def budget_status(df, budgets, year, month):
    """Rows: category, budget, spent, pct, status (ok/warning/over)."""
    spend = category_spend(df, year, month)
    rows = []
    for cat, limit in budgets.items():
        spent = float(spend.get(cat, 0.0))
        pct = spent / limit * 100 if limit > 0 else 0
        status = "over" if pct > 100 else "warning" if pct >= 80 else "ok"
        rows.append({"category": cat, "budget": limit, "spent": spent, "pct": pct, "status": status})
    return pd.DataFrame(rows)


def forecast_month_end(df, year, month, today=None):
    """Project month-end total per category.
    Blend of (a) daily run-rate extrapolation and (b) linear regression on cumulative spend."""
    today = today or date.today()
    days_in_month = calendar.monthrange(year, month)[1]
    day = min(today.day, days_in_month) if (today.year, today.month) == (year, month) else days_in_month
    m = month_slice(df, year, month)
    m = m[m["type"] == "expense"]
    out = {}
    if m.empty:
        return out, 0.0
    for cat, g in m.groupby("category"):
        spent = g["amount"].sum()
        run_rate = spent / max(day, 1) * days_in_month
        daily = g.groupby(g["date"].dt.day)["amount"].sum().reindex(range(1, day + 1), fill_value=0).cumsum()
        if day >= 5:
            slope, intercept = np.polyfit(np.arange(1, day + 1), daily.values, 1)
            lin = slope * days_in_month + intercept
            proj = 0.5 * run_rate + 0.5 * max(lin, spent)
        else:
            proj = run_rate
        out[cat] = float(max(proj, spent))
    return out, float(sum(out.values()))


def detect_anomalies(df, z_thresh=3.5, min_samples=4, min_ratio=3.0):
    """Flag unusually large expenses compared with what is normal for that merchant/description
    (or, when a description is rare, for its category).
    Rule: modified z-score (median/MAD, cutoff 3.5) AND amount >= min_ratio x the group median."""
    e = df[df["type"] == "expense"].copy()
    cols = ["date", "description", "category", "amount", "typical", "zscore"]
    if e.empty:
        return pd.DataFrame(columns=cols)
    e["_desc"] = e["description"].str.lower().str.strip()
    counts = e["_desc"].map(e["_desc"].value_counts())
    e["_grp"] = np.where(counts >= min_samples, "d:" + e["_desc"], "c:" + e["category"])
    flags = []
    for _, g in e.groupby("_grp"):
        if len(g) < min_samples:
            continue
        med = g["amount"].median()
        mad = (g["amount"] - med).abs().median() or g["amount"].std() or 1.0
        z = 0.6745 * (g["amount"] - med) / mad
        mask = (z > z_thresh) & (g["amount"] >= min_ratio * med)
        hit = g[mask].copy()
        hit["zscore"], hit["typical"] = z[mask], med
        flags.append(hit)
    if not flags:
        return pd.DataFrame(columns=cols)
    return pd.concat(flags).sort_values("zscore", ascending=False)[cols]


def insights(df, budgets, year, month, today=None):
    """Return a list of (level, message) tips. level in {'danger','warn','info','good'}."""
    today = today or date.today()
    tips = []
    if df.empty:
        return [("info", "Add some transactions to unlock personalised insights.")]
    k = kpis(df, year, month)
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    cur, prev = category_spend(df, year, month), category_spend(df, prev_y, prev_m)

    # budget alerts
    bs = budget_status(df, budgets, year, month)
    for _, r in bs.iterrows():
        if r["status"] == "over":
            tips.append(("danger", f"{r['category']}: over budget by ₹{r['spent'] - r['budget']:,.0f} "
                                   f"({r['pct']:.0f}% used)."))
        elif r["status"] == "warning":
            tips.append(("warn", f"{r['category']}: {r['pct']:.0f}% of budget used - slow down."))

    # forecast vs budget
    proj, total = forecast_month_end(df, year, month, today)
    for cat, p in proj.items():
        lim = budgets.get(cat)
        if lim and p > lim and cur.get(cat, 0) < lim:
            tips.append(("warn", f"At this pace you'll exceed your {cat} budget by about ₹{p - lim:,.0f} by month-end."))

    # month-over-month changes
    for cat, v in cur.items():
        pv = prev.get(cat, 0)
        if pv > 500 and v > pv * 1.3 and v > 500:
            tips.append(("warn", f"{cat} spending is up {((v / pv) - 1) * 100:.0f}% vs last month "
                                 f"(₹{v:,.0f} vs ₹{pv:,.0f})."))
        elif pv > 500 and v < pv * 0.7:
            tips.append(("good", f"Nice! {cat} spending is down {(1 - v / pv) * 100:.0f}% vs last month."))

    # 50/30/20 rule
    if k["income"] > 0:
        needs = sum(cur.get(c, 0) for c in ["Rent", "Groceries", "Bills & Utilities", "Health", "Education"])
        wants = sum(cur.get(c, 0) for c in ["Food", "Shopping", "Entertainment", "Travel", "Other"])
        n, w, s = needs / k["income"] * 100, wants / k["income"] * 100, k["savings_rate"]
        tips.append(("info", f"50/30/20 check -> Needs {n:.0f}% (target 50), Wants {w:.0f}% (target 30), "
                             f"Savings {s:.0f}% (target 20)."))
        if s >= 20:
            tips.append(("good", f"Great job - you're saving {s:.0f}% of income this month."))
        elif s < 0:
            tips.append(("danger", "You're spending more than you earn this month."))
        elif s < 10:
            tips.append(("warn", "Savings rate is below 10%. Try trimming your biggest 'Wants' category."))

    if len(cur):
        top = cur.index[0]
        tips.append(("info", f"Your biggest expense category this month is {top} "
                             f"(₹{cur.iloc[0]:,.0f}, {cur.iloc[0] / cur.sum() * 100:.0f}% of spending)."))

    # weekend vs weekday
    m = month_slice(df, year, month)
    m = m[m["type"] == "expense"]
    if len(m) > 10:
        wk = m[m["date"].dt.weekday >= 5]["amount"].sum()
        if wk / m["amount"].sum() > 0.45:
            tips.append(("info", f"{wk / m['amount'].sum() * 100:.0f}% of your spending happens on weekends."))
    return tips


def people_ledger(df, year=None, month=None):
    """Person-to-person UPI view: per person, how much you sent, received and the net balance.
    Uses transactions whose category is 'Other' (unknown payee) or 'Income' (money in)."""
    d = month_slice(df, year, month) if year else df
    if d.empty:
        return pd.DataFrame(columns=["person", "sent", "received", "net", "txns"])
    d = d[d["category"].isin(["Other", "Income"])].copy()
    d["person"] = d["description"].str.strip().str.title()
    sent = d[d["type"] == "expense"].groupby("person")["amount"].sum()
    got = d[d["type"] == "income"].groupby("person")["amount"].sum()
    cnt = d.groupby("person")["amount"].count()
    out = pd.DataFrame({"sent": sent, "received": got, "txns": cnt}).fillna(0)
    out["net"] = out["received"] - out["sent"]
    out = out.reset_index().rename(columns={"index": "person"})
    out["txns"] = out["txns"].astype(int)
    return out.reindex(out["net"].abs().sort_values(ascending=False).index).reset_index(drop=True)
