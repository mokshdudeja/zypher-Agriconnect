"""
AgriConnect — Shared Backend Utilities
"""


def normalize_phone(phone: str) -> str:
    """
    Normalize an Indian phone number to E.164 format (+91XXXXXXXXXX).
    
    Handles:
    - Raw 10-digit: 9876543210 → +919876543210
    - With leading 0: 09876543210 → +919876543210
    - With country code: 919876543210 → +919876543210
    - Already formatted: +919876543210 → +919876543210
    - Strips spaces and dashes
    """
    normalized = phone.strip().replace(" ", "").replace("-", "")
    
    if normalized.startswith("+"):
        # Already has +, just clean up
        return "+" + normalized.lstrip("+")
    elif normalized.startswith("91") and len(normalized) > 10:
        # Has country code without +
        return "+" + normalized
    elif normalized.startswith("0"):
        # Has leading 0
        return "+91" + normalized.lstrip("0")
    else:
        # Raw 10-digit
        return "+91" + normalized
