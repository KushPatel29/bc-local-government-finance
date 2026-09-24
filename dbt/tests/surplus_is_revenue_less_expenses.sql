select municipality_id, year, total_revenue, total_expenses, annual_surplus
from {{ ref('fct_municipal_year') }}
where abs(total_revenue - total_expenses - annual_surplus) > 2
