-- Schedule 304: financial assets less liabilities is net financial assets, and
-- net financial assets plus non-financial assets is the accumulated surplus.
with p as (
    select municipality_id, year,
        {{ pick('304', 'total_financial_assets') }} as fa,
        {{ pick('304', 'total_liabilities') }} as l,
        {{ pick('304', 'net_financial_assets_debt') }} as nfa,
        {{ pick('304', 'total_non_financial_assets') }} as nfin,
        {{ pick('304', 'accumulated_surplus') }} as acc
    from {{ ref('stg_facts') }}
    group by municipality_id, year
)
select * from p where abs(fa - l - nfa) > 2 or abs(nfa + nfin - acc) > 2
