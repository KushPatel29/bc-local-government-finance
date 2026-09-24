"""An independent recomputation of what the workbook calculates.

The workbook does its arithmetic in Excel formulas over the dbt gold tables.
This module does the same arithmetic in pandas from the same CSVs, without
reading the workbook, and tests/test_workbook.py holds the two to each other.
It also recomputes the gold tables' own indicators straight from the silver
facts (tests/test_gold.py), so dbt's SQL has a second implementation too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

import layout as L

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold"
SILVER = ROOT / "data" / "silver"


@dataclass(frozen=True)
class Gold:
    dim: pd.DataFrame
    year: pd.DataFrame
    assets: pd.DataFrame
    tax: pd.DataFrame
    peers: pd.DataFrame
    province: pd.DataFrame


def load() -> Gold:
    read = lambda n: pd.read_csv(GOLD / f"{n}.csv")  # noqa: E731
    return Gold(read("dim_municipality"), read("fct_municipal_year"), read("fct_asset_category"),
                read("fct_tax_class"), read("mart_peer_benchmark"), read("mart_province_trend"))


def municipality_id(g: Gold, display_name: str) -> str:
    return g.dim.set_index("display_name").loc[display_name, "municipality_id"]


def value(g: Gold, mid: str, column: str, year: int):
    row = g.year[(g.year.municipality_id == mid) & (g.year.year == year)]
    v = row[column].iloc[0] if len(row) else np.nan
    return None if pd.isna(v) else v


def base_year(g: Gold, mid: str) -> int:
    rows = g.year[(g.year.municipality_id == mid) & g.year.total_revenue.notna()]
    return int(rows.year.max())


# ------------------------------------------------------------------ the plan
@dataclass
class Drivers:
    cpi: float = L.PLAN["cpi"]
    wage_growth: float = L.PLAN["wage_growth"]
    wage_share: float = L.PLAN["wage_share"]
    gap_closure: float = L.PLAN["gap_closure"]
    debt_share: float = L.PLAN["debt_share"]
    reserve_share: float = L.PLAN["reserve_share"]
    mfa_rate: float = L.PLAN["mfa_rate"]
    term: int = L.PLAN["term"]
    extra: dict = field(default_factory=dict)


def pmt(rate: float, n: int, pv: float) -> float:
    """Excel's PMT(rate, n, -pv): the level annual payment on a loan of pv."""
    return pv * rate / (1 - (1 + rate) ** -n) if rate else pv / n


def plan(g: Gold, mid: str, d: Drivers | None = None) -> pd.DataFrame:
    d = d or Drivers()
    by = base_year(g, mid)
    v = lambda c, y=by: value(g, mid, c, y)  # noqa: E731
    try:
        pop_growth = (v("population") / v("population", by - 2)) ** 0.5 - 1
    except TypeError:
        pop_growth = 0.0
    cost_growth = d.wage_share * d.wage_growth + (1 - d.wage_share) * d.cpi + pop_growth
    rev_growth = d.cpi + pop_growth
    add3 = v("tca_additions_3yr")
    base_capital = add3 if add3 is not None else (v("tca_additions") or 0.0)
    gap = v("annual_renewal_gap") or 0.0
    rows, borrowed = [], []
    for t in range(L.PLAN_YEARS + 1):
        cash = v("cash_expenses") * (1 + cost_growth) ** t
        non_tax = (v("total_revenue") - v("taxation")) * (1 + rev_growth) ** t
        capital = (base_capital + gap * d.gap_closure * t / L.PLAN_YEARS) * (1 + d.cpi) ** t
        incremental = capital - base_capital
        borrowed.append(d.debt_share * incremental)
        new_servicing = sum(pmt(d.mfa_rate, d.term, b) for b in borrowed)
        rows.append({"year": by + t, "cash_expenses": cash, "non_tax_revenue": non_tax, "capital": capital,
                     "incremental_capital": incremental, "new_borrowing": borrowed[-1],
                     "new_servicing": new_servicing, "reserve_draw": d.reserve_share * incremental,
                     "tax_capital": (1 - d.debt_share - d.reserve_share) * incremental})
    p = pd.DataFrame(rows)
    p["taxation"] = (v("taxation") + (p.cash_expenses - p.cash_expenses.iloc[0]) + p.new_servicing + p.tax_capital
                     - (p.non_tax_revenue - p.non_tax_revenue.iloc[0]))
    p["tax_increase"] = p.taxation / p.taxation.shift() - 1
    p["reserves"] = v("financial_reserves") - p.reserve_draw.cumsum()
    p["servicing"] = v("debt_servicing_cost") + p.new_servicing
    scale = (p.taxation + p.non_tax_revenue) / (p.taxation.iloc[0] + p.non_tax_revenue.iloc[0])
    p["limit_used"] = p.servicing / (0.25 * v("revenue_for_limit") * scale)
    p["house_tax"] = v("house_municipal_tax") * p.taxation / p.taxation.iloc[0]
    return p


