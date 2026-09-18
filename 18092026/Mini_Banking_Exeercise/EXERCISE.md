# Mini Banking & Payments System

**Python OOP + Exception Handling — Coding Test**

FIL Fresher Training · 90 minutes · Standard library only

*Focus: Correctness • Clarity • Idiomatic Python • Best Practices*

---

## 1. What you are building

A small banking core: money that cannot lose paise to floating-point error,
accounts that cannot be corrupted from outside, transfers that either happen
completely or not at all, and month-end processing that can be extended without
editing existing code.

The domain is small on purpose. The marks are in **how** you build it.

You are given a starter repository with every module, class, method and
docstring already in place. Each body you must write says
`raise NotImplementedError("TODO")`. **Do not change any signature, class name
or module name** — the test suite imports them by name.

```
mini_banking_exercise/
├── EXERCISE.md              <- this document
├── README.md                <- how to run things
├── requirements.txt
├── pytest.ini
├── demo.py                  <- end-to-end smoke script (not graded)
├── minibank/
│   ├── __init__.py          GIVEN   public API
│   ├── exceptions.py        GIVEN   the full exception hierarchy
│   ├── money.py             TASK 1  value object, operator overloading
│   ├── transaction.py       TASK 2  immutable ledger record (enum GIVEN)
│   ├── mixins.py            TASK 3  multiple inheritance
│   ├── accounts.py          TASK 4  abstract base + two concrete types
│   ├── strategies.py        TASK 5  duck-typed month-end strategies
│   └── bank.py              TASK 6  factory + orchestration
└── tests/                   GIVEN   171 tests. Do not edit.
```

**Definition of done:** `pytest` reports 171 passed.

On a fresh clone 14 already pass (they exercise the given code). The other 157
are yours.

---

## 2. The rules

1. **Standard library only.** `decimal`, `abc`, `enum`, `dataclasses`,
   `functools`, `itertools`, `json`, `re`, `datetime`. Nothing else is needed.
2. **Never `float` for money.** Not once, not "just for the interest rate".
3. **No bare `except:`** and no `except Exception:`. Catch the narrowest
   exception that can actually occur.
4. **Chain wrapped exceptions** with `raise NewError(...) from exc`.
5. **No public mutable state.** No public setter for a balance, ever.
6. **Do not edit `tests/`.** Private helper methods inside the given modules
   are welcome; new public methods are not needed.
7. **Docstrings on every public method.** One line is enough where the
   docstring already given is accurate — keep it.

A solution that passes every test while breaking rules 2, 3 or 5 loses more
marks than a solution that misses a few tests cleanly.

---

## 3. Task 1 — `Money` (20 min)

A value object wrapping `Decimal` + a 3-letter currency code.

### Why

`0.1 + 0.2 != 0.3` in binary floating point. A bank that adds interest in
`float` will not balance. `Decimal` is exact for decimal fractions, which is
what money is.

### Invariants the tests check

| # | Invariant |
|---|-----------|
| I1 | `amount` is a `Decimal` quantised to exactly 2 places, `ROUND_HALF_UP`. `Money("100.005").amount == Decimal("100.01")` |
| I2 | `currency` is 3 uppercase letters. `"inr"` → `"INR"`; `"IN"`, `"RUPEE"`, `"1NR"`, `""` → `InvalidAmountError` |
| I3 | Instances are immutable — assigning to `m.amount` raises |
| I4 | Instances are hashable, and equal instances hash equally |
| I5 | Negative and zero amounts are legal (a checking account can be overdrawn). Only *unparseable input* is rejected |
| I6 | `+`, `-` and ordering across currencies raise `CurrencyMismatchError` |

`Money` does **not** enforce business rules. "You cannot deposit ₹0" is an
*account* rule, not a *Money* rule. Keeping validation at the right layer is
part of the grade.

### Constructor behaviour

Accepts `int`, `str`, `Decimal`. `float` is accepted only by going through
`str(value)` first — `Decimal(0.1)` is `0.1000000000000000055511151231257827`,
which defeats the point. Anything unparseable raises `InvalidAmountError`
chained from the `decimal.InvalidOperation`.

