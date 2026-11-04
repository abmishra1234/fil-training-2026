# 09 - Domain primer for engineers

Enough asset-management vocabulary to build FundLens. Twenty minutes of reading.

## How a fund range works

A **fund** pools money from many investors and invests it according to an **objective** (for example "capital growth from global technology companies"). Investors buy **shares** (units) of the fund at its **NAV** (net asset value per share), calculated once per **dealing day**.

Our fictional funds are **sub-funds** of one **SICAV** (an umbrella investment company, common in Luxembourg). They are **UCITS** funds, the EU standard for funds sold to the public.

## Share classes

One fund, several **share classes** with different fees, minimums or currencies. All classes own the same portfolio.

- **Acc** (accumulating): income is reinvested in the share price.
- **Dis** (distributing): income is paid out; the **distribution yield** is the yearly income as % of the price.
- **A** = standard retail, **Y** = cheaper "clean" retail class sold via advisers and platforms, **I** = institutional, large minimums, lowest fees.

## Identifiers

- **ISIN**: 12-character security ID. Real ISINs start with a country code (LU, IE, GB). Ours start with **ZZ** so they can never clash with a real one; the last digit is a valid check digit.
- **fund_id** (F01-F08) is our internal key.

## Costs

- **OCF (ongoing charges figure)**: yearly running cost as % of your investment, already taken out of the price and of published performance. The number analysts are asked about most.
- **Entry charge**: one-off % on the amount invested; a maximum, distributors may charge less.
- **Exit charge**: on selling (none at LCI).
- **Transaction costs**: buying and selling the fund's investments; shown in the KID, not part of the OCF.
- **Switching fee**: moving money from one fund to another (rules in POL-01).
- **Swing pricing**: price adjustment on days with big inflows/outflows to protect remaining investors; not a fee.

## Risk and performance

- **SRI (summary risk indicator)**: 1 (lower risk) to 7 (higher risk), shown in every KID. Equity funds are often 5-6, short bond funds 2.
- **Annualised return**: the average yearly return over several years (3y, 5y).
- **Cumulative vs calendar-year returns**: total over a period vs each calendar year separately.
- **Benchmark**: an index the fund compares itself against. **Outperform / underperform** = did better / worse than the benchmark. Ours are from a fictional provider "Meridex".
- **Contributors / detractors**: holdings that helped / hurt performance in a period.
- **Duration** (bond funds): sensitivity to interest-rate changes in years. Rates up → bond prices down.

## Documents

- **Factsheet**: monthly marketing summary: facts, charges, performance, top 10 holdings, allocation.
- **KID (Key Information Document)**: regulated 2-3 page document (EU PRIIPs) with the SRI, **performance scenarios** (stress, unfavourable, moderate, favourable), costs and **recommended holding period**. Its wording is precise and conservative.
- **Commentary**: the portfolio manager's quarterly explanation of performance and outlook. Outlook statements are opinions, not forecasts you can repeat as facts.
- **Prospectus**: the full legal document (not in our corpus).

## Regulation and conduct ideas used in the rules

- **No personal advice**: servicing staff give information, not recommendations. Only a regulated adviser can say what suits a person.
- **No forecasts or guarantees**: never promise returns or income.
- **Past performance warning** and **risk warning**: mandatory whenever performance is quoted.
- **SFDR Article 6 / 8 / 9**: EU sustainability labels: 6 = no specific ESG promotion, 8 = promotes environmental or social characteristics, 9 = has a sustainable investment objective.
- **Vulnerable clients**: people at higher risk of harm (bereavement, illness, money worries) get extra care.
- **Dealing cut-off and forward pricing**: orders before the cut-off get that day's price, which is not known when the order is placed.
- **Settlement T+3**: money is paid three business days after the dealing day.

## A worked example

"What is the ongoing charge of the Global Tech Fund, A-Acc share class?"
→ resolve "Global Tech Fund" to F01 → class A-Acc-USD → `fund_lookup(F01, A-Acc, [ocf_pct])` → 1.89 → "The OCF of the LCI Global Technology Fund A-Acc-USD share class is 1.89% a year, as of 30 September 2026 [DATA-FUND-MASTER §F01/A-Acc-USD]."
