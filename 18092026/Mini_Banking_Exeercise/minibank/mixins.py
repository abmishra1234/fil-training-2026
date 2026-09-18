"""Task 3 -- mixins and multiple inheritance.

A mixin adds ONE capability and is never instantiated on its own. It does not
define ``__init__`` state that clashes with the host class, and it always calls
``super().__init__(*args, **kwargs)`` so cooperative multiple inheritance works.

``Account`` will be declared as::

    class Account(JSONSerializableMixin, AuditableMixin, ABC):

so its MRO is  Account -> JSONSerializableMixin -> AuditableMixin -> ABC -> object.
You should be able to explain that MRO out loud; ``Account.__mro__`` prints it.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class JSONSerializableMixin:
    """Gives a class ``to_dict`` / ``to_json`` / ``from_json`` behaviour.

    The mixin does NOT know what the host class's fields are: the host must
    override :meth:`to_dict`. ``to_json`` is written once, here.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Subclass hook. The mixin's own version must raise
        ``NotImplementedError`` with a message naming the class, e.g.
        ``"SavingsAccount must implement to_dict()"``."""
        raise NotImplementedError("TODO")

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialise ``self.to_dict()``.

        Must handle values that ``json`` cannot encode natively by passing
        ``default=str``, so ``Decimal`` and ``datetime`` do not blow up.
        """
        raise NotImplementedError("TODO")

    @classmethod
    def from_json(cls, payload: str) -> Dict[str, Any]:
        """Parse JSON text into a plain dict.

        Invalid JSON must be re-raised as ``BankError`` chained from the
        ``json.JSONDecodeError`` -- demonstrate ``raise ... from exc``.
        """
        raise NotImplementedError("TODO")


class AuditableMixin:
    """Gives a class an append-only audit trail of human-readable strings.

    Separate from the transaction ledger on purpose: the ledger records money,
    the audit trail records EVENTS ("account opened", "account closed",
    "withdrawal rejected: insufficient funds").
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create the private log, then hand control up the MRO.

        MUST call ``super().__init__(*args, **kwargs)`` -- forgetting this is
        the classic multiple-inheritance bug and costs marks.
        """
        raise NotImplementedError("TODO")

    def audit(self, message: str) -> None:
        """Append a timestamped entry, e.g. ``"2025-09-22T11:03:15+00:00 | opened"``."""
        raise NotImplementedError("TODO")

    @property
    def audit_trail(self) -> tuple:
        """Read-only snapshot of the log.

        Must return a ``tuple``, so a caller cannot mutate the internal list.
        """
        raise NotImplementedError("TODO")
