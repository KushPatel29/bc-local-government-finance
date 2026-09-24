-- Assessment, rate, class multiple and municipal taxes by property class (schedule 707).
select
    municipality_id,
    year,
    item as property_class,
    max(case when line = 'authenticated_roll_general_taxable_values' then value end) as assessment,
    max(case when line = 'municipal_purposes_tax_rates' then value end) as municipal_rate,
    max(case when line = 'tax_class_multiples' then value end) as class_multiple,
    max(case when line = 'total_municipal_variable_rate_taxes' then value end) as variable_rate_taxes,
    max(case when line = 'flat_and_other_taxes' then value end) as flat_and_other_taxes,
    max(case when line = 'total_municipal_taxes' then value end) as municipal_taxes
from {{ ref('stg_facts') }}
where schedule = '707' and item <> 'Totals'
group by municipality_id, year, item
order by municipality_id, year, item
