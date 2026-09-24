"""What each schedule is allowed to look like, year by year.

The Province's spreadsheets drift. Between 2019 and 2024 a header gained a
footnote digit ("Major Industry1"), abbreviations were spelt out ("Bus. and
Other"), population columns carry their census year, the liabilities schedule
was restructured in 2024 and the fund-balance columns in 2023, and new lines
appeared (asset retirement accretion, the approval-free liability zone).
Municipalities were renamed (Queen Charlotte is now Daajing Giids), one was
dissolved (Jumbo Glacier), and from 2021 the Province dropped the " - C" / " - D"
suffix, so "Langley" is two municipalities told apart only by their type.

Nothing here is guessed at run time. Every header must map to a line this file
names, and every line must be present in the years this file says it exists;
anything else stops the pipeline with the schedule, year and header. A silent
rename would otherwise reach the workbook as a column of blanks.
"""
from __future__ import annotations

import re

# Headers that name the row, not a figure.
KEYS = {"Municipalities": "municipality", "Type": "type", "RD": "regional_district"}

# Schedules with several rows per municipality, and the column that says which.
ITEM_COLUMN = {"503": "Asset Category", "702": "Purpose of Tax Rate", "707": "Property Class"}

# The rows each multi-row schedule may carry, and spellings that changed.
ITEMS = {
    "503": {"Land", "Buildings", "Fleet", "Parks and Recreation", "Water System", "Sewer System", "Drainage System",
            "Transportation System", "Other Engineering Systems", "Other Tangible Capital Assets",
            "Work In Progress", "Total TCA"},
    "702": {"Municipal", "Reg'l District", "Hospital", "School", "Other", "Totals"},
    "707": {"Residential", "Utilities", "Supportive Housing", "Major Industry", "Light Industry", "Business/Other",
            "Managed Forest", "Recreation", "Farm", "Totals"},
}
ITEM_RENAMES = {"702": {"Total": "Totals"}}

# Spelling changes between years -> the current spelling (applied after the
# footnote digit is removed).
RENAMES = {
    "201": {"2016 Census": "Census", "2021 Census": "Census", "2022 Census": "Census"},
    "701": {"General Purposes Major Ind.": "General Purposes Major Industry",
            "General Purposes Light Ind.": "General Purposes Light Industry",
            "General Purposes Bus. and Other": "General Purposes Business and Other",
            "General Purposes Managed For. Land": "General Purposes Managed Forest Land",
            "General Purposes Recreation Non-Profit": "General Purposes Recreation and Non-Profit"},
    # "Regional District" here is the regional district's tax, not the key column.
    "703": {"GVTA, Victoria Transit": "Translink & Victoria Transit", "1% Utility Tax": "One Percent Utility Tax",
            "Regional District": "Regional District Tax"},
    "704": {"General Municipal Total": "General Municipal", "Total Res. User Fees": "Total Res User Fees",
            "Regional District": "Regional District Tax",
            "Total Residential Property Taxes And Charges": "Total Residential Property Taxes and Charges"},
    "707": {"Flat Taxes, Split Rate Taxes, Ports Property Taxes, Tax Sharing": "Flat and Other Taxes",
            "Flat, Split Rate & Utility Taxes, Tax Sharing, Ports, Boundary & Other Adjustments":
                "Flat and Other Taxes",
            "% Total Taxes": "Share of Total Taxes", "% Total Assessment": "Share of Total Assessment"},
}
# Year-stamped headers, matched by pattern.
PATTERNS = {"707": [(re.compile(r"population estimates", re.I), "Population Estimate")]}

ALL_YEARS = set(range(2019, 2025))


def years(first: int = 2019, last: int = 2024) -> set[int]:
    return set(range(first, last + 1))


