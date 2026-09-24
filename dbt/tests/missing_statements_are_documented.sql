-- A municipality-year with no statements must be listed in the seed, and a
-- listed one that now has statements must be removed from it: both directions,
-- so the published list of gaps is always the real one.
with gaps as (
    select municipality_id, year from {{ ref('fct_municipal_year') }} where total_revenue is null
),
listed as (
    select municipality_id, cast(year as integer) as year from {{ ref('missing_statements') }}
)
select 'undocumented gap' as problem, * from (select * from gaps except select * from listed)
union all
select 'gap now filled' as problem, * from (select * from listed except select * from gaps)
