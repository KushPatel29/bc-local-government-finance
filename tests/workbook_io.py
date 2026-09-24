"""Read the workbook through its defined names, so a test never hard-codes a cell."""
from __future__ import annotations

import base64
import io
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def block(wb, name: str) -> list[list]:
    sheet, coord = next(wb.defined_names[name].destinations)
    cells = wb[sheet][coord.replace("$", "")]
    if not isinstance(cells, tuple):
        return [[cells.value]]
    if not isinstance(cells[0], tuple):
        cells = (cells,)
    return [[c.value for c in row] for row in cells]


def cell(wb, name: str):
    return block(wb, name)[0][0]


def spill(wb, name: str, width: int) -> list[list]:
    """The rows a dynamic array wrote from the named anchor down, until a blank first column."""
    sheet, coord = next(wb.defined_names[name].destinations)
    ws = wb[sheet]
    top = ws[coord.replace("$", "")]
    out, r = [], top.row
    while ws.cell(r, top.column).value not in (None, ""):
        out.append([ws.cell(r, top.column + j).value for j in range(width)])
        r += 1
    return out


def parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def power_query_m(pkg: dict) -> str:
    for name, raw in pkg.items():
        if not re.fullmatch(r"customXml/item\d+\.xml", name):
            continue
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
        found = re.search(r"<DataMashup[^>]*>(.*)</DataMashup>", text, re.S)
        if found:
            blob = base64.b64decode(found.group(1))
            size = int.from_bytes(blob[4:8], "little")
            with zipfile.ZipFile(io.BytesIO(blob[8:8 + size])) as z:
                return z.read("Formulas/Section1.m").decode("utf-8-sig")
    raise AssertionError("no DataMashup part")
