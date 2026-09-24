-- The re-derived renewal need exists only where the replacement value passed
-- the screen; a ratio computed on an implausible value is exactly the error the
-- screen exists to stop.
select municipality_id, year, replacement_to_cost, renewal_need
from {{ ref('fct_municipal_year') }}
where renewal_need is not null and not (replacement_to_cost between 1 and 6)
