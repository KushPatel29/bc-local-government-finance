"""The analysis sheets: Dashboard, Profile, Peers, Assets, Plan, Tax, Debt, Province.

Every figure is a formula over the gold tables (tbl_Year, tbl_Peers, tbl_Assets,
tbl_Tax, tbl_Province) keyed on the selected municipality, so changing the
selector on the Dashboard re-runs the whole workbook for any of BC's 161
municipalities. Named ranges mark every block the tests read.
"""
from __future__ import annotations

import layout as L
from xl import (
    AMBER, FAV, INK, MUTED, NAVY, RULE, TEAL, TILE, UNFAV, XL_BAR_CLUSTERED, XL_COLUMN_CLUSTERED,
    XL_COLUMN_STACKED, XL_EXPRESSION, XL_LEGEND_BOTTOM, XL_LINE_MARKERS, XL_RIGHT, XL_VALID_ALERT_STOP, XL_VALIDATE_LIST, XL_BETWEEN, band, box, col, fill, font, fx, header,
    input_cell, new_chart, numfmt, put, rgb, sign_colours, style_chart, title, total_row, widths,
)

MONEY = '$#,##0;($#,##0);"–"'
MONEY_M = '$#,##0.0,,"M";($#,##0.0,,"M");"–"'
PCT = '0.0%;(0.0%);"–"'
PCT_SIGNED = '+0.0%;-0.0%;0.0%'
RATIO = '0.00"x"'
YEAR_COLS = "DEFGHI"          # 2019..2024 on Profile


def names(wb, specs: dict) -> None:
    for name, ref in specs.items():
        wb.Names.Add(Name=name, RefersTo="=" + ref)


def peer_col(key: str) -> str:
    return f'XLOOKUP("{key}",tbl_Peers[#Headers],tbl_Peers)'


def peer_value(key: str) -> str:
    return f"XLOOKUP(SelId,tbl_Peers[municipality_id],{peer_col(key)},\"\")"


# ------------------------------------------------------------------ Profile
def profile(wb, pos: dict) -> None:
    ws = wb.Worksheets("Profile")
    title(ws, '="Six-year profile: "&Selected', "Every line is the Province's schedule for that year, looked up "
          "for the selected municipality. A dash means the Province published nothing for that year.", span="J")
    put(ws, "B5", "Line")
    put(ws, "C5", "Column")
    for j, y in enumerate(L.YEARS):
        put(ws, f"{YEAR_COLS[j]}5", y)
    put(ws, "J5", "Change")
    header(ws, 5, ["Line", "Column", *L.YEARS, "Change, first to last"])
    r = 6
    first = r
    for item in L.PROFILE:
        if item[0] == "band":
            band(ws, r, item[1], "B", "J")
            r += 1
            continue
        label, key, kind = item
        put(ws, f"B{r}", label)
        put(ws, f"C{r}", key)
        fx(ws, f"D{r}:I{r}", f"=YV(XLOOKUP($C{r},tbl_Year[#Headers],tbl_Year),D$5)")
        fmt = {"m": MONEY, "p": PCT, "n": "#,##0", "x": RATIO}[kind]
        numfmt(ws.Range(f"D{r}:I{r}"), fmt)
        if kind == "p":
            fx(ws, f"J{r}", f'=IFERROR(I{r}-D{r},"")')
            numfmt(ws.Range(f"J{r}"), '+0.0" pts";-0.0" pts";"–"')
        else:
            fx(ws, f"J{r}", f'=IFERROR(I{r}/D{r}-1,"")')
            numfmt(ws.Range(f"J{r}"), PCT_SIGNED)
        if key in ("total_revenue", "total_expenses", "net_financial_assets"):
            total_row(ws.Range(f"B{r}:J{r}"))
        r += 1
    last = r - 1
    font(ws.Range(f"C{first}:C{last}"), color=MUTED, size=8)
    widths(ws, {"A": 2, "B": 40, "C": 22, "D:I": 13, "J": 13})
    ws.Range(f"D5:J{last}").HorizontalAlignment = XL_RIGHT
    names(wb, {"profile_years": "Profile!$D$5:$I$5", "profile_keys": f"Profile!$C${first}:$C${last}",
               "profile_block": f"Profile!$D${first}:$I${last}"})
    pos["profile"] = (first, last)


