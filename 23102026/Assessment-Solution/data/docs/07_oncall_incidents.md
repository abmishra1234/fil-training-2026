# On-call and Incident Response (ENG-PROC-05)

## Severity levels
Sev-1: customer money movement is down or wrong for many users (for example settlements failing). Sev-2: a major feature is degraded, or a single large merchant is affected. Sev-3: minor issue with a workaround.

## Escalation matrix
For a Sev-1, page the primary on-call engineer through "PagerNova". If there is no acknowledgement in 10 minutes, the page escalates to the secondary on-call, and after 20 minutes to the Engineering Manager on duty. The Incident Commander is appointed within 15 minutes and opens a bridge call.

## Response times
Sev-1 must be acknowledged within 5 minutes, any time of day or night. Sev-2 within 30 minutes during business hours and 60 minutes outside business hours.

## On-call allowance
Engineers on the on-call rotation receive an allowance of INR 1,500 per weekday night and INR 3,000 per weekend day or public holiday. Graduate trainees shadow on-call for their first 6 months and do not carry the pager alone.

## Postmortem
Every Sev-1 and Sev-2 needs a blameless postmortem within 5 working days, with action items tracked in the engineering backlog.
