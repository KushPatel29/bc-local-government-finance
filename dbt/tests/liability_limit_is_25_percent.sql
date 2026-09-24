-- Community Charter s.174 and B.C. Reg. 254/2004: the liability servicing limit
-- is 25% of revenue for the purposes of the limit.
select municipality_id, year, revenue_for_limit, liability_servicing_limit
from {{ ref('fct_municipal_year') }}
where abs(0.25 * revenue_for_limit - liability_servicing_limit) > 1