# ------------------------------------------------------------------ Peers
def peers(wb, pos: dict) -> None:
    ws = wb.Worksheets("Peers")
    title(ws, '="Peers: "&Selected&" against "&SelTierLabel', "Every active municipality in the same population "
          "tier, from the latest year. Percentiles count only municipalities that report the metric; 100% is the "
          "highest value, which is the best only where the direction says so.", span="N")
    band(ws, 4, "The selected municipality on every metric", "B", "I")
    header(ws, 5, ["Metric", "Key", "Value", "Tier median", "Tier percentile", "Province percentile", "Direction",
                   "Reading"])
    r0 = 6
    for i, (key, label, fmt, direction) in enumerate(L.METRICS):
        r = r0 + i
        put(ws, f"B{r}", label)
        put(ws, f"C{r}", key)
        fx(ws, f"D{r}", f"={peer_value(key)}")
        fx(ws, f"E{r}", f'=XLOOKUP(SelId,tbl_Peers[municipality_id],{peer_col(key + "_tier_median")},"")')
        # The percentile is computed here, not looked up: the same (count below) /
        # (count reporting - 1) as the pipeline's percent_rank, so Checks can hold
        # the two to each other.
        fx(ws, f"F{r}", f'=LET(c,{peer_col(key)},v,D{r},t,tbl_Peers[size_tier]=SelTier,'
                        f'IF(v="","",SUM(t*(c<>"")*(c<v))/(SUM(t*(c<>""))-1)))')
        fx(ws, f"G{r}", f'=LET(c,{peer_col(key)},v,D{r},'
                        f'IF(v="","",SUM((c<>"")*(c<v))/(SUM(--(c<>""))-1)))')
        put(ws, f"H{r}", direction)
        fx(ws, f"I{r}", f'=IF(D{r}="","not reported",IF(H{r}="context",IF(D{r}>E{r},"above","below")&" the tier median",'
                        f'IF((D{r}>E{r})=(H{r}="higher"),"better","weaker")&" than the tier median"))')
        numfmt(ws.Range(f"D{r}:E{r}"), fmt)
    r1 = r0 + len(L.METRICS) - 1
    numfmt(ws.Range(f"F{r0}:G{r1}"), "0%")
    font(ws.Range(f"C{r0}:C{r1}"), color=MUTED, size=8)
    for rng, colour in ((f"I{r0}:I{r1}", None),):
        good = ws.Range(rng).FormatConditions.Add(XL_EXPRESSION, Formula1=f'=LEFT($I{r0},6)="better"')
        good.Font.Color = rgb(FAV)
        bad = ws.Range(rng).FormatConditions.Add(XL_EXPRESSION, Formula1=f'=LEFT($I{r0},6)="weaker"')
        bad.Font.Color = rgb(UNFAV)
    bar = ws.Range(f"F{r0}:F{r1}").FormatConditions.AddDatabar()
    bar.BarColor.Color = rgb("#9DB4CF")

    # --- the tier, ranked on a chosen metric
    k0 = r1 + 3
    band(ws, k0, "The tier, ranked", "B", "I")
    put(ws, f"B{k0 + 1}", "Rank the tier by")
    put(ws, f"D{k0 + 1}", "Share of the legal debt-servicing limit used")
    input_cell(ws.Range(f"D{k0 + 1}:F{k0 + 1}"))
    ws.Range(f"D{k0 + 1}:F{k0 + 1}").Merge()
    dv = ws.Range(f"D{k0 + 1}").Validation
    dv.Delete()
    dv.Add(XL_VALIDATE_LIST, XL_VALID_ALERT_STOP, XL_BETWEEN, f"=Peers!$B${r0}:$B${r1}")
    fx(ws, f"G{k0 + 1}", f"=XLOOKUP(D{k0 + 1},B{r0}:B{r1},C{r0}:C{r1})")
    font(ws.Range(f"G{k0 + 1}"), color=MUTED, size=8)
    header(ws, k0 + 2, ["Municipality", "Population", "Value", "Regional district"])
    h = k0 + 3
    fx(ws, f"B{h}", f'=LET(c,XLOOKUP(G{k0 + 1},tbl_Peers[#Headers],tbl_Peers),'
                    f'keep,(tbl_Peers[size_tier]=SelTier)*(c<>""),'
                    f'SORTBY(FILTER(HSTACK(tbl_Peers[display_name],tbl_Peers[population],c,'
                    f'tbl_Peers[regional_district]&""),keep),FILTER(c,keep),-1))')
    numfmt(ws.Range(f"C{h}:C{h + 120}"), "#,##0")
    numfmt(ws.Range(f"D{h}:D{h + 120}"), "#,##0.000")
    hi = ws.Range(f"B{h}:E{h + 120}").FormatConditions.Add(XL_EXPRESSION, Formula1=f"=$B{h}=Selected")
    hi.Interior.Color = rgb("#FFF1C7")
    hi.Font.Bold = True
    widths(ws, {"A": 2, "B": 42, "C": 24, "D:G": 13, "H": 10, "I": 30})
    names(wb, {"peer_benchmark": f"Peers!$B${r0}:$I${r1}", "peer_metric_input": f"Peers!$D${k0 + 1}",
               "peer_ranking": f"Peers!$B${h}"})
    pos["peers"] = (r0, r1)


# ------------------------------------------------------------------ Assets
def assets(wb, pos: dict) -> None:
    ws = wb.Worksheets("Assets")
    title(ws, '="Infrastructure: "&Selected&", "&LatestYear', "Schedule 503: what the municipality owns, what it "
          "would cost to replace, and whether capital spending keeps up with wear. The renewal need is re-derived, "
          "because the Province's own field is not usable as published (see Province).", span="L")
    band(ws, 4, "Assets by category, latest year", "B", "J")
    header(ws, 5, ["Category", "Historical cost", "Accumulated amortization", "Net book value", "Additions",
                   "Replacement value", "Life used up", "Asset management plan", "Replacement value share"])
    a = 6
    fx(ws, f"B{a}", '=LET(k,(tbl_Assets[municipality_id]=SelId)*(tbl_Assets[year]=LatestYear),'
                    'd,FILTER(HSTACK(tbl_Assets[asset_category],tbl_Assets[historical_cost],'
                    'tbl_Assets[accumulated_amortization],tbl_Assets[net_book_value],tbl_Assets[additions],'
                    'tbl_Assets[replacement_value],tbl_Assets[consumption_ratio],'
                    'SUBSTITUTE(tbl_Assets[amp_status]&"","_"," ")),k,""),'
                    'SORTBY(d,CHOOSECOLS(d,6),-1))')
    fx(ws, f"J{a}", f'=IFERROR(CHOOSECOLS(B{a}#,6)/SUM(CHOOSECOLS(B{a}#,6)),"")')
    numfmt(ws.Range(f"C{a}:G{a + 11}"), MONEY)
    numfmt(ws.Range(f"H{a}:H{a + 11}"), "0%")
    numfmt(ws.Range(f"J{a}:J{a + 11}"), "0%")
    s = a + 14
    band(ws, s, "Renewal: is capital spending keeping up with wear?", "B", "J")
    rows = [
        ("Data quality of the replacement values", "=YV(tbl_Year[asset_data_quality],LatestYear)", "@"),
        ("Replacement value against historical cost", "=YV(tbl_Year[replacement_to_cost],LatestYear)", RATIO),
        ("Amortization this year", "=YV(tbl_Year[amortization],LatestYear)", MONEY),
        ("Renewal need (amortization at replacement cost)", "=YV(tbl_Year[renewal_need],LatestYear)", MONEY),
        ("Capital additions, three-year average", "=YV(tbl_Year[tca_additions_3yr],LatestYear)", MONEY),
        ("Reinvestment ratio", "=YV(tbl_Year[reinvestment_ratio],LatestYear)", RATIO),
        ("Annual renewal gap", "=YV(tbl_Year[annual_renewal_gap],LatestYear)", MONEY),
        ("Share of replacement value under an asset management plan",
         "=YV(tbl_Year[amp_coverage],LatestYear)", "0%"),
        ("Share of asset life used up (depreciable assets)", "=YV(tbl_Year[asset_consumption_ratio],LatestYear)",
         "0%"),
    ]
    for i, (label, formula, fmt) in enumerate(rows):
        r = s + 1 + i
        put(ws, f"B{r}", label)
        fx(ws, f"E{r}", formula)
        numfmt(ws.Range(f"E{r}"), fmt)
        ws.Range(f"E{r}").HorizontalAlignment = XL_RIGHT
    r = s + 1 + len(rows)
    fx(ws, f"B{r + 1}", '=IF(E{0}<>"plausible","The replacement values do not pass the screen ("&E{0}&"), so no '
                        'renewal need is estimated for "&Selected&".",IF(E{1}<1,"Capital additions cover "&'
                        'TEXT(E{1},"0%")&" of the renewal need: "&MONEY(E{2})&" a year short of keeping pace '
                        'with wear.","Capital additions exceed the renewal need ("&TEXT(E{1},"0.00")&"x). They '
                        'include growth assets, so this is an upper bound on renewal."))'.format(
                            s + 1, s + 6, s + 7))
    font(ws.Range(f"B{r + 1}"), italic=True, color=INK)
    chart = new_chart(ws, XL_BAR_CLUSTERED, "L4", "S22", [("Replacement value", f"G{a}:G{a + 10}")],
                      f"B{a}:B{a + 10}", "Replacement value by category")
    chart.HasLegend = False
    chart.FullSeriesCollection(1).Format.Fill.ForeColor.RGB = rgb(NAVY)
    chart.Axes(2).TickLabels.NumberFormat = MONEY_M
    chart.Axes(1).ReversePlotOrder = True
    style_chart(chart)
    widths(ws, {"A": 2, "B": 30, "C:G": 14, "H": 11, "I": 16, "J": 12})
    names(wb, {"assets_table": f"Assets!$B${a}", "asset_renewal": f"Assets!$E${s + 1}:$E${s + len(rows)}",
               "asset_sentence": f"Assets!$B${r + 1}"})


