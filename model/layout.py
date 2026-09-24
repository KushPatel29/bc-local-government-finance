"""Names and positions shared by the workbook builder and the tests."""
from __future__ import annotations

WORKBOOK = "BC_Local_Government_Finance_Model.xlsx"
DEFAULT_MUNICIPALITY = "Fernie"
YEARS = list(range(2019, 2025))

SHEETS = ["Cover", "Dashboard", "Profile", "Peers", "Assets", "Plan", "Tax", "Debt", "Province", "Checks",
          "Assumptions", "PQ_Categories", "PQ_Tiers", "Data_Municipal", "Data_Assets", "Data_Tax",
          "Data_Peers", "Data_Lists"]

# gold CSV -> (sheet, table name, first column)
TABLES = {
    "dim_municipality": ("Data_Lists", "tbl_Dim", "B"),
    "fct_municipal_year": ("Data_Municipal", "tbl_Year", "B"),
    "fct_asset_category": ("Data_Assets", "tbl_Assets", "B"),
    "fct_tax_class": ("Data_Tax", "tbl_Tax", "B"),
    "mart_peer_benchmark": ("Data_Peers", "tbl_Peers", "B"),
    "mart_province_trend": ("Data_Lists", "tbl_Province", "AA"),
}
SEEDS = {
    "missing_statements": ("Data_Lists", "tbl_Missing", "AZ"),
    "known_exceptions": ("Data_Lists", "tbl_Exceptions", "BE"),
}

# The metric catalogue: key (a column of tbl_Peers), label, number format, direction.
METRICS = [
    ("revenue_per_capita", "Revenue per resident", "$#,##0", "context"),
    ("expenses_per_capita", "Spending per resident", "$#,##0", "context"),
    ("municipal_tax_per_capita", "Municipal property tax per resident", "$#,##0", "context"),
    ("own_source_share", "Own-source share of revenue", "0.0%", "higher"),
    ("surplus_ratio", "Annual surplus as a share of revenue", "0.0%", "higher"),
    ("limit_used", "Share of the legal debt-servicing limit used", "0.0%", "lower"),
    ("debt_per_capita", "Long-term debt per resident", "$#,##0", "lower"),
    ("reserves_per_capita", "Reserves and surplus per resident", "$#,##0", "higher"),
    ("reserves_to_cash_expenses", "Reserves against a year of cash spending", '0.00"x"', "higher"),
    ("asset_consumption_ratio", "Share of asset life used up", "0.0%", "lower"),
    ("reinvestment_ratio", "Capital reinvestment against renewal need", '0.00"x"', "higher"),
    ("house_total_charges", "Taxes and charges on a representative house", "$#,##0", "lower"),
    ("effective_municipal_rate", "Municipal tax per $1,000 of assessment", "0.00", "lower"),
]
TILES = ["own_source_share", "limit_used", "reserves_to_cash_expenses", "asset_consumption_ratio",
         "reinvestment_ratio", "house_total_charges", "municipal_tax_per_capita", "debt_per_capita"]

# The profile: label, tbl_Year column, format ("m" money, "p" percent, "n" number, "x" ratio)
PROFILE = [
    ("band", "Revenue"),
    ("Taxation and grants in lieu", "taxation", "m"),
    ("Sale of services", "sale_of_services", "m"),
    ("Government transfers", "government_transfers", "m"),
    ("Investment income", "investment_income", "m"),
    ("Developer contributions", "developer_contributions", "m"),
    ("Total revenue", "total_revenue", "m"),
    ("band", "Expenses"),
    ("Cash expenses", "cash_expenses", "m"),
    ("Amortization", "amortization", "m"),
    ("Total expenses", "total_expenses", "m"),
    ("Annual surplus", "annual_surplus", "m"),
    ("band", "Financial position"),
    ("Financial assets", "total_financial_assets", "m"),
    ("Liabilities", "total_liabilities", "m"),
    ("Net financial assets", "net_financial_assets", "m"),
    ("Reserves and operating/capital surplus", "financial_reserves", "m"),
    ("Long-term debt", "long_term_debt", "m"),
    ("band", "Debt capacity"),
    ("Revenue for the liability limit", "revenue_for_limit", "m"),
    ("Liability servicing limit (25%)", "liability_servicing_limit", "m"),
    ("Actual debt servicing", "debt_servicing_cost", "m"),
    ("Share of the limit used", "limit_used", "p"),
    ("band", "Assets and tax"),
    ("Capital additions", "tca_additions", "m"),
    ("Replacement value", "replacement_value", "m"),
    ("Municipal property tax", "municipal_property_tax", "m"),
    ("Representative house value", "house_value", "m"),
    ("Taxes and charges, representative house", "house_total_charges", "m"),
    ("Population (BC Stats estimate)", "population", "n"),
]

# Five-year plan defaults.
PLAN = {
    "cpi": 0.025, "wage_growth": 0.035, "wage_share": 0.55, "gap_closure": 1.0, "debt_share": 0.30,
    "reserve_share": 0.20, "mfa_rate": 0.043, "term": 20,
}
PLAN_YEARS = 5
GRID_CLOSURE = [0.0, 0.25, 0.5, 0.75, 1.0]
GRID_DEBT = [0.0, 0.15, 0.3, 0.45, 0.6]
