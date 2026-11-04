# 02 - Data dictionary

## The eight funds

All funds are sub-funds of the fictional umbrella "Lumen Crest Funds SICAV". Clients and analysts use the short names and aliases, so your fund resolver must map them to `fund_id` (`data/fund_aliases.json`).

| fund_id | Fund name | Also called (aliases) | Asset class | Base ccy | SFDR | ESG flag | SRI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | LCI Global Technology Fund | Global Tech Fund, Global Technology, GTF | Equity | USD | Article 6 | N | 6 |
| F02 | LCI India Focus Equity Fund | India Equity Fund, India Focus Fund, India Fund | Equity | USD | Article 6 | N | 6 |
| F03 | LCI Sustainable Global Equity Fund | Sustainable Global Equity, SGE Fund, ESG Global Equity Fund | Equity | USD | Article 9 | Y | 5 |
| F04 | LCI Asia Pacific Dividend Fund | Asia Pacific Dividend, APAC Dividend Fund, Asia Dividend Fund | Equity | USD | Article 8 | Y | 5 |
| F05 | LCI Global Multi Asset Income Fund | Multi Asset Income Fund, GMAI Fund, Multi Asset Income | Multi Asset | USD | Article 8 | Y | 3 |
| F06 | LCI Euro Short Duration Bond Fund | Euro Short Duration Bond, Euro Short Bond Fund, ESDB Fund | Fixed Income | EUR | Article 6 | N | 2 |
| F07 | LCI Sustainable Climate Bond Fund | Climate Bond Fund, Sustainable Climate Bond, Green Bond Fund | Fixed Income | USD | Article 9 | Y | 3 |
| F08 | LCI China Consumer Fund | China Consumer, China Fund, CCF | Equity | USD | Article 6 | N | 6 |

"ESG funds" in a question means funds with `esg_flag = Y` (Article 8 or Article 9). "Sustainable funds" means the same.

## Share classes

Every fund has four share classes. The suffix is the fund's base currency (USD, or EUR for F06).

| Class | Distribution | Who buys it | OCF vs A class | Entry charge | Minimum initial investment |
| --- | --- | --- | --- | --- | --- |
| A-Acc | Accumulating (income reinvested) | Retail | base | up to 5.25% equity / 3.50% bond and multi asset | 2,500 |
| A-Dis | Distributing (income paid out) | Retail | same as A-Acc | same as A-Acc | 2,500 |
| Y-Acc | Accumulating | Retail via advisers and platforms ("clean" class) | lower | 0% | 2,500 |
| I-Acc | Accumulating | Institutional | lowest | 0% | 10,000,000 |

If a question names no share class, use **A-Acc** in the base currency and say so in the answer.

## `data/fund_master.csv` (doc_id `DATA-FUND-MASTER`)

32 rows (8 funds x 4 classes), all as of **2026-09-30**. This file is the authoritative source for figures (POL-02 §3.3). When a factsheet disagrees with it, the CSV wins and the answer should mention the stale source.

| Column | Type | Meaning | Example |
| --- | --- | --- | --- |
| fund_id | str | Fund key F01-F08 | F01 |
| fund_name | str | Full fund name | LCI Global Technology Fund |
| share_class | str | Class + currency | A-Acc-USD |
| isin | str | Fake ISIN, 12 characters, country code ZZ, valid check digit | ZZ0000010072 |
| currency | str | Share class currency | USD |
| distribution | str | Accumulating or Distributing | Accumulating |
| investor_type | str | Retail / Retail via advisers / Institutional | Retail |
| asset_class | str | Equity, Fixed Income, Multi Asset | Equity |
| region | str | Investment focus | Global |
| sfdr_article | str | EU sustainability classification | Article 9 |
| esg_flag | Y/N | Y for Article 8 or 9 | Y |
| benchmark | str | Fictional comparison index | Meridex ACWI Information Technology Index (Net) |
| ocf_pct | float | Ongoing charges figure, % per year | 1.89 |
| entry_charge_max_pct | float | Maximum entry charge, % | 5.25 |
| exit_charge_pct | float | Always 0.00 | 0.00 |
| performance_fee | str | Always None | None |
| min_initial_investment | int | In share class currency | 2500 |
| sri_risk_score | int | Summary risk indicator 1 (low) to 7 (high) | 6 |
| return_1y_pct | float | 1-year total return, net of fees, % | 21.4 |
| return_3y_ann_pct | float | 3-year return, annualised, % | 14.9 |
| return_5y_ann_pct | float | 5-year return, annualised, % | 16.2 |
| distribution_yield_pct | float or empty | Only for Distributing classes | 5.1 |
| fund_aum_musd | float | Fund size in millions of base currency (fund level, same on all 4 rows) | 4820.5 |
| fund_launch_date | date | | 2011-03-14 |
| share_class_launch_date | date | | 2014-05-12 |
| fund_managers | str | Fictional people, `; ` separated | Rohan Mehtani; Clara Whitfield |
| dealing_frequency | str | | Daily (each Luxembourg business day) |
| as_of_date | date | Data date | 2026-09-30 |
| source_doc_id | str | Cite this | DATA-FUND-MASTER |

## Document IDs

| Pattern | Document | Example |
| --- | --- | --- |
| `FS-Fnn` | Factsheet | FS-F03 |
| `KID-Fnn` | Key Information Document (A-Acc class) | KID-F07 |
| `COM-Fnn-YYYYQn` | Quarterly commentary | COM-F02-2026Q3 |
| `POL-nn-vX.Y` | Policy, versioned | POL-01-v3.0 |
| `RULES-COMPLIANCE` | Compliance rules YAML | |
| `EML-nnn` | Client email | EML-004 |
| `DATA-FUND-MASTER` | Fund master CSV | |

## Metadata on every document

Markdown files start with YAML front matter; emails and the rules file start with `# key: value` lines; each KID PDF has a metadata line at the top of page 1. Your chunks must carry these fields (FR-01):

| Field | Values |
| --- | --- |
| doc_id | see above |
| doc_type | factsheet, kid, commentary, policy, rules, client_email, fund_data |
| fund_id | F01-F08, or ALL for policies |
| share_class | e.g. A-Acc-USD, or ALL |
| section | heading (e.g. "4. Performance") or clause (e.g. "§4.2") - you assign it when chunking |
| as_of_date | ISO date of the data in the document |
| version | e.g. 1.0, 3.0 |
| status | ACTIVE or SUPERSEDED (policies) |

## Citation format

`[doc_id §section]`, for example `[POL-01-v3.0 §4.2]`, `[FS-F01 §3. Share class information]`, `[DATA-FUND-MASTER §F01/A-Acc-USD]`. Put the citation at the end of the sentence it supports.
