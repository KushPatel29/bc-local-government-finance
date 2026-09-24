-- Schedule 601.1: opening + new + refinancing - repayment - actuarial = closing.
with d as (
    select municipality_id, year,
        {{ pick('601_1', 'total_debt_at_year_start') }} + {{ pick('601_1', 'proceeds_from_new_debt') }}
        + {{ pick('601_1', 'proceeds_from_term_refinancing') }} - {{ pick('601_1', 'debt_repayment') }}
        - {{ pick('601_1', 'actuarial_adjustment') }} - {{ pick('601_1', 'total_debt_at_year_end') }} as difference
    from {{ ref('stg_facts') }}
    group by municipality_id, year
)
select * from d where abs(difference) > 2
