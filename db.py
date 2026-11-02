"""SQLite data layer + simple authentication."""
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import date

DB_PATH = os.environ.get("EXPENSE_DB", os.path.join(os.path.dirname(__file__), "expenses.db"))

CATEGORIES = [
    "Food", "Travel", "Rent", "Shopping", "Entertainment", "Bills & Utilities",
    "Health", "Education", "Groceries", "Other",
]
PAYMENT_MODES = ["UPI", "Cash", "Card", "Net Banking"]


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense','income')),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                payment_mode TEXT DEFAULT 'UPI'
            );
            CREATE TABLE IF NOT EXISTS budgets(
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                PRIMARY KEY(user_id, category)
            );
            """
        )


# ---------- auth ----------
def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def register(name, email, password):
    email = email.strip().lower()
    if not name or not email or len(password) < 4:
        return None, "Fill all fields (password min 4 chars)."
    salt = os.urandom(8).hex()
    try:
        with conn() as c:
            cur = c.execute(
                "INSERT INTO users(name,email,password_hash,salt) VALUES(?,?,?,?)",
                (name.strip(), email, _hash(password, salt), salt),
            )
            return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, "Email already registered."


def login(email, password):
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if row and _hash(password, row["salt"]) == row["password_hash"]:
        return dict(row)
    return None


# ---------- transactions ----------
def add_transaction(user_id, dt, amount, ttype, category, description="", payment_mode="UPI"):
    with conn() as c:
        c.execute(
            "INSERT INTO transactions(user_id,date,amount,type,category,description,payment_mode)"
            " VALUES(?,?,?,?,?,?,?)",
            (user_id, str(dt), float(amount), ttype, category, description, payment_mode),
        )


def add_many(user_id, rows):
    with conn() as c:
        c.executemany(
            "INSERT INTO transactions(user_id,date,amount,type,category,description,payment_mode)"
            " VALUES(?,?,?,?,?,?,?)",
            [(user_id, str(r["date"]), float(r["amount"]), r["type"], r["category"],
              r.get("description", ""), r.get("payment_mode", "UPI")) for r in rows],
        )


def update_transaction(tid, user_id, dt, amount, ttype, category, description, payment_mode):
    with conn() as c:
        c.execute(
            "UPDATE transactions SET date=?,amount=?,type=?,category=?,description=?,payment_mode=?"
            " WHERE id=? AND user_id=?",
            (str(dt), float(amount), ttype, category, description, payment_mode, tid, user_id),
        )


def delete_transaction(tid, user_id):
    with conn() as c:
        c.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tid, user_id))


def fetch_transactions(user_id):
    import pandas as pd

    with conn() as c:
        df = pd.read_sql_query(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC, id DESC", c, params=(user_id,)
        )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# ---------- budgets ----------
def set_budget(user_id, category, limit_amount):
    with conn() as c:
        c.execute(
            "INSERT INTO budgets(user_id,category,limit_amount) VALUES(?,?,?)"
            " ON CONFLICT(user_id,category) DO UPDATE SET limit_amount=excluded.limit_amount",
            (user_id, category, float(limit_amount)),
        )


def get_budgets(user_id) -> dict:
    with conn() as c:
        rows = c.execute("SELECT category,limit_amount FROM budgets WHERE user_id=?", (user_id,)).fetchall()
    return {r["category"]: r["limit_amount"] for r in rows}


def today():
    return date.today()
