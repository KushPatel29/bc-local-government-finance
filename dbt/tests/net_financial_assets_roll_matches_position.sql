-- Schedule 404's closing net financial assets equal schedule 304's, except the
-- published exceptions.
with n as (
    select municipality_id, year,
        {{ pick('404', 'net_financial_assets_net_debt_at_year_end') }} - {{ pick('304', 'net_financial_assets_debt') }}
            as difference
    from {{ ref('stg_facts') }}
    group by municipality_id, year
)
select n.* from n
left join {{ ref('known_exceptions') }} k
    on k.rule = 'nfa_roll_matches_position' and k.municipality_id = n.municipality_id and k.year = n.year
where abs(n.difference) > 2 and k.rule is null