### Operators

| Expression | Result |
|---|---|
| `Money("100.50") + Money("9.50")` | `Money('110.00', 'INR')` |
| `Money("100") - Money("150")` | `Money('-50.00', 'INR')` |
| `Money("100") * 3`, `3 * Money("100")` | `Money('300.00', 'INR')` |
| `Money("100") * Decimal("0.04")` | `Money('4.00', 'INR')` |
| `Money("100") * Money("2")` | `TypeError` |
| `Money("100") + 5` | `TypeError` |
| `-Money("10")`, `abs(Money("-10"))` | `Money('-10.00')`, `Money('10.00')` |
| `Money("0") == 0` | `False` — never an exception |
| `Money("1", "INR") < Money("1", "USD")` | `CurrencyMismatchError` |
| `repr(Money("110.5", "usd"))` | `"Money('110.50', 'USD')"` |
| `str(Money("1234.5"))` | `"INR 1234.50"` |
| `bool(Money("0"))` | `False` |

### Three things that separate a good answer from a passing one

* **Return `NotImplemented`, do not raise**, when the other operand is the
  wrong type. That is the protocol: Python then tries the reflected operation
  and raises `TypeError` itself. Raising `TypeError` directly breaks
  interoperability with types you have never heard of.
* **Implement `__lt__` only** and decorate the class with
  `functools.total_ordering` to get `<=`, `>`, `>=`. Writing all four by hand
  is four chances to get a sign wrong.
* **Use `@dataclass(frozen=True)`** and normalise in `__post_init__` via
  `object.__setattr__`. That is the idiomatic way to have an immutable type
  that still cleans its inputs.

---

## 4. Task 2 — `Transaction` (10 min)

An immutable, hashable record of something that happened.

`TransactionType` is **given**: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_IN`,
`TRANSFER_OUT`, `INTEREST`, `FEE`, with an `is_credit` property. Use it.

### Fields

| Field | Notes |
|---|---|
| `txn_id` | Unique; generated by the account, not the caller |
| `type` | A `TransactionType` member. Anything else → `InvalidAmountError` |
| `amount` | Always a **positive** `Money`. Direction lives in `type`, not in the sign |
| `balance_after` | Balance once this entry was applied — makes the ledger auditable without replaying it |
| `description` | Free text, may be empty |
| `timestamp` | Defaults to timezone-**aware** UTC. A naive datetime in a financial record is a bug |

### Required behaviour

* `signed_amount` → `+amount` for credits, `-amount` for debits.
* `__hash__` and `__eq__` both key on `txn_id` alone. Two objects with the same
  id are the same record, whatever else differs — this is what lets you drop a
  replayed batch into a `set` and de-duplicate it.
* `__repr__` contains the id, the type name and the amount.
* `to_dict()` returns **exactly** these keys:

```python
{"txn_id": str, "type": str, "amount": str, "currency": str,
 "balance_after": str, "description": str, "timestamp": str}
```

`amount` and `balance_after` are plain decimal strings (`"100.00"`, no
currency prefix); `timestamp` is `datetime.isoformat()`.

---

## 5. Task 3 — Mixins (10 min)

Two mixins, each adding exactly one capability.

### `JSONSerializableMixin`

| Method | Contract |
|---|---|
| `to_dict()` | Hook for the host class. The mixin's own version raises `NotImplementedError` naming the class: `"SavingsAccount must implement to_dict()"` |
| `to_json(*, indent=None)` | `json.dumps` of `to_dict()`, with `default=str` so `Decimal` and `datetime` do not blow up |
| `from_json(payload)` (classmethod) | Returns a dict. Invalid JSON → `BankError` **chained** from the `json.JSONDecodeError` |

### `AuditableMixin`

An append-only trail of human-readable event strings. Deliberately separate
from the transaction ledger: the ledger records **money**, the trail records
**events** ("opened", "closed", "withdrawal rejected: insufficient funds").

| Member | Contract |
|---|---|
| `__init__(*args, **kwargs)` | Create the private list, then **`super().__init__(*args, **kwargs)`** |
| `audit(message)` | Append an ISO-timestamped entry |
| `audit_trail` | Read-only **tuple** snapshot |

### The one thing that is actually being tested

`Account` is declared as:

```python
class Account(JSONSerializableMixin, AuditableMixin, ABC):
```

so `Account.__mro__` is
`Account → JSONSerializableMixin → AuditableMixin → ABC → object`.

If `AuditableMixin.__init__` forgets `super().__init__(...)`, the chain stops
there and everything after it is silently skipped. That is *the* classic
multiple-inheritance bug, it is why cooperative `super()` exists, and you
should be able to explain it at the review. Print `Account.__mro__` and look.

---

## 6. Task 4 — The account hierarchy (25 min)

```
Account (ABC, + JSONSerializableMixin, AuditableMixin)
  ├── InterestBearingAccount (ABC)      adds annual_interest_rate + accrual
  │     └── SavingsAccount              minimum balance, earns interest
  └── CheckingAccount                   overdraft allowed, monthly fee
