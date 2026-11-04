"""FR-11 tools: fund_lookup and compare_funds over data/fund_master.csv.  >>> YOU BUILD THIS (Day 3) <<<

Contract (from the requirements):
- fund_lookup(fund: str, share_class: str | None, fields: list[str]) -> list[FundRecord]
    `fund` may be a fund_id ("F01"), the full name, or an alias ("Global Tech Fund"). See docs/02_data_dictionary.md
    for the alias table. Default share class when none is given: A-Acc in the fund's base currency.
- compare_funds(funds: list[str] (2-4), fields: list[str], share_class: str = "A-Acc") -> list[FundRecord]
Every returned value carries as_of_date and source_doc_id so the answer can cite it.
"""
from __future__ import annotations

from ..schemas import FundRecord


def fund_lookup(fund: str, share_class: str | None = None, fields: list[str] | None = None) -> list[FundRecord]:
    raise NotImplementedError


def compare_funds(funds: list[str], fields: list[str], share_class: str = "A-Acc") -> list[FundRecord]:
    raise NotImplementedError
