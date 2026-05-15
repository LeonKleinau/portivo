import pytest

from datetime import date

from calculations import (
    amortisation_schedule,
    breakeven_rate_pct,
    cash_on_cash,
    cashflow_at_new_rate,
    current_restschuld,
    equity_buildup,
    gesamtrendite_components,
    gross_yield,
    net_yield,
    projected_restschuld,
    restschuld_is_projection,
    tax_summary,
    true_total_return,
)


# --- gross_yield ---


def test_gross_yield_basic():
    assert gross_yield(12_000, 300_000) == pytest.approx(4.0)


def test_gross_yield_zero_price_safe():
    assert gross_yield(10_000, 0) == 0.0


def test_gross_yield_negative_price_safe():
    assert gross_yield(10_000, -1) == 0.0


# --- net_yield ---


def test_net_yield_basic():
    assert net_yield(12_000, 2_000, 330_000) == pytest.approx(
        10_000 / 330_000 * 100
    )


def test_net_yield_zero_acquisition_safe():
    assert net_yield(10_000, 1_000, 0) == 0.0


# --- cash_on_cash ---


def test_cash_on_cash_basic():
    # 10k - 2k - 5k = 3k cashflow / 100k EK = 3 %
    assert cash_on_cash(10_000, 2_000, 5_000, 100_000) == pytest.approx(3.0)


def test_cash_on_cash_zero_equity_safe():
    assert cash_on_cash(10_000, 1_000, 5_000, 0) == 0.0


def test_cash_on_cash_can_be_negative():
    # rent below opex + debt → negative cashflow → negative return
    assert cash_on_cash(10_000, 5_000, 8_000, 50_000) == pytest.approx(-6.0)


def test_cash_on_cash_no_debt():
    # Without debt service, cash-on-cash collapses to net yield (using EK as denominator)
    assert cash_on_cash(10_000, 2_000, 0, 100_000) == pytest.approx(8.0)


# --- true_total_return ---


def test_true_total_return_basic():
    # cashflow=3000, tilgung=4000, knk=20000/10y=2000/y
    # numerator = 3000 + 4000 - 2000 = 5000
    # / 100000 EK = 5 %
    result = true_total_return(
        annual_rent=10_000,
        annual_opex=2_000,
        annual_debt_service=5_000,
        annual_tilgung=4_000,
        kaufnebenkosten=20_000,
        eigenkapital=100_000,
        holding_period_years=10,
    )
    assert result == pytest.approx(5.0)


def test_true_total_return_zero_equity_safe():
    result = true_total_return(
        annual_rent=10_000,
        annual_opex=2_000,
        annual_debt_service=5_000,
        annual_tilgung=4_000,
        kaufnebenkosten=20_000,
        eigenkapital=0,
        holding_period_years=10,
    )
    assert result == 0.0


def test_true_total_return_zero_holding_period_safe():
    result = true_total_return(
        annual_rent=10_000,
        annual_opex=2_000,
        annual_debt_service=5_000,
        annual_tilgung=4_000,
        kaufnebenkosten=20_000,
        eigenkapital=100_000,
        holding_period_years=0,
    )
    assert result == 0.0


# --- Excel reconciliation against seed data ---
#
# BER-001 (Schönhauser Allee 12):
#   purchase_price          = 420,000
#   kaufnebenkosten_total   =  42,000
#   gesamterwerb            = 462,000
#   kaltmiete_monthly       =     910  ->  annual = 10,920
#   opex_monthly_total      =     180  ->  annual =  2,160
#   loan.darlehenssumme     = 336,000
#   loan.zinssatz_pct       =     1.5
#   loan.tilgung_anfang_pct =     2.0
#   annual_debt_service     = 336,000 × 3.5 % = 11,760
#   annual_tilgung_y1       = 336,000 × 2.0 % =  6,720
#   eigenkapital            = 462,000 - 336,000 = 126,000
#   knk_amortised (10y)     =  42,000 / 10     =  4,200
#
#   Brutto             = 10,920 / 420,000           = 2.6000 %
#   Netto              = (10,920 - 2,160) / 462,000 = 1.8961 %
#   Cash-on-Cash       = (10,920 - 2,160 - 11,760) / 126,000 = -3,000 / 126,000 = -2.3810 %
#   Gesamtrendite      = (-3,000 + 6,720 - 4,200) / 126,000  =   -480 / 126,000 = -0.3810 %


def test_ber001_gross_yield_matches_excel():
    annual_rent = 910 * 12
    assert gross_yield(annual_rent, 420_000) == pytest.approx(2.6, abs=1e-4)


