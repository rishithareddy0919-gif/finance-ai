"""PHASE 7b - plain-language explanations. Gemini only WRITES the text; every number comes from the agent.
Only category, amount ratio, rules fired, probability and factor contributions are sent: no merchant names,
no transaction ids. If Gemini fails, or writes a number that is not in the data, the template text is used."""
import json
import re

from gemini import GeminiError, call_gemini

FACTOR_LABELS = {
    ("AmountDeviation", "normal"): "the amount is normal", ("AmountDeviation", "high"): "the amount is high",
    ("AmountDeviation", "very_high"): "the amount is very high",
    ("NewMerchant", "yes"): "the merchant is new", ("NewMerchant", "no"): "the merchant is familiar",
    ("CategoryOverspend", "yes"): "category spending is above usual", ("CategoryOverspend", "no"): "category spending is normal",
    ("UnusualTime", "yes"): "the time of day is unusual", ("UnusualTime", "no"): "the time of day is usual",
}
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def build_payload(category, amount_ratio, rules_fired, probability, contributions):
    """The ONLY data that may go to Gemini. All numbers are pre-formatted so nothing needs calculating."""
    return {
        "category": category,
        "amount_ratio": f"{amount_ratio:.1f}",
        "rules_fired": [r["description"] for r in rules_fired],
        "probability_percent": f"{round(probability * 100)}",
        "factors": [{"factor": FACTOR_LABELS[(c["variable"], c["state"])],
                     "change_percent": f"{round(c['contribution'] * 100):+d}"} for c in contributions],
    }


def template_explanation(payload):
    parts = [f"This {payload['category']} transaction is potentially unusual, with an estimated probability of "
             f"{payload['probability_percent']}%."]
    parts.append(f"The amount is {payload['amount_ratio']} times your usual average for this category.")
    if payload["factors"]:
        top = ", ".join(f"{f['factor']} ({f['change_percent']} points)" for f in payload["factors"][:2])
        parts.append(f"The biggest factors were: {top}.")
    parts.append("Next step: check the transaction in your payment app and confirm whether it was you.")
    return " ".join(parts)


def _numbers_allowed(text, payload):
    allowed = {n.lstrip("+-") for n in NUMBER.findall(json.dumps(payload))}
    allowed |= {str(float(n)) for n in allowed}
    return all(n in allowed or str(float(n)) in allowed for n in NUMBER.findall(text))


def explain(payload, caller=call_gemini):
    """Return (text, source) where source is 'gemini' or 'template'."""
    prompt = ("Write a 3 to 4 sentence plain-language explanation for a student about one payment, using ONLY the "
              "JSON below. Say 'potentially unusual' and never say 'fraud'. Do not invent or calculate any number: "
              "use only numbers that appear in the JSON. End with one suggested next step. No bullet points.\n\n"
              + json.dumps(payload))
    try:
        text = caller(prompt).strip()
    except GeminiError:
        return template_explanation(payload), "template"
    if not text or "fraud" in text.lower() or not _numbers_allowed(text, payload):
        return template_explanation(payload), "template"
    return text, "gemini"
