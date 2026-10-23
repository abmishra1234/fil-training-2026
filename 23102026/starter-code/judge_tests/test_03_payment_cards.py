"""
Group C - Payment card numbers: 13 to 19 digits (spaces or dashes allowed) that pass Luhn.   JT12 - JT16
"""
from __future__ import annotations

import adapter
import pytest
from samples import (
    AMEX, CARD_13, CARD_19, DISCOVER, LUHN_12, MASTERCARD, MC_BAD, RANDOM_BAD, VISA_BAD, VISA_DASHES, VISA_PLAIN,
    VISA_SPACES, luhn_ok,
)

P = adapter.make_passage
V = adapter.result_view


def card_count(text: str) -> int:
    r = V(adapter.check("q", [P("t#0", text)]))
    return r["findings"].get(adapter.TYPE_CARD, 0)


@pytest.mark.parametrize("card", [VISA_SPACES, VISA_DASHES, VISA_PLAIN, MASTERCARD, AMEX, DISCOVER],
                         ids=["visa-spaces", "visa-dashes", "visa-plain", "mastercard", "amex-4-6-5", "discover"])
def test_JT12_valid_cards_in_every_layout(card):
    """Spaces, dashes, no separator and non 4-4-4-4 grouping (Amex 4-6-5) are all cards."""
    assert luhn_ok(card.replace(" ", "").replace("-", ""))
    assert card_count(f"Refund to {card} was declined.") == 1
    q = V(adapter.check(f"charge {card} again", [P("q#0", "clean")]))
    assert q["decision"] == "BLOCK_QUERY"


def test_JT13_length_bounds_13_and_19_digits():
    """13 and 19 digit Luhn-valid numbers are cards; a 12 digit Luhn-valid number is not."""
    assert len(CARD_13) == 13 and len(CARD_19) == 19 and len(LUHN_12) == 12
    assert luhn_ok(CARD_13) and luhn_ok(CARD_19) and luhn_ok(LUHN_12)
    assert card_count(f"old card {CARD_13} expired") == 1
    assert card_count(f"corporate card {CARD_19} active") == 1
    assert card_count(f"account ref {LUHN_12} closed") == 0


@pytest.mark.parametrize("number", [VISA_BAD, MC_BAD, RANDOM_BAD], ids=["visa-bad", "mc-bad", "random-16"])
def test_JT14_luhn_failures_are_not_cards(number):
    """16 digits that fail the Luhn check are not card numbers (no over-blocking)."""
    assert not luhn_ok(number.replace(" ", ""))
    r = V(adapter.check("q", [P("n#0", f"Order reference {number} shipped.")]))
    assert r["decision"] == "ALLOW" and r["dropped"] == []


def test_JT15_ordinary_numbers_do_not_trigger():
    """Phone numbers, dates, amounts, UTRs, ticket ids, versions and error codes are not cards."""
    texts = [
        "Call the helpdesk on +91 98765 43210 or 1800-209-4567.",
        "The release is on 2026-10-23 at 18:30 IST.",
        "Hotel cap is INR 1,20,000 per quarter; per diem INR 2,500.",
        "Duplicate UTR 412345678901 detected on the bank file.",
        "Raise INC-20261023-0042; error PAY-E4031 and AUTH-E1107 are known.",
        "Upgrade from version 1.13.2 to 2.0.0 before 31/12/2026.",
    ]
    r = V(adapter.check("q", [P(f"n#{i}", t) for i, t in enumerate(texts)]))
    assert r["dropped"] == [], f"false positives: {r['dropped']} {r['findings']}"
    assert r["decision"] == "ALLOW"


def test_JT16_multiple_cards_punctuation_and_text_edges():
    """Two cards in one passage count 2; cards at the very start / end or in brackets still count."""
    assert card_count(f"Cards ({VISA_DASHES}) and {MASTERCARD.replace(' ', '')}.") == 2
    assert card_count(VISA_PLAIN) == 1
    assert card_count(f"{AMEX}\nend") == 1
    assert card_count(f"start\n{VISA_SPACES}") == 1
