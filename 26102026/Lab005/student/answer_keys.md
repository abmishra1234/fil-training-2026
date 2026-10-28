# Capstone answer keys (all samples)

## Brief A · expense-claim-checker (`samples/expense/`)
Verified with the reference `scripts/policy_check.py`.

| Sample | Employee | Claimed | Approvable | Status | Findings |
|---|---|---|---|---|---|
| claim_01_neha | FIL2088 Neha Verma, L2, Mumbai (tier-1) | 8,270.00 | 8,270.00 | **APPROVE** | none (₹420 lunch without receipt is fine: ≤ ₹500) |
| claim_02_aarav | FIL1023 Aarav Sharma, L1, Bengaluru (tier-1) | 7,550.00 | 4,600.00 | **PARTIAL** | hotel 5,200 → 4,000 OVER_LIMIT; meals 450+300=750 → 600 OVER_LIMIT; beer 900 NOT_ALLOWED; auto+metro 700 NO_RECEIPT |
| claim_03_unknown | FIL9999 (not in HR) | 3,300.00 | 0.00 | **NEEDS_INFO** | unknown employee |

## Brief B · leave-balance-explainer (`samples/leave/`)

| Sample | Employee | Request | Balance | Status | Notes |
|---|---|---|---|---|---|
| q1_aarav | FIL1023 | Earned, 10–14 Nov 2026 | 11.5 | **ENOUGH** | 4 working days (Sat 14 Nov excluded), 7.5 left. The user said 5: good skills correct this politely. |
| q2_priya | FIL1150 | Casual, "next Friday and Monday" (2 days) | 0 | **NOT_ENOUGH** | Relative dates: a good skill asks for exact dates or resolves them from today's date; either way 0 casual left. |
| q3_noid | unknown | Sick, 3 days | — | **NEEDS_INFO** | No employee ID. Must not guess. |

## Brief C · meeting-minutes-formatter (`samples/minutes/`)

| Sample | Event | Status | Why |
|---|---|---|---|
| notes_01_complete | EVT-7781, 21 Oct 2026, 4 attendees | **COMPLETE** | 3 actions, each with an attendee owner and a date after the meeting |
| notes_02_missing_owner | EVT-7790, 23 Oct 2026 (Fri) | **MISSING_OWNERS** | "prepare 3 quality cases by Sunday": no owner, no date; "someone to book the demo room": no owner, no date. Priya's action is fine. |
| notes_03_no_event | none | **NEEDS_INFO** | No event ID, so attendees cannot be checked; "follow up on Thursday" has no owner either. |

## Reference trigger set for Brief A (with decoys)
3 positives (check a claim before approval · how much is reimbursed · which items get
rejected) and 3 near-misses (book a hotel → travel-booking-assistant · salary question →
payroll-query-answerer · vendor invoice → invoice-summary-formatter). Score **6/6**.
