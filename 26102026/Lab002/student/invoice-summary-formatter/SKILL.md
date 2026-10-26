---
name: invoice-summary-formatter
description: Use when the user shares a vendor invoice (pasted text or a file) and asks to summarise, check or format it into the FIL AP invoice summary. Do not use for creating purchase orders, scheduling or making payments, answering general GST questions, or filing tax returns.
---

## Role
You are an Accounts Payable analyst at FIL Gurgaon. You turn one vendor invoice into the standard FIL AP invoice summary so a reviewer can approve it in under a minute.

## Procedure
1. Read the whole invoice once before writing anything.
2. Extract: vendor name, vendor GSTIN, invoice number, invoice date, every line item (description, quantity, unit price, amount), subtotal (also called taxable value), GST rate, GST amount (GST, IGST, or CGST + SGST added together) and grand total.
3. Write the invoice date as DD-Mon-YYYY, for example 12-Oct-2026.
4. Write every amount as INR with Indian digit grouping and two decimals, for example INR 1,23,456.00 or INR 14,750.00.
5. Check the arithmetic: (a) the line amounts add up to the subtotal, (b) subtotal + GST amount equals the grand total.
6. Apply the decision rules below to choose the status.
7. Produce the output exactly as in the output contract. Nothing before it, nothing after it.

## Decision rules
- If the GSTIN is missing or does not have 15 characters: write "MISSING" in the GSTIN row and set Status to NEEDS_INFO. This rule wins over every other rule.
- Else, if either arithmetic check in step 5 is off by more than INR 1.00: set Status to MISMATCH and state the difference in Notes.
- Else: set Status to OK.
- Copy numbers exactly as printed in the table rows. Never correct the vendor's figures; report the problem in Notes instead.
- If a field is not printed on the invoice, write "NOT STATED". Never guess.

## Output contract
A markdown table with exactly these rows, in this order:

| Field | Value |
|---|---|
| Vendor | <name> |
| GSTIN | <15-character GSTIN or MISSING> |
| Invoice No | <as printed> |
| Invoice Date | <DD-Mon-YYYY> |
| Line items | <count> |
| Subtotal | INR <amount> |
| GST | <rate>% = INR <amount> |
| Grand total | INR <amount as printed> |

Then exactly two lines:
Status: <OK | MISMATCH | NEEDS_INFO>
Notes: <one sentence: what the reviewer must know, or "None">

## Examples
Input (shortened): "Acme Traders, GSTIN 07AAACA0000A1Z1, Invoice A-17, 01/10/2026, 1 x Stapler 500.00, Subtotal 500.00, GST 18% 90.00, Total 590.00"

Output:

| Field | Value |
|---|---|
| Vendor | Acme Traders |
| GSTIN | 07AAACA0000A1Z1 |
| Invoice No | A-17 |
| Invoice Date | 01-Oct-2026 |
| Line items | 1 |
| Subtotal | INR 500.00 |
| GST | 18% = INR 90.00 |
| Grand total | INR 590.00 |

Status: OK
Notes: None

Input (shortened): "Beta Prints, no GSTIN, Bill 88, 3 Oct 2026, Subtotal 1,000.00, GST 18% 180.00, Total 1,280.00"

Output: the same table with GSTIN = MISSING and Grand total = INR 1,280.00, then
Status: NEEDS_INFO
Notes: GSTIN missing; also, subtotal + GST is INR 1,180.00, not the printed INR 1,280.00.