def test_ber001_net_yield_matches_excel():
    annual_rent = 910 * 12
    annual_opex = 180 * 12
    total_acq = 420_000 + 42_000
    expected = 8_760 / 462_000 * 100
    assert net_yield(annual_rent, annual_opex, total_acq) == pytest.approx(
        expected, abs=1e-6
    )


def test_ber001_cash_on_cash_matches_excel():
    coc = cash_on_cash(
        annual_rent=910 * 12,
        annual_opex=180 * 12,
        annual_debt_service=11_760,
        eigenkapital=126_000,
    )
    assert coc == pytest.approx(-3_000 / 126_000 * 100, abs=1e-6)


def test_ber001_true_total_return_matches_excel():
    ttr = true_total_return(
        annual_rent=910 * 12,
        annual_opex=180 * 12,
        annual_debt_service=11_760,
        annual_tilgung=6_720,
        kaufnebenkosten=42_000,
        eigenkapital=126_000,
        holding_period_years=10,
    )
    assert ttr == pytest.approx(-480 / 126_000 * 100, abs=1e-6)


# --- current_restschuld ---


def test_current_restschuld_at_purchase_returns_darlehenssumme():
    loan = {"darlehenssumme": 100_000, "zinssatz_pct": 2.0, "tilgung_anfang_pct": 2.0}
    assert current_restschuld(
        loan, "2026-05-15", today=date(2026, 5, 15)
    ) == 100_000


def test_current_restschuld_after_full_year_matches_schedule_end():
    loan = {"darlehenssumme": 100_000, "zinssatz_pct": 2.0, "tilgung_anfang_pct": 2.0}
    sched = amortisation_schedule(100_000, 2.0, 2.0, years=5)
    # 366 days = ~1.002 years to land just past full_years=1 boundary
    val = current_restschuld(loan, "2025-05-15", today=date(2026, 5, 16))
    assert val == pytest.approx(sched[0]["closing_balance"], abs=100)


def test_current_restschuld_interpolates_within_year():
    loan = {"darlehenssumme": 100_000, "zinssatz_pct": 2.0, "tilgung_anfang_pct": 2.0}
    sched = amortisation_schedule(100_000, 2.0, 2.0, years=5)
    # ~6 months elapsed
    val = current_restschuld(loan, "2025-11-15", today=date(2026, 5, 15))
    midpoint = 100_000 - 0.5 * (100_000 - sched[0]["closing_balance"])
    assert abs(val - midpoint) < 300


def test_current_restschuld_zero_for_no_loan():
    assert current_restschuld(None, "2020-01-01") == 0


def test_current_restschuld_zero_beyond_full_amortisation():
    loan = {"darlehenssumme": 100_000, "zinssatz_pct": 2.0, "tilgung_anfang_pct": 2.0}
    # 60 years past purchase — well past full amort
    val = current_restschuld(loan, "1970-01-01", today=date(2030, 1, 1))
    assert val == 0


# BER-001 reconciliation:
#   purchase 2019-06-15, today 2026-05-15 → 2526 days ≈ 6.916 years
#   schedule[5] closing ≈ 294,137 (year 6 end)
#   schedule[6] closing ≈ 286,789 (year 7 end)
#   current ≈ 294,137 - 0.916 × (294,137 - 286,789) ≈ 287,406


def test_ber001_current_restschuld_matches_excel():
    loan = {"darlehenssumme": 336_000, "zinssatz_pct": 1.5, "tilgung_anfang_pct": 2.0}
    val = current_restschuld(loan, "2019-06-15", today=date(2026, 5, 15))
    assert 287_000 < val < 288_000


def test_current_restschuld_prefers_user_override():
    loan = {
        "darlehenssumme": 336_000,
        "zinssatz_pct": 1.5,
        "tilgung_anfang_pct": 2.0,
        "restschuld_current": 280_000,
    }
    val = current_restschuld(loan, "2019-06-15", today=date(2026, 5, 15))
    assert val == 280_000


def test_projected_restschuld_ignores_user_override():
    loan = {
        "darlehenssumme": 336_000,
        "zinssatz_pct": 1.5,
        "tilgung_anfang_pct": 2.0,
        "restschuld_current": 280_000,
    }
    val = projected_restschuld(loan, "2019-06-15", today=date(2026, 5, 15))
    assert 287_000 < val < 288_000


