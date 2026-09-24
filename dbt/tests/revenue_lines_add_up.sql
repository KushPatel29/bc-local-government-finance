-- Schedule 401: the revenue lines add up to total revenue, to the dollar.
select municipality_id, year
from {{ ref('stg_facts') }}
where schedule = '401'
group by municipality_id, year
having abs(sum(case when line <> 'total_revenue' then coalesce(value, 0) else -value end)) > 2
