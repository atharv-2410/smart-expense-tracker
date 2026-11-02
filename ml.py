"""Smart features: auto-categorisation (rules + Naive Bayes) and natural-language entry parsing."""
import re
from datetime import date, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# Stage 1: transparent keyword rules (fast, explainable)
KEYWORDS = {
    "Food": ["zomato", "swiggy", "restaurant", "cafe", "pizza", "burger", "biryani", "lunch", "dinner",
             "breakfast", "snacks", "tea", "chai", "coffee", "canteen", "mess", "dominos", "kfc", "mcdonald", "hotel", "juice", "bakery"],
    "Groceries": ["bigbasket", "blinkit", "zepto", "grocery", "vegetables", "fruits", "milk", "dmart", "kirana"],
    "Travel": ["uber", "ola", "rapido", "auto", "bus", "metro", "train", "irctc", "petrol", "fuel", "cab",
               "flight", "ticket", "taxi", "msrtc", "st bus", "depo"],
    "Rent": ["rent", "hostel", "pg", "deposit", "maintenance"],
    "Shopping": ["amazon", "flipkart", "myntra", "clothes", "shoes", "shirt", "mall", "meesho", "ajio"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "pvr", "game", "hotstar", "prime", "concert",
                      "party", "youtube"],
    "Bills & Utilities": ["electricity", "recharge", "wifi", "broadband", "internet", "jio", "airtel", "water bill",
                          "gas", "bill", "mobile"],
    "Health": ["medicine", "doctor", "pharmacy", "hospital", "gym", "clinic", "medical", "apollo", "wellness"],
    "Education": ["book", "course", "udemy", "coursera", "tuition", "fees", "exam", "stationery", "xerox", "print"],
}

# Stage 2: small labelled seed corpus to train Naive Bayes (grows with the user's own data)
TRAINING = [
    ("zomato order", "Food"), ("swiggy dinner", "Food"), ("lunch at canteen", "Food"), ("chai and samosa", "Food"),
    ("pizza hut", "Food"), ("biryani with friends", "Food"), ("starbucks coffee", "Food"), ("college mess fee", "Food"),
    ("bigbasket vegetables", "Groceries"), ("blinkit milk eggs", "Groceries"), ("dmart monthly stock", "Groceries"),
    ("fruits from market", "Groceries"), ("uber ride", "Travel"), ("ola cab to station", "Travel"),
    ("metro card recharge", "Travel"), ("petrol for bike", "Travel"), ("train ticket irctc", "Travel"),
    ("auto fare", "Travel"), ("bus pass", "Travel"), ("hostel rent", "Rent"), ("pg rent october", "Rent"),
    ("room deposit", "Rent"), ("amazon order headphones", "Shopping"), ("flipkart sale shoes", "Shopping"),
    ("myntra tshirt", "Shopping"), ("new jeans", "Shopping"), ("netflix subscription", "Entertainment"),
    ("movie tickets pvr", "Entertainment"), ("spotify premium", "Entertainment"), ("gaming topup", "Entertainment"),
    ("birthday party", "Entertainment"), ("electricity bill", "Bills & Utilities"),
    ("jio mobile recharge", "Bills & Utilities"), ("wifi broadband bill", "Bills & Utilities"),
    ("airtel postpaid", "Bills & Utilities"), ("pharmacy medicines", "Health"), ("doctor consultation", "Health"),
    ("gym membership", "Health"), ("apollo clinic", "Health"), ("textbook purchase", "Education"),
    ("udemy python course", "Education"), ("exam fees", "Education"), ("xerox and printing", "Education"),
    ("stationery pens notebooks", "Education"),
    ("dentist visit", "Health"), ("eye checkup glasses", "Health"), ("vitamin tablets", "Health"),
    ("blood test lab", "Health"), ("physiotherapy session", "Health"), ("health checkup", "Health"),
    ("lab record book", "Education"), ("project materials", "Education"), ("college fee installment", "Education"),
    ("library fine", "Education"), ("photocopy notes", "Education"), ("scientific calculator", "Education"),
    ("hackathon registration", "Education"), ("certification exam", "Education"),
    ("haircut", "Other"), ("laundry", "Other"), ("gift for friend", "Other"), ("donation", "Other"),
    ("salon", "Other"), ("temple offering", "Other"), ("shoe repair", "Other"), ("courier charges", "Other"),
    ("lent to friend", "Other"), ("miscellaneous", "Other"),
    ("samosa and juice", "Food"), ("ice cream", "Food"), ("sandwich", "Food"), ("thali", "Food"),
    ("maggi noodles", "Food"), ("paratha", "Food"), ("dosa", "Food"), ("cold drink", "Food"),
    ("tomatoes onions potatoes", "Groceries"), ("rice dal atta", "Groceries"), ("eggs and bread", "Groceries"),
    ("cooking oil", "Groceries"), ("supermarket", "Groceries"), ("toothpaste soap shampoo", "Groceries"),
    ("rickshaw", "Travel"), ("bike service", "Travel"), ("parking", "Travel"), ("toll", "Travel"),
    ("bus ticket home", "Travel"), ("outstation trip", "Travel"), ("fastag recharge", "Travel"),
    ("room rent share", "Rent"), ("flat advance", "Rent"), ("landlord payment", "Rent"),
    ("backpack", "Shopping"), ("watch", "Shopping"), ("earphones", "Shopping"), ("sneakers", "Shopping"),
    ("phone cover", "Shopping"), ("kurta", "Shopping"), ("gadget", "Shopping"),
    ("bowling", "Entertainment"), ("cricket turf booking", "Entertainment"), ("ott subscription", "Entertainment"),
    ("amusement park", "Entertainment"), ("night out", "Entertainment"), ("steam game", "Entertainment"),
    ("dth recharge", "Bills & Utilities"), ("cylinder refill", "Bills & Utilities"), ("water charges", "Bills & Utilities"),
    ("data pack", "Bills & Utilities"), ("insurance premium", "Bills & Utilities"), ("cloud storage plan", "Bills & Utilities"),
]


