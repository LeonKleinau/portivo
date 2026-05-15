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


def amortisation_schedule(
    principal, annual_interest_rate_pct, initial_tilgung_pct, years=30
):
    if principal <= 0 or years <= 0:
        return []
    annuity = principal * (annual_interest_rate_pct + initial_tilgung_pct) / 100
    rate = annual_interest_rate_pct / 100
    schedule = []
    balance = principal
    for year in range(1, years + 1):
        if balance <= 0:
            break
        opening = balance
        interest = balance * rate
        principal_payment = annuity - interest
        if principal_payment > balance:
            principal_payment = balance
            annuity_this_year = interest + principal_payment
        else:
            annuity_this_year = annuity
        balance = balance - principal_payment
        if balance < 0:
            balance = 0
        schedule.append(
            {
                "year": year,
                "opening_balance": opening,
                "interest": interest,
                "principal": principal_payment,
                "annuity": annuity_this_year,
                "closing_balance": balance,
            }
        )
    return schedule