# ------------------------------------------------------------------ Plan
PLAN_ROWS = [  # key, label, format
    ("year", "Year", "0"),
    ("cash_expenses", "Cash operating expenses", MONEY),
    ("non_tax_revenue", "Revenue other than taxation", MONEY),
    ("capital", "Capital program", MONEY),
    ("incremental_capital", "Capital above the base-year program", MONEY),
    ("new_borrowing", "New borrowing", MONEY),
    ("new_servicing", "Servicing on new borrowing", MONEY),
    ("reserve_draw", "Drawn from reserves", MONEY),
    ("tax_capital", "Capital funded from taxation", MONEY),
    ("taxation", "Taxation required", MONEY),
    ("tax_increase", "Increase on the year before", PCT_SIGNED),
    ("reserves", "Reserves and surplus, closing", MONEY),
    ("servicing", "Total debt servicing", MONEY),
    ("limit_used", "Share of the legal limit used", PCT),
    ("house_tax", "Municipal tax on the representative house", MONEY),
]


def plan(wb, pos: dict) -> None:
    ws = wb.Worksheets("Plan")
    title(ws, '="Five-year financial plan: "&Selected', "The plan the Community Charter (s.165) requires, built "
          "from the latest statements: costs grow with wages, prices and population; the renewal gap closes on a "
          "straight line to the target; new capital is funded from debt, reserves and taxation in the shares "
          "below. The output is the tax increase each year needs.", span="J")
    band(ws, 4, "Drivers (change the yellow cells)", "B", "J")
    drivers = [
        ("plan_cpi", "Inflation (CPI)", L.PLAN["cpi"], PCT),
        ("plan_wage", "Wage and contract growth", L.PLAN["wage_growth"], PCT),
        ("plan_wage_share", "Wage-like share of cash costs", L.PLAN["wage_share"], "0%"),
        ("plan_closure", "Share of the renewal gap closed by year 5", L.PLAN["gap_closure"], "0%"),
        ("plan_debt", "Share of new capital borrowed", L.PLAN["debt_share"], "0%"),
        ("plan_reserve", "Share of new capital from reserves", L.PLAN["reserve_share"], "0%"),
        ("plan_rate", "MFA borrowing rate", L.PLAN["mfa_rate"], "0.00%"),
        ("plan_term", "Borrowing term (years)", L.PLAN["term"], "0"),
    ]
    for i, (name, label, value, fmt) in enumerate(drivers):
        r = 5 + i
        put(ws, f"B{r}", label)
        put(ws, f"E{r}", value)
        numfmt(ws.Range(f"E{r}"), fmt)
        input_cell(ws.Range(f"E{r}"))
        names(wb, {name: f"Plan!$E${r}"})
    base = [  # derived from the statements
        ("plan_base_year", "Base year (latest with statements)", "=BaseYear", "0"),
        ("plan_pop_growth", "Population growth, two-year average",
         "=IFERROR((YV(tbl_Year[population],BaseYear)/YV(tbl_Year[population],BaseYear-2))^(1/2)-1,0)", PCT),
        ("plan_cost_growth", "Cost growth (wages, prices, population)",
         "=plan_wage_share*plan_wage+(1-plan_wage_share)*plan_cpi+plan_pop_growth", PCT),
        ("plan_rev_growth", "Growth in revenue other than taxation", "=plan_cpi+plan_pop_growth", PCT),
        ("plan_base_capital", "Base capital program (three-year average additions)",
         "=LET(a,YV(tbl_Year[tca_additions_3yr],BaseYear),IF(a=\"\",N(YV(tbl_Year[tca_additions],BaseYear)),a))",
         MONEY),
        ("plan_gap", "Annual renewal gap at the base year", "=N(YV(tbl_Year[annual_renewal_gap],BaseYear))", MONEY),
    ]
    for i, (name, label, formula, fmt) in enumerate(base):
        r = 5 + i
        put(ws, f"G{r}", label)
        fx(ws, f"J{r}", formula)
        numfmt(ws.Range(f"J{r}"), fmt)
        names(wb, {name: f"Plan!$J${r}"})
    font(ws.Range("G5:G10"), color=MUTED)

    t0 = 15
    band(ws, t0 - 1, "The plan", "B", "J")
    header(ws, t0, ["", "", *[f"Year {k}" for k in range(6)]])
    r = {key: t0 + 1 + i for i, (key, _l, _f) in enumerate(PLAN_ROWS)}
    for key, label, fmt in PLAN_ROWS:
        put(ws, f"B{r[key]}", label)
        numfmt(ws.Range(f"D{r[key]}:I{r[key]}"), fmt)
    fx(ws, f"D{r['year']}:I{r['year']}", f"=BaseYear+COLUMN()-COLUMN($D${r['year']})")
    t = "(COLUMN()-COLUMN($D$1))"      # 0 in the base-year column
    fx(ws, f"D{r['cash_expenses']}:I{r['cash_expenses']}",
       f"=YV(tbl_Year[cash_expenses],BaseYear)*(1+plan_cost_growth)^{t}")
    fx(ws, f"D{r['non_tax_revenue']}:I{r['non_tax_revenue']}",
       f"=(YV(tbl_Year[total_revenue],BaseYear)-YV(tbl_Year[taxation],BaseYear))*(1+plan_rev_growth)^{t}")
    fx(ws, f"D{r['capital']}:I{r['capital']}",
       f"=(plan_base_capital+plan_gap*plan_closure*{t}/{L.PLAN_YEARS})*(1+plan_cpi)^{t}")
    fx(ws, f"D{r['incremental_capital']}:I{r['incremental_capital']}", f"=D{r['capital']}-plan_base_capital")
    fx(ws, f"D{r['new_borrowing']}:I{r['new_borrowing']}", f"=plan_debt*D{r['incremental_capital']}")
    # Each year's borrowing is serviced from that year on: a sum of level payments.
    fx(ws, f"D{r['new_servicing']}:I{r['new_servicing']}",
       f"=SUM(PMT(plan_rate,plan_term,-$D{r['new_borrowing']}:D{r['new_borrowing']}))")
    fx(ws, f"D{r['reserve_draw']}:I{r['reserve_draw']}", f"=plan_reserve*D{r['incremental_capital']}")
    fx(ws, f"D{r['tax_capital']}:I{r['tax_capital']}",
       f"=(1-plan_debt-plan_reserve)*D{r['incremental_capital']}")
    fx(ws, f"D{r['taxation']}:I{r['taxation']}",
       f"=YV(tbl_Year[taxation],BaseYear)+(D{r['cash_expenses']}-$D{r['cash_expenses']})+D{r['new_servicing']}"
       f"+D{r['tax_capital']}-(D{r['non_tax_revenue']}-$D{r['non_tax_revenue']})")
    fx(ws, f"E{r['tax_increase']}:I{r['tax_increase']}", f"=E{r['taxation']}/D{r['taxation']}-1")
    fx(ws, f"D{r['reserves']}:I{r['reserves']}",
       f"=YV(tbl_Year[financial_reserves],BaseYear)-SUM($D{r['reserve_draw']}:D{r['reserve_draw']})")
    fx(ws, f"D{r['servicing']}:I{r['servicing']}", f"=YV(tbl_Year[debt_servicing_cost],BaseYear)+D{r['new_servicing']}")
    fx(ws, f"D{r['limit_used']}:I{r['limit_used']}",
       f"=D{r['servicing']}/(0.25*YV(tbl_Year[revenue_for_limit],BaseYear)*(D{r['taxation']}+D{r['non_tax_revenue']})"
       f"/($D{r['taxation']}+$D{r['non_tax_revenue']}))")
    fx(ws, f"D{r['house_tax']}:I{r['house_tax']}",
       f"=YV(tbl_Year[house_municipal_tax],BaseYear)*D{r['taxation']}/$D{r['taxation']}")
    for key in ("taxation",):
        total_row(ws.Range(f"B{r[key]}:I{r[key]}"))
    sign_colours(ws.Range(f"E{r['tax_increase']}:I{r['tax_increase']}"), reverse=True)
    last = t0 + len(PLAN_ROWS)
    o = last + 2
    put(ws, f"B{o}", "Average tax increase a year, years 1 to 5")
    fx(ws, f"E{o}", f"=(I{r['taxation']}/D{r['taxation']})^(1/{L.PLAN_YEARS})-1")
    numfmt(ws.Range(f"E{o}"), PCT_SIGNED)
    font(ws.Range(f"B{o}:E{o}"), bold=True)
    fx(ws, f"B{o + 1}", f'="Closing "&TEXT(plan_closure,"0%")&" of the renewal gap by year 5, borrowing "&'
                        f'TEXT(plan_debt,"0%")&" of the new capital, needs municipal tax increases averaging "&'
                        f'TEXT(E{o},"0.0%")&" a year. The representative house\'s municipal tax goes from "&'
                        f'TEXT(D{r["house_tax"]},"$#,##0")&" to "&TEXT(I{r["house_tax"]},"$#,##0")&", and debt '
                        f'servicing reaches "&TEXT(I{r["limit_used"]},"0%")&" of the legal limit."')
    font(ws.Range(f"B{o + 1}"), italic=True)
    names(wb, {"plan_table": f"Plan!$D${t0 + 1}:$I${last}", "plan_avg_increase": f"Plan!$E${o}",
               "plan_year1_increase": f"Plan!$E${r['tax_increase']}",
               "plan_sentence": f"Plan!$B${o + 1}"})

    # --- what-if: gap closure down the side, debt share across the top
    g = o + 4
    band(ws, g - 1, "What-if data table: average tax increase by gap closure and debt share", "B", "J")
    put(ws, f"B{g}", "Gap closed ↓   Debt share →")
    font(ws.Range(f"B{g}"), color=MUTED, italic=True)
    fx(ws, f"C{g}", f"=E{o}")
    for j, d in enumerate(L.GRID_DEBT):
        put(ws, f"{col(4 + j)}{g}", d)
    for i, c in enumerate(L.GRID_CLOSURE):
        put(ws, f"C{g + 1 + i}", c)
    corner = ws.Range(f"C{g}").GetResize(len(L.GRID_CLOSURE) + 1, len(L.GRID_DEBT) + 1)
    corner.Table(ws.Range("E9"), ws.Range("E8"))       # row input: debt share; column input: gap closure
    grid = ws.Range(f"D{g + 1}").GetResize(len(L.GRID_CLOSURE), len(L.GRID_DEBT))
    numfmt(grid, PCT_SIGNED)
    numfmt(ws.Range(f"D{g}").GetResize(1, len(L.GRID_DEBT)), "0%")
    numfmt(ws.Range(f"C{g + 1}").GetResize(len(L.GRID_CLOSURE), 1), "0%")
    font(ws.Range(f"C{g}"), color=MUTED, size=8)
    numfmt(ws.Range(f"C{g}"), PCT_SIGNED)
    scale = grid.FormatConditions.AddColorScale(3)
    scale.ColorScaleCriteria(1).FormatColor.Color = rgb("#BFE3CB")
    scale.ColorScaleCriteria(2).FormatColor.Color = rgb("#FFFFFF")
    scale.ColorScaleCriteria(3).FormatColor.Color = rgb("#F4C7C0")
    names(wb, {"plan_grid": f"Plan!$D${g + 1}:${col(3 + len(L.GRID_DEBT))}${g + len(L.GRID_CLOSURE)}"})

    chart = new_chart(ws, XL_COLUMN_CLUSTERED, "L4", "S22",
                      [("Taxation required", f"D{r['taxation']}:I{r['taxation']}")], f"D{r['year']}:I{r['year']}",
                      "Taxation required, base year and plan")
    chart.HasLegend = False
    chart.FullSeriesCollection(1).Format.Fill.ForeColor.RGB = rgb(NAVY)
    chart.Axes(2).TickLabels.NumberFormat = MONEY_M
    style_chart(chart)
    widths(ws, {"A": 2, "B": 40, "C": 12, "D:I": 13, "J": 14})
    pos["plan"] = {"rows": r, "avg": o, "grid": g}


