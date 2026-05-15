def gross_yield(annual_rent, purchase_price):
    if purchase_price <= 0:
        return 0.0
    return (annual_rent / purchase_price) * 100


def net_yield(annual_rent, annual_opex, total_acquisition_cost):
    if total_acquisition_cost <= 0:
        return 0.0
    return ((annual_rent - annual_opex) / total_acquisition_cost) * 100


def cash_on_cash(annual_rent, annual_opex, annual_debt_service, eigenkapital):
    if eigenkapital <= 0:
        return 0.0
    cashflow = annual_rent - annual_opex - annual_debt_service
    return (cashflow / eigenkapital) * 100


def true_total_return(
    annual_rent,
    annual_opex,
    annual_debt_service,
    annual_tilgung,
    kaufnebenkosten,
    eigenkapital,
    holding_period_years=10,
):
    if eigenkapital <= 0 or holding_period_years <= 0:
        return 0.0
    cashflow = annual_rent - annual_opex - annual_debt_service
    knk_amortised = kaufnebenkosten / holding_period_years
    return ((cashflow + annual_tilgung - knk_amortised) / eigenkapital) * 100