```

`InterestBearingAccount` exists to prove you can put an abstract class
*between* levels rather than pushing interest onto every account. A checking
account must **not** have an `accrue_monthly_interest` method at all.

### Encapsulation (graded hard)

`_balance` and `_ledger` are private. There is **no** public setter. The only
things that change the balance are `deposit`, `withdraw`, `transfer_out`,
`transfer_in` and the protected `_apply` used for interest and fees.

* `account.balance` → read-only property. `account.balance = ...` must raise.
* `account.ledger` → a **tuple**, so a caller cannot append to the real list.
* No public attributes in `vars(account)` at all. A test asserts this.

### The abstract contract

Three members every concrete subclass must supply:

| Member | Savings | Checking |
|---|---|---|
| `account_type` | `"SAVINGS"` | `"CHECKING"` |
| `withdrawable_balance` | `balance - minimum_balance`, floored at zero | `balance + overdraft_limit` |
| `_insufficient_funds_error(requested)` | `InsufficientFundsError` | `OverdraftLimitExceededError` (carries `limit`) |

**`withdraw` is written once, in the base class, in terms of
`withdrawable_balance`.** That is the polymorphism this task is testing. A test
asserts `withdraw` does not appear in either subclass's `__dict__`. Same idea
for `deposit`, `close`, `__len__`, `__repr__`, `to_dict`.

### Money movement

`_validate(amount)` is the shared guard. It raises **in this order**:

1. `AccountClosedError` — the account is closed
2. `InvalidAmountError` — not a `Money` instance
3. `CurrencyMismatchError` — wrong currency
4. `InvalidAmountError` — not strictly positive

`_apply(txn_type, amount, description)` is the single place `_balance` is
written. Credits add, debits subtract; it appends the `Transaction` and returns
it. Everything else goes through it.

| Method | Ledger entry | Extra rule |
|---|---|---|
| `deposit` | `DEPOSIT` | — |
| `withdraw` | `WITHDRAWAL` | refuse if `amount > withdrawable_balance` |
| `transfer_out` | `TRANSFER_OUT` | same limit check as `withdraw` |
| `transfer_in` | `TRANSFER_IN` | same guard as `deposit` |

`withdraw` and `transfer_out` share the limit check — extract one private
helper. Copy-pasting the body costs marks.

**A refused withdrawal changes nothing.** Not the balance, not the ledger. It
*does* write an audit entry containing the word "reject", then raises
`self._insufficient_funds_error(amount)`.

### Defaults

| | Savings | Checking |
|---|---|---|
| minimum balance | `Money("1000")` | — |
| overdraft limit | — | `Money("5000")` |
| annual interest | `Decimal("0.04")` | none |
| monthly fee | `Money("0")` | `Money("150")` |

All overridable per account via constructor keywords. Negative values →
`InvalidAmountError`.

### Interest

```
monthly_interest() = balance * annual_interest_rate / 12
```

Return `Money.zero(currency)` when the balance is not positive — **never pay
interest on an overdrawn account**. Rounding is whatever `Money` already does.

`accrue_monthly_interest()` credits it and returns the `INTEREST` transaction,
or `None` when the interest is zero or the account is closed. No zero-value
ledger noise.

Worked example: balance ₹12,000 at 12% p.a. → `12000 × 0.12 / 12` = **₹120.00**,
new balance ₹12,120.00.

### Lifecycle

`close()` is idempotent, writes an audit entry, and may leave a non-zero
balance (the Bank decides policy). After closing, `deposit` and `withdraw`
raise `AccountClosedError`.

### Dunders

`__len__` (transaction count), `__iter__` (over the ledger), `__repr__`
(`SavingsAccount(id='SB0001', owner='Asha', balance=INR 5000.00)` — use
`type(self).__name__` so subclasses need no override), `__eq__`/`__hash__`
(identity is the `account_id`, so a savings and a checking account with the
same id are "equal" — ids are unique in practice).

### `to_dict`

Base keys:

```python
{"account_id", "account_type", "owner", "currency",
 "balance", "is_closed", "transactions"}
