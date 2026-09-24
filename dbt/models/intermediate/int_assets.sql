-- Depreciable assets only: land does not wear out and work in progress is not
-- yet in service, so neither belongs in a consumption ratio or a renewal need.
select
    municipality_id,
    year,
    sum(case when line = 'historical_cost' then value end) as depreciable_cost,
    sum(case when line = 'accumulated_amortization' then value end) as depreciable_amortization,
    sum(case when line = 'estimated_current_replacement_value' then value end) as depreciable_replacement_value,
    sum(case when line = 'estimated_annual_replacement_value_amortization' then value end) as reported_renewal_need
from {{ ref('stg_facts') }}
where schedule = '503' and item not in ('Land', 'Work In Progress', 'Total TCA')
group by municipality_id, year
