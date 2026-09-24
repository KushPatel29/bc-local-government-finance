-- Tangible capital assets by category, municipality and year (schedule 503).
select
    municipality_id,
    year,
    item as asset_category,
    max(case when line = 'historical_cost' then value end) as historical_cost,
    max(case when line = 'accumulated_amortization' then value end) as accumulated_amortization,
    max(case when line = 'net_book_value' then value end) as net_book_value,
    max(case when line = 'total_asset_additions_in_year' then value end) as additions,
    max(case when line = 'estimated_current_replacement_value' then value end) as replacement_value,
    max(case when line = 'estimated_annual_replacement_value_amortization' then value end) as annual_replacement_need,
    max(case when line = 'asset_management_plan_in_place' then text end) as amp_status,
    max(case when line = 'accumulated_amortization' then value end)
        / nullif(max(case when line = 'historical_cost' then value end), 0) as consumption_ratio
from {{ ref('stg_facts') }}
where schedule = '503' and item <> 'Total TCA'
group by municipality_id, year, item
order by municipality_id, year, item