```

`balance` is a decimal string; `transactions` is a list of transaction dicts.
Savings adds `minimum_balance` and `interest_rate`; Checking adds
`overdraft_limit` and `monthly_fee` — all strings. **Call `super().to_dict()`
and add to it.** Rebuilding the common keys costs marks.

---

## 7. Task 5 — Month-end strategies (10 min)

A strategy is **any** object shaped like this:

```python
class SomeStrategy:
    name: str
    def apply(self, account) -> list[Transaction]: ...
```

There is deliberately **no abstract base class**. That is the point: Python
does not need one. `Bank.monthly_process` validates the *shape* with
`getattr`/`callable`, not the *type*.

Every `apply` must return a list (possibly empty) of the transactions it
created, skip closed accounts, and never raise for a normal no-op.

| Strategy | `name` | Behaviour |
|---|---|---|
| `InterestStrategy` | `"interest"` | Accrue interest if the account is an `InterestBearingAccount` and open. Anything else → `[]` |
| `MaintenanceFeeStrategy` | `"maintenance-fee"` | Charge `account.monthly_fee()`. Fee ≤ 0 → `[]`. Charge it **through `account.withdraw`** so the account's own limits apply. If refused, catch `InsufficientFundsError` *specifically*, audit it, return `[]` |
| `CompositeStrategy` | children joined with `"+"` | Run children in order, concatenate results. Reject an object with no `apply` at construction time with `TypeError` |

`InterestStrategy` is the one place an explicit `isinstance` check is the right
call, because the capability *is* defined by the abstract class. Everywhere
else, ask for behaviour, not for a type.

`CompositeStrategy` is composition beating inheritance: no strategy subclasses
another, they are held in a list, and they nest.

Why route the fee through `withdraw` rather than `_apply`? Because a fee must
not be able to break a rule the account guarantees. A ₹150 fee on a checking
account with ₹100 and a ₹40 overdraft limit must be **refused**, not forced
through. A test checks exactly that.

---

## 8. Task 6 — The `Bank` orchestrator (15 min)

The Bank never touches `account._balance`. It only calls the public account
API. That is what makes the encapsulation real rather than decorative.

### Factory

`ACCOUNT_TYPES` is a class-level registry: `{"SAVINGS": SavingsAccount,
"CHECKING": CheckingAccount}`.

```python
bank.open_account("CHECKING", "Ravi", Money("2000"),
                  overdraft_limit=Money("10000"))