# schedule -> {canonical line: the years it must appear in}
LINES: dict[str, dict[str, set[int]]] = {
    "201": {n: ALL_YEARS for n in (
        "census", "census_including_increases_certified_by_minister", "bc_stats_population_estimates",
        "land_area_ha", "water_area_ha", "total_area_ha", "water_pipe_distance_km", "sewer_pipe_distance_km",
        "drainage_pipe_distance_km", "distance_of_roads_km", "distance_of_active_transportation_km")},
    "301": {n: ALL_YEARS for n in (
        "cash_and_investments", "taxes_receivable", "receivables_from_government",
        "receivables_from_non_government", "mfa_deposit_notes", "loans_receivable", "property_held_for_resale",
        "government_business_enterprise_equity", "other_financial_assets", "total_financial_assets")},
    "302": {
        **{n: ALL_YEARS for n in ("revenue_anticipation_borrowing", "accounts_payable_and_accrued_liabilities",
                                  "long_term_debt", "leases_and_equipment_financing", "future_obligations",
                                  "other_liabilities", "total_liabilities")},
        **{n: years(2019, 2023) for n in ("mfa_debt_reserves", "development_cost_charges",
                                          "other_restricted_and_deferred_revenue",
                                          "total_restricted_and_deferred_revenue")},
        **{n: years(2024) for n in ("development_amenity_cost_charges", "other_restricted_revenue",
                                    "deferred_revenue")},
    },
    "304": {
        **{n: ALL_YEARS for n in ("total_financial_assets", "total_liabilities", "net_financial_assets_debt",
                                  "total_non_financial_assets", "accumulated_surplus", "water_statutory_reserves",
                                  "sewer_statutory_reserves", "other_statutory_reserves",
                                  "equity_in_tangible_capital_assets")},
        **{n: years(2019, 2022) for n in ("operating_funds", "capital_funds")},
        "total_operating_capital_surplus": years(2023),
    },
    "401": {n: ALL_YEARS for n in (
        "total_own_purpose_taxation_and_grants_in_lieu", "sale_of_services", "federal_government_transfers",
        "provincial_government_transfers", "regional_and_other_governments_transfers", "investment_income",
        "income_from_government_business_enterprise", "developer_and_other_contributions_donations",
        "gain_on_sale_of_assets", "other_revenue", "total_revenue")},
    "402": {
        **{n: ALL_YEARS for n in (
            "general_government", "protective_services", "solid_waste_management_and_recycling",
            "health_social_services_and_housing", "development_services", "transportation_and_transit",
            "parks_recreation_and_culture", "water_services", "sewer_services", "other_services", "amortization",
            "loss_on_disposition_of_assets", "other_adjustments", "total_expenses")},
        "asset_retirement_obligation_accretion": years(2023),
    },
    "404": {n: ALL_YEARS for n in (
        "annual_surplus_deficit", "acquisition_of_tangible_capital_assets", "amortization_expense",
        "net_book_value_of_tangible_capital_assets_sold", "write_offs_of_tangible_capital_assets",
        "acquisition_of_inventory_and_prepaids", "consumption_of_inventory_and_prepaid_expenses",
        "other_adjustments", "change_in_net_financial_assets_net_debt",
        "net_financial_assets_net_debt_at_year_start", "net_financial_assets_net_debt_at_year_end")},
    "503": {n: ALL_YEARS for n in (
        "historical_cost", "accumulated_amortization", "net_book_value", "total_asset_additions_in_year",
        "estimated_current_replacement_value", "estimated_annual_replacement_value_amortization",
        "asset_management_plan_in_place")},
    "601_1": {n: ALL_YEARS for n in (
        "total_debt_at_year_start", "proceeds_from_new_debt", "proceeds_from_term_refinancing", "debt_repayment",
        "actuarial_adjustment", "total_debt_at_year_end", "interest_expense", "debt_financing_cost_in_year")},
    "602_1": {
        **{n: ALL_YEARS for n in (
            "total_municipal_revenue", "less_actual_class_4_revenue", "plus_capped_class_4_revenue",
            "total_revenue_for_purposes_of_limit", "liability_servicing_limit", "actual_debt_servicing_cost",
            "additional_estimated_debt_servicing_cost", "liability_servicing_capacity_available")},
        "approval_free_zone_servicing_capacity_available": years(2023),
    },
    "701": {n: ALL_YEARS for n in (
        "general_purposes_residential", "general_purposes_utilities", "general_purposes_supportive_housing",
        "general_purposes_major_industry", "general_purposes_light_industry", "general_purposes_business_and_other",
        "general_purposes_managed_forest_land", "general_purposes_recreation_and_non_profit",
        "general_purposes_farm", "total_general_purposes_assessed_value", "total_school_purposes_value",
        "total_hospital_purposes_value")},
    "702": {n: ALL_YEARS for n in (
        "residential", "utilities", "supportive_housing", "major_industry", "light_industry", "business",
        "managed_forest_land", "recreation_non_profit", "farm")},
    "703": {n: ALL_YEARS for n in (
        "school", "general_municipal_total", "regional_district_tax", "hospital", "translink_victoria_transit",
        "bca_mfa_and_other", "total_variable_rate_taxes", "total_parcel_taxes", "total_local_area_service_taxes",
        "one_percent_utility_tax", "total_user_fees", "total_property_taxes_and_charges")},
    "704": {n: ALL_YEARS for n in (
        "house_value", "school", "general_municipal", "regional_district_tax", "hospital", "bca_mfa_and_other",
        "total_res_variable_rate_taxes", "total_res_parcel_taxes", "total_res_user_fees",
        "total_residential_property_taxes_and_charges")},
    "707": {n: ALL_YEARS for n in (
        "population_estimate", "authenticated_roll_general_taxable_values", "municipal_purposes_tax_rates",
        "tax_class_multiples", "total_municipal_variable_rate_taxes", "flat_and_other_taxes",
        "total_municipal_taxes", "share_of_total_taxes", "share_of_total_assessment", "municipal_taxes_per_capita")},
}

