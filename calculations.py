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


def realized_return(prop, loan):
    if not prop or prop.get("status") != "sold":
        return None
    from datetime import date as _date

    if not prop.get("verkaufs_datum") or not prop.get("verkaufspreis"):
        return None
    purchase = _date.fromisoformat(prop["purchase_date"])
    sale = _date.fromisoformat(prop["verkaufs_datum"])
    holding_years = (sale - purchase).days / 365.25
    ten_year_anniversary = _date(purchase.year + 10, purchase.month, purchase.day)
    spek_frist_passed = sale >= ten_year_anniversary

    rest_at_sale = (
        projected_restschuld(loan, prop["purchase_date"], today=sale) if loan else 0
    )

    verkaufspreis = float(prop["verkaufspreis"])
    verkaufsnebenkosten = float(prop.get("verkaufsnebenkosten", 0))

    netto_erlos = verkaufspreis - verkaufsnebenkosten - rest_at_sale
    initial_eigenkapital = (
        prop["purchase_price"] + prop["kaufnebenkosten_total"]
    ) - (loan["darlehenssumme"] if loan else 0)
    veraeusserungsgewinn = (
        verkaufspreis - prop["purchase_price"] - prop["kaufnebenkosten_total"]
    )

    return {
        "holding_years": holding_years,
        "verkaufspreis": verkaufspreis,
        "verkaufsnebenkosten": verkaufsnebenkosten,
        "rest_at_sale": rest_at_sale,
        "netto_erlos": netto_erlos,
        "initial_eigenkapital": initial_eigenkapital,
        "wealth_multiple": (
            netto_erlos / initial_eigenkapital if initial_eigenkapital > 0 else 0
        ),
        "veraeusserungsgewinn": veraeusserungsgewinn,
        "spek_frist_passed": spek_frist_passed,
    }


def irr(cashflows, tol=1e-7, max_iter=200):
    if not cashflows or len(cashflows) < 2:
        return None
    has_pos = any(cf > 0 for cf in cashflows)
    has_neg = any(cf < 0 for cf in cashflows)
    if not (has_pos and has_neg):
        return None

    def npv(rate):
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))

    low, high = -0.99, 10.0
    f_low = npv(low)
    f_high = npv(high)
    if f_low * f_high > 0:
        return None

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) < tol or (high - low) / 2 < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2


def scenario_projection(
    prop,
    loan,
    holding_years,
    today,
    annual_appreciation_pct=2.0,
    annual_rent_growth_pct=1.5,
    annual_opex_growth_pct=2.0,
    anschluss_rate_pct=3.8,
    selling_costs_pct=5.0,
):
    from datetime import date as _date

    if today is None:
        today = _date.today()
    purchase_d = _date.fromisoformat(prop["purchase_date"])

    current_value = float(prop["purchase_price"])
    rest_t0 = current_restschuld(loan, prop["purchase_date"], today) if loan else 0
    equity_t0 = current_value - rest_t0

    if loan:
        zb_d = _date.fromisoformat(loan["zinsbindung_end"])
        years_to_zb_end = max(0.0, (zb_d - today).days / 365.25)
        original_annuity = (
            loan["darlehenssumme"]
            * (loan["zinssatz_pct"] + loan["tilgung_anfang_pct"])
            / 100
        )
        original_rate = loan["zinssatz_pct"]
        tilgung_pct = loan["tilgung_anfang_pct"]
    else:
        years_to_zb_end = 0.0
        original_annuity = 0
        original_rate = 0
        tilgung_pct = 0

    rest = rest_t0
    rent_y1 = prop["kaltmiete_monthly"] * 12
    opex_y1 = prop["opex_monthly_total"] * 12

    yearly = []
    anschluss_annuity = None

    for year in range(1, int(holding_years) + 1):
        rent = rent_y1 * ((1 + annual_rent_growth_pct / 100) ** (year - 1))
        opex = opex_y1 * ((1 + annual_opex_growth_pct / 100) ** (year - 1))

        if loan and rest > 0:
            if year <= years_to_zb_end + 0.5:
                annuity_this_year = original_annuity
                interest = rest * original_rate / 100
            else:
                if anschluss_annuity is None:
                    anschluss_annuity = (
                        rest * (anschluss_rate_pct + tilgung_pct) / 100
                    )
                annuity_this_year = anschluss_annuity
                interest = rest * anschluss_rate_pct / 100

            principal = annuity_this_year - interest
            if principal > rest:
                principal = rest
                annuity_this_year = interest + principal

            debt_service = annuity_this_year
            rest = max(0.0, rest - principal)
        else:
            interest = 0
            principal = 0
            debt_service = 0

        net_cf = rent - opex - debt_service
        yearly.append(
            {
                "year": year,
                "rent": rent,
                "opex": opex,
                "interest": interest,
                "principal_paydown": principal,
                "debt_service": debt_service,
                "net_cashflow": net_cf,
                "rest_end": rest,
            }
        )

    exit_price = current_value * ((1 + annual_appreciation_pct / 100) ** holding_years)
    selling_costs = exit_price * selling_costs_pct / 100
    rest_at_exit = rest
    equity_at_exit = exit_price - rest_at_exit - selling_costs

    cashflows = [-equity_t0]
    for i, y in enumerate(yearly):
        cf = y["net_cashflow"]
        if i == len(yearly) - 1:
            cf += equity_at_exit
        cashflows.append(cf)

    return {
        "equity_t0": equity_t0,
        "current_value_t0": current_value,
        "rest_t0": rest_t0,
        "yearly": yearly,
        "exit_price": exit_price,
        "selling_costs": selling_costs,
        "rest_at_exit": rest_at_exit,
        "equity_at_exit": equity_at_exit,
        "irr_cashflows": cashflows,
        "cumulative_cashflow": sum(y["net_cashflow"] for y in yearly),
    }


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
    if not loan or not loan.get("darlehenssumme"):
        return 0
    if loan.get("restschuld_current") is not None:
        return float(loan["restschuld_current"])
    return projected_restschuld(loan, purchase_date_iso, today=today)


def projected_restschuld(loan, purchase_date_iso, today=None):
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


def restschuld_is_projection(loan):
    return not (loan and loan.get("restschuld_current") is not None)


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
