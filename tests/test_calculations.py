import pytest

from calculations import gross_yield, net_yield


def test_gross_yield_basic():
    assert gross_yield(12_000, 300_000) == pytest.approx(4.0)


def test_gross_yield_zero_price_safe():
    assert gross_yield(10_000, 0) == 0.0


def test_gross_yield_negative_price_safe():
    assert gross_yield(10_000, -1) == 0.0


def test_net_yield_basic():
    assert net_yield(12_000, 2_000, 330_000) == pytest.approx(
        10_000 / 330_000 * 100
    )


def test_net_yield_zero_acquisition_safe():
    assert net_yield(10_000, 1_000, 0) == 0.0


# --- Excel reconciliation against seed data ---
#
# BER-001 (Schönhauser Allee 12):
#   purchase_price          = 420,000
#   kaufnebenkosten_total   =  42,000
#   gesamterwerb            = 462,000
#   kaltmiete_monthly       =     910  ->  annual = 10,920
#   opex_monthly_total      =     180  ->  annual =  2,160
#
#   Bruttomietrendite = 10,920 / 420,000 = 2.60000 %
#   Nettomietrendite  = (10,920 - 2,160) / 462,000 = 8,760 / 462,000 = 1.89610 %


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
