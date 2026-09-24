"""Build workbook/BC_Local_Government_Finance_Model.xlsx by driving desktop Excel over COM.

    python model/build_workbook.py [--visible] [--no-pdf]

Needs Windows and Microsoft 365 Excel. The workbook's data sheets hold the dbt
gold tables (data/gold/*.csv) unchanged; every analysis cell is an Excel formula,
a Power Query step or a what-if data table over them, keyed on the municipality
chosen on the Dashboard. tests/ holds the saved workbook to the gold tables and
to model/reference.py.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client
from win32com.client import gencache

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import layout as L  # noqa: E402
import sheets  # noqa: E402
from xl import (  # noqa: E402
    BODY_FONT, FAIL_FILL, GREY, MUTED, NAVY, PASS_FILL, TEAL, XL_CALC_AUTOMATIC,
    XL_CALC_MANUAL, XL_CELL_VALUE, XL_EQUAL, XL_LANDSCAPE, XL_SRC_MODEL, XL_SRC_RANGE, XL_TYPE_PDF, XL_WORKBOOK,
    XL_YES, FAV, band, font, fx, header, numfmt, put, rgb, title, widths,
)

ROOT = HERE.parent
GOLD = ROOT / "data" / "gold"
SEEDS = ROOT / "dbt" / "seeds"
OUT = ROOT / "workbook" / L.WORKBOOK
PDF = ROOT / "docs" / "board_pack.pdf"
BUSY = (-2147418111, -2147417846)
CONN = 'OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location={};Extended Properties=""'

LAMBDAS = {
    "YV": ('=LAMBDA(column,yr,LET(r,XLOOKUP(SelId&":"&yr,tbl_Year[municipality_year],column,""),'
           'IF(ISREF(r),IF(ISBLANK(r),"",r),r)))',
           "The selected municipality's value in a tbl_Year column for a year; blank when not published."),
    "MONEY": ('=LAMBDA(x,IF(x="","–",IF(ABS(x)>=999500000,TEXT(x/1000000000,"$#,##0.00")&"B",IF(ABS(x)>=999500,'
              'TEXT(x/1000000,"$#,##0.0")&"M",TEXT(x/1000,"$#,##0")&"K"))))',
              "$1.23B / $4.5M / $350K style amounts for written commentary."),
}

M_CATEGORIES = """// Schedule 503 across the province, latest year: what BC's municipalities own,
// by category, and how much of it sits under an asset management plan.
let
    Source = Excel.CurrentWorkbook(){[Name="tbl_Assets"]}[Content],
    Typed = Table.TransformColumnTypes(Source, {{"year", Int64.Type}, {"historical_cost", type number},
        {"accumulated_amortization", type number}, {"additions", type number}, {"replacement_value", type number},
        {"asset_category", type text}, {"amp_status", type text}}),
    Latest = Table.SelectRows(Typed, each [year] = List.Max(Typed[year])),
    Grouped = Table.Group(Latest, {"asset_category"}, {
        {"municipalities", each List.Count(List.Select([replacement_value], each _ <> null and _ > 0)), Int64.Type},
        {"historical_cost", each List.Sum([historical_cost]), type number},
        {"accumulated_amortization", each List.Sum([accumulated_amortization]), type number},
        {"additions", each List.Sum([additions]), type number},
        {"replacement_value", each List.Sum([replacement_value]), type number},
        {"replacement_under_plan", each List.Sum(Table.SelectRows(_, each [amp_status] = "Yes")[replacement_value]),
            type number}}),
    Ratios = Table.AddColumn(Grouped, "share_under_plan",
        each if [replacement_value] = null or [replacement_value] = 0 then null
             else [replacement_under_plan] / [replacement_value], type number),
    Sorted = Table.Sort(Ratios, {{"replacement_value", Order.Descending}})
