"""Smart Expense Tracker & Budget Analyzer - run with:  streamlit run app.py"""
import calendar
import io
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as an
import db
import importer as imp
import ml
import seed

st.set_page_config(page_title="Smart Expense Tracker", page_icon="💸", layout="wide")
db.init_db()

COLORS = {"ok": "#2e9e5b", "warning": "#e0a100", "over": "#d64545"}
LEVEL_ICON = {"danger": "🔴", "warn": "🟠", "info": "🔵", "good": "🟢"}


def inr(x):
    return f"₹{x:,.0f}"


# ---------------------------------------------------------------- auth
def auth_screen():
    st.title("💸 Smart Expense Tracker")
    st.caption("Auto-categorise spending, forecast overspending early and get actionable advice.")
    tab_login, tab_reg, tab_demo = st.tabs(["Login", "Register", "Try demo"])
    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                u = db.login(email, pw)
                if u:
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
    with tab_reg:
        with st.form("register"):
            name = st.text_input("Name")
            email = st.text_input("Email", key="reg_email")
            pw = st.text_input("Password", type="password", key="reg_pw")
            if st.form_submit_button("Create account"):
                uid, err = db.register(name, email, pw)
                if err:
                    st.error(err)
                else:
                    st.session_state.user = db.login(email, pw)
                    st.rerun()
    with tab_demo:
        st.write("Loads a demo account pre-filled with 3 months of realistic data - perfect for the presentation.")
        if st.button("Launch demo account"):
            u = db.login("demo@demo.com", "demo1234")
            if not u:
                uid, _ = db.register("Demo Student", "demo@demo.com", "demo1234")
                seed.seed(uid)
                u = db.login("demo@demo.com", "demo1234")
            st.session_state.user = u
            st.rerun()


if "user" not in st.session_state:
    auth_screen()
    st.stop()

user = st.session_state.user
uid = user["id"]
df = db.fetch_transactions(uid)
budgets = db.get_budgets(uid)

# train categoriser on built-in corpus + this user's own labelled history (personalisation)
history = []
if not df.empty:
    e = df[(df["type"] == "expense") & (df["description"].str.len() > 2)]
    history = list(zip(e["description"].str.lower(), e["category"]))
ml.train(history)

# ---------------------------------------------------------------- sidebar
st.sidebar.title("💸 Smart Expense Tracker")
st.sidebar.write(f"Hi, **{user['name']}** 👋")
page = st.sidebar.radio("Navigate", ["📊 Dashboard", "➕ Add Transaction", "🧾 Transactions",
                                     "🎯 Budgets", "💡 Insights & Forecast", "👥 People Ledger", "📁 Import / Export"])

today = date.today()
if not df.empty:
    periods = sorted({(d.year, d.month) for d in df["date"]}, reverse=True)
else:
    periods = [(today.year, today.month)]
labels = [f"{calendar.month_name[m]} {y}" for y, m in periods]
sel = st.sidebar.selectbox("Month", labels)
year, month = periods[labels.index(sel)]

if st.sidebar.button("Logout"):
    del st.session_state["user"]
    st.rerun()

