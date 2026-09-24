-- The latest year for every active municipality, ranked within its size tier
-- and across the province. A percentile of 1.0 is the highest value, which is
-- not always the best: the direction is in the metric catalogue (schema.yml).
-- Ranks count only municipalities that report the metric: percent_rank() over a
-- partition that includes NULLs would put them in the denominator.
{% set metrics = ['revenue_per_capita', 'expenses_per_capita', 'municipal_tax_per_capita', 'own_source_share',
                  'surplus_ratio', 'limit_used', 'debt_per_capita', 'reserves_per_capita',
                  'reserves_to_cash_expenses', 'asset_consumption_ratio', 'reinvestment_ratio',
                  'house_total_charges', 'effective_municipal_rate'] %}
with latest as (
    select f.*, d.display_name, d.type_name, d.regional_district, d.size_tier
    from {{ ref('fct_municipal_year') }} f
    join {{ ref('dim_municipality') }} d using (municipality_id)
    where d.active and f.year = (select max(year) from {{ ref('fct_municipal_year') }})
)
select
    municipality_id,
    display_name,
    type_name,
    regional_district,
    size_tier,
    year,
    population,
    {% for m in metrics %}
    {{ m }},
    case when {{ m }} is not null then
        percent_rank() over (partition by size_tier, {{ m }} is null order by {{ m }}) end as {{ m }}_tier_pct,
    median({{ m }}) over (partition by size_tier) as {{ m }}_tier_median,
    case when {{ m }} is not null then
        percent_rank() over (partition by {{ m }} is null order by {{ m }}) end as {{ m }}_province_pct{{ ',' if not loop.last }}
    {% endfor %}
from latest
order by municipality_id
