"""judge_tests/samples.py - SYNTHETIC secrets and look-alikes. No real data."""
from __future__ import annotations


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def with_check_digit(body: str) -> str:
    """Append the digit that makes body+digit pass Luhn."""
    for d in "0123456789":
        if luhn_ok(body + d):
            return body + d
    raise AssertionError("unreachable")


def without_check_digit(body: str) -> str:
    """Append a digit that makes body+digit FAIL Luhn."""
    for d in "0123456789":
        if not luhn_ok(body + d):
            return body + d
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- credentials (from the brief + variants)
SK_KEY = "sk-test-9f8e7d6c5b4a3f2e1d0c"
SK_LIVE = "sk-live-4f3e2d1c0b9a8f7e6d5c4b3a"
AKIA_KEY = "AKIA4EXAMPLE7KEY9XYZ"
PASSWORD_ASSIGN = "password=Winter2026!"
CLIENT_SECRET = "client_secret: Qx7abc"

# ---------------------------------------------------------------- cards
VISA_SPACES = "4111 1111 1111 1111"
VISA_DASHES = "4111-1111-1111-1111"
VISA_PLAIN = "4111111111111111"
MASTERCARD = "5555 5555 5555 4444"
AMEX = "3782 822463 10005"
DISCOVER = "6011-0009-9013-9424"
CARD_13 = "4222222222222"
CARD_19 = with_check_digit("601100000000000000")           # 19 digits, Luhn-valid
LUHN_12 = with_check_digit("41111111111")                   # 12 digits, Luhn-valid -> too short
VISA_BAD = "4111 1111 1111 1112"                              # fails Luhn
MC_BAD = "5555 5555 5555 4440"                                # fails Luhn
RANDOM_BAD = without_check_digit("123456789012345")          # 16 digits, fails Luhn

# ---------------------------------------------------------------- codenames (default config must list these two)
FALCON = "Project Falcon"
MONSOON = "Project Monsoon"

# Every secret string the judge ever plants (used by the "never leaks" checks)
ALL_SECRET_STRINGS = [
    SK_KEY, SK_LIVE, AKIA_KEY, "Winter2026!", "Qx7abc", VISA_SPACES, VISA_DASHES, VISA_PLAIN,
    MASTERCARD, AMEX, "Project Falcon", "Project Monsoon", "project falcon", "PROJECT MONSOON",
]

CLEAN_TEXT = (
    "NovaPay hybrid working: employees work from the office on two anchor days per week, "
    "Tuesday and Thursday. Team leads may agree a different pattern in writing. "
)


def handbook_like(n_chars: int, seed: str = "") -> str:
    """Realistic clean filler of about n_chars characters, with numbers that must NOT trigger anything."""
    base = (
        "Per diem for Pune is INR 2,500 per day; hotels are capped at INR 7,500 per night. "
        "Raise a ticket INC-20261023-0042 or call 1800-209-4567. Error PAY-E4031 means the settlement "
        "batch missed the 18:30 cut-off; retry after 2026-10-24 09:00. The RTO of Ledgerline is 30 minutes "
        "and the RPO is 5 minutes. UTR 412345678901 was duplicated. Version 1.13.2 fixed the bug. "
        "Passwords must be at least 14 characters; report a leaked secret to security within 1 hour. "
    )
    text = (seed + " " + base * (n_chars // len(base) + 1))[:n_chars]
    return text
