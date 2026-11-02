"""Generate 3 months of realistic demo data so charts look rich in the presentation."""
import random
from datetime import date, timedelta

import db

EXPENSE_TEMPLATES = [  # (description, category, low, high, weight)
    ("Zomato order", "Food", 180, 520, 9), ("Swiggy dinner", "Food", 200, 480, 6),
    ("Canteen lunch", "Food", 60, 140, 10), ("Chai and snacks", "Food", 30, 120, 10),
    ("BigBasket vegetables", "Groceries", 250, 900, 4), ("Blinkit milk", "Groceries", 80, 300, 6),
    ("Uber ride", "Travel", 90, 380, 5), ("Metro card recharge", "Travel", 100, 500, 2),
    ("Auto fare", "Travel", 40, 160, 6), ("Petrol", "Travel", 200, 500, 2),
    ("Amazon order", "Shopping", 250, 1200, 2.5), ("Myntra clothes", "Shopping", 400, 1500, 1.0),
    ("Netflix subscription", "Entertainment", 199, 199, 0.3), ("Movie tickets PVR", "Entertainment", 250, 700, 1.5),
    ("Spotify premium", "Entertainment", 119, 119, 0.3), ("Birthday party", "Entertainment", 300, 1200, 0.8),
    ("Mobile recharge", "Bills & Utilities", 239, 299, 0.6), ("Wifi bill", "Bills & Utilities", 600, 800, 0.3),
    ("Pharmacy medicines", "Health", 120, 450, 1.2), ("Udemy course", "Education", 399, 799, 0.3),
    ("Xerox and printing", "Education", 20, 150, 1.5), ("Stationery", "Education", 50, 300, 0.8),
]


def seed(user_id, months=3, today=None, rng_seed=7):
    rng = random.Random(rng_seed)
    today = today or date.today()
    start = today - timedelta(days=months * 30)
    rows, d = [], start
    weights = [t[4] for t in EXPENSE_TEMPLATES]
    while d <= today:
        for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
            desc, cat, lo, hi, _w = rng.choices(EXPENSE_TEMPLATES, weights)[0]
            amt = round(rng.uniform(lo, hi) * (1.4 if d.weekday() >= 5 and cat in ("Food", "Entertainment") else 1))
            rows.append(dict(date=d, amount=amt, type="expense", category=cat, description=desc,
                             payment_mode=rng.choice(db.PAYMENT_MODES)))
        if d.day == 1:
            rows.append(dict(date=d, amount=6500, type="expense", category="Rent", description="Hostel rent",
                             payment_mode="Net Banking"))
            rows.append(dict(date=d, amount=22000, type="income", category="Income", description="Pocket money / stipend",
                             payment_mode="Net Banking"))
        if d.day == 15:
            rows.append(dict(date=d, amount=rng.choice([2000, 3000, 4500]), type="income", category="Income",
                             description="Freelance project", payment_mode="UPI"))
        d += timedelta(days=1)
    for off in (12, 25, 40, 55):  # normal Amazon orders so the outlier stands out statistically
        rows.append(dict(date=today - timedelta(days=off), amount=rng.choice([450, 620, 780, 900]), type="expense",
                         category="Shopping", description="Amazon order", payment_mode="Card"))
    # one deliberate outlier so the anomaly detector has something to show in the demo
    rows.append(dict(date=today - timedelta(days=3), amount=4999, type="expense", category="Shopping",
                     description="Amazon order", payment_mode="Card"))
    db.add_many(user_id, rows)
    for cat, lim in {"Food": 5000, "Groceries": 2500, "Travel": 2000, "Shopping": 3000, "Entertainment": 1500,
                     "Bills & Utilities": 1200, "Rent": 6500, "Health": 800, "Education": 800}.items():
        db.set_budget(user_id, cat, lim)
    return len(rows)