# ------------------------------------------------------------------ Tax
def tax(wb, pos: dict) -> None:
    ws = wb.Worksheets("Tax")
    title(ws, '="Property tax by class: "&Selected&", "&LatestYear', "Schedule 707. BC sets each class's rate as "
          "a multiple of the residential rate, so one number, the residential rate, sets them all. The calculator "
          "turns a levy change into the rates that raise it.", span="L")
    band(ws, 4, "The classes", "B", "J")
    header(ws, 5, ["Property class", "Assessment", "Rate per $1,000", "Class multiple", "Variable-rate taxes",
                   "Flat and other taxes", "Municipal taxes", "Share of taxes", "Assessment × multiple"])
    a = 6
    fx(ws, f"B{a}", '=LET(k,(tbl_Tax[municipality_id]=SelId)*(tbl_Tax[year]=LatestYear),'
                    'd,FILTER(HSTACK(tbl_Tax[property_class],tbl_Tax[assessment],tbl_Tax[municipal_rate],'
                    'tbl_Tax[class_multiple],tbl_Tax[variable_rate_taxes],tbl_Tax[flat_and_other_taxes],'
                    'tbl_Tax[municipal_taxes]),k,""),SORTBY(d,CHOOSECOLS(d,7),-1))')
    fx(ws, f"I{a}", f'=IFERROR(CHOOSECOLS(B{a}#,7)/SUM(CHOOSECOLS(B{a}#,7)),"")')
    fx(ws, f"J{a}", f'=IFERROR(CHOOSECOLS(B{a}#,2)*CHOOSECOLS(B{a}#,4),"")')
    numfmt(ws.Range(f"C{a}:C{a + 9}"), MONEY)
    numfmt(ws.Range(f"D{a}:D{a + 9}"), "0.0000")
    numfmt(ws.Range(f"E{a}:E{a + 9}"), "0.00")
    numfmt(ws.Range(f"F{a}:H{a + 9}"), MONEY)
    numfmt(ws.Range(f"I{a}:I{a + 9}"), "0.0%")
    numfmt(ws.Range(f"J{a}:J{a + 9}"), MONEY)
    c = a + 12
    band(ws, c, "Levy to rates", "B", "J")
    lines = [
        ("tax_variable_levy", "Variable-rate levy this year", f"=SUM(CHOOSECOLS(B{a}#,5))", MONEY),
        ("tax_weighted_base", "Assessment weighted by class multiples", f"=SUM(J{a}#)", MONEY),
        ("tax_res_rate_implied", "Residential rate the levy implies (per $1,000)",
         "=tax_variable_levy*1000/tax_weighted_base", "0.00000"),
        ("tax_res_rate_published", "Residential rate the Province publishes",
         f'=XLOOKUP("Residential",CHOOSECOLS(B{a}#,1),CHOOSECOLS(B{a}#,3),"")', "0.00000"),
        ("tax_levy_change", "Levy change to test (defaults to plan year 1)", "=plan_year1_increase", PCT_SIGNED),
        ("tax_res_rate_new", "New residential rate", "=tax_res_rate_implied*(1+tax_levy_change)", "0.00000"),
        ("tax_house_value", "Representative house value", "=YV(tbl_Year[house_value],LatestYear)", MONEY),
        ("tax_house_now", "Municipal tax on it now", "=YV(tbl_Year[house_municipal_tax],LatestYear)", MONEY),
        ("tax_house_new", "Municipal tax on it after the change", "=tax_house_now*(1+tax_levy_change)", MONEY),
    ]
    for i, (name, label, formula, fmt) in enumerate(lines):
        r = c + 1 + i
        put(ws, f"B{r}", label)
        fx(ws, f"F{r}", formula)
        numfmt(ws.Range(f"F{r}"), fmt)
        names(wb, {name: f"Tax!$F${r}"})
    input_cell(ws.Range(f"F{c + 5}"))
    r = c + 2 + len(lines)
    fx(ws, f"B{r}", '="The levy and the class multiples imply a residential rate of "&TEXT(tax_res_rate_implied,'
                    '"0.0000")&" per $1,000; the Province publishes "&TEXT(tax_res_rate_published,"0.0000")&'
                    '". A "&TEXT(tax_levy_change,"+0.0%;-0.0%")&" levy change moves it to "&TEXT(tax_res_rate_new,'
                    '"0.0000")&", and the representative house\'s municipal tax from "&TEXT(tax_house_now,'
                    '"$#,##0")&" to "&TEXT(tax_house_new,"$#,##0")&"."')
    font(ws.Range(f"B{r}"), italic=True)
    widths(ws, {"A": 2, "B": 34, "C:H": 14, "I": 11, "J": 16})
    names(wb, {"tax_table": f"Tax!$B${a}", "tax_sentence": f"Tax!$B${r}"})


