import pytest

from calculations import (
    amortisation_schedule,
    cash_on_cash,
    gesamtrendite_components,
    gross_yield,
    net_yield,
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
