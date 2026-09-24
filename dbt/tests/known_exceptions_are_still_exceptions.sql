-- An exception the data no longer shows must be deleted from the seed, or the
-- list stops meaning anything.
with nfa as (
    select municipality_id, year,
        {{ pick('404', 'net_financial_assets_net_debt_at_year_end') }} - {{ pick('304', 'net_financial_assets_debt') }} as d
    from {{ ref('stg_facts') }} group by municipality_id, year
),
cap as (
    select municipality_id, year,
        {{ pick('602_1', 'liability_servicing_limit') }} - {{ pick('602_1', 'actual_debt_servicing_cost') }}
        - {{ pick('602_1', 'additional_estimated_debt_servicing_cost') }}
        - {{ pick('602_1', 'liability_servicing_capacity_available') }} as d
    from {{ ref('stg_facts') }} group by municipality_id, year
)
select k.* from {{ ref('known_exceptions') }} k
left join {{ ref('fct_municipal_year') }} f on k.rule = 'population_repair' and f.municipality_id = k.municipality_id
    and f.year = k.year
left join nfa on k.rule = 'nfa_roll_matches_position' and nfa.municipality_id = k.municipality_id
    and nfa.year = k.year
left join cap on k.rule = 'servicing_capacity' and cap.municipality_id = k.municipality_id and cap.year = k.year
where (k.rule <> 'population_repair' and abs(coalesce(nfa.d, cap.d, 0)) <= 2)
   or (k.rule = 'population_repair' and not coalesce(f.population_repaired, false))