# ------------------------------------------------------------------ Debt
def debt(wb, pos: dict) -> None:
    ws = wb.Worksheets("Debt")
    title(ws, '="Borrowing room: "&Selected&", "&BaseYear', "The Community Charter caps annual liability servicing "
          "at 25% of revenue (B.C. Reg. 254/2004). Schedule 602.1 reports the limit and what is used; the "
          "calculator turns the room left into a borrowing amount.", span="J")
    band(ws, 4, "The limit", "B", "G")
    lines = [
        ("debt_revenue_for_limit", "Revenue for the purposes of the limit",
         "=YV(tbl_Year[revenue_for_limit],BaseYear)", MONEY),
        ("debt_limit", "Liability servicing limit (25%)", "=YV(tbl_Year[liability_servicing_limit],BaseYear)",
         MONEY),
        ("debt_servicing", "Actual debt servicing", "=YV(tbl_Year[debt_servicing_cost],BaseYear)", MONEY),
        ("debt_capacity", "Servicing capacity available", "=YV(tbl_Year[servicing_capacity],BaseYear)", MONEY),
        ("debt_limit_used", "Share of the limit used", "=debt_servicing/debt_limit", PCT),
        ("debt_outstanding", "Long-term debt outstanding", "=YV(tbl_Year[long_term_debt],BaseYear)", MONEY),
    ]
    for i, (name, label, formula, fmt) in enumerate(lines):
        r = 5 + i
        put(ws, f"B{r}", label)
        fx(ws, f"F{r}", formula)
        numfmt(ws.Range(f"F{r}"), fmt)
        names(wb, {name: f"Debt!$F${r}"})
    b = 5 + len(lines) + 2
    band(ws, b, "Borrowing calculator", "B", "G")
    calc = [
        ("debt_rate", "Borrowing rate", "=plan_rate", "0.00%", True),
        ("debt_term", "Term (years)", "=plan_term", "0", True),
        ("debt_amount", "Amount to borrow", 10_000_000, MONEY, True),
        ("debt_payment", "Annual servicing on it", "=PMT(debt_rate,debt_term,-debt_amount)", MONEY, False),
        ("debt_capacity_after", "Capacity left after it", "=debt_capacity-debt_payment", MONEY, False),
        ("debt_max_borrowing", "Most the remaining capacity could service",
         "=PV(debt_rate,debt_term,-debt_capacity)", MONEY, False),
    ]
    for i, (name, label, value, fmt, is_input) in enumerate(calc):
        r = b + 1 + i
        put(ws, f"B{r}", label)
        put(ws, f"F{r}", value)
        numfmt(ws.Range(f"F{r}"), fmt)
        if is_input:
            input_cell(ws.Range(f"F{r}"))
        names(wb, {name: f"Debt!$F${r}"})
    r = b + 2 + len(calc)
    fx(ws, f"B{r}", '=Selected&" uses "&TEXT(debt_limit_used,"0%")&" of its legal servicing limit. The "&'
                    'MONEY(debt_capacity)&" a year still available would service about "&MONEY(debt_max_borrowing)'
                    '&" of new borrowing at "&TEXT(debt_rate,"0.0%")&" over "&debt_term&" years."')
    font(ws.Range(f"B{r}"), italic=True)
    t = r + 2
    band(ws, t, "Six years of servicing against the limit", "B", "G")
    header(ws, t + 1, ["Year", "Limit", "Servicing", "Share used"])
    for j, y in enumerate(L.YEARS):
        rr = t + 2 + j
        put(ws, f"B{rr}", y)
        fx(ws, f"C{rr}", f"=YV(tbl_Year[liability_servicing_limit],B{rr})")
        fx(ws, f"D{rr}", f"=YV(tbl_Year[debt_servicing_cost],B{rr})")
        fx(ws, f"E{rr}", f'=IFERROR(D{rr}/C{rr},"")')
        numfmt(ws.Range(f"C{rr}:D{rr}"), MONEY)
        numfmt(ws.Range(f"E{rr}"), PCT)
    chart = new_chart(ws, XL_LINE_MARKERS, "I4", "P20",
                      [("Share of the limit used", f"E{t + 2}:E{t + 7}")], f"B{t + 2}:B{t + 7}",
                      "Share of the legal debt-servicing limit used")
    chart.HasLegend = False
    chart.Axes(2).TickLabels.NumberFormat = "0%"
    chart.FullSeriesCollection(1).Format.Line.ForeColor.RGB = rgb(TEAL)
    style_chart(chart)
    widths(ws, {"A": 2, "B": 44, "C:E": 14, "F": 16, "G": 4})
    names(wb, {"debt_sentence": f"Debt!$B${r}", "debt_history": f"Debt!$B${t + 2}:$E${t + 7}"})


