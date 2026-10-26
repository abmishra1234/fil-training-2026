# Brief C · meeting-minutes-formatter

**Customer:** FIL team leads
**Pain today:** minutes are free text; action items get lost because nobody owns them.

## What users type
* "Turn my notes from today's sprint review into proper minutes"
* "Write up the minutes for EVT-7781 from these notes"
* "Format these meeting notes and list the action items with owners"

## Near-misses (your skill must stay quiet)
Scheduling or rescheduling meetings · writing an agenda for a future meeting ·
summarising documents that are not meetings · sending emails

## Rules (this is your Knowledge: put it in references/)
* Every action item needs an **owner** (an employee ID who attended) and a **due date**
  (YYYY-MM-DD). "Someone", "the team" or "by Sunday" are not acceptable.
* Attendees come from the calendar connector using the meeting's event ID.
* Decisions are listed separately from action items.
* Minutes never include personal remarks or anything said "off the record".

## Connector (mocked)
`mock_connectors/calendar_events.json` (event ID → title, date, attendees) and
`mock_connectors/hr_employees.json` (employee ID → name).

## Output the team lead needs
Title, date, attendees by name, decisions, an action table (owner, task, due date);
`Status: COMPLETE | MISSING_OWNERS | NEEDS_INFO` and a one-line `Notes:`.

## Suggested Action
A script that takes the extracted action items as JSON, checks each owner is an attendee
of the event and each due date is a valid date on or after the meeting, and returns
per-item verdicts plus the status.

## Samples (for your quality evals): `samples/minutes/`