```

* `kind` matched case-insensitively; unknown → `UnknownAccountTypeError`.
* `**kwargs` forwarded to the concrete class — so the Bank does not need to
  know what a checking account is.
* Ids generated per kind: `SB0001`, `SB0002`, `CH0001`, …
* Opening balance in a foreign currency → `CurrencyMismatchError`.

`register_account_type(kind, cls)` (a `@classmethod`) adds a type. **Adding a
new account type must not require editing `open_account`** — that is the
open/closed principle, and a test registers a new subclass to prove it. A
non-`Account` class → `TypeError`.

`validate_account_id(id)` is a `@staticmethod` (it needs neither instance nor
class state — that *is* the lesson). Valid shape: two letters then four
digits. Returns it upper-cased; anything else → `ValueError`.

### Transfers — atomicity

```python
debit, credit = bank.transfer(from_id, to_id, amount, description)
```

| Situation | Result |
|---|---|
| `from_id == to_id` | `TransferError`, nothing recorded |
| either account closed | `AccountClosedError`, nothing recorded |
| currencies differ | `CurrencyMismatchError`, nothing recorded |
| source cannot afford it | the `InsufficientFundsError` from the debit propagates unchanged, nothing recorded anywhere |
| debit succeeds, credit then fails | **put the money back** with a compensating `transfer_in` on the source, then `raise TransferError(...) from exc` |

A passing transfer conserves `total_assets()` exactly. The test for the last
row monkeypatches the destination's `transfer_in` to explode and then asserts
the source balance is untouched — this is the one place in the exercise where
you must think like someone who has seen a half-completed transfer in
production.

### Reporting

`total_assets()` sums the balances of all **open** accounts in the bank's base
currency; accounts in another currency are skipped (no FX here). Overdrawn
accounts count as negative. Empty bank → `Money.zero(currency)`. Build the sum
out of `Money.__add__` — do not reach for `Decimal`.

### `monthly_process(strategy)`

1. Validate the shape: callable `apply` plus a `name`, else `TypeError` naming
   what was missing. Do **not** require a base class.
2. Return `{account_id: [transactions created]}`, including empty lists.
3. A `BankError` from one account must not abort the run: record it in that
   account's audit trail and carry on. One account's bad month is not the
   bank's bad month.

### Dunders

`__len__`, `__contains__` (accepts an id string *or* an `Account`), `__iter__`,
`__getitem__` (same as `get_account`), `__repr__`
(`Bank(name='FIL Bank', accounts=3, assets=INR 12500.00)`), and `to_dict` with
keys `{"name", "currency", "total_assets", "accounts"}`.

---

## 9. The exception hierarchy (given — read it)

```
BankError
├── CurrencyMismatchError            .left  .right
├── InvalidAmountError (+ValueError) .value .reason
├── InsufficientFundsError           .requested .available
│   └── OverdraftLimitExceededError  + .limit
├── AccountError
│   ├── AccountNotFoundError (+KeyError)  .account_id
│   ├── DuplicateAccountError             .account_id
│   └── AccountClosedError                .account_id
├── TransferError
└── UnknownAccountTypeError (+ValueError) .kind
```

Three design decisions worth understanding, because you will be asked:

* **Everything derives from `BankError`**, so a caller can write
  `except BankError` and be sure. A library that raises bare `ValueError` from
  six places is untestable.
* **`OverdraftLimitExceededError` subclasses `InsufficientFundsError`.**
  Callers that only care about "not enough money" keep working; callers that
  care about the overdraft specifically can catch the narrower type. Design
  your hierarchy for the `except` clauses people will actually write.
* **Multiple inheritance from builtins** (`InvalidAmountError(BankError,
  ValueError)`) lets generic numeric code keep working while domain code stays
  specific. Use it sparingly and on purpose.

Exceptions carry **data**, not just a message: `exc.available` is what lets a
caller tell the customer how much they *can* withdraw.

---

## 10. Marking scheme (100)

| Area | Marks | What earns them |
|---|---|---|
| Tests passing | 40 | Proportional. 171/171 = 40 |
| Encapsulation | 10 | Private state, read-only properties, tuple snapshots, no leaked internals |
| Abstraction & polymorphism | 10 | `withdraw` written once; no `isinstance` chains where polymorphism belongs; the abstract mid-layer used properly |
| Operator overloading | 10 | `NotImplemented` not `TypeError`; `total_ordering`; consistent `__eq__`/`__hash__` |
| Exception handling | 10 | Narrow `except`, `raise ... from`, no bare `except`, exceptions carry data, atomic transfer |
| Idiomatic Python | 10 | `Decimal` throughout, dataclasses, enums, `@property`/`@classmethod`/`@staticmethod` used for the right reasons, no duplicated logic |
| Clarity | 10 | Docstrings, readable names, short methods, `NOTES.md` |

Automatic deductions: any `float` in a money path (−10); any bare `except:` or
`except Exception:` (−10); a public balance setter (−10); editing `tests/` (−20).

---

## 11. Timeboxing

| Minutes | Do this |
|---|---|
| 0–5 | Read this document. Run `pytest` and watch it fail. Skim `exceptions.py` |
| 5–25 | Task 1 — `pytest tests/test_money.py` green |
| 25–35 | Task 2 |
| 35–45 | Task 3 |
| 45–70 | Task 4 (the big one) |
| 70–80 | Task 5 |
| 80–90 | Task 6, then `python demo.py`, then `NOTES.md` |

If you fall behind, **keep what you have green**. A clean solution to five
tasks beats six broken ones. Write `NOTES.md` even if you are out of time —
naming what you would do next is worth more than a half-finished module.

---

## 12. Submitting

The repository, plus a short `NOTES.md`:

1. One design decision you made and the alternative you rejected.
2. Where you used composition instead of inheritance, and why.
3. Anything unfinished, and what you would do next.

---

## Appendix A — Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest                          # all 171
pytest tests/test_money.py      # one task
pytest -x -q                    # stop at first failure
pytest -k overdraft             # one behaviour
pytest --lf                     # only what failed last time

python demo.py                  # end-to-end smoke test
```