# ------------------------------------------------------------------ Province
def province(wb, pos: dict) -> None:
    ws = wb.Worksheets("Province")
    title(ws, "The province: 161 municipalities, and how far their asset data can be trusted", "Totals and "
          "medians by year from mart_province_trend, and the data-quality screen behind every renewal figure in "
          "this workbook.", span="L")
    band(ws, 4, "By year", "B", "J")
    header(ws, 5, ["Year", "Municipalities", "Revenue", "Expenses", "Long-term debt", "Replacement value",
                   "Median limit used", "Median house charges", "Replacement values plausible"])
    for j, y in enumerate(L.YEARS):
        r = 6 + j
        put(ws, f"B{r}", y)
        for c, key, fmt in (("C", "municipalities", "0"), ("D", "total_revenue", MONEY_M),
                            ("E", "total_expenses", MONEY_M), ("F", "long_term_debt", MONEY_M),
                            ("G", "replacement_value", MONEY_M), ("H", "median_limit_used", PCT),
                            ("I", "median_house_total_charges", MONEY), ("J", "assets_plausible", "0")):
            fx(ws, f"{c}{r}", f'=XLOOKUP($B{r},tbl_Province[year],tbl_Province[{key}])')
            numfmt(ws.Range(f"{c}{r}"), fmt)
    s = 14
    band(ws, s, "Latest year: the renewal picture", "B", "J")
    facts = [
        ("prov_screened", "Municipalities whose replacement values pass the screen",
         "=XLOOKUP(LatestYear,tbl_Province[year],tbl_Province[screened_for_renewal])", "0"),
        ("prov_below", "…of which reinvest less than their renewal need",
         "=XLOOKUP(LatestYear,tbl_Province[year],tbl_Province[below_renewal_need])", "0"),
        ("prov_reinvestment", "Their combined reinvestment ratio",
         "=XLOOKUP(LatestYear,tbl_Province[year],tbl_Province[reinvestment_ratio])", RATIO),
        ("prov_not_reported", "Municipalities reporting no replacement value",
         "=XLOOKUP(LatestYear,tbl_Province[year],tbl_Province[assets_not_reported])", "0"),
        ("prov_amp_full", "Municipalities with every asset class under a management plan",
         "=XLOOKUP(LatestYear,tbl_Province[year],tbl_Province[fully_covered_by_amp])", "0"),
        ("prov_missing", "Municipality-years with no statements published (2019-2024)",
         "=ROWS(tbl_Missing)", "0"),
        ("prov_vancouver_rate", "Vancouver's reported renewal need, as a share of its replacement value",
         '=XLOOKUP("vancouver-c:"&LatestYear,tbl_Year[municipality_year],tbl_Year[reported_need_rate])', "0%"),
    ]
    for i, (name, label, formula, fmt) in enumerate(facts):
        r = s + 1 + i
        put(ws, f"B{r}", label)
        fx(ws, f"H{r}", formula)
        numfmt(ws.Range(f"H{r}"), fmt)
        names(wb, {name: f"Province!$H${r}"})
    r = s + 2 + len(facts)
    fx(ws, f"B{r}", '="In "&LatestYear&", "&prov_screened&" municipalities report replacement values that pass the '
                    'screen; "&prov_below&" of them invested less over three years than their assets wore out. The '
                    'field the Province labels annual replacement need is not usable as published: Vancouver\'s is "'
                    '&TEXT(prov_vancouver_rate,"0%")&" of its replacement value a year."')
    font(ws.Range(f"B{r}"), italic=True)
    chart = new_chart(ws, XL_COLUMN_CLUSTERED, "L4", "S20",
                      [("Replacement values plausible", "J6:J11")], "B6:B11",
                      "Municipalities with plausible replacement values")
    chart.HasLegend = False
    chart.FullSeriesCollection(1).Format.Fill.ForeColor.RGB = rgb(TEAL)
    style_chart(chart)
    widths(ws, {"A": 2, "B": 12, "C": 13, "D:G": 14, "H": 13, "I": 14, "J": 14})
    ws.Columns("B").ColumnWidth = 12
    names(wb, {"province_trend": "Province!$B$6:$J$11", "province_sentence": f"Province!$B${r}"})


