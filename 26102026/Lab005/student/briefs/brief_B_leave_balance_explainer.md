# Brief B · leave-balance-explainer

**Customer:** every FIL employee
**Pain today:** HR gets ~200 "how much leave do I have?" messages a month.

## What users type
* "Can I take 5 days of earned leave from 10 to 14 November?"
* "How many casual leaves do I have left?"
* "Do I have enough sick leave for 3 days next week?"

## Near-misses (your skill must stay quiet)
Actually applying for or cancelling leave (another skill does that) · payroll questions ·
booking travel · general HR policy questions not about the user's own balance

## Rules (this is your Knowledge: put it in references/)
* Leave types: casual, sick, earned. Balances come from the HR connector.
* Requests are counted in **working days**: Monday to Friday, excluding FIL holidays.
* FIL holiday calendar extract (fictional, for training): 2026-11-09, 2026-11-24, 2026-12-25.
* Casual leave: at most 3 consecutive working days per request.
* Earned leave can be taken in half days (0.5).
* An employee may only see **their own** balance.

## Connector (mocked)
`mock_connectors/hr_employees.json` stands in for the HR system: balances in `leave`.

## Output the employee needs
Leave type, working days requested, balance now, balance after;
`Status: ENOUGH | NOT_ENOUGH | NEEDS_INFO` and a one-line `Notes:`.

## Suggested Action
A script that counts working days between two dates (weekends and holidays excluded),
checks the casual-leave rule and compares with the balance.

## Samples (for your quality evals): `samples/leave/`
