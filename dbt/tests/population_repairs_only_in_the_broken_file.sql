-- Population repairs are expected in schedule 201 for 2022, plus the single rows
-- listed in seeds/known_exceptions.csv, and nowhere else. Any other repair is a
-- new defect in the Province's data and should be looked at before a rule
-- quietly smooths it over.
select f.municipality_id, f.year, f.population_published, f.population
from {{ ref('fct_municipal_year') }} f
left join {{ ref('known_exceptions') }} k
    on k.rule = 'population_repair' and k.municipality_id = f.municipality_id and k.year = f.year
where f.population_repaired and f.year <> 2022 and k.rule is null
