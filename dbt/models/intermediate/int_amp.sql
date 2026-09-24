-- Asset management plan status by category, joined to the category's replacement value.
with status as (
    select municipality_id, year, item, text as amp_status
    from {{ ref('stg_facts') }}
    where schedule = '503' and line = 'asset_management_plan_in_place'
),
value as (
    select municipality_id, year, item, value as replacement_value
    from {{ ref('stg_facts') }}
    where schedule = '503' and line = 'estimated_current_replacement_value'
)
select
    s.municipality_id,
    s.year,
    sum(case when s.amp_status = 'Yes' then v.replacement_value else 0 end)
        / nullif(sum(case when s.amp_status in ('Yes', 'No', 'In_Progress') then v.replacement_value end), 0)
        as amp_coverage
from status s
join value v using (municipality_id, year, item)
where s.item not in ('Land', 'Work In Progress', 'Total TCA')
group by s.municipality_id, s.year
