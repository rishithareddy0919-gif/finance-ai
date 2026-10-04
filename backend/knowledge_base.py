"""PHASE 3 - KNOWLEDGE BASE (AI concept: knowledge representation).
Facts about the world stored as plain data: which merchant belongs to which category.
categorize() uses them in this order: exact merchant, then keyword, then an unknown-merchant fallback."""

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Entertainment", "Education"]
FALLBACK_CATEGORY = "Other"

MERCHANT_MAP = {                       # lower-case merchant name -> category
    "swiggy": "Food", "zomato": "Food", "college canteen": "Food", "hostel mess": "Food",
    "uber": "Travel", "ola": "Travel", "irctc": "Travel", "redbus": "Travel", "indigo airlines": "Travel",
    "metro card recharge": "Travel",
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping", "croma electronics": "Shopping",
    "jio": "Bills", "airtel": "Bills", "pg electricity": "Bills",
    "spotify": "Entertainment", "netflix": "Entertainment", "bookmyshow": "Entertainment",
    "udemy": "Education", "campus stationery": "Education", "university fee portal": "Education",
}

KEYWORDS = {                           # words that hint at a category when the merchant is not in the map
    "Food": ["canteen", "mess", "cafe", "restaurant", "pizza", "biryani", "chai", "bakery", "kitchen"],
    "Travel": ["cab", "taxi", "metro", "bus", "flight", "airlines", "railway", "petrol", "fuel"],
    "Shopping": ["mart", "fashion", "electronics", "mall", "bazaar"],
    "Bills": ["electricity", "internet", "broadband", "phone", "mobile", "water", "gas", "rent", "wifi"],
    "Entertainment": ["movie", "cinema", "game", "gaming", "music", "stream"],
    "Education": ["fee", "tuition", "course", "college", "university", "book", "stationery", "exam"],
}


def categorize_with_reason(merchant_name):
    """Return (category, reason). reason is 'merchant', 'keyword:<word>' or 'fallback'."""
    name = " ".join(str(merchant_name or "").lower().split())
    if name in MERCHANT_MAP:
        return MERCHANT_MAP[name], "merchant"
    for category in CATEGORIES:                     # fixed order: the first category with a hit wins
        for word in KEYWORDS[category]:
            if word in name:
                return category, "keyword:" + word
    return FALLBACK_CATEGORY, "fallback"


def categorize(merchant_name):
    return categorize_with_reason(merchant_name)[0]
