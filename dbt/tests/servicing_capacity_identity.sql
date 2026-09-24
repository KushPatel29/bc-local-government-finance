-- Capacity = limit - actual servicing - additional estimated servicing, except
-- where the Province's own figure disagrees (seeds/known_exceptions.csv).
with c as (
    select municipality_id, year,
        {{ pick('602_1', 'liability_servicing_limit') }} - {{ pick('602_1', 'actual_debt_servicing_cost') }}
        - {{ pick('602_1', 'additional_estimated_debt_servicing_cost') }}
        - {{ pick('602_1', 'liability_servicing_capacity_available') }} as difference
    from {{ ref('stg_facts') }}
    group by municipality_id, year
)
select c.* from c
left join {{ ref('known_exceptions') }} k
    on k.rule = 'servicing_capacity' and k.municipality_id = c.municipality_id and k.year = c.year
where abs(c.difference) > 1 and k.rule is null
