"""Bronze: download the Province's municipal statistics, exactly as published.

    python pipeline/fetch_sources.py            # every schedule, every year in YEARS
    python pipeline/fetch_sources.py --check    # re-download and report what changed

The Ministry of Municipal Affairs publishes each municipality's audited
financial data as one spreadsheet per schedule per year ("Local Government
Statistics"). The files are kept byte for byte in data/raw/, and
data/sources.json records each one's URL, size and SHA-256, so every figure
downstream traces to a file the Province can be asked about.

Licence: Open Government Licence - British Columbia.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "sources.json"
BASE = ("https://www2.gov.bc.ca/assets/gov/british-columbians-our-governments/local-governments/"
        "finance/local-government-statistics/")
PAGE = "https://www2.gov.bc.ca/gov/content/governments/local-governments/facts-framework/statistics/statistics"
YEARS = range(2019, 2025)

# schedule -> what it holds
SCHEDULES = {
    "201": "General statistics: population, area, network lengths",
    "301": "Financial assets",
    "302": "Liabilities",
    "304": "Summary statement of financial position",
    "401": "Consolidated revenue",
    "402": "Consolidated expenses by function",
    "404": "Changes in net financial assets",
    "503": "Tangible capital assets by category, with replacement values",
    "601_1": "Total debt and financing costs",
    "602_1": "Liability servicing limit",
    "701": "Assessed values by property class",
    "702": "Tax rates by purpose and class",
    "703": "Total taxes and charges",
    "704": "Taxes and charges on a representative house",
    "707": "Assessments, rates, multiples and municipal taxes by class",
}
USER_AGENT = "Mozilla/5.0 (portfolio research; bc-local-government-finance)"


def candidates(schedule: str, year: int) -> list[str]:
    # 2019-2024 are .xlsx, except the 70x tax schedules for 2019, which are .xls.
    return [f"schedule{schedule}_{year}.xlsx", f"schedule{schedule}_{year}.xls"]


def download(name: str) -> bytes | None:
    for attempt in range(4):
        try:
            request = urllib.request.Request(BASE + name, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"could not download {name}")
    # A missing file comes back as an HTML page with status 200. Keep only real
    # workbooks: xlsx is a zip ("PK"), xls is an OLE compound file.
    if body[:2] == b"PK" or body[:4] == b"\xd0\xcf\x11\xe0":
        return body
    return None


def fetch(check: bool = False) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"files": []}
    old_hash = {f["file"]: f["sha256"] for f in old["files"]}
    files, changed = [], []
    for schedule in SCHEDULES:
        for year in YEARS:
            for name in candidates(schedule, year):
                body = download(name)
                if body is None:
                    continue
                digest = hashlib.sha256(body).hexdigest()
                if old_hash.get(name) != digest:
                    changed.append(name)
                if not check:
                    (RAW / name).write_bytes(body)
                files.append({"file": name, "schedule": schedule, "year": year, "url": BASE + name,
                              "bytes": len(body), "sha256": digest})
                break
            else:
                raise SystemExit(f"schedule {schedule} {year}: no workbook published")
    if check:
        print(f"{len(files)} files checked, {len(changed)} differ from data/sources.json")
        for name in changed:
            print("  changed:", name)
        return 1 if changed else 0
    MANIFEST.write_text(json.dumps({
        "publisher": "Province of British Columbia, Ministry of Municipal Affairs",
        "page": PAGE,
        "licence": "Open Government Licence - British Columbia",
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": [YEARS.start, YEARS.stop - 1],
        "schedules": SCHEDULES,
        "files": files,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"{len(files)} files in data/raw, {len(changed)} new or changed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    sys.exit(fetch(ap.parse_args().check))