def test_restschuld_is_projection_flag():
    loan_proj = {"darlehenssumme": 100_000, "zinssatz_pct": 2.0, "tilgung_anfang_pct": 2.0}
    loan_override = dict(loan_proj, restschuld_current=80_000)
    assert restschuld_is_projection(loan_proj) is True
    assert restschuld_is_projection(loan_override) is False


# --- cashflow_at_new_rate ---


def test_cashflow_at_new_rate_basic():
    # rent=1000 opex=100 restschuld=200_000 rate=3 tilgung=2
    # annuity = 200_000 × 5 % / 12 = 833.333...
    # cashflow = 1000 - 100 - 833.333 = 66.667
    assert cashflow_at_new_rate(1000, 100, 200_000, 3.0, 2.0) == pytest.approx(
        1000 - 100 - 200_000 * 0.05 / 12, abs=1e-6
    )


def test_cashflow_at_new_rate_no_debt():
    assert cashflow_at_new_rate(1000, 100, 0, 3.0, 2.0) == 900


def test_cashflow_at_new_rate_high_rate_goes_negative():
    cf = cashflow_at_new_rate(1000, 100, 200_000, 10.0, 2.0)
    assert cf < 0


# --- breakeven_rate_pct ---


def test_breakeven_rate_basic():
    # net_op = 900, restschuld = 200_000, tilgung = 2
    # breakeven = 900 × 1200 / 200_000 - 2 = 5.4 - 2 = 3.4 %
    assert breakeven_rate_pct(1000, 100, 200_000, 2.0) == pytest.approx(3.4)


def test_breakeven_rate_no_debt_returns_none():
    assert breakeven_rate_pct(1000, 100, 0, 2.0) is None


def test_breakeven_rate_round_trip_zero_cashflow():
    # Plugging the breakeven rate back into cashflow_at_new_rate must yield ~0
    rate = breakeven_rate_pct(1000, 100, 200_000, 2.0)
    cf = cashflow_at_new_rate(1000, 100, 200_000, rate, 2.0)
    assert cf == pytest.approx(0, abs=1e-6)


# BER-003 reconciliation: post-Zinsbindung Cashflow-Sensitivität
#   rent=1,310 opex=220 restschuld_current=360,000 tilgung=2.0
#   net_op = 1,090
#   breakeven = 1,090 × 1200 / 360,000 - 2.0 = 3.6333... - 2.0 = 1.6333... %


def test_ber003_breakeven_matches_excel():
    assert breakeven_rate_pct(1310, 220, 360_000, 2.0) == pytest.approx(
        1090 * 1200 / 360_000 - 2.0, abs=1e-6
    )


def test_ber003_cashflow_at_market_rate_matches_excel():
    # Marktzins ≈ 3.8 %, post-prolongation: rest=360_000, tilgung=2.0
    # annuity = 360_000 × 5.8 % / 12 = 1,740
    # cashflow = 1,310 - 220 - 1,740 = -650
    cf = cashflow_at_new_rate(1310, 220, 360_000, 3.8, 2.0)
    assert cf == pytest.approx(1310 - 220 - 360_000 * 0.058 / 12, abs=1e-6)


# --- amortisation_schedule ---


def test_amortisation_empty_for_zero_principal():
    assert amortisation_schedule(0, 1.5, 2.0, years=10) == []


def test_amortisation_empty_for_zero_years():
    assert amortisation_schedule(100_000, 1.5, 2.0, years=0) == []


def test_amortisation_schedule_length():
    schedule = amortisation_schedule(100_000, 1.5, 2.0, years=5)
    assert len(schedule) == 5


def test_amortisation_year1_constant_annuity():
    # annuity is constant: principal * (rate + tilgung) / 100
    schedule = amortisation_schedule(100_000, 2.0, 3.0, years=3)
    expected_annuity = 100_000 * 0.05  # 5,000
    for entry in schedule:
        assert entry["annuity"] == pytest.approx(expected_annuity)


def test_amortisation_interest_decreases_principal_increases():
    schedule = amortisation_schedule(100_000, 2.0, 3.0, years=5)
    for i in range(1, len(schedule)):
        assert schedule[i]["interest"] < schedule[i - 1]["interest"]
        assert schedule[i]["principal"] > schedule[i - 1]["principal"]


def test_amortisation_balance_decreases_to_zero_eventually():
    schedule = amortisation_schedule(100_000, 2.0, 3.0, years=50)
    assert schedule[-1]["closing_balance"] == pytest.approx(0, abs=0.01)


