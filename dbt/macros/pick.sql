{#- One published line as a column: max() over the single matching row. -#}
{% macro pick(schedule, line, item='') -%}
    max(case when schedule = '{{ schedule }}' and line = '{{ line }}' and item = '{{ item }}' then value end)
{%- endmacro %}