_model = None


def _build_model(extra=None):
    data = TRAINING + (extra or [])
    X, y = [d[0].lower() for d in data], [d[1] for d in data]
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), MultinomialNB(alpha=0.3))
    model.fit(X, y)
    return model, X, y


def train(extra=None):
    """(Re)train the model. `extra` = list of (description, category) from the user's history."""
    global _model
    _model, X, y = _build_model(extra)
    return _model


def model_accuracy(extra=None):
    """Accuracy of the full categoriser (rules + Naive Bayes) on HELD-OUT, hand-labelled descriptions
    that are never used for training. Quote this number in your presentation."""
    from eval_data import HELD_OUT
    train(extra)
    hits = sum(categorize(t)[0] == c for t, c in HELD_OUT)
    return hits / len(HELD_OUT), len(HELD_OUT)


def categorize(text: str):
    """Return (category, confidence, method)."""
    t = (text or "").lower().strip()
    if not t:
        return "Other", 0.0, "default"
    for cat, words in KEYWORDS.items():
        for w in words:
            if re.search(rf"\b{re.escape(w)}(?:s|es)?\b", t):
                return cat, 0.95, "rule"
    if _model is None:
        train()
    probs = _model.predict_proba([t])[0]
    i = probs.argmax()
    if probs[i] >= 0.35:
        return _model.classes_[i], float(probs[i]), "ml"
    return "Other", float(probs[i]), "default"


_DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def parse_entry(text: str, today=None):
    """Parse e.g. 'spent 250 on auto yesterday' / 'Zomato 340' / 'got 5000 pocket money on 12 oct'.
    Returns dict(amount, type, date, description, category, confidence, method) or None."""
    today = today or date.today()
    s = (text or "").strip()
    if not s:
        return None
    low = s.lower()

    m = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:rs\.?|rupees|₹|/-)?", low)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))
    rest = (low[:m.start()] + " " + low[m.end():])

    ttype = "income" if re.search(r"\b(got|received|earned|salary|stipend|income|credited|pocket money)\b", low) else "expense"

    d = today
    if re.search(r"\bday before yesterday\b", rest):
        d = today - timedelta(days=2)
        rest = rest.replace("day before yesterday", " ")
    elif "yesterday" in rest:
        d = today - timedelta(days=1)
        rest = rest.replace("yesterday", " ")
    elif "today" in rest:
        rest = rest.replace("today", " ")
    else:
        mm = re.search(r"\blast (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", rest)
        if mm:
            diff = (today.weekday() - _DAYS[mm.group(1)]) % 7 or 7
            d = today - timedelta(days=diff)
            rest = rest.replace(mm.group(0), " ")
        else:
            mm = re.search(r"\b(\d+)\s+days?\s+ago\b", rest)
            if mm:
                d = today - timedelta(days=int(mm.group(1)))
                rest = rest.replace(mm.group(0), " ")
            else:
                months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                mm = re.search(r"\b(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(months) + r")[a-z]*\b", rest)
                if mm:
                    try:
                        d = date(today.year, months.index(mm.group(2)) + 1, int(mm.group(1)))
                        if d > today:
                            d = d.replace(year=today.year - 1)
                    except ValueError:
                        d = today
                    rest = rest.replace(mm.group(0), " ")

    stop = r"\b(spent|spend|paid|pay|bought|buy|for|on|at|to|got|received|earned|the|a|an|of|in|rs|rupees|inr|credited)\b"
    desc = re.sub(stop, " ", rest)
    desc = re.sub(r"[^\w&\s]", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip().title()

    if ttype == "income":
        cat, conf, method = "Income", 0.9, "rule"
    else:
        cat, conf, method = categorize(desc or low)
    return {"amount": amount, "type": ttype, "date": d, "description": desc or "Expense",
            "category": cat, "confidence": conf, "method": method}