# Excel reconciliation: BER-001 year 1 of amortisation schedule
#   principal = 336,000  rate = 1.5 %  tilgung = 2.0 %
#   annuity   = 336,000 × 3.5 % = 11,760
#   y1 interest          = 336,000 × 1.5 % = 5,040
#   y1 principal payment = 11,760 − 5,040  = 6,720
#   y1 closing balance   = 336,000 − 6,720 = 329,280


def test_ber001_amortisation_year_one_matches_excel():
    schedule = amortisation_schedule(336_000, 1.5, 2.0, years=10)
    y1 = schedule[0]
    assert y1["opening_balance"] == 336_000
    assert y1["interest"] == pytest.approx(5_040)
    assert y1["principal"] == pytest.approx(6_720)
    assert y1["annuity"] == pytest.approx(11_760)
    assert y1["closing_balance"] == pytest.approx(329_280)


# --- tax_summary ---


BER001 = {
    "property_id": "BER-001",
    "address": "Schönhauser Allee 12, 10437 Berlin",
    "purchase_price": 420_000,
    "kaufnebenkosten_total": 42_000,
    "purchase_date": "2019-06-15",
    "kaltmiete_monthly": 910,
    "opex_monthly_total": 180,
    "wohnflaeche_sqm": 65,
    "baujahr": 1900,
}

BER001_LOAN = {
    "darlehenssumme": 336_000,
    "zinssatz_pct": 1.5,
    "tilgung_anfang_pct": 2.0,
}


def test_tax_summary_returns_none_before_purchase_year():
    assert tax_summary(BER001, BER001_LOAN, year=2018) is None


def test_tax_summary_uses_2pct_afa_for_altbau():
    s = tax_summary(BER001, BER001_LOAN, year=2025)
    assert s["afa_rate_pct"] == 2.0


def test_tax_summary_uses_3pct_afa_for_neubau_post_2023():
    prop = dict(BER001, baujahr=2024)
    s = tax_summary(prop, None, year=2025)
    assert s["afa_rate_pct"] == 3.0


def test_tax_summary_afa_basis_uses_80_pct_of_total_acq():
    # purchase 420k + KNK 42k = 462k total. 80% building share = 369,600.
    s = tax_summary(BER001, BER001_LOAN, year=2025)
    assert s["building_basis"] == pytest.approx(369_600)
    assert s["afa_gebaeude"] == pytest.approx(369_600 * 0.02)


def test_tax_summary_mieteinnahmen_is_annual_kaltmiete():
    s = tax_summary(BER001, BER001_LOAN, year=2025)
    assert s["mieteinnahmen"] == 910 * 12


def test_tax_summary_no_schuldzinsen_without_loan():
    s = tax_summary(BER001, None, year=2025)
    assert s["schuldzinsen"] == 0


def test_tax_summary_schuldzinsen_decreases_year_over_year():
    s_2020 = tax_summary(BER001, BER001_LOAN, year=2020)
    s_2025 = tax_summary(BER001, BER001_LOAN, year=2025)
    assert s_2020["schuldzinsen"] > s_2025["schuldzinsen"]


# Excel reconciliation: BER-001 tax year 2019 (= loan year 1)
#   Mieteinnahmen = 10,920
#   Schuldzinsen Jahr 1 = 5,040
#   Bewirtschaftung = 2,160
#   AfA Gebäude = (420k + 42k) × 0.80 × 2 % = 369,600 × 0.02 = 7,392
#   Σ Werbungskosten = 14,592
#   Verlust = 10,920 - 14,592 = -3,672


def test_ber001_tax_summary_2019_matches_excel():
    s = tax_summary(BER001, BER001_LOAN, year=2019)
    assert s["mieteinnahmen"] == pytest.approx(10_920)
    assert s["schuldzinsen"] == pytest.approx(5_040)
    assert s["bewirtschaftungskosten"] == pytest.approx(2_160)
    assert s["afa_gebaeude"] == pytest.approx(7_392)
    assert s["summe_werbungskosten"] == pytest.approx(14_592)
    assert s["ueberschuss_verlust"] == pytest.approx(-3_672)


# --- gesamtrendite_components ---


def test_gesamtrendite_components_sums_to_true_total_return():
    args = dict(
        annual_rent=10_000,
        annual_opex=2_000,
        annual_debt_service=5_000,
        annual_tilgung=4_000,
        kaufnebenkosten=20_000,
        eigenkapital=100_000,
        holding_period_years=10,
    )
    parts = gesamtrendite_components(**args)
    ttr = true_total_return(**args)
    assert parts["total"] == pytest.approx(ttr, abs=1e-9)


