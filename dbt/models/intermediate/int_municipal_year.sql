-- The lines the marts use, one row per municipality and year. Named for what
-- they mean rather than how the Province spells them.
{% set lines = {
    'population':                ('201', 'bc_stats_population_estimates'),
    'taxation':                  ('401', 'total_own_purpose_taxation_and_grants_in_lieu'),
    'sale_of_services':          ('401', 'sale_of_services'),
    'federal_transfers':         ('401', 'federal_government_transfers'),
    'provincial_transfers':      ('401', 'provincial_government_transfers'),
    'regional_transfers':        ('401', 'regional_and_other_governments_transfers'),
    'investment_income':         ('401', 'investment_income'),
    'developer_contributions':   ('401', 'developer_and_other_contributions_donations'),
    'total_revenue':             ('401', 'total_revenue'),
    'general_government':        ('402', 'general_government'),
    'protective_services':       ('402', 'protective_services'),
    'transportation':            ('402', 'transportation_and_transit'),
    'parks_recreation':          ('402', 'parks_recreation_and_culture'),
    'water_services':            ('402', 'water_services'),
    'sewer_services':            ('402', 'sewer_services'),
    'amortization':              ('402', 'amortization'),
    'total_expenses':            ('402', 'total_expenses'),
    'annual_surplus':            ('404', 'annual_surplus_deficit'),
    'capital_acquisitions':      ('404', 'acquisition_of_tangible_capital_assets'),
    'cash_and_investments':      ('301', 'cash_and_investments'),
    'total_financial_assets':    ('304', 'total_financial_assets'),
    'total_liabilities':         ('304', 'total_liabilities'),
    'net_financial_assets':      ('304', 'net_financial_assets_debt'),
    'accumulated_surplus':       ('304', 'accumulated_surplus'),
    'water_reserves':            ('304', 'water_statutory_reserves'),
    'sewer_reserves':            ('304', 'sewer_statutory_reserves'),
    'other_reserves':            ('304', 'other_statutory_reserves'),
    'operating_capital_surplus_new': ('304', 'total_operating_capital_surplus'),
    'operating_funds':           ('304', 'operating_funds'),
    'capital_funds':             ('304', 'capital_funds'),
    'debt_start':                ('601_1', 'total_debt_at_year_start'),
    'debt_issued':               ('601_1', 'proceeds_from_new_debt'),
    'debt_repaid':               ('601_1', 'debt_repayment'),
    'long_term_debt':            ('601_1', 'total_debt_at_year_end'),
    'interest_expense':          ('601_1', 'interest_expense'),
    'revenue_for_limit':         ('602_1', 'total_revenue_for_purposes_of_limit'),
    'liability_servicing_limit': ('602_1', 'liability_servicing_limit'),
    'debt_servicing_cost':       ('602_1', 'actual_debt_servicing_cost'),
    'additional_servicing_cost': ('602_1', 'additional_estimated_debt_servicing_cost'),
    'servicing_capacity':        ('602_1', 'liability_servicing_capacity_available'),
    'assessed_value':            ('701', 'total_general_purposes_assessed_value'),
    'residential_assessment':    ('701', 'general_purposes_residential'),
    'municipal_property_tax':    ('703', 'general_municipal_total'),
    'total_taxes_and_charges':   ('703', 'total_property_taxes_and_charges'),
    'house_value':               ('704', 'house_value'),
    'house_municipal_tax':       ('704', 'general_municipal'),
    'house_total_charges':       ('704', 'total_residential_property_taxes_and_charges'),
} %}
{% set assets = {
    'tca_cost':              'historical_cost',
    'tca_accumulated_amortization': 'accumulated_amortization',
    'tca_net_book_value':    'net_book_value',
    'tca_additions':         'total_asset_additions_in_year',
    'replacement_value':     'estimated_current_replacement_value',
    'annual_replacement_need': 'estimated_annual_replacement_value_amortization',
} %}
select
    municipality_id,
    year,
    {% for name, (schedule, line) in lines.items() %}
    {{ pick(schedule, line) }} as {{ name }},
    {% endfor %}
    {% for name, line in assets.items() %}
    {{ pick('503', line, 'Total TCA') }} as {{ name }}{{ ',' if not loop.last }}
    {% endfor %}
from {{ ref('stg_facts') }}
group by municipality_id, year
