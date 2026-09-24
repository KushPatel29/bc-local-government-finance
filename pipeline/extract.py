"""Silver: every published figure as one typed row, held to pipeline/contracts.py.

    python pipeline/extract.py

Reads data/raw/ (bronze) and writes:

* data/silver/municipalities.csv  one row per municipality: a stable id, name,
  type and regional district, with the spellings it was published under;
* data/silver/facts.csv           municipality_id, year, schedule, item, line,
  value (numeric) or text, one row per published cell.

A header the contract does not know, a line missing from a year it should be
in, a duplicate (municipality, year, schedule, item, line), or a value that is
neither a number nor an agreed blank marker stops the run and names the file.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import openpyxl
import xlrd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contracts as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SILVER = ROOT / "data" / "silver"
BLANKS = {None, "", "N/A", "n/a", "-", "--", "No Data Submitted"}


class ContractError(Exception):
    pass


def read_rows(path: Path) -> list[list]:
    if path.suffix == ".xls":
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)
        return [sheet.row_values(i) for i in range(sheet.nrows)]
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return [list(row) for row in book.worksheets[0].iter_rows(values_only=True)]


def number(value, where: str) -> float | None:
    if isinstance(value, str):
        value = value.strip().replace(",", "")
    if value in BLANKS:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ContractError(f"{where}: {value!r} is not a number") from None


def slug(name: str, kind: str) -> str:
    # Transliterate rather than drop: "shíshálh" -> "shishalh", not "shshlh".
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return f"{base or 'municipality'}-{kind.lower()}"


def parse(path: Path) -> tuple[str, int, list[dict]]:
    m = re.fullmatch(r"schedule(\w+?)_(\d{4})\.xlsx?", path.name)
    schedule, year = m.group(1), int(m.group(2))
    rows = read_rows(path)
    header_at = next(i for i, row in enumerate(rows) if row and str(row[0]).strip() == "Municipalities")
    header = rows[header_at]
    item_col = C.ITEM_COLUMN.get(schedule)
    columns = {}
    for j, h in enumerate(header):
        if h in (None, ""):
            continue
        text = re.sub(r"\s+", " ", str(h)).strip()
        if text in C.KEYS:
            columns[C.KEYS[text]] = j
        elif item_col and text == item_col:
            columns["item"] = j
        else:
            line = C.clean_header(schedule, text)
            if line not in C.LINES[schedule]:
                raise ContractError(f"{path.name}: header {text!r} -> {line!r} is not in the contract")
            columns[line] = j
    expected = {line for line, ys in C.LINES[schedule].items() if year in ys}
    found = set(columns) - {"municipality", "type", "regional_district", "item"}
    if found != expected:
        raise ContractError(f"{path.name}: missing {sorted(expected - found)}, unexpected {sorted(found - expected)}")

    out = []
    for r, row in enumerate(rows[header_at + 1:], start=header_at + 2):
        name = row[columns["municipality"]] if len(row) > columns["municipality"] else None
        if name in (None, "") or str(name).strip() == "Grand Totals":
            continue
        item = ""
        if item_col:
            item = re.sub(r"\s+", " ", str(row[columns["item"]] or "")).strip()
            item = C.ITEM_RENAMES.get(schedule, {}).get(item, item)
            if item not in C.ITEMS[schedule]:
                raise ContractError(f"{path.name} row {r}: {item_col} {item!r} is not in the contract")
        kind = str(row[columns["type"]]).strip()
        out.append({"published_name": str(name), "type": kind,
                    "regional_district": str(row[columns["regional_district"]] or "").strip(),
                    "item": item, "values": {
                        line: row[j] if j < len(row) else None
                        for line, j in columns.items() if line not in ("municipality", "type",
                                                                         "regional_district", "item")},
                    "where": f"{path.name} row {r}"})
    return schedule, year, out


def extract() -> dict[str, int]:
    SILVER.mkdir(parents=True, exist_ok=True)
    municipalities: dict[str, dict] = {}
    spellings = defaultdict(set)
    facts, seen = [], set()
    for path in sorted(RAW.glob("schedule*")):
        schedule, year, rows = parse(path)
        for row in rows:
            name = C.clean_municipality(row["published_name"])
            row["type"] = C.CURRENT_TYPE.get(name, row["type"])
            mid = slug(name, row["type"])
            spellings[mid].add(re.sub(r"\s+", " ", row["published_name"]).strip())
            record = municipalities.setdefault(mid, {"municipality_id": mid, "name": name, "type": row["type"],
                                                     "first_year": year, "last_year": year,
                                                     "regional_district": row["regional_district"]})
            record["first_year"] = min(record["first_year"], year)
            if year >= record["last_year"]:
                record["last_year"], record["regional_district"] = year, row["regional_district"]
            for line, raw in row["values"].items():
                key = (mid, year, schedule, row["item"], line)
                if key in seen:
                    raise ContractError(f"{row['where']}: duplicate {key}")
                seen.add(key)
                if (schedule, line) in C.TEXT_LINES:
                    text = "" if raw in C_BLANK_TEXT else str(raw).strip()
                    if text and text not in C.TEXT_VALUES:
                        raise ContractError(f"{row['where']} {line}: {text!r} is not an agreed value")
                    text = C.TEXT_VALUES.get(text, text)
                    facts.append((mid, year, schedule, row["item"], line, "", text))
                else:
                    value = number(raw, f"{row['where']} {line}")
                    facts.append((mid, year, schedule, row["item"], line, "" if value is None else repr(value), ""))

    with (SILVER / "municipalities.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["municipality_id", "name", "type", "type_name", "regional_district", "first_year", "last_year",
                    "published_as"])
        for m in sorted(municipalities.values(), key=lambda m: m["municipality_id"]):
            w.writerow([m["municipality_id"], m["name"], m["type"], C.TYPE_NAMES.get(m["type"], m["type"]),
                        m["regional_district"], m["first_year"], m["last_year"],
                        " | ".join(sorted(spellings[m["municipality_id"]]))])
    facts.sort()
    with (SILVER / "facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["municipality_id", "year", "schedule", "item", "line", "value", "text"])
        w.writerows(facts)
    counts = {"municipalities": len(municipalities), "facts": len(facts)}
    (SILVER / "manifest.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return counts


C_BLANK_TEXT = {None, ""}

if __name__ == "__main__":
    try:
        print(extract())
    except ContractError as error:
        sys.exit(f"contract broken: {error}")
