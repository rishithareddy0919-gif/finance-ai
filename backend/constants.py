"""Shared constants. Phase 1 has no AI: this file only lists the allowed values."""
CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Entertainment", "Education"]
ALL_CATEGORIES = CATEGORIES + ["Other"]          # "Other" is the fallback for unknown merchants
PAYMENT_METHODS = ["UPI", "Card", "Cash", "Net Banking", "Wallet"]
SOURCES = ["manual", "csv", "screenshot"]
STATUSES = ["confirmed", "pending_confirmation"]
