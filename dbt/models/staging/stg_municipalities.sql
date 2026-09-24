select
    municipality_id,
    name,
    type,
    type_name,
    regional_district,
    cast(first_year as integer) as first_year,
    cast(last_year as integer) as last_year,
    published_as
from {{ source('silver', 'municipalities') }}
