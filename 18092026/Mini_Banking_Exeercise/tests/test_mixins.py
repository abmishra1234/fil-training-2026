"""Acceptance tests -- Task 3: mixins and multiple inheritance."""

import json

import pytest

from minibank.exceptions import BankError
from minibank.mixins import AuditableMixin, JSONSerializableMixin


class Widget(JSONSerializableMixin, AuditableMixin):
    """A minimal host class, to prove the mixins work on anything."""

    def __init__(self, name):
        super().__init__()
        self.name = name

    def to_dict(self):
        return {"name": self.name}


class Bare(JSONSerializableMixin):
    """Deliberately does NOT override to_dict."""


def test_mixin_to_dict_must_be_overridden():
    with pytest.raises(NotImplementedError) as exc:
        Bare().to_dict()
    assert "Bare" in str(exc.value)


def test_to_json_uses_host_to_dict():
    assert json.loads(Widget("w").to_json()) == {"name": "w"}


def test_to_json_accepts_indent():
    assert "\n" in Widget("w").to_json(indent=2)


def test_to_json_survives_non_serialisable_values():
    class Odd(JSONSerializableMixin):
        def to_dict(self):
            return {"when": object()}

    json.loads(Odd().to_json())  # must not raise


def test_from_json_parses():
    assert JSONSerializableMixin.from_json('{"a": 1}') == {"a": 1}


def test_from_json_wraps_and_chains_errors():
    with pytest.raises(BankError) as exc:
        JSONSerializableMixin.from_json("{not json")
    assert isinstance(exc.value.__cause__, json.JSONDecodeError)


def test_auditable_cooperates_with_super_init():
    w = Widget("w")           # would fail if AuditableMixin ate the MRO
    assert w.name == "w"
    assert w.audit_trail == ()


def test_audit_appends_in_order():
    w = Widget("w")
    w.audit("first")
    w.audit("second")
    assert len(w.audit_trail) == 2
    assert "first" in w.audit_trail[0]
    assert "second" in w.audit_trail[1]


def test_audit_entries_are_timestamped():
    w = Widget("w")
    w.audit("event")
    assert "T" in w.audit_trail[0]  # ISO-8601 timestamp present


def test_audit_trail_cannot_be_mutated_from_outside():
    w = Widget("w")
    w.audit("one")
    trail = w.audit_trail
    assert isinstance(trail, tuple)
    with pytest.raises(AttributeError):
        trail.append("two")  # type: ignore[attr-defined]
    assert len(w.audit_trail) == 1


def test_mro_order_is_declared_left_to_right():
    names = [c.__name__ for c in Widget.__mro__]
    assert names.index("JSONSerializableMixin") < names.index("AuditableMixin")
