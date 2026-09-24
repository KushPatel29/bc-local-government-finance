"""dbt's gold tables, recomputed from silver in pandas: two implementations, one answer."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import layout as L
import reference as R
from workbook_io import ROOT

CENT = 0.01


@pytest.fixture(scope="module")
def wide():
    return R.silver_wide()


@pytest.fixture(scope="module")
def fct(gold):
    return gold.year.set_index(["municipality_id", "year"])


def g(wide, schedule, line):
    return wide[(schedule, line)] if (schedule, line) in wide.columns else pd.Series(np.nan, index=wide.index)


@pytest.mark.parametrize("column,schedule,line", [
    ("total_revenue", "401", "total_revenue"),
    ("taxation", "401", "total_own_purpose_taxation_and_grants_in_lieu"),
    ("total_expenses", "402", "total_expenses"),
    ("annual_surplus", "404", "annual_surplus_deficit"),
    ("net_financial_assets", "304", "net_financial_assets_debt"),
    ("long_term_debt", "601_1", "total_debt_at_year_end"),
    ("liability_servicing_limit", "602_1", "liability_servicing_limit"),
    ("municipal_property_tax", "703", "general_municipal_total"),
    ("house_total_charges", "704", "total_residential_property_taxes_and_charges"),
])
def test_published_lines_pass_through(fct, wide, column, schedule, line):
    pd.testing.assert_series_equal(fct[column], g(wide, schedule, line).reindex(fct.index),
                                   check_names=False, atol=CENT)


def test_derived_indicators(fct, wide):
    transfers = (g(wide, "401", "federal_government_transfers").fillna(0)
                 + g(wide, "401", "provincial_government_transfers").fillna(0)
                 + g(wide, "401", "regional_and_other_governments_transfers").fillna(0))
    own = g(wide, "401", "total_revenue") - transfers - g(wide, "401", "developer_and_other_contributions_donations").fillna(0)
    share = (own / g(wide, "401", "total_revenue")).reindex(fct.index)
    np.testing.assert_allclose(fct.own_source_share, share, rtol=1e-12, equal_nan=True)
    limit_used = (g(wide, "602_1", "actual_debt_servicing_cost") / g(wide, "602_1", "liability_servicing_limit"))
    np.testing.assert_allclose(fct.limit_used, limit_used.reindex(fct.index), rtol=1e-12, equal_nan=True)
    ocs = g(wide, "304", "total_operating_capital_surplus").fillna(
        g(wide, "304", "operating_funds") + g(wide, "304", "capital_funds"))
    reserves = ocs + sum(g(wide, "304", f"{k}_statutory_reserves").fillna(0) for k in ("water", "sewer", "other"))
    np.testing.assert_allclose(fct.financial_reserves, reserves.reindex(fct.index), atol=CENT, equal_nan=True)


def test_population_repair_is_the_rule_the_readme_states(fct, wide):
    published = g(wide, "201", "bc_stats_population_estimates").unstack()
    median = published.median(axis=1)
    bad = published.div(median, axis=0).sub(1).abs() > 0.25
    assert bad[2022].sum() == 77 and bad.drop(columns=2022).values.sum() == 1   # Northern Rockies, 2020
    before, after = published.shift(1, axis=1), published.shift(-1, axis=1)
    repaired = published.where(~bad, ((before + after) / 2).fillna(pd.DataFrame(
        np.repeat(median.values[:, None], published.shape[1], 1), index=published.index, columns=published.columns)))
    got = fct.population.unstack()
    np.testing.assert_allclose(got.values, repaired.reindex(got.index).values, rtol=1e-12, equal_nan=True)
    assert fct.loc[("fernie-c", 2022), "population_published"] == 1700


def test_renewal_need_and_reinvestment(gold, fct):
    a = gold.assets[~gold.assets.asset_category.isin(["Land", "Work In Progress"])]
    dep = a.groupby(["municipality_id", "year"])[["historical_cost", "replacement_value"]].sum()
    rep_to_cost = (dep.replacement_value / dep.historical_cost).reindex(fct.index)
    plausible = rep_to_cost.between(1, 6)
    need = (fct.amortization * rep_to_cost).where(plausible)
    np.testing.assert_allclose(fct.renewal_need, need, rtol=1e-12, equal_nan=True)
    add3 = fct.tca_additions.groupby(level=0).transform(lambda s: s.rolling(3).mean())
    np.testing.assert_allclose(fct.reinvestment_ratio, (add3 / need).where(plausible), rtol=1e-9, equal_nan=True)


@pytest.mark.parametrize("metric", [m[0] for m in L.METRICS])
def test_peer_percentiles_count_only_reporters(gold, metric):
    p = gold.peers
    for tier, grp in p.groupby("size_tier"):
        rep = grp[grp[metric].notna()]
        want = rep[metric].apply(lambda v: (rep[metric] < v).sum() / (len(rep) - 1))
        np.testing.assert_allclose(grp.loc[rep.index, f"{metric}_tier_pct"], want, atol=1e-12)
        assert grp.loc[grp[metric].isna(), f"{metric}_tier_pct"].isna().all()


def test_province_trend(gold):
    y = gold.year
    t = gold.province.set_index("year")
    np.testing.assert_allclose(t.total_revenue, y.groupby("year").total_revenue.sum(), rtol=1e-12)
    np.testing.assert_allclose(t.municipalities, y.groupby("year").size())
    latest = y[y.year == y.year.max()]
    screened = latest[latest.reinvestment_ratio.notna()]
    assert t.loc[latest.year.iloc[0], "screened_for_renewal"] == len(screened)
    assert t.loc[latest.year.iloc[0], "below_renewal_need"] == (screened.reinvestment_ratio < 1).sum()


def test_missing_statements_are_exactly_the_documented_ones(gold):
    seed = pd.read_csv(ROOT / "dbt" / "seeds" / "missing_statements.csv")
    gaps = gold.year.loc[gold.year.total_revenue.isna(), ["municipality_id", "year"]]
    assert set(map(tuple, gaps.values)) == set(map(tuple, seed[["municipality_id", "year"]].values))
