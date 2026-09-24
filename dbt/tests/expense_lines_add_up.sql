-- Schedule 402: the expense lines add up to total expenses, to the dollar.
select municipality_id, year
from {{ ref('stg_facts') }}
where schedule = '402'
group by municipality_id, year
having abs(sum(case when line <> 'total_expenses' then coalesce(value, 0) else -value end)) > 2