## Appendix B — Worked end-to-end example

```python
from decimal import Decimal
from minibank import Bank, Money, InterestStrategy, MaintenanceFeeStrategy, CompositeStrategy

bank = Bank("FIL Bank")
savings  = bank.open_account("SAVINGS",  "Asha", Money("50000"), interest_rate=Decimal("0.06"))
checking = bank.open_account("CHECKING", "Ravi", Money("8000"))

bank.transfer(savings.account_id, checking.account_id, Money("12000"), "rent")
# savings INR 38000.00    checking INR 20000.00

savings.withdraw(Money("999999"))
# InsufficientFundsError: requested INR 999999.00, only INR 37000.00 available
#   (50000 - 12000 - 1000 minimum balance)

checking.withdraw(Money("999999"))
# OverdraftLimitExceededError: requested INR 999999.00, only INR 25000.00 available
#   (20000 balance + 5000 overdraft limit)

bank.monthly_process(CompositeStrategy(InterestStrategy(), MaintenanceFeeStrategy()))
# {'SB0001': [Transaction(T…, INTEREST, INR 190.00)],     38000 × 0.06/12
#  'CH0001': [Transaction(T…, WITHDRAWAL, INR 150.00)]}   the maintenance fee

bank.total_assets()      # Money('58040.00', 'INR')
print(savings.statement())
```

## Appendix C — Concept checklist

Tick these off before you submit; each one is somewhere in the tests.

* **Encapsulation** — private attributes · read-only properties · defensive
  copies (`tuple`) · no public setters
* **Inheritance** — abstract base with `ABC`/`@abstractmethod` · an abstract
  mid-layer · `super()` used for real, including in `to_dict`
* **Polymorphism** — one `withdraw` for every account type · duck-typed
  strategies · an `__eq__` that refuses to guess
* **Abstraction** — behaviour named at the level it belongs to
  (`withdrawable_balance`, `_insufficient_funds_error`)
* **Operator overloading** — `__add__` `__sub__` `__mul__` `__rmul__`
  `__neg__` `__abs__` `__eq__` `__lt__` `__hash__` `__repr__` `__str__`
  `__bool__` `__len__` `__iter__` `__contains__` `__getitem__`
* **Multiple inheritance** — two mixins · a readable MRO · cooperative
  `super().__init__`
* **Decorators** — `@property` · `@classmethod` (factory registry) ·
  `@staticmethod` (pure validator) · `@abstractmethod` ·
  `@dataclass(frozen=True)` · `@functools.total_ordering`
* **Exceptions** — a rooted hierarchy · data on the exception · narrow
  `except` · `raise ... from` · a compensating rollback
