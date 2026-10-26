# Lab 4 · Permission manifest + security gate  (student copy)

**Time:** 20 minutes · **Work in:** pairs · **Badge:** 🏅 Security Gatekeeper
**Primitive practised:** 7 Permission manifest (design rule 4: *least privilege by default*)

## Why this lab

A colleague added two helper scripts to the invoice skill: one saves the summary for the
reviewer, the other keeps an audit log. Before the skill ships, the **security gate**
compares what the code *does* with what the manifest *declares*. Right now the skill
declares nothing, so the gate fails.

Your job: make the gate pass **the right way**. Declaring everything the code does is
the wrong way. Remove what the skill does not need, then declare only what is left.

## Folder you start with

```
student/
├── invoice-summary-formatter/
│   ├── SKILL.md                  ← no manifest yet
│   └── scripts/
│       ├── totals.py, totals_schema.json   ← from Lab 2 (clean)
│       ├── export_summary.py               ← saves the summary for the reviewer
│       └── helpers.py                      ← audit log + "useful" extras
└── tools/gate.py
```

## Steps

1. Run the gate and read every line:
   ```bash
   python tools/gate.py invoice-summary-formatter
   ```
2. Add the manifest to the SKILL.md frontmatter (between the `---` lines):
   ```yaml
   allowed-tools: Read Bash(python:scripts/*)
   metadata:
     fil.permissions:
       data_scopes: [ap.invoices:read]
       network_egress: none        # or a list of hosts
       writes: [./output/]         # or none
       credentials: none           # or a list of env var names
       side_effects: none          # or a list, e.g. [send_email]
   ```
3. For **each** finding decide: *declare it* or *remove the code*. Ask:
   * Does an AP invoice summary really need to call the internet?
   * Should this skill read an ERP service token? Whose token is it?
   * Should it write into a folder shared by the whole team?
4. Re-run until the gate prints `RESULT: PASS` **and** every declaration is actually needed.
5. **Neighbour review.** Swap folders with the next pair. The gate is a static checker:
   can you find something it **missed**? Read every line of `scripts/` yourself.

## Done when ✅

- [ ] Gate prints `RESULT: PASS`
- [ ] Every declared scope is actually used (no `[warn]` lines)
- [ ] `network_egress` is `none` unless you can justify it to the trainer
- [ ] Neighbour review done: you found (or ruled out) a gap the gate missed

## Hints

* The fastest way to pass is to declare `network_egress: [api.example-fx.com]`.
  That is also how most data leaks start.
* Least privilege means the smallest set that still does the job.
* A gate can be fooled by renaming things. Your eyes are the second gate.

## Think about it

1. Why does the gate fail a write to `../../shared/`, even after you declared `./output/`?
2. What did your neighbour find that the gate did not? How would you improve `gate.py`?
