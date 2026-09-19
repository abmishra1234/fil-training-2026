# Implementation Notes

## Design decision

All account debits share the private `_debit` helper in `Account`. It validates
the amount, applies the concrete account's `withdrawable_balance` policy, and
then creates either a withdrawal or transfer transaction. The rejected
alternative was duplicating this logic in `withdraw`, `transfer_out`, and each
account subclass, which would make validation order and audit behavior drift.

## Composition instead of inheritance

`CompositeStrategy` stores child strategy objects and invokes them in order.
The strategies do not inherit from one another: any object with the required
`name` and callable `apply` behavior can participate. This keeps month-end
processing extensible without coupling unrelated strategies.

## Completion status

All six tasks are implemented. The complete 171-test suite passes, and
`python demo.py` runs successfully. No known work is unfinished.
