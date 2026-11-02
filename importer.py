"""Bank-statement importer: handles CSV/XLSX with separate Debit/Credit columns, Dr/Cr flags,
day-first dates, junk header rows and UPI narrations."""
import io
import re

import pandas as pd

DATE_KEYS = ["transaction date", "txn date", "tran date", "value date", "posting date", "date"]
DESC_KEYS = ["narration", "description", "particulars", "transaction remarks", "remarks", "details", "transaction details"]
DEBIT_KEYS = ["withdrawal", "debit", "dr amount", "dr", "paid out", "withdrawals"]
CREDIT_KEYS = ["deposit", "credit", "cr amount", "cr", "paid in", "deposits"]
AMOUNT_KEYS = ["amount", "transaction amount", "txn amount"]
FLAG_KEYS = ["dr/cr", "cr/dr", "type", "debit/credit"]


def _find(cols, keys):
    low = {c: str(c).strip().lower() for c in cols}
    for k in keys:  # exact first, then substring
        for c, l in low.items():
            if l == k:
                return c
    for k in keys:
        for c, l in low.items():
            if k in l and len(k) > 3:
                return c
    return None


def _num(x):
    if pd.isna(x):
        return 0.0
    s = re.sub(r"[^\d.\-]", "", str(x).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def clean_narration(text: str) -> str:
    """UPI/123456789/zomato/okhdfc... -> 'Zomato'; strips refs and noise."""
    t = str(text or "").strip()
    m = re.search(r"(?i)\b(upi[a-z]{0,2}|imps|neft|rtgs)[/\-:]", t)
    if m:
        parts = [p for p in re.split(r"[/\-:]", t[m.start():]) if p.strip()]
        cand = [p for p in parts[1:] if not re.fullmatch(r"[\d\s]+", p) and len(p) > 2
                and not re.search(r"(?i)@|^\s*(upi\w*|payment|paid|ok(hdfc|sbi|icici|axis)|ybl|ibl|axl|dr|cr|rev)\s*$", p)]
        if cand:
            return cand[0].strip().title()
    t = re.sub(r"\b\d{6,}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip().title()[:60]
    return t if re.search(r"[A-Za-z]{2}", t) else "Bank Transfer"


def _read(file, name):
    name = (name or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, header=None, dtype=str)
    import csv
    raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
    text = raw.decode("utf-8-sig", errors="ignore")
    best = None
    for delim in [",", ";", "\t", "|"]:
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
        width = max((len(r) for r in rows), default=0)
        if best is None or width > best[0]:
            best = (width, rows)
    width, rows = best
    rows = [r + [None] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows, dtype=str)


def parse_statement(file, name=""):
    """Return (DataFrame[date, amount, type, description], notes list)."""
    raw = _read(file, name)
    notes = []
    # locate the header row: first row containing a date-ish AND a description/amount-ish label
    hdr = None
    for i in range(min(len(raw), 40)):
        vals = [str(v).strip().lower() for v in raw.iloc[i].tolist() if pd.notna(v)]
        has_date = any("date" in v for v in vals)
        has_money = any(any(k in v for k in ["debit", "withdraw", "credit", "deposit", "amount", "dr", "cr"]) for v in vals)
        if has_date and has_money:
            hdr = i
            break
    if hdr is None:
        raise ValueError("Couldn't find the header row (needs a Date column and Debit/Credit/Amount columns).")
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(c).strip() if pd.notna(c) else f"col{i}" for i, c in enumerate(raw.iloc[hdr])]
    df = df.dropna(how="all")

    c_date, c_desc = _find(df.columns, DATE_KEYS), _find(df.columns, DESC_KEYS)
    c_deb, c_cred = _find(df.columns, DEBIT_KEYS), _find(df.columns, CREDIT_KEYS)
    c_amt, c_flag = _find(df.columns, AMOUNT_KEYS), _find(df.columns, FLAG_KEYS)
    if not c_date or not (c_deb or c_cred or c_amt):
        raise ValueError(f"Unrecognised columns: {list(df.columns)}")

    ds = df[c_date].astype(str).str.strip()
    iso = ds.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    dates = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    dates[iso] = pd.to_datetime(ds[iso], errors="coerce", format="mixed")
    dates[~iso] = pd.to_datetime(ds[~iso], dayfirst=True, errors="coerce", format="mixed")
    out = pd.DataFrame({"date": dates})
    out["description_raw"] = df[c_desc].fillna("") if c_desc else ""
    if c_deb or c_cred:
        deb = df[c_deb].map(_num) if c_deb else pd.Series(0.0, index=df.index)
        cred = df[c_cred].map(_num) if c_cred else pd.Series(0.0, index=df.index)
        out["amount"] = deb.where(deb > 0, cred)
        out["type"] = ["expense" if d > 0 else "income" for d in deb]
    else:
        amt = df[c_amt].map(_num)
        out["amount"] = amt.abs()
        if c_flag:
            flag = df[c_flag].astype(str).str.lower()
            out["type"] = ["income" if f.startswith(("cr", "credit")) else "expense" for f in flag]
        else:
            out["type"] = ["expense" if a < 0 else "income" for a in amt]
            notes.append("No Dr/Cr column: treated negative amounts as expenses.")
    bad = out["date"].isna() | (out["amount"] <= 0)
    if bad.sum():
        notes.append(f"Skipped {int(bad.sum())} non-transaction rows (totals, opening balance, blanks).")
    out = out[~bad].copy()
    out["description"] = out["description_raw"].map(clean_narration)
    out["date"] = out["date"].dt.date
    return out[["date", "amount", "type", "description", "description_raw"]].reset_index(drop=True), notes
