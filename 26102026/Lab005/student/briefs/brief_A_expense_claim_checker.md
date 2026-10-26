# Brief A · expense-claim-checker

**Customer:** FIL managers who approve travel expense claims
**Pain today:** managers approve claims without checking the policy; Finance rejects ~1 in 5 later.

## What users type
* "Can you check Aarav's Bengaluru claim before I approve it?"
* "How much of this hotel and cab claim will be reimbursed?"
* "Which items in my Mumbai trip expenses will get rejected?"

## Near-misses (your skill must stay quiet)
Booking travel · applying for leave · payroll and salary questions · vendor invoices

## Policy (this is your Knowledge: put it in references/)
| Grade | Meals per day | Hotel per night tier-1 | Hotel per night tier-2 | Local travel per day |
|---|---|---|---|---|
| L1 | 600 | 4,000 | 3,000 | 1,500 |
| L2 | 900 | 6,000 | 4,500 | 1,500 |
| L3 | 1,200 | 8,000 | 6,000 | 2,500 |

* Limits are per calendar day per category; above the limit is not reimbursed (the rest is).
* Tier-1 cities: Mumbai, Delhi NCR (Delhi, Gurugram, Noida), Bengaluru, Chennai, Hyderabad, Kolkata, Pune.
* Receipt required for any item above INR 500.
* Items older than 30 days at submission are not reimbursed.
* Never reimbursable: alcohol, fines and penalties, personal entertainment.

## Connector (mocked)
`mock_connectors/hr_employees.json` stands in for the HR system: employee ID → name, grade.

## Output the manager needs
Claimed, approvable and not-reimbursable amounts; each problem item with the reason;
`Status: APPROVE | PARTIAL | REJECT | NEEDS_INFO` and a one-line `Notes:`.

## Suggested Action
A script that takes the claim as JSON, looks up the grade, applies limits, receipts and
deadlines with Decimal maths, and returns per-item verdicts plus the status.

## Samples (for your quality evals): `samples/expense/`
