-- Province totals and medians by year, over the municipalities reporting that year.
select
    year,
    count(*) as municipalities,
    sum(population) as population,
    sum(total_revenue) as total_revenue,
    sum(total_expenses) as total_expenses,
    sum(municipal_property_tax) as municipal_property_tax,
    sum(long_term_debt) as long_term_debt,
    sum(financial_reserves) as financial_reserves,
    sum(replacement_value) as replacement_value,
    sum(annual_replacement_need) as reported_renewal_need,
    sum(renewal_need) as renewal_need,
    sum(case when reinvestment_ratio is not null then tca_additions_3yr end) as tca_additions_3yr_screened,
    sum(case when reinvestment_ratio is not null then tca_additions_3yr end)
        / nullif(sum(case when reinvestment_ratio is not null then renewal_need end), 0) as reinvestment_ratio,
    sum(case when reinvestment_ratio < 1 then 1 else 0 end) as below_renewal_need,
    sum(case when reinvestment_ratio is not null then 1 else 0 end) as screened_for_renewal,
    sum(case when asset_data_quality = 'plausible' then 1 else 0 end) as assets_plausible,
    sum(case when asset_data_quality = 'not reported' then 1 else 0 end) as assets_not_reported,
    median(limit_used) as median_limit_used,
    median(house_total_charges) as median_house_total_charges,
    median(asset_consumption_ratio) as median_asset_consumption_ratio,
    sum(case when amp_coverage >= 0.999 then 1 else 0 end) as fully_covered_by_amp
from {{ ref('fct_municipal_year') }}
group by year
order by year
