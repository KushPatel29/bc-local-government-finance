"""Bronze and silver: the Province's files, kept byte for byte and held to the contracts."""
from __future__ import annotations

import hashlib
import json

import openpyxl
import pandas as pd
import pytest

import contracts as C
import extract as X
from workbook_io import ROOT

RAW = ROOT / "data" / "raw"
MANIFEST = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))


def test_every_schedule_is_there_for_every_year():
    have = {(f["schedule"], f["year"]) for f in MANIFEST["files"]}
    want = {(s, y) for s in MANIFEST["schedules"] for y in range(MANIFEST["years"][0], MANIFEST["years"][1] + 1)}
    assert have == want


@pytest.mark.parametrize("entry", MANIFEST["files"], ids=[f["file"] for f in MANIFEST["files"]])
def test_raw_file_is_the_one_downloaded(entry):
    body = (RAW / entry["file"]).read_bytes()
    assert len(body) == entry["bytes"]
    assert hashlib.sha256(body).hexdigest() == entry["sha256"]
    assert entry["url"].startswith("https://www2.gov.bc.ca/")


def test_silver_is_what_the_extractor_writes_today(tmp_path, monkeypatch):
    monkeypatch.setattr(X, "SILVER", tmp_path)
    counts = X.extract()
    assert counts == json.loads((ROOT / "data" / "silver" / "manifest.json").read_text())
    for name in ("facts.csv", "municipalities.csv"):
        assert (tmp_path / name).read_bytes() == (ROOT / "data" / "silver" / name).read_bytes(), name


@pytest.mark.parametrize("schedule,published,canonical", [
    ("702", "Major Industry1", "major_industry"),
    ("701", "General Purposes Bus. and Other", "general_purposes_business_and_other"),
    ("201", "2016 Census", "census"),
    ("707", "July 1, 2018 BC STATS Population Estimates (Dec. 2018 Release)", "population_estimate"),
    ("703", "Regional District", "regional_district_tax"),
    ("707", "% Total Taxes", "share_of_total_taxes"),
])
def test_published_spellings_map_to_one_line(schedule, published, canonical):
    assert C.clean_header(schedule, published) == canonical


def test_an_unknown_header_stops_the_pipeline(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["401 - Consolidated Revenue"])
    ws.append(["Municipalities", "Type", "RD", "Total Revenue", "A Line Nobody Agreed"])
    ws.append(["Somewhere", "V", "XX", 1, 2])
    path = tmp_path / "schedule401_2024.xlsx"
    wb.save(path)
    with pytest.raises(X.ContractError, match="not in the contract"):
        X.parse(path)


def test_a_line_missing_from_its_year_stops_the_pipeline(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["401 - Consolidated Revenue"])
    ws.append(["Municipalities", "Type", "RD", "Total Revenue"])
    ws.append(["Somewhere", "V", "XX", 1])
    path = tmp_path / "schedule401_2024.xlsx"
    wb.save(path)
    with pytest.raises(X.ContractError, match="missing"):
        X.parse(path)


def test_municipalities_have_one_stable_id_each():
    m = pd.read_csv(ROOT / "data" / "silver" / "municipalities.csv")
    assert m.municipality_id.is_unique and len(m) == 162
    assert {"langley-c", "langley-d", "north-vancouver-c", "north-vancouver-d"} <= set(m.municipality_id)
    renamed = m.set_index("municipality_id").published_as
    assert "Queen Charlotte" in renamed["daajing-giids-v"]
    assert "Sechelt Indian Government" in renamed["shishalh-nation-government-district-d"]
    assert "Vancouver1" in renamed["vancouver-c"]              # a footnote digit on the name itself
    assert m.set_index("municipality_id").loc["mission-c", "first_year"] == 2019   # District until 2021
    assert m.set_index("municipality_id").loc["jumbo-glacier-v", "last_year"] == 2020


def test_asset_plan_status_has_one_spelling_per_meaning():
    f = pd.read_csv(ROOT / "data" / "silver" / "facts.csv", dtype={"schedule": str}, low_memory=False)
    text = f.loc[f.line == "asset_management_plan_in_place", "text"].dropna()
    assert set(text) == {"Yes", "No", "In_Progress", "Not applicable"}
