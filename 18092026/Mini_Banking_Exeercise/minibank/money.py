"""Task 1 -- the ``Money`` value object.

Implement every method marked ``TODO``. Do not change any signature.

WHY A VALUE OBJECT?
-------------------
``float`` cannot represent 0.10 exactly, so ``0.1 + 0.2 != 0.3``. Banking code
must never use float for amounts. ``Money`` wraps ``decimal.Decimal`` and a
currency code, and behaves like a number through operator overloading.

INVARIANTS you must enforce (the tests check all of them):
  I1. ``amount`` is always a ``Decimal`` quantized to exactly 2 decimal places
      using ``ROUND_HALF_UP``.  Money("10.005") -> Decimal("10.01").
  I2. ``currency`` is always a 3-letter UPPERCASE code. "inr" -> "INR".
      Anything that is not 3 alphabetic characters -> InvalidAmountError.
  I3. Instances are IMMUTABLE. Every operator returns a NEW Money.
      Assigning to ``m.amount`` must raise. (Hint: ``@dataclass(frozen=True)``
      plus ``object.__setattr__`` inside ``__post_init__``.)
  I4. Instances are HASHABLE, and equal instances hash equally.
  I5. Money may be negative or zero (a checking account can go overdrawn).
      It is ACCOUNTS that reject non-positive deposits, not Money itself.
      The only thing Money rejects is input it cannot parse.
  I6. Mixing currencies in +, -, or an ordering comparison raises
      CurrencyMismatchError.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Union

from minibank.exceptions import CurrencyMismatchError, InvalidAmountError

#: Anything accepted as an amount by the constructor.
Numeric = Union[int, str, Decimal, "Money"]

#: Number of decimal places every Money is stored with.
PLACES = Decimal("0.01")

DEFAULT_CURRENCY = "INR"


@dataclass(frozen=True, order=False)
class Money:
    """An immutable amount of a single currency.

    Examples
    --------
    >>> Money("100.50") + Money("9.50")
    Money('110.00', 'INR')
    >>> Money(100) * 3
    Money('300.00', 'INR')
    >>> Money("100") > Money("99.99")
    True
    >>> str(Money("1234.5"))
    'INR 1234.50'
    """

    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    # ------------------------------------------------------------------ #
    # construction
    # ------------------------------------------------------------------ #
    def __post_init__(self) -> None:
        """Normalise and validate the fields (enforces I1, I2, I3).

        Accept ``int``, ``str``, ``Decimal`` (and ``float`` ONLY by converting
        ``str(value)``, never ``Decimal(float)``). Reject anything unparseable
        with ``InvalidAmountError``, chaining the ``decimal.InvalidOperation``.

        Because the dataclass is frozen, write the normalised values with
        ``object.__setattr__(self, "amount", ...)``.
        """
        raise NotImplementedError("TODO: normalise amount and currency")

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        """Return ``Money(0, currency)``. Use this instead of ``Money(0)``
        wherever the currency must be preserved."""
        raise NotImplementedError("TODO")

    @classmethod
    def parse(cls, text: str) -> "Money":
        """Parse ``"INR 1234.50"`` or ``"1234.50 INR"`` or ``"1234.50"``.

        Raise ``InvalidAmountError`` if the text has neither shape.
        """
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _check_currency(self, other: "Money") -> None:
        """Raise ``CurrencyMismatchError`` if ``other`` is a different currency."""
        raise NotImplementedError("TODO")

    @property
    def is_positive(self) -> bool:
        """True when the amount is strictly greater than zero."""
        raise NotImplementedError("TODO")

    @property
    def is_negative(self) -> bool:
        """True when the amount is strictly less than zero."""
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # arithmetic -- MANDATORY dunders
    # ------------------------------------------------------------------ #
    def __add__(self, other: "Money") -> "Money":
        """Money + Money -> Money. Different currency -> CurrencyMismatchError.
        A non-Money operand must return ``NotImplemented`` (NOT raise), so that
        Python can fall back to the other operand's ``__radd__``."""
        raise NotImplementedError("TODO")

    def __sub__(self, other: "Money") -> "Money":
        """Money - Money -> Money. Same rules as ``__add__``."""
        raise NotImplementedError("TODO")

    def __mul__(self, factor: Union[int, Decimal]) -> "Money":
        """Money * number -> Money (used for interest and fees).

        Multiplying two Money values is meaningless -> return ``NotImplemented``.
        ``float`` factors must be converted via ``str`` to stay exact.
        """
        raise NotImplementedError("TODO")

    def __rmul__(self, factor: Union[int, Decimal]) -> "Money":
        """Make ``3 * Money(...)`` work too."""
        raise NotImplementedError("TODO")

    def __neg__(self) -> "Money":
        """Unary minus."""
        raise NotImplementedError("TODO")

    def __abs__(self) -> "Money":
        """Absolute value, currency preserved."""
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # equality, ordering, hashing -- MANDATORY dunders
    # ------------------------------------------------------------------ #
    def __eq__(self, other: Any) -> bool:
        """Equal iff same currency AND same amount.

        Comparing against a non-Money returns ``False`` (never raises):
        ``Money("0") == 0`` is ``False``.
        """
        raise NotImplementedError("TODO")

    def __hash__(self) -> int:
        """Hash of ``(amount, currency)`` so equal instances hash equally."""
        raise NotImplementedError("TODO")

    def __lt__(self, other: "Money") -> bool:
        """Order by amount, after a currency check.

        Implement ``__lt__`` only and decorate the class with
        ``functools.total_ordering`` to get ``<=``, ``>``, ``>=`` for free --
        that is the idiomatic answer and what the reviewer looks for.
        """
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # representation -- MANDATORY dunders
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        """Unambiguous, round-trippable: ``Money('110.00', 'INR')``."""
        raise NotImplementedError("TODO")

    def __str__(self) -> str:
        """Human readable: ``INR 110.00``."""
        raise NotImplementedError("TODO")

    def __bool__(self) -> bool:
        """Falsey only when the amount is exactly zero."""
        raise NotImplementedError("TODO")