# Text lines: kept as text, not coerced to numbers, with their spellings unified.
TEXT_LINES = {("503", "asset_management_plan_in_place")}
TEXT_VALUES = {"Yes": "Yes", "No": "No", "In_Progress": "In_Progress",
               "N/A": "Not applicable", "NA": "Not applicable"}      # both spellings are published

# Municipalities: the Province's spelling in any year -> (stable name, type).
NAME_FIXES = {
    "Queen Charlotte": "Daajing Giids",                                # renamed 2022
    "Sechelt Indian Government": "shíshálh Nation Government District",  # renamed 2023
}
SUFFIX = re.compile(r"\s+-\s+(C|D|REGM)$")
DISSOLVED = {"Jumbo Glacier": 2020}                                     # last year reported
# Municipalities whose status changed: keyed on the current type so the history
# stays one municipality. Mission became a City in 2021.
CURRENT_TYPE = {"Mission": "C"}

TYPE_NAMES = {"C": "City", "D": "District", "T": "Town", "V": "Village", "IM": "Island Municipality",
              "RGM": "Regional Municipality", "IGD": "Indian Government District",
              "M": "Mountain Resort Municipality"}


def clean_header(schedule: str, header: str) -> str | None:
    """The canonical snake_case line for a published header, or None for a key column."""
    text = re.sub(r"\s+", " ", str(header)).strip()
    if text == ITEM_COLUMN.get(schedule):
        return None
    text = re.sub(r"(?<=[A-Za-z.)])\d$", "", text)          # footnote markers: "Farm1" -> "Farm"
    text = RENAMES.get(schedule, {}).get(text, text)
    for pattern, replacement in PATTERNS.get(schedule, []):
        if pattern.search(text):
            text = replacement
    text = text.replace("%", "").replace("&", " ").replace("/", " ")
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def clean_municipality(name: str) -> str:
    text = re.sub(r"\s+", " ", str(name)).strip()
    text = SUFFIX.sub("", text)
    text = re.sub(r"(?<=[A-Za-z])\d$", "", text)          # a footnote marker: "Vancouver1"
    return NAME_FIXES.get(text, text)
