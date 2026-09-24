-- One row per published cell, typed. The item is '' for single-row schedules,
-- so it can sit in a key without NULL-equality surprises.
select
    municipality_id,
    cast(year as integer) as year,
    schedule,
    coalesce(item, '') as item,
    line,
    cast(nullif(value, '') as double) as value,  -- strict: a malformed number fails the build
    nullif(text, '') as text
from {{ source('silver', 'facts') }}
