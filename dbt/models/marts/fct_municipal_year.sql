-- One row per municipality and year, with every indicator the workbook shows.
-- Ratios are fractions; money is dollars; per-capita figures use BC Stats'
-- population estimate for the same year.
with y as (
    select
        i.*,
        coalesce(i.operating_capital_surplus_new, i.operating_funds + i.capital_funds) as operating_capital_surplus,
        coalesce(i.water_reserves, 0) + coalesce(i.sewer_reserves, 0) + coalesce(i.other_reserves, 0)
            as statutory_reserves,
        coalesce(i.federal_transfers, 0) + coalesce(i.provincial_transfers, 0) + coalesce(i.regional_transfers, 0)
            as government_transfers,
        a.depreciable_cost,
        a.depreciable_amortization,
        a.depreciable_replacement_value,
        a.reported_renewal_need,
        a.depreciable_replacement_value / nullif(a.depreciable_cost, 0) as replacement_to_cost,
        p.amp_coverage,
        -- Capital additions averaged over the year and the two before it: one
        -- year's additions swing with a single project.
        avg(i.tca_additions) over (
            partition by i.municipality_id order by i.year rows between 2 preceding and current row
        ) as tca_additions_3yr,
        count(i.tca_additions) over (
            partition by i.municipality_id order by i.year rows between 2 preceding and current row
        ) as tca_additions_years
    from (
        select i0.* exclude (population), pop.population, pop.population_published, pop.population_repaired
        from {{ ref('int_municipal_year') }} i0
        join {{ ref('int_population') }} pop using (municipality_id, year)
    ) i
    left join {{ ref('int_assets') }} a using (municipality_id, year)
    left join {{ ref('int_amp') }} p using (municipality_id, year)
)
select
    municipality_id,
    year,
    municipality_id || ':' || year as municipality_year,
    population,
    population_published,
    population_repaired,
    total_revenue,
    taxation,
    sale_of_services,
    government_transfers,
    investment_income,
    developer_contributions,
    total_revenue - government_transfers - coalesce(developer_contributions, 0) as own_source_revenue,
    total_expenses,
    amortization,
    total_expenses - amortization as cash_expenses,
    general_government,
    protective_services,
    transportation,
    parks_recreation,
    water_services,
    sewer_services,
    annual_surplus,
    capital_acquisitions,
    cash_and_investments,
    total_financial_assets,
    total_liabilities,
    net_financial_assets,
    accumulated_surplus,
    operating_capital_surplus,
    statutory_reserves,
    operating_capital_surplus + statutory_reserves as financial_reserves,
    long_term_debt,
    debt_issued,
    debt_repaid,
    interest_expense,
    revenue_for_limit,
    liability_servicing_limit,
    debt_servicing_cost,
    servicing_capacity,
    assessed_value,
    residential_assessment,
    municipal_property_tax,
    total_taxes_and_charges,
    house_value,
    house_municipal_tax,
    house_total_charges,
    tca_cost,
    tca_net_book_value,
    tca_additions,
    tca_additions_3yr,
    replacement_value,
    annual_replacement_need,
    amp_coverage,
    -- ratios
    (total_revenue - government_transfers - coalesce(developer_contributions, 0)) / nullif(total_revenue, 0)
        as own_source_share,
    annual_surplus / nullif(total_revenue, 0) as surplus_ratio,
    debt_servicing_cost / nullif(liability_servicing_limit, 0) as limit_used,
    debt_servicing_cost / nullif(revenue_for_limit, 0) as debt_service_ratio,
    (operating_capital_surplus + statutory_reserves) / nullif(total_expenses - amortization, 0)
        as reserves_to_cash_expenses,
    depreciable_amortization / nullif(depreciable_cost, 0) as asset_consumption_ratio,
    replacement_to_cost,
    reported_renewal_need / nullif(depreciable_replacement_value, 0) as reported_need_rate,
    -- The Province's "estimated annual replacement value amortization" is not fit
    -- to use as published: Vancouver reports 37% of its replacement value a year,
    -- and most municipalities reported no replacement value at all before 2024.
    -- So the renewal need is re-derived -- this year's amortization scaled from
    -- historical to replacement cost -- and only where the replacement value is
    -- plausible: at least the historical cost and at most six times it.
    case
        when depreciable_replacement_value is null or depreciable_replacement_value = 0 then 'not reported'
        when replacement_to_cost < 1 or replacement_to_cost > 6 then 'replacement value implausible'
        when reported_renewal_need / depreciable_replacement_value not between 0.005 and 0.10
            then 'reported need implausible'
        else 'plausible'
    end as asset_data_quality,
    case when replacement_to_cost between 1 and 6 then amortization * replacement_to_cost end as renewal_need,
    case when replacement_to_cost between 1 and 6 and tca_additions_years = 3
        then tca_additions_3yr / nullif(amortization * replacement_to_cost, 0) end as reinvestment_ratio,
    case when replacement_to_cost between 1 and 6 and tca_additions_years = 3
        then greatest(amortization * replacement_to_cost - tca_additions_3yr, 0) end as annual_renewal_gap,
    municipal_property_tax / nullif(assessed_value, 0) * 1000 as effective_municipal_rate,
    house_municipal_tax / nullif(house_total_charges, 0) as house_municipal_share,
    -- per capita
    total_revenue / nullif(population, 0) as revenue_per_capita,
    total_expenses / nullif(population, 0) as expenses_per_capita,
    municipal_property_tax / nullif(population, 0) as municipal_tax_per_capita,
    long_term_debt / nullif(population, 0) as debt_per_capita,
    (operating_capital_surplus + statutory_reserves) / nullif(population, 0) as reserves_per_capita,
    replacement_value / nullif(population, 0) as replacement_value_per_capita
from y
order by municipality_id, year