# ------------------------------------------------------------------ Dashboard
def dashboard(wb, pos: dict) -> None:
    ws = wb.Worksheets("Dashboard")
    put(ws, "B1", '="BC local government finance: "&Selected')
    fx(ws, "B1", '="BC local government finance: "&Selected')
    font(ws.Range("B1"), size=20, bold=True, color=NAVY, name="Aptos Display")
    ws.Rows(1).RowHeight = 32
    put(ws, "B3", "Municipality")
    font(ws.Range("B3"), bold=True)
    put(ws, "C3", L.DEFAULT_MUNICIPALITY)
    input_cell(ws.Range("C3:E3"))
    ws.Range("C3:E3").Merge()
    font(ws.Range("C3"), bold=True, size=12)
    dv = ws.Range("C3").Validation
    dv.Delete()
    dv.Add(XL_VALIDATE_LIST, XL_VALID_ALERT_STOP, XL_BETWEEN, "=ActiveList")
    fx(ws, "G3", '=SelType&" in the "&SelRD&" regional district · population "&TEXT(YV(tbl_Year[population],'
                 'LatestYear),"#,##0")&" · peer tier "&SelTierLabel&" ("&SelTierCount&" municipalities) · '
                 'statements through "&BaseYear')
    font(ws.Range("G3"), color=MUTED)

    # KPI tiles: two rows of four
    for i, key in enumerate(L.TILES):
        _k, label, fmt, direction = next(m for m in L.METRICS if m[0] == key)
        c1 = col(2 + (i % 4) * 3)
        c3 = col(4 + (i % 4) * 3)
        top = 5 + (i // 4) * 6
        rng = ws.Range(f"{c1}{top}:{c3}{top + 4}")
        fill(rng, TILE)
        box(rng, RULE)
        for rr in range(top, top + 5):
            ws.Range(f"{c1}{rr}:{c3}{rr}").Merge()
        put(ws, f"{c1}{top}", label)
        font(ws.Range(f"{c1}{top}"), size=9, bold=True, color=MUTED)
        ws.Range(f"{c1}{top}").WrapText = True
        ws.Rows(top).RowHeight = 26
        fx(ws, f"{c1}{top + 1}", f'=LET(v,{peer_value(key)},IF(v="","not reported",v))')
        numfmt(ws.Range(f"{c1}{top + 1}"), fmt)
        font(ws.Range(f"{c1}{top + 1}"), size=20, bold=True, color=NAVY, name="Aptos Display")
        ws.Range(f"{c1}{top + 1}").HorizontalAlignment = -4131
        ws.Rows(top + 1).RowHeight = 30
        fx(ws, f"{c1}{top + 2}", f'="tier median "&TEXT(XLOOKUP(SelId,tbl_Peers[municipality_id],'
                                 f'{peer_col(key + "_tier_median")}),"{fmt.replace(chr(34), chr(34) * 2)}")')
        font(ws.Range(f"{c1}{top + 2}"), size=9, color=MUTED)
        fx(ws, f"{c1}{top + 3}", f"=XLOOKUP(\"{key}\",Peers!$C$6:$C$18,Peers!$I$6:$I$18)")
        font(ws.Range(f"{c1}{top + 3}"), size=9, bold=True)
        good = ws.Range(f"{c1}{top + 3}").FormatConditions.Add(XL_EXPRESSION,
                                                               Formula1=f'=LEFT(${c1}${top + 3},6)="better"')
        good.Font.Color = rgb(FAV)
        bad = ws.Range(f"{c1}{top + 3}").FormatConditions.Add(XL_EXPRESSION,
                                                              Formula1=f'=LEFT(${c1}${top + 3},6)="weaker"')
        bad.Font.Color = rgb(UNFAV)
        fx(ws, f"{c1}{top + 4}", f'=IFERROR("percentile in tier: "&TEXT(XLOOKUP("{key}",Peers!$C$6:$C$18,'
                                 f'Peers!$F$6:$F$18),"0%"),"")')
        font(ws.Range(f"{c1}{top + 4}"), size=8, color=MUTED)
    names(wb, {"dash_tiles": "Dashboard!$B$6:$M$6,Dashboard!$B$12:$M$12"})

    band(ws, 17, "What the numbers say", "B", "M")
    sentences = [
        '=Selected&", "&LatestYear&": revenue "&MONEY(YV(tbl_Year[total_revenue],BaseYear))&", expenses "&'
        'MONEY(YV(tbl_Year[total_expenses],BaseYear))&", a surplus of "&MONEY(YV(tbl_Year[annual_surplus],'
        'BaseYear))&" ("&TEXT(YV(tbl_Year[surplus_ratio],BaseYear),"0.0%")&" of revenue); "&TEXT(YV(tbl_Year['
        'own_source_share],BaseYear),"0%")&" of revenue is its own."',
        "=debt_sentence",
        "=asset_sentence",
        "=plan_sentence",
        '="A representative "&TEXT(YV(tbl_Year[house_value],LatestYear),"$#,##0")&" house pays "&TEXT(YV('
        'tbl_Year[house_total_charges],LatestYear),"$#,##0")&" in property taxes and charges, against a tier '
        'median of "&TEXT(XLOOKUP(SelId,tbl_Peers[municipality_id],tbl_Peers[house_total_charges_tier_median]),'
        '"$#,##0")&"; "&TEXT(YV(tbl_Year[house_municipal_share],LatestYear),"0%")&" of it is the municipal share."',
    ]
    for i, s in enumerate(sentences):
        r = 18 + i
        fx(ws, f"B{r}", s)
        ws.Range(f"B{r}:M{r}").Merge()
        ws.Range(f"B{r}").WrapText = True
        ws.Rows(r).RowHeight = 30
    names(wb, {"dash_commentary": "Dashboard!$B$18:$B$22"})

    # charts from the profile
    p0, _p1 = pos["profile"]
    rows = {key: p0 + i for i, (key) in enumerate(_profile_keys())}
    rev = new_chart(ws, XL_COLUMN_STACKED, "B24", "G40",
                    [(lab, f"Profile!D{rows[k]}:I{rows[k]}") for lab, k in (
                        ("Taxation", "taxation"), ("Sale of services", "sale_of_services"),
                        ("Government transfers", "government_transfers"),
                        ("Investment income", "investment_income"))],
                    "Profile!D5:I5", "Revenue by source")
    rev.Axes(2).TickLabels.NumberFormat = MONEY_M
    rev.HasLegend = True
    rev.Legend.Position = XL_LEGEND_BOTTOM
    for i, colour in enumerate((NAVY, TEAL, AMBER, "#9DB4CF")):
        rev.FullSeriesCollection(i + 1).Format.Fill.ForeColor.RGB = rgb(colour)
    style_chart(rev)
    lim = new_chart(ws, XL_LINE_MARKERS, "H24", "M40",
                    [("Share of the limit used", f"Profile!D{rows['limit_used']}:I{rows['limit_used']}")],
                    "Profile!D5:I5", "Debt servicing against the legal limit")
    lim.HasLegend = False
    lim.Axes(2).TickLabels.NumberFormat = "0%"
    lim.FullSeriesCollection(1).Format.Line.ForeColor.RGB = rgb(TEAL)
    style_chart(lim)
    put(ws, "B42", "Independent analysis of the Province of British Columbia's Local Government Statistics "
                   "(Open Government Licence – British Columbia). Not affiliated with or endorsed by any "
                   "municipality or the Province. Built in Excel by Kush Patel.")
    font(ws.Range("B42"), size=8, color=MUTED, italic=True)
    widths(ws, {"A": 2, "B:M": 11})


def _profile_keys() -> list[str]:
    out = []
    for item in L.PROFILE:
        out.append("band" if item[0] == "band" else item[1])
    return out