in
    Sorted"""

M_TIERS = """// The peer tiers: how many municipalities, and the median of the metrics the
// Dashboard benchmarks against, computed here in M rather than in the pipeline.
let
    Source = Excel.CurrentWorkbook(){[Name="tbl_Peers"]}[Content],
    Median = (values as list) => List.Median(List.RemoveNulls(values)),
    Grouped = Table.Group(Source, {"size_tier"}, {
        {"municipalities", each Table.RowCount(_), Int64.Type},
        {"median_population", each Median([population]), type number},
        {"median_revenue_per_capita", each Median([revenue_per_capita]), type number},
        {"median_limit_used", each Median([limit_used]), type number},
        {"median_reinvestment_ratio", each Median([reinvestment_ratio]), type number},
        {"median_house_total_charges", each Median([house_total_charges]), type number}}),
    Sorted = Table.Sort(Grouped, {{"size_tier", Order.Ascending}})
in
    Sorted"""


# ------------------------------------------------------------------ Excel session
def start_excel(visible: bool):
    pythoncom.CoInitialize()
    xl = gencache.EnsureDispatch(win32com.client.DispatchEx("Excel.Application")._oleobj_)
    xl.Visible = visible
    xl.DisplayAlerts = False
    xl.ScreenUpdating = visible
    xl.EnableEvents = False
    return xl


def patient(fn, *args, seconds: float = 300):
    deadline = time.time() + seconds
    while True:
        try:
            return fn(*args)
        except pywintypes.com_error as e:
            if e.hresult not in BUSY or time.time() > deadline:
                raise
            time.sleep(0.5)


def step(label: str, t0: float) -> None:
    print(f"[{time.time() - t0:6.1f}s] {label}", flush=True)


# ------------------------------------------------------------------ data
def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def kind_of(values: list[str]) -> str:
    seen = [v for v in values if v not in ("",)]
    if seen and all(v in ("true", "false") for v in seen):
        return "bool"
    try:
        [float(v) for v in seen]
        return "num"
    except ValueError:
        return "text"


def convert(value: str, kind: str):
    if value == "":
        return None
    if kind == "num":
        return float(value)
    if kind == "bool":
        return value == "true"
    return value


def write_table(ws, first_col: str, first_row: int, name: str, head, body) -> int:
    kinds = [kind_of([r[j] for r in body]) for j in range(len(head))]
    if "year" in head:          # years are integers, never 2,019.00
        kinds[head.index("year")] = "num"
    values = tuple(tuple(convert(v, k) for v, k in zip(r, kinds)) for r in body)
    top = ws.Range(f"{first_col}{first_row}")
    hdr = top.GetResize(1, len(head))
    hdr.NumberFormat = "@"
    hdr.Value = (tuple(head),)
    for j, k in enumerate(kinds):
        top.GetOffset(1, j).GetResize(len(values), 1).NumberFormat = "@" if k == "text" else "General"
    top.GetOffset(1, 0).GetResize(len(values), len(head)).Value = values
    lo = ws.ListObjects.Add(SourceType=XL_SRC_RANGE, Source=top.GetResize(len(values) + 1, len(head)),
                            XlListObjectHasHeaders=XL_YES)
    lo.Name = name
    lo.TableStyle = "TableStyleLight1"
    return len(values)


def data_sheets(wb) -> dict:
    counts = {}
    captions = {
        "Data_Municipal": "dbt gold: fct_municipal_year, one row per municipality and year",
        "Data_Assets": "dbt gold: fct_asset_category, schedule 503 by category",
        "Data_Tax": "dbt gold: fct_tax_class, schedule 707 by property class",
        "Data_Peers": "dbt gold: mart_peer_benchmark, the latest year with tier and province percentiles",
        "Data_Lists": "dbt gold: municipalities, the province by year, and the documented data gaps",
    }
    for sheet, caption in captions.items():
        title(wb.Worksheets(sheet), caption, "Loaded unchanged from data/gold/ (written by dbt) and dbt/seeds/. "
                                             "Formulas and Power Query read these tables by name.")
    for csv_name, (sheet, table, first) in L.TABLES.items():
        head, body = read_csv(GOLD / f"{csv_name}.csv")
        counts[table] = write_table(wb.Worksheets(sheet), first, 4, table, head, body)
    for csv_name, (sheet, table, first) in L.SEEDS.items():
        head, body = read_csv(SEEDS / f"{csv_name}.csv")
        counts[table] = write_table(wb.Worksheets(sheet), first, 4, table, head, body)
    return counts


# ------------------------------------------------------------------ names and inputs
def assumptions(wb) -> None:
    ws = wb.Worksheets("Assumptions")
    title(ws, "Assumptions and lists", "The selector, the names every sheet reads, and the list the Dashboard's "
                                       "dropdown offers. Plan drivers live on the Plan sheet, next to the data "
                                       "table that varies them.", span="H")
    band(ws, 4, "The selected municipality", "B", "H")
    rows = [
        ("SelId", "Municipality id", "=XLOOKUP(Selected,tbl_Dim[display_name],tbl_Dim[municipality_id])"),
        ("SelType", "Type", "=XLOOKUP(SelId,tbl_Dim[municipality_id],tbl_Dim[type_name])"),
        ("SelRD", "Regional district", "=XLOOKUP(SelId,tbl_Dim[municipality_id],tbl_Dim[regional_district])"),
        ("SelTier", "Peer tier", "=XLOOKUP(SelId,tbl_Dim[municipality_id],tbl_Dim[size_tier])"),
        ("SelTierLabel", "Peer tier, as shown", '=MID(SelTier,4,99)&" residents"'),
        ("SelTierCount", "Municipalities in the tier", "=COUNTIF(tbl_Peers[size_tier],SelTier)"),
        ("LatestYear", "Latest year published", "=MAX(tbl_Year[year])"),
        ("BaseYear", "Latest year with statements for the selection",
         '=MAXIFS(tbl_Year[year],tbl_Year[municipality_id],SelId,tbl_Year[total_revenue],"<>")'),
    ]
    for i, (name, label, formula) in enumerate(rows):
        r = 5 + i
        put(ws, f"B{r}", label)
        fx(ws, f"E{r}", formula)
        wb.Names.Add(Name=name, RefersTo=f"=Assumptions!$E${r}")
    band(ws, 15, "Active municipalities (the Dashboard's list)", "B", "H")
    fx(ws, "B16", "=SORT(FILTER(tbl_Dim[display_name],tbl_Dim[active]=TRUE))")
    wb.Names.Add(Name="ActiveList", RefersTo="=Assumptions!$B$16#")
    widths(ws, {"A": 2, "B": 36, "C:D": 4, "E": 30})


def lambdas(wb) -> None:
    for name, (formula, comment) in LAMBDAS.items():
        n = wb.Names.Add(Name=name, RefersTo=formula)
        n.Comment = comment


def power_query(wb) -> None:
    for name, m, sheet, table, caption in (
            ("Categories", M_CATEGORIES, "PQ_Categories", "tbl_Categories",
             "The province's assets by category, latest year (Power Query)"),
            ("Tiers", M_TIERS, "PQ_Tiers", "tbl_Tiers", "The peer tiers and their medians (Power Query)")):
        ws = wb.Worksheets(sheet)
        title(ws, caption, "Output of a Power Query query (Data > Queries & Connections) over the gold tables.")
        wb.Queries.Add(name, m, f"BC local government finance: {name}")
        conn = wb.Connections.Add2(f"Query - {name}", f"Connection to the '{name}' query.",
                                   CONN.format(name), f'"{name}"', 6, True, False)
        lo = ws.ListObjects.Add(SourceType=XL_SRC_MODEL, Source=conn, Destination=ws.Range("B4"))
        lo.TableStyle = "TableStyleLight1"
        to = lo.TableObject
        to.RowNumbers = False
        to.PreserveFormatting = True
        to.RefreshStyle = 1
        to.AdjustColumnWidth = True
        lo.DisplayName = table
        to.Refresh()
        ws.Columns("A").ColumnWidth = 2


# ------------------------------------------------------------------ Checks
def checks(wb, counts: dict, pos: dict) -> None:
    ws = wb.Worksheets("Checks")
    title(ws, "Checks: the model proves its own numbers", "Each control compares two independent routes to the "
                                                           "same figure, with a stated tolerance.", span="H")
    header(ws, 4, ["#", "Check", "Expected", "Actual", "Tolerance", "Status"])
    g = pos["plan"]["grid"]
    items = [
        ("Municipality-year rows loaded = dbt gold", counts["tbl_Year"], "=ROWS(tbl_Year)", 0),
        ("Asset rows loaded = dbt gold", counts["tbl_Assets"], "=ROWS(tbl_Assets)", 0),
        ("Tax-class rows loaded = dbt gold", counts["tbl_Tax"], "=ROWS(tbl_Tax)", 0),
        ("Peer rows = active municipalities", "=COUNTIF(tbl_Dim[active],TRUE)", "=ROWS(tbl_Peers)", 0),
        ("Every active municipality is in the Dashboard list", "=COUNTIF(tbl_Dim[active],TRUE)",
         "=ROWS(ActiveList)", 0),
        ("Selection: financial assets less liabilities = net financial assets, every year",
         0, "=SUMPRODUCT(ABS(N(+YV(tbl_Year[total_financial_assets],{2019,2020,2021,2022,2023,2024}))"
            "-N(+YV(tbl_Year[total_liabilities],{2019,2020,2021,2022,2023,2024}))"
            "-N(+YV(tbl_Year[net_financial_assets],{2019,2020,2021,2022,2023,2024}))))", 12),
        ("Selection: revenue less expenses = annual surplus, every year",
         0, "=SUMPRODUCT(ABS(N(+YV(tbl_Year[total_revenue],{2019,2020,2021,2022,2023,2024}))"
            "-N(+YV(tbl_Year[total_expenses],{2019,2020,2021,2022,2023,2024}))"
            "-N(+YV(tbl_Year[annual_surplus],{2019,2020,2021,2022,2023,2024}))))", 12),
        ("Selection: the liability limit is 25% of revenue for the limit", "=0.25*debt_revenue_for_limit",
         "=debt_limit", 1),
        ("Levy and class multiples reproduce the published residential rate", "=tax_res_rate_published",
         "=tax_res_rate_implied", 0.0001),
        ("Plan year 0 taxation = the base year's statements", "=YV(tbl_Year[taxation],BaseYear)",
         "=INDEX(plan_table,10,1)", 0.01),
        ("Plan: taxation grows only by the cost, capital and revenue changes", 0,
         "=ABS(INDEX(plan_table,10,6)-INDEX(plan_table,10,1)-(INDEX(plan_table,2,6)-INDEX(plan_table,2,1))"
         "-INDEX(plan_table,7,6)-INDEX(plan_table,9,6)+(INDEX(plan_table,3,6)-INDEX(plan_table,3,1)))", 0.01),
        ("Data table at the live drivers = the live plan", "=plan_avg_increase",
         f"=INDEX(plan_grid,MATCH(plan_closure,Plan!$C${g + 1}:$C${g + len(L.GRID_CLOSURE)},0),"
         f"MATCH(plan_debt,Plan!$D${g}:${chr(ord('C') + len(L.GRID_DEBT))}${g},0))", 1e-12),
        ("Peer tier percentiles computed here = the pipeline's, all metrics", 0,
         "=SUM(MAP(Peers!C6:C18,Peers!F6:F18,LAMBDA(k,f,ABS(N(f)-N(XLOOKUP(SelId,tbl_Peers[municipality_id],"
         "XLOOKUP(k&\"_tier_pct\",tbl_Peers[#Headers],tbl_Peers)))))))", 1e-9),
        ("Asset categories' replacement value = the municipality-year total",
         "=N(YV(tbl_Year[replacement_value],LatestYear))",
         "=SUMIFS(tbl_Assets[replacement_value],tbl_Assets[municipality_id],SelId,tbl_Assets[year],LatestYear)", 2),
        ("Power Query tiers cover every peer", "=ROWS(tbl_Peers)", "=SUM(tbl_Tiers[municipalities])", 0),
        ("Power Query categories cover the province's replacement value",
         '=SUMIFS(tbl_Assets[replacement_value],tbl_Assets[year],LatestYear)',
         "=SUM(tbl_Categories[replacement_value])", 1),
        ("Documented missing statements = municipality-years without revenue", "=ROWS(tbl_Missing)",
         '=COUNTIFS(tbl_Year[total_revenue],"")', 0),
    ]
    for i, (label, expected, actual, tol) in enumerate(items):
        r = 5 + i
        put(ws, f"B{r}", i + 1)
        put(ws, f"C{r}", label)
        if isinstance(expected, str):
            fx(ws, f"D{r}", expected)
        else:
            put(ws, f"D{r}", expected)
        fx(ws, f"E{r}", actual)
        put(ws, f"F{r}", tol)
        fx(ws, f"G{r}", f'=IF(ABS(E{r}-D{r})<=F{r},"PASS","FAIL")')
    last = 4 + len(items)
    fx(ws, "B2", f'=IF(COUNTIF(G5:G{last},"PASS")={len(items)},"All {len(items)} checks pass",'
                 f'COUNTIF(G5:G{last},"FAIL")&" of {len(items)} checks FAIL")')
    font(ws.Range("B2"), bold=True, size=12, color=NAVY)
    ok = ws.Range(f"G5:G{last}").FormatConditions.Add(XL_CELL_VALUE, XL_EQUAL, '="PASS"')
    ok.Interior.Color = rgb(PASS_FILL)
    bad = ws.Range(f"G5:G{last}").FormatConditions.Add(XL_CELL_VALUE, XL_EQUAL, '="FAIL"')
    bad.Interior.Color = rgb(FAIL_FILL)
    numfmt(ws.Range(f"D5:E{last}"), "#,##0.########")
    widths(ws, {"A": 2, "B": 4, "C": 70, "D:E": 18, "F": 10, "G": 9})
    wb.Names.Add(Name="checks_status", RefersTo=f"=Checks!$G$5:$G${last}")
    wb.Names.Add(Name="checks_summary", RefersTo="=Checks!$B$2")


# ------------------------------------------------------------------ Cover
def cover(wb) -> None:
    ws = wb.Worksheets("Cover")
    put(ws, "B2", "BC local government finance model")
    font(ws.Range("B2"), size=26, bold=True, color=NAVY, name="Aptos Display")
    ws.Rows(2).RowHeight = 40
    fx(ws, "B3", '="Every municipality in British Columbia, 2019-"&LatestYear&": benchmarks, infrastructure renewal, '
                 'a five-year financial plan, property tax by class and borrowing room. Now showing: "&Selected&"."')
    font(ws.Range("B3"), size=11, color=MUTED)
    put(ws, "B5", "Independent analysis of the Province of British Columbia's Local Government Statistics. Not "
                  "affiliated with or endorsed by any municipality or by the Province.")
    font(ws.Range("B5"), italic=True, size=9, color=MUTED)
    band(ws, 7, "How to use it", "B", "D")
    steps = ["Pick a municipality in the yellow cell on the Dashboard. Every sheet follows.",
             "Change the plan drivers on Plan: inflation, wages, how much of the renewal gap to close, and how "
             "much of it to borrow.",
             "Test a levy change on Tax, and a borrowing amount on Debt.",
             "Rank a municipality's tier on any metric on Peers.",
             "Checks proves the numbers; Province shows how far the asset data can be trusted."]
    for i, s in enumerate(steps):
        put(ws, f"B{8 + i}", f"{i + 1}. {s}")
    band(ws, 14, "Sheets", "B", "D")
    guide = [("Dashboard", "Eight tiles against the peer tier, five sentences written by formulas, two charts"),
             ("Profile", "Six years of revenue, expenses, position, debt, assets and tax"),
             ("Peers", "Thirteen metrics with tier and province percentiles; the tier ranked on any of them"),
             ("Assets", "Schedule 503 by category; renewal need and the reinvestment ratio"),
             ("Plan", "A five-year financial plan and a what-if data table over its two big choices"),
             ("Tax", "Assessment, rates and multiples by class; a levy-to-rates calculator"),
             ("Debt", "The legal servicing limit, the room left, and what it would borrow"),
             ("Province", "Totals by year and the asset data-quality screen"),
             ("Checks", "17 controls, each with a tolerance")]
    for i, (s, d) in enumerate(guide):
        r = 15 + i
        ws.Hyperlinks.Add(ws.Range(f"B{r}"), "", f"'{s}'!A1", "", s)
        put(ws, f"C{r}", d)
    band(ws, 25, "Sources", "B", "D")
    put(ws, "B26", "Province of British Columbia, Ministry of Municipal Affairs: Local Government Statistics, "
                   "schedules 201-707, 2019-2024. Open Government Licence – British Columbia.")
    put(ws, "B27", "Pipeline: pipeline/ (bronze and silver, held to contracts), dbt/ (gold marts and 31 data tests). "
                   "data/sources.json records every file's URL and SHA-256.")
    widths(ws, {"A": 2, "B": 20, "C": 110, "D": 2})


# ------------------------------------------------------------------ finish
PDF_ORDER = ["Cover", "Dashboard", "Profile", "Peers", "Assets", "Plan", "Tax", "Debt", "Province", "Checks"]


def finish(xl, wb) -> None:
    xl.ScreenUpdating = True
    for ws in wb.Worksheets:
        ws.Activate()
        win = xl.ActiveWindow
        win.DisplayGridlines = ws.Name.startswith(("Data_", "PQ_"))
        win.Zoom = 90
        ws.Range("A1").Select()
    xl.ScreenUpdating = False
    for name in PDF_ORDER:
        ws = wb.Worksheets(name)
        ps = ws.PageSetup
        ps.Orientation = XL_LANDSCAPE
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = 1
        ps.CenterFooter = "Independent analysis of BC Local Government Statistics · &A · page &P"
    colours = {"Dashboard": NAVY, "Checks": FAV}
    for ws in wb.Worksheets:
        ws.Tab.Color = rgb(colours.get(ws.Name, GREY if ws.Name.startswith(("Data_", "PQ_")) else TEAL))
    wb.Worksheets("Cover").Activate()


def export_pdf(wb, path: Path) -> None:
    wb.Worksheets(PDF_ORDER).Select()
    wb.ActiveSheet.ExportAsFixedFormat(XL_TYPE_PDF, str(path))
    wb.Worksheets("Cover").Select()


def calculate(xl) -> None:
    xl.Calculation = XL_CALC_AUTOMATIC
    patient(xl.CalculateFull)
    patient(xl.CalculateUntilAsyncQueriesDone)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--visible", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    xl = start_excel(args.visible)
    wb = None
    try:
        wb = xl.Workbooks.Add()
        xl.Calculation = XL_CALC_MANUAL
        wb.Worksheets(1).Name = L.SHEETS[0]
        for name in L.SHEETS[1:]:
            wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count)).Name = name
        wb.Styles("Normal").Font.Name = BODY_FONT
        wb.Styles("Normal").Font.Size = 10
        counts = data_sheets(wb)
        step("gold tables", t0)
        wb.Names.Add(Name="Selected", RefersTo="=Dashboard!$C$3")
        wb.Worksheets("Dashboard").Range("C3").Value = L.DEFAULT_MUNICIPALITY
        assumptions(wb)
        lambdas(wb)
        power_query(wb)
        step("names, LAMBDAs, Power Query", t0)
        pos: dict = {}
        for label, build in (("Profile", sheets.profile), ("Peers", sheets.peers), ("Assets", sheets.assets),
                             ("Plan", sheets.plan), ("Tax", sheets.tax), ("Debt", sheets.debt),
                             ("Province", sheets.province), ("Dashboard", sheets.dashboard)):
            build(wb, pos)
            step(label, t0)
        checks(wb, counts, pos)
        cover(wb)
        step("Checks and Cover", t0)
        calculate(xl)
        step("calculated", t0)
        finish(xl, wb)
        wb.BuiltinDocumentProperties("Title").Value = "BC local government finance model"
        wb.BuiltinDocumentProperties("Author").Value = "Kush Patel"
        OUT.parent.mkdir(exist_ok=True)
        wb.SaveAs(str(OUT), XL_WORKBOOK)
        step(f"saved {OUT.relative_to(ROOT)}", t0)
        print("checks:", patient(lambda: wb.Worksheets("Checks").Range("B2").Value))
        if not args.no_pdf:
            PDF.parent.mkdir(exist_ok=True)
            export_pdf(wb, PDF)
            step(f"exported {PDF.relative_to(ROOT)}", t0)
        wb.Close(False)
        wb = None
    finally:
        if wb is not None and not args.visible:
            wb.Close(False)
        if not args.visible:
            xl.Quit()


if __name__ == "__main__":
    main()
