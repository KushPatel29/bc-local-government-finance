-- Population, repaired where the Province's file is misaligned.
--
-- Schedule 201 for 2022 carries 77 rows whose figures belong to other
-- municipalities: Fernie is published at 1,700 between 5,739 (2021) and 6,000
-- (2023), Kelowna at 6,948 between 149,687 and 160,693. Every financial schedule
-- for 2022 lines up; only this one does not.
--
-- The rule: a published figure more than 25% away from the municipality's own
-- six-year median is replaced by the average of the years either side. The
-- published figure and a flag stay in the table, and a test fails if a repair
-- is ever needed outside the file known to be broken.
with p as (
    select municipality_id, year, population as population_published
    from {{ ref('int_municipal_year') }}
),
m as (
    select *,
        median(population_published) over (partition by municipality_id) as population_median,
        lag(population_published) over (partition by municipality_id order by year) as population_before,
        lead(population_published) over (partition by municipality_id order by year) as population_after
    from p
)
select
    municipality_id,
    year,
    population_published,
    abs(population_published / nullif(population_median, 0) - 1) > 0.25 as population_repaired,
    case
        when abs(population_published / nullif(population_median, 0) - 1) > 0.25
            then coalesce((population_before + population_after) / 2, population_median)
        else population_published
    end as population
from m
