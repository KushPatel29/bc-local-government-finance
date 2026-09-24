-- Schedule 503: the categories add up to the "Total TCA" row the Province publishes.
with c as (
    select municipality_id, year, line,
        sum(case when item <> 'Total TCA' then coalesce(value, 0) else 0 end) as categories,
        max(case when item = 'Total TCA' then value end) as total
    from {{ ref('stg_facts') }}
    where schedule = '503' and line <> 'asset_management_plan_in_place'
    group by municipality_id, year, line
)
select * from c where abs(categories - coalesce(total, 0)) > 2
