-- 77 rows of the 2022 file are misaligned. If the Province republishes it, this
-- count changes and the rule and the README must be revisited.
select count(*) as repaired
from {{ ref('fct_municipal_year') }}
where population_repaired and year = 2022
having count(*) <> 77
