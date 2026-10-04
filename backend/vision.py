"""PHASE 7 - payment screenshot extraction with Gemini. The image is processed in memory only: never written
to disk or the database. Fields that are not visible must be null; we never guess."""
import json
import re
from datetime import datetime

from constants import PAYMENT_METHODS
from gemini import GeminiError, call_gemini

FIELDS = ["amount", "currency", "date", "time", "merchant_or_payee", "transaction_id", "payment_method", "location"]
PROMPT = (
    "You read screenshots of UPI or card payments. Return ONLY a JSON object with exactly these keys: "
    + ", ".join(FIELDS) + ". Each key maps to {\"value\": ..., \"confidence\": \"high\"|\"medium\"|\"low\"}. "
    "Use date format YYYY-MM-DD, time in 24-hour HH:MM, amount as a plain number. If a field is not clearly "
    "visible, use {\"value\": null, \"confidence\": \"low\"}. Never guess or invent values.")
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]
TIME_FORMATS = ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p", "%I:%M%p"]


def _amount(v):
    try:
        n = float(re.sub(r"[₹,\sA-Za-z]", "", str(v)))
    except ValueError:
        return None
    return round(n, 2) if n > 0 else None


def _date(v):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(str(v).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _time(v):
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(str(v).strip().upper(), fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def _text(v, limit=80):
    s = " ".join(str(v).split())
    return s[:limit] or None


def _method(v):
    s = str(v).strip().lower()
    for name in PAYMENT_METHODS:
        if s == name.lower():
            return name
    return "UPI" if "upi" in s else None


CLEANERS = {"amount": _amount, "currency": lambda v: _text(v, 5), "date": _date, "time": _time,
            "merchant_or_payee": _text, "transaction_id": lambda v: _text(v, 40),
            "payment_method": _method, "location": _text}


def empty_fields():
    return {f: {"value": None, "confidence": "low"} for f in FIELDS}


def result(ok, fields, error=None, warnings=None):
    merchant = fields["merchant_or_payee"]
    return {"ok": ok, "error": error, "fields": fields, "warnings": warnings or [],
            "needs_merchant_confirmation": merchant["value"] is None or merchant["confidence"] != "high"}


def clean_extraction(raw_text):
    """Parse and validate Gemini's reply. Never raises: bad input becomes empty low-confidence fields."""
    text = re.sub(r"^```(?:json)?|```$", "", str(raw_text).strip(), flags=re.M).strip()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return result(False, empty_fields(), "The screenshot could not be read reliably. Please enter the details yourself.")
    fields, warnings = empty_fields(), []
    for name in FIELDS:
        item = data.get(name)
        value = item.get("value") if isinstance(item, dict) else item
        confidence = item.get("confidence") if isinstance(item, dict) else "low"
        if confidence not in ("high", "medium", "low"):
            confidence = "low"
        if value is None or str(value).strip() == "":
            continue
        cleaned = CLEANERS[name](value)
        if cleaned is None:
            warnings.append(f"{name}: could not understand '{value}', please check it")
            continue
        fields[name] = {"value": cleaned, "confidence": confidence}
    return result(True, fields, warnings=warnings)


def extract(image_bytes, mime_type, caller=call_gemini):
    try:
        raw = caller(PROMPT, image_bytes=image_bytes, mime_type=mime_type, json_mode=True)
    except GeminiError as e:
        return result(False, empty_fields(), f"Screenshot reading is unavailable ({e}). Enter the details yourself.")
    return clean_extraction(raw)