# ---------------------------------------------------------------- dashboard
if page == "📊 Dashboard":
    st.header(f"Dashboard - {sel}")
    k = an.kpis(df, year, month)
    bs = an.budget_status(df, budgets, year, month)
    total_budget = sum(budgets.values())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total spent", inr(k["spent"]))
    c2.metric("Income", inr(k["income"]))
    c3.metric("Remaining budget", inr(total_budget - k["spent"]) if total_budget else "-")
    c4.metric("Savings rate", f"{k['savings_rate']:.0f}%")

    for _, r in bs.iterrows():
        if r["status"] == "over":
            st.error(f"🚨 {r['category']} budget exceeded: {inr(r['spent'])} of {inr(r['budget'])}")
        elif r["status"] == "warning":
            st.warning(f"⚠️ {r['category']} at {r['pct']:.0f}% of budget")

    m = an.month_slice(df, year, month)
    exp = m[m["type"] == "expense"]
    left, right = st.columns(2)
    with left:
        st.subheader("Spending by category")
        cs = an.category_spend(df, year, month)
        if len(cs):
            fig = px.pie(values=cs.values, names=cs.index, hole=0.45)
            fig.update_traces(textinfo="label+percent")
            st.plotly_chart(fig)
        else:
            st.info("No expenses this month.")
    with right:
        st.subheader("Daily spending & cumulative trend")
        if len(exp):
            daily = exp.groupby(exp["date"].dt.date)["amount"].sum().reset_index()
            daily["cumulative"] = daily["amount"].cumsum()
            fig = go.Figure()
            fig.add_bar(x=daily["date"], y=daily["amount"], name="Daily")
            fig.add_scatter(x=daily["date"], y=daily["cumulative"], name="Cumulative", yaxis="y2")
            fig.update_layout(yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h"))
            st.plotly_chart(fig)
        else:
            st.info("No expenses this month.")

    left, right = st.columns(2)
    with left:
        st.subheader("Budget progress")
        if bs.empty:
            st.info("Set budgets in the Budgets tab.")
        for _, r in bs.iterrows():
            st.write(f"**{r['category']}** - {inr(r['spent'])} / {inr(r['budget'])}")
            st.progress(min(r["pct"] / 100, 1.0))
    with right:
        st.subheader("Top 5 expenses")
        if len(exp):
            top = exp.nlargest(5, "amount")[["date", "description", "category", "amount"]].copy()
            top["date"] = top["date"].dt.date
            st.dataframe(top, hide_index=True)
        st.subheader("Last 6 months trend")
        mm = df[df["type"] == "expense"].copy()
        if len(mm):
            mm["month"] = mm["date"].dt.to_period("M").astype(str)
            tr = mm.groupby("month")["amount"].sum().reset_index()
            st.plotly_chart(px.bar(tr.tail(6), x="month", y="amount"))

# ---------------------------------------------------------------- add
elif page == "➕ Add Transaction":
    st.header("Add transaction")
    st.subheader("✨ Smart entry (type it naturally)")
    st.caption("Try: `Zomato 340` · `spent 250 on auto yesterday` · `got 5000 pocket money on 12 oct` · `paid 600 wifi bill 2 days ago`")
    with st.form("nl"):
        text = st.text_input("What did you spend?")
        go_parse = st.form_submit_button("Understand it")
    if go_parse:
        p = ml.parse_entry(text, today)
        if p is None:
            st.error("Couldn't find an amount. Include a number, e.g. 'Zomato 340'.")
        else:
            st.session_state.pending = p
            st.session_state.pcount = st.session_state.get("pcount", 0) + 1
    p = st.session_state.get("pending")
    pc = st.session_state.get("pcount", 0)
    if p:
        method = {"rule": "keyword rule", "ml": "Naive Bayes model", "default": "fallback"}[p["method"]]
        st.success(f"Detected: **{inr(p['amount'])}** · {p['type']} · **{p['category']}** "
                   f"({p['confidence'] * 100:.0f}% confidence via {method}) · {p['date']}")
        cats = db.CATEGORIES + ["Income"]
        c1, c2, c3 = st.columns(3)
        amt = c1.number_input("Amount (₹)", value=float(p["amount"]), min_value=0.0, key=f"p_amt_{pc}")
        cat = c2.selectbox("Category", cats, index=cats.index(p["category"]) if p["category"] in cats else 0, key=f"p_cat_{pc}")
        dte = c3.date_input("Date", value=p["date"], key=f"p_date_{pc}")
        desc = st.text_input("Description", value=p["description"], key=f"p_desc_{pc}")
        mode = st.selectbox("Payment mode", db.PAYMENT_MODES, key=f"p_mode_{pc}")
        if st.button("✅ Save this transaction"):
            db.add_transaction(uid, dte, amt, p["type"], cat, desc, mode)
            st.session_state.pending = None
            st.toast("Saved!")
            st.rerun()

    st.divider()
    st.subheader("Manual entry")
    with st.form("manual", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ttype = c1.radio("Type", ["expense", "income"], horizontal=True)
        amount = c2.number_input("Amount (₹)", min_value=0.0, step=10.0)
        c3, c4, c5 = st.columns(3)
        category = c3.selectbox("Category", db.CATEGORIES + ["Income"])
        dte = c4.date_input("Date", value=today)
        mode = c5.selectbox("Payment mode", db.PAYMENT_MODES)
        desc = st.text_input("Description")
        if st.form_submit_button("Add"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(uid, dte, amount, ttype, category, desc, mode)
                st.success("Added!")

# ---------------------------------------------------------------- transactions
elif page == "🧾 Transactions":
    st.header("Transactions")
    if df.empty:
        st.info("Nothing here yet.")
    else:
        f1, f2, f3 = st.columns(3)
        cat_f = f1.multiselect("Category", sorted(df["category"].unique()))
        type_f = f2.selectbox("Type", ["all", "expense", "income"])
        q = f3.text_input("Search description")
        v = df.copy()
        if cat_f:
            v = v[v["category"].isin(cat_f)]
        if type_f != "all":
            v = v[v["type"] == type_f]
        if q:
            v = v[v["description"].str.contains(q, case=False, na=False)]
        v = v.head(300)[["id", "date", "type", "category", "description", "amount", "payment_mode"]].copy()
        v["date"] = v["date"].dt.date
        v["delete"] = False
        edited = st.data_editor(
            v, hide_index=True, disabled=["id"], key="editor",
            column_config={
                "type": st.column_config.SelectboxColumn(options=["expense", "income"]),
                "category": st.column_config.SelectboxColumn(options=db.CATEGORIES + ["Income"]),
                "payment_mode": st.column_config.SelectboxColumn(options=db.PAYMENT_MODES),
                "date": st.column_config.DateColumn(),
                "amount": st.column_config.NumberColumn(format="₹%.0f"),
            },
        )
        if st.button("💾 Apply edits / deletions"):
            n_upd = n_del = 0
            orig = v.set_index("id")
            for _, r in edited.iterrows():
                if r["delete"]:
                    db.delete_transaction(int(r["id"]), uid)
                    n_del += 1
                elif not r.drop("id").equals(orig.loc[r["id"]]):
                    db.update_transaction(int(r["id"]), uid, r["date"], r["amount"], r["type"],
                                          r["category"], r["description"], r["payment_mode"])
                    n_upd += 1
            st.success(f"Updated {n_upd}, deleted {n_del}.")
            st.rerun()

# ---------------------------------------------------------------- budgets
elif page == "🎯 Budgets":
    st.header("Monthly budgets")
    st.caption("Set a limit for each category. You'll get alerts at 80% and 100%.")
    with st.form("budgets"):
        cols = st.columns(2)
        new = {}
        for i, c in enumerate(db.CATEGORIES):
            new[c] = cols[i % 2].number_input(c, min_value=0.0, step=100.0, value=float(budgets.get(c, 0.0)))
        if st.form_submit_button("Save budgets"):
            for c, val in new.items():
                if val > 0:
                    db.set_budget(uid, c, val)
            st.success("Budgets saved.")
            st.rerun()
    bs = an.budget_status(df, budgets, year, month)
    if not bs.empty:
        fig = go.Figure()
        fig.add_bar(x=bs["category"], y=bs["budget"], name="Budget", marker_color="#b0b7c3")
        fig.add_bar(x=bs["category"], y=bs["spent"], name="Spent", marker_color=[COLORS[s] for s in bs["status"]])
        fig.update_layout(barmode="group", title=f"Budget vs spent - {sel}")
        st.plotly_chart(fig)

# ---------------------------------------------------------------- insights
elif page == "💡 Insights & Forecast":
    st.header("Insights & forecast")
    st.subheader("Smart tips")
    for level, msg in an.insights(df, budgets, year, month, today):
        st.write(f"{LEVEL_ICON[level]} {msg}")

    st.subheader("📈 Month-end forecast")
    proj, total = an.forecast_month_end(df, year, month, today)
    if proj:
        rows = []
        spent = an.category_spend(df, year, month)
        for c, p in sorted(proj.items(), key=lambda x: -x[1]):
            lim = budgets.get(c)
            rows.append({"Category": c, "Spent so far": round(spent.get(c, 0)), "Projected month-end": round(p),
                         "Budget": lim if lim else None,
                         "Status": "—" if not lim else ("⚠️ will exceed" if p > lim else "✅ on track")})
        st.metric("Projected total spending this month", inr(total))
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Method: average of daily run-rate extrapolation and linear regression on cumulative spend.")
    else:
        st.info("Not enough data for this month.")

    st.subheader("🔍 Unusual transactions (anomaly detection)")
    an_df = an.detect_anomalies(df)
    if an_df.empty:
        st.success("No unusual transactions found.")
    else:
        show = an_df.head(10)[["date", "description", "category", "amount", "typical", "zscore"]].copy()
        show["date"] = show["date"].dt.date
        show.columns = ["Date", "Description", "Category", "Amount", "Typical in category", "Outlier score"]
        st.dataframe(show.round(1), hide_index=True)
        st.caption("Method: robust z-score (median/MAD) per category - flags amounts far above what is normal for you.")

    st.subheader("🧠 Categoriser model")
    acc, n_test = ml.model_accuracy(history)
    st.write(f"Categoriser accuracy: **{acc * 100:.0f}%** on {n_test} held-out, hand-labelled descriptions "
             f"(keyword rules + Naive Bayes, trained on {len(ml.TRAINING) + len(history)} examples incl. your history).")

# ---------------------------------------------------------------- people ledger
elif page == "👥 People Ledger":
    st.header("👥 People ledger (UPI friends & family)")
    st.caption("Most student spending is UPI transfers to people, not shops. See who you sent money to, "
               "who sent you money, and the net balance.")
    scope = st.radio("Period", ["Selected month", "All time"], horizontal=True)
    led = an.people_ledger(df, year, month) if scope == "Selected month" else an.people_ledger(df)
    if led.empty:
        st.info("No person-to-person transactions found.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Sent to people", inr(led["sent"].sum()))
        c2.metric("Received from people", inr(led["received"].sum()))
        c3.metric("People involved", len(led))
        top = led.head(12).copy()
        top["direction"] = top["net"].apply(lambda v: "You are owed" if v > 0 else "You paid more")
        fig = px.bar(top, x="net", y="person", orientation="h", color="direction",
                     color_discrete_map={"You are owed": "#2e9e5b", "You paid more": "#d64545"})
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Net (received - sent), ₹")
        st.plotly_chart(fig)
        show = led.copy()
        show.columns = ["Person", "Sent ₹", "Received ₹", "Net ₹", "Transactions"]
        st.dataframe(show.round(0), hide_index=True)
        st.caption("Net > 0: they sent you more than you sent them. Net < 0: you paid more than you received.")

# ---------------------------------------------------------------- import / export
elif page == "📁 Import / Export":
    st.header("Import / Export")
    st.subheader("Import bank statement / CSV")
    st.caption("Works with most bank statements (CSV or Excel) with Date, Narration, Withdrawal/Debit and "
               "Deposit/Credit columns, or a simple `date,amount,description` file. Everything stays on your laptop.")
    up = st.file_uploader("Upload statement", type=["csv", "xlsx", "xls"])
    if up is not None:
        try:
            parsed, notes = imp.parse_statement(up, up.name)
            for n in notes:
                st.info(n)
            parsed["category"] = [
                "Income" if t == "income" else ml.categorize(d or r)[0]
                for d, r, t in zip(parsed["description"], parsed["description_raw"], parsed["type"])
            ]
            st.write(f"Found **{len(parsed)}** transactions. Review / fix categories before importing:")
            cats = db.CATEGORIES + ["Income"]
            review = st.data_editor(
                parsed[["date", "description", "amount", "type", "category"]], hide_index=True, key="imp_editor",
                column_config={"category": st.column_config.SelectboxColumn(options=cats),
                               "type": st.column_config.SelectboxColumn(options=["expense", "income"])})
            if st.button(f"Import {len(review)} transactions"):
                rows = [dict(date=r["date"], amount=float(r["amount"]), type=r["type"], category=r["category"],
                             description=r["description"], payment_mode="UPI") for _, r in review.iterrows()]
                db.add_many(uid, rows)
                st.success("Imported! Open the Dashboard and pick the month in the sidebar.")
                st.rerun()
        except Exception as ex:
            st.error(f"Could not read file: {ex}")

    st.subheader("Export")
    if df.empty:
        st.info("No data to export.")
    else:
        out = df.drop(columns=["user_id"]).copy()
        out["date"] = out["date"].dt.date
        st.download_button("⬇️ CSV", out.to_csv(index=False), "transactions.csv", "text/csv")
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            out.to_excel(xw, sheet_name="Transactions", index=False)
            an.category_spend(df, year, month).rename("Spent").to_frame().to_excel(xw, sheet_name=f"Summary {sel}"[:31])
            an.budget_status(df, budgets, year, month).to_excel(xw, sheet_name="Budget status", index=False)
        st.download_button("⬇️ Excel report", buf.getvalue(), f"report_{year}_{month:02d}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    if st.button("Load demo data into my account"):
        seed.seed(uid)
        st.rerun()
