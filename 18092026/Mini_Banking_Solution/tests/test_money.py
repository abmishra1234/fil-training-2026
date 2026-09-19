"""Acceptance tests -- Task 1: Money."""

from decimal import Decimal

import pytest

from minibank.exceptions import CurrencyMismatchError, InvalidAmountError
from minibank.money import Money


# --------------------------------------------------------------------- #
# construction & normalisation
# --------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
    [
        (100, "100.00"),
        ("100", "100.00"),
        ("100.5", "100.50"),
        ("100.555", "100.56"),   # ROUND_HALF_UP
        ("100.005", "100.01"),   # ROUND_HALF_UP, not banker's rounding
        (Decimal("0.1"), "0.10"),
        ("-50.5", "-50.50"),
        (0, "0.00"),
    ],
)
def test_amount_is_quantised_to_two_places(raw, expected):
    assert str(Money(raw).amount) == expected


def test_currency_is_upper_cased():
    assert Money("1", "inr").currency == "INR"


@pytest.mark.parametrize("bad", ["IN", "RUPEE", "1NR", "", "  "])
def test_bad_currency_rejected(bad):
    with pytest.raises(InvalidAmountError):
        Money("1", bad)


@pytest.mark.parametrize("bad", ["abc", "1.2.3", None, [], "1,000"])
def test_unparseable_amount_rejected(bad):
    with pytest.raises(InvalidAmountError):
        Money(bad)


def test_default_currency_is_inr():
    assert Money("1").currency == "INR"


def test_zero_classmethod():
    z = Money.zero("USD")
    assert z.amount == Decimal("0.00") and z.currency == "USD"


@pytest.mark.parametrize("text", ["INR 1234.50", "1234.50 INR", "1234.50"])
def test_parse(text):
    assert Money.parse(text) == Money("1234.50", "INR")


def test_parse_rejects_garbage():
    with pytest.raises(InvalidAmountError):
        Money.parse("a lot of money")


# --------------------------------------------------------------------- #
# immutability & hashing
# --------------------------------------------------------------------- #
def test_is_immutable():
    m = Money("10")
    with pytest.raises(Exception):
        m.amount = Decimal("20")


def test_hashable_and_equal_instances_hash_equally():
    assert hash(Money("10")) == hash(Money("10.00"))
    assert len({Money("10"), Money("10.00"), Money("11")}) == 2


def test_usable_as_dict_key():
    assert {Money("5"): "five"}[Money("5.00")] == "five"


# --------------------------------------------------------------------- #
# arithmetic
# --------------------------------------------------------------------- #
def test_add_and_sub():
    assert Money("100.50") + Money("9.50") == Money("110.00")
    assert Money("100") - Money("150") == Money("-50")


def test_add_returns_new_instance():
    a = Money("10")
    b = a + Money("5")
    assert a == Money("10") and b == Money("15") and a is not b


def test_multiply_by_number():
    assert Money("100") * 3 == Money("300")
    assert 3 * Money("100") == Money("300")
    assert Money("100") * Decimal("0.04") == Money("4.00")


def test_multiplying_two_money_is_not_allowed():
    with pytest.raises(TypeError):
        Money("100") * Money("2")


def test_adding_a_number_is_not_allowed():
    with pytest.raises(TypeError):
        Money("100") + 5


def test_neg_and_abs():
    assert -Money("10") == Money("-10")
    assert abs(Money("-10")) == Money("10")
    assert abs(Money("-10", "USD")).currency == "USD"


def test_currency_mismatch_on_add():
    with pytest.raises(CurrencyMismatchError) as exc:
        Money("1", "INR") + Money("1", "USD")
    assert exc.value.left == "INR" and exc.value.right == "USD"


def test_currency_mismatch_on_sub():
    with pytest.raises(CurrencyMismatchError):
        Money("1", "INR") - Money("1", "USD")


def test_no_float_drift():
    total = sum((Money("0.10") for _ in range(10)), Money.zero())
    assert total == Money("1.00")


# --------------------------------------------------------------------- #
# comparison
# --------------------------------------------------------------------- #
def test_ordering():
    assert Money("100") > Money("99.99")
    assert Money("1") < Money("2") <= Money("2")
    assert sorted([Money("3"), Money("1"), Money("2")]) == [
        Money("1"),
        Money("2"),
        Money("3"),
    ]


def test_ordering_across_currencies_raises():
    with pytest.raises(CurrencyMismatchError):
        Money("1", "INR") < Money("1", "USD")


def test_equality_with_non_money_is_false_not_error():
    assert (Money("0") == 0) is False
    assert (Money("10") != "INR 10.00") is True


def test_predicates_and_truthiness():
    assert Money("1").is_positive and not Money("1").is_negative
    assert Money("-1").is_negative
    assert not Money("0").is_positive and not Money("0").is_negative
    assert bool(Money("0.01")) and not bool(Money("0"))


# --------------------------------------------------------------------- #
# representation
# --------------------------------------------------------------------- #
def test_repr_round_trips():
    m = Money("110.5", "usd")
    assert repr(m) == "Money('110.50', 'USD')"
    assert eval(repr(m)) == m  # noqa: S307 - deliberate round-trip check


def test_str_is_human_readable():
    assert str(Money("1234.5")) == "INR 1234.50"
