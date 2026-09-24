"""The committed gold tables are what dbt builds today, on this machine or CI's.

dbt is re-run into a temporary directory (profiles.yml reads BC_GOLD and
BC_DUCKDB) and every table is compared to the committed CSV on values: row
order and the last floating-point digit are not part of what gold promises.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pandas as pd
import pytest

from workbook_io import ROOT

GOLD = ROOT / "data" / "gold"
KEYS = {"dim_municipality": ["municipality_id"], "fct_municipal_year": ["municipality_id", "year"],
        "fct_asset_category": ["municipality_id", "year", "asset_category"],
        "fct_tax_class": ["municipality_id", "year", "property_class"],
        "mart_peer_benchmark": ["municipality_id"], "mart_province_trend": ["year"]}


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    dbt = shutil.which("dbt")
    if dbt is None:
        pytest.skip("dbt is not installed")
    out = tmp_path_factory.mktemp("gold")
    env = dict(os.environ, BC_GOLD=str(out), BC_DUCKDB=str(out / "bc.duckdb"))
    run = subprocess.run([dbt, "build", "--project-dir", "dbt", "--profiles-dir", "dbt"], cwd=ROOT, env=env,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout[-3000:]
    return out


@pytest.mark.parametrize("name", sorted(KEYS))
def test_gold_table_is_what_dbt_builds(rebuilt, name):
    want = pd.read_csv(rebuilt / f"{name}.csv").sort_values(KEYS[name]).reset_index(drop=True)
    got = pd.read_csv(GOLD / f"{name}.csv").sort_values(KEYS[name]).reset_index(drop=True)
    assert list(got.columns) == list(want.columns)
    pd.testing.assert_frame_equal(got, want, check_exact=False, rtol=1e-12, atol=1e-9)