def test_gesamtrendite_components_zero_equity_safe():
    parts = gesamtrendite_components(
        annual_rent=10_000,
        annual_opex=2_000,
        annual_debt_service=5_000,
        annual_tilgung=4_000,
        kaufnebenkosten=20_000,
        eigenkapital=0,
    )
    assert parts == {"cashflow": 0.0, "tilgung": 0.0, "knk_amort": 0.0, "total": 0.0}


# BER-001 reconciliation:
#   cashflow:    (-3,000) / 126,000 × 100 = -2.38095 %
#   tilgung:     6,720    / 126,000 × 100 = +5.33333 %
#   knk_amort:   -4,200   / 126,000 × 100 = -3.33333 %
#   total:                                  -0.38095 %


def test_ber001_gesamtrendite_decomposition_matches_excel():
    parts = gesamtrendite_components(
        annual_rent=910 * 12,
        annual_opex=180 * 12,
        annual_debt_service=11_760,
        annual_tilgung=6_720,
        kaufnebenkosten=42_000,
        eigenkapital=126_000,
        holding_period_years=10,
    )
    assert parts["cashflow"] == pytest.approx(-3_000 / 126_000 * 100, abs=1e-6)
    assert parts["tilgung"] == pytest.approx(6_720 / 126_000 * 100, abs=1e-6)
    assert parts["knk_amort"] == pytest.approx(-4_200 / 126_000 * 100, abs=1e-6)
    assert parts["total"] == pytest.approx(-480 / 126_000 * 100, abs=1e-6)


# --- equity_buildup ---


def test_equity_buildup_year_zero_no_appreciation():
    # At t=0 with 0% appreciation: equity = purchase_price - initial_loan (KNK is sunk).
    schedule = amortisation_schedule(300_000, 2.0, 2.0, years=5)
    buildup = equity_buildup(
        purchase_price=400_000,
        initial_loan=300_000,
        appreciation_pct_annual=0.0,
        amort_schedule=schedule,
    )
    assert buildup[0]["year"] == 0
    assert buildup[0]["equity"] == pytest.approx(100_000)


def test_equity_buildup_no_appreciation_grows_only_via_tilgung():
    # With 0% appreciation, equity growth equals Tilgung accumulated.
    schedule = amortisation_schedule(300_000, 2.0, 2.0, years=5)
    buildup = equity_buildup(
        purchase_price=400_000,
        initial_loan=300_000,
        appreciation_pct_annual=0.0,
        amort_schedule=schedule,
    )
    year_5_tilgung_accumulated = 300_000 - schedule[4]["closing_balance"]
    assert buildup[5]["equity"] == pytest.approx(100_000 + year_5_tilgung_accumulated)


def test_equity_buildup_appreciation_compounds_on_property_value():
    # With 2% appreciation, year 10 property value = purchase_price × 1.02^10
    schedule = amortisation_schedule(300_000, 2.0, 2.0, years=10)
    buildup = equity_buildup(
        purchase_price=400_000,
        initial_loan=300_000,
        appreciation_pct_annual=2.0,
        amort_schedule=schedule,
    )
    expected_year10_value = 400_000 * (1.02 ** 10)
    assert buildup[10]["property_value"] == pytest.approx(expected_year10_value)


# BER-001 reconciliation: at Zinsbindung-Ende (year 10)
#   purchase_price        = 420,000
#   restschuld year 10    = 264,077.71 (from amort_schedule(336000, 1.5, 2.0))
#   property_value 0% app = 420,000
#   equity 0% appreciation = 420,000 - 264,077.71 = 155,922.29
#
#   eigenkapital eingesetzt (cash actually paid) = 462,000 - 336,000 = 126,000
#   So even at 0% appreciation, by year 10 EK has grown from day-1 84,000 (= 420k-336k)
#   to 155,922 — recovering the 42k KNK paid on day 1 and adding 29,922 of true wealth.


def test_ber001_equity_buildup_year10_no_appreciation():
    schedule = amortisation_schedule(336_000, 1.5, 2.0, years=15)
    buildup = equity_buildup(
        purchase_price=420_000,
        initial_loan=336_000,
        appreciation_pct_annual=0.0,
        amort_schedule=schedule,
    )
    y10 = buildup[10]
    assert y10["restschuld"] == pytest.approx(264_077.71, abs=0.01)
    assert y10["equity"] == pytest.approx(420_000 - 264_077.71, abs=0.01)
