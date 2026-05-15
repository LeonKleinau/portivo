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


def equity_buildup(
    purchase_price,
    initial_loan,
    appreciation_pct_annual,
    amort_schedule,
    horizon_years=None,
):
    rate = appreciation_pct_annual / 100
    if horizon_years is None:
        horizon_years = len(amort_schedule)

    rest_by_year = {0: initial_loan}
    for entry in amort_schedule:
        rest_by_year[entry["year"]] = entry["closing_balance"]
    last_known_year = max(rest_by_year.keys()) if rest_by_year else 0

    out = []
    for year in range(0, horizon_years + 1):
        if year in rest_by_year:
            restschuld = rest_by_year[year]
        elif year > last_known_year:
            restschuld = 0
        else:
            restschuld = initial_loan
        property_value = purchase_price * ((1 + rate) ** year)
        out.append(
            {
                "year": year,
                "restschuld": restschuld,
                "property_value": property_value,
                "equity": property_value - restschuld,
            }
        )
    return out


def tax_summary(prop, loan, year, land_share_pct=20.0):
    if not prop.get("purchase_date"):
        return None
    from datetime import date as _date

    purchase = _date.fromisoformat(prop["purchase_date"])
    if year < purchase.year:
        return None

    mieteinnahmen = prop["kaltmiete_monthly"] * 12
    bewirtschaftungskosten = prop["opex_monthly_total"] * 12

    schuldzinsen = 0.0
    if loan:
        loan_year = year - purchase.year + 1
        schedule = amortisation_schedule(
            loan["darlehenssumme"],
            loan["zinssatz_pct"],
            loan["tilgung_anfang_pct"],
            years=50,
        )
        if 1 <= loan_year <= len(schedule):
            schuldzinsen = schedule[loan_year - 1]["interest"]

    baujahr = prop.get("baujahr", 0) or 0
    afa_rate = 3.0 if baujahr >= 2023 else 2.0
    building_basis = (prop["purchase_price"] + prop["kaufnebenkosten_total"]) * (
        1 - land_share_pct / 100
    )
    afa_gebaeude = building_basis * afa_rate / 100

    summe_werbungskosten = schuldzinsen + bewirtschaftungskosten + afa_gebaeude
    ueberschuss = mieteinnahmen - summe_werbungskosten

    return {
        "property_id": prop["property_id"],
        "address": prop["address"],
        "year": year,
        "mieteinnahmen": mieteinnahmen,
        "schuldzinsen": schuldzinsen,
        "bewirtschaftungskosten": bewirtschaftungskosten,
        "afa_gebaeude": afa_gebaeude,
        "afa_rate_pct": afa_rate,
        "building_basis": building_basis,
        "summe_werbungskosten": summe_werbungskosten,
        "ueberschuss_verlust": ueberschuss,
    }


def gesamtrendite_components(
    annual_rent,
    annual_opex,
    annual_debt_service,
    annual_tilgung,
    kaufnebenkosten,
    eigenkapital,
    holding_period_years=10,
):
    if eigenkapital <= 0 or holding_period_years <= 0:
        return {"cashflow": 0.0, "tilgung": 0.0, "knk_amort": 0.0, "total": 0.0}
    cashflow = annual_rent - annual_opex - annual_debt_service
    knk_amortised = kaufnebenkosten / holding_period_years
    cf_pct = cashflow / eigenkapital * 100
    tilgung_pct = annual_tilgung / eigenkapital * 100
    knk_pct = -knk_amortised / eigenkapital * 100
    return {
        "cashflow": cf_pct,
        "tilgung": tilgung_pct,
        "knk_amort": knk_pct,
        "total": cf_pct + tilgung_pct + knk_pct,
    }


def current_restschuld(loan, purchase_date_iso, today=None):
    from datetime import date as _date

    if not loan or not loan.get("darlehenssumme"):
        return 0
    today = today or _date.today()
    purchase = _date.fromisoformat(purchase_date_iso)
    days_elapsed = max(0, (today - purchase).days)
    years_elapsed = days_elapsed / 365.25

    schedule = amortisation_schedule(
        loan["darlehenssumme"],
        loan["zinssatz_pct"],
        loan["tilgung_anfang_pct"],
        years=50,
    )
    if not schedule:
        return loan["darlehenssumme"]

    full_years = int(years_elapsed)
    fraction = years_elapsed - full_years

    if full_years == 0:
        opening = loan["darlehenssumme"]
        closing = schedule[0]["closing_balance"]
    elif full_years >= len(schedule):
        return 0
    else:
        opening = schedule[full_years - 1]["closing_balance"]
        closing = schedule[full_years]["closing_balance"]

    return max(0, opening - fraction * (opening - closing))


def cashflow_at_new_rate(
    rent_monthly, opex_monthly, restschuld, new_rate_pct, tilgung_pct
):
    if restschuld <= 0:
        return rent_monthly - opex_monthly
    monthly_annuity = restschuld * (new_rate_pct + tilgung_pct) / 100 / 12
    return rent_monthly - opex_monthly - monthly_annuity


def breakeven_rate_pct(rent_monthly, opex_monthly, restschuld, tilgung_pct):
    if restschuld <= 0:
        return None
    net_op = rent_monthly - opex_monthly
    return net_op * 1200 / restschuld - tilgung_pct


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