def average_increase(p: pd.DataFrame) -> float:
    return (p.taxation.iloc[-1] / p.taxation.iloc[0]) ** (1 / L.PLAN_YEARS) - 1


def plan_grid(g: Gold, mid: str) -> pd.DataFrame:
    return pd.DataFrame([[average_increase(plan(g, mid, Drivers(gap_closure=c, debt_share=s)))
                          for s in L.GRID_DEBT] for c in L.GRID_CLOSURE], index=L.GRID_CLOSURE, columns=L.GRID_DEBT)


# ------------------------------------------------------------------ tax and debt
def levy_to_rate(g: Gold, mid: str, change: float) -> dict:
    latest = int(g.year.year.max())
    t = g.tax[(g.tax.municipality_id == mid) & (g.tax.year == latest)]
    levy = t.variable_rate_taxes.fillna(0).sum()
    weighted = (t.assessment.fillna(0) * t.class_multiple.fillna(0)).sum()
    implied = levy * 1000 / weighted
    house_now = value(g, mid, "house_municipal_tax", latest)
    return {"levy": levy, "weighted": weighted, "implied": implied,
            "published": t.set_index("property_class").loc["Residential", "municipal_rate"],
            "new_rate": implied * (1 + change), "house_now": house_now, "house_new": house_now * (1 + change)}


def debt(g: Gold, mid: str, amount: float = 10_000_000, d: Drivers | None = None) -> dict:
    d = d or Drivers()
    by = base_year(g, mid)
    capacity = value(g, mid, "servicing_capacity", by)
    payment = pmt(d.mfa_rate, d.term, amount)
    max_borrowing = capacity * (1 - (1 + d.mfa_rate) ** -d.term) / d.mfa_rate
    return {"limit_used": value(g, mid, "debt_servicing_cost", by) / value(g, mid, "liability_servicing_limit", by),
            "payment": payment, "capacity_after": capacity - payment, "max_borrowing": max_borrowing}


def tier_percentile(g: Gold, mid: str, metric: str) -> float | None:
    p = g.peers
    row = p[p.municipality_id == mid].iloc[0]
    v = row[metric]
    if pd.isna(v):
        return None
    tier = p[(p.size_tier == row.size_tier) & p[metric].notna()]
    return (tier[metric] < v).sum() / (len(tier) - 1)


# ------------------------------------------------------------------ gold, from silver
def silver_wide() -> pd.DataFrame:
    """The single-row schedules, one column per (schedule, line), straight from silver."""
    f = pd.read_csv(SILVER / "facts.csv", dtype={"schedule": str}, low_memory=False)
    f["item"] = f["item"].fillna("")
    w = f[f["item"] == ""].pivot_table(index=["municipality_id", "year"], columns=["schedule", "line"],
                                        values="value", aggfunc="first")
    return w
