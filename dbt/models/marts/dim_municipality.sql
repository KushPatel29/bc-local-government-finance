-- One row per municipality. Two pairs share a name (Langley, North Vancouver),
-- so the display name carries the type wherever a name is not unique.
with m as (
    select *, count(*) over (partition by name) as same_name
    from {{ ref('stg_municipalities') }}
),
latest as (
    select municipality_id, population
    from {{ ref('int_municipal_year') }}
    where year = (select max(year) from {{ ref('int_municipal_year') }})
)
select
    m.municipality_id,
    m.name,
    case when m.same_name > 1 then m.name || ' (' || m.type_name || ')' else m.name end as display_name,
    m.type,
    m.type_name,
    m.regional_district,
    m.first_year,
    m.last_year,
    m.last_year = (select max(year) from {{ ref('int_municipal_year') }}) as active,
    l.population as population_latest,
    case
        when l.population is null then null
        when l.population < 2500 then '1: under 2,500'
        when l.population < 10000 then '2: 2,500 to 9,999'
        when l.population < 50000 then '3: 10,000 to 49,999'
        when l.population < 150000 then '4: 50,000 to 149,999'
        else '5: 150,000 and over'
    end as size_tier,
    m.published_as
from m
left join latest l using (municipality_id)
order by m.municipality_id
