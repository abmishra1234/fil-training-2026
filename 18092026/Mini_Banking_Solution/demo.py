"""Smoke demo -- run this once your implementation is working.

    python demo.py

It is NOT part of the grading, but if this script runs end to end you have
almost certainly wired the pieces together correctly.
"""

from decimal import Decimal

from minibank import (
    Bank,
    CompositeStrategy,
    InsufficientFundsError,
    InterestStrategy,
    MaintenanceFeeStrategy,
    Money,
    OverdraftLimitExceededError,
)


def main() -> None:
    bank = Bank("FIL Bank")

    savings = bank.open_account(
        "SAVINGS", "Asha Verma", Money("50000"), interest_rate=Decimal("0.06")
    )
    checking = bank.open_account("CHECKING", "Ravi Kumar", Money("8000"))

    print(bank)
    print(savings)
    print(checking)

    bank.transfer(savings.account_id, checking.account_id, Money("12000"), "rent")
    print("\nafter transfer:", savings.balance, checking.balance)

    try:
        savings.withdraw(Money("999999"))
    except InsufficientFundsError as exc:
        print("refused:", exc, "| withdrawable was", exc.available)

    try:
        checking.withdraw(Money("999999"))
    except OverdraftLimitExceededError as exc:
        print("refused:", exc, "| limit", exc.limit)

    month_end = CompositeStrategy(InterestStrategy(), MaintenanceFeeStrategy())
    print("\nrunning month end:", month_end.name)
    for account_id, txns in bank.monthly_process(month_end).items():
        print(f"  {account_id}: {[t.type.value for t in txns]}")

    print("\ntotal assets:", bank.total_assets())
    print("\n" + savings.statement())
    print("\naudit trail (savings):")
    for entry in savings.audit_trail:
        print("  " + entry)


if __name__ == "__main__":
    main()
