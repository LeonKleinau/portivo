from datetime import date

import pytest

from engagement import (
    MARKET_RATE_PCT,
    all_alerts,
    geg_alerts,
    mietspiegel_alert,
    prolongation_alert,
)


SAMPLE_LOAN = {
    "loan_id": "TEST",
    "property_id": "TEST",
    "bank": "Testbank",
    "darlehenssumme": 300_000,
    "zinssatz_pct": 1.5,
    "zinsbindung_end": "2027-01-15",
    "tilgung_anfang_pct": 2.0,
    "restschuld_current": 250_000,
}


# --- prolongation_alert ---


def test_prolongation_alert_returns_none_for_no_loan():
    assert prolongation_alert(None, today=date(2026, 5, 15)) is None


def test_prolongation_alert_none_when_more_than_18_months():
    # 2027-01-15 minus 2025-01-01 = 745 days ≈ 24.5 months
    assert prolongation_alert(SAMPLE_LOAN, today=date(2025, 1, 1)) is None


def test_prolongation_alert_info_at_18_months():
    # 2027-01-15 minus 2025-07-15 ≈ 18 months
    alert = prolongation_alert(SAMPLE_LOAN, today=date(2025, 7, 15))
    assert alert is not None
    assert alert["severity"] == "info"


def test_prolongation_alert_warning_at_12_months():
    alert = prolongation_alert(SAMPLE_LOAN, today=date(2026, 1, 15))
    assert alert is not None
    assert alert["severity"] == "warning"


def test_prolongation_alert_urgent_at_6_months():
    alert = prolongation_alert(SAMPLE_LOAN, today=date(2026, 7, 15))
    assert alert is not None
    assert alert["severity"] == "urgent"


def test_prolongation_alert_urgent_past_expiry():
    alert = prolongation_alert(SAMPLE_LOAN, today=date(2027, 6, 1))
    assert alert is not None
    assert alert["severity"] == "urgent"


def test_prolongation_alert_includes_delta_vs_market():
    alert = prolongation_alert(SAMPLE_LOAN, today=date(2026, 1, 15))
    assert alert["delta_pct"] == pytest.approx(MARKET_RATE_PCT - 1.5)
    assert alert["current_rate_pct"] == 1.5
    assert alert["market_rate_pct"] == MARKET_RATE_PCT


# --- geg_alerts ---


def test_geg_no_alerts_for_empty_property():
    assert geg_alerts({}, today=date(2026, 5, 15)) == []


def test_geg_energieausweis_warning_within_18_months_of_expiry():
    prop = {"energieausweis_date": "2017-01-01"}  # expires 2027-01-01
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert any(a["id"] == "energieausweis_expiring" for a in alerts)
    expiring = next(a for a in alerts if a["id"] == "energieausweis_expiring")
    assert expiring["severity"] == "warning"


def test_geg_energieausweis_urgent_when_expired():
    prop = {"energieausweis_date": "2015-01-01"}  # expires 2025-01-01
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert any(a["id"] == "energieausweis_expired" for a in alerts)
    expired = next(a for a in alerts if a["id"] == "energieausweis_expired")
    assert expired["severity"] == "urgent"


def test_geg_no_energieausweis_alert_when_far_from_expiry():
    prop = {"energieausweis_date": "2024-01-01"}
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert not any(a["id"].startswith("energieausweis") for a in alerts)


def test_geg_heating_alert_for_old_gas():
    prop = {
        "heizungsart": "Gas-Zentralheizung",
        "heizung_installation_year": 2015,
    }
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert any(a["id"] == "geg_heating" for a in alerts)


def test_geg_no_heating_alert_for_fernwaerme():
    prop = {
        "heizungsart": "Fernwärme",
        "heizung_installation_year": 2010,
    }
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert not any(a["id"] == "geg_heating" for a in alerts)


def test_geg_no_heating_alert_for_new_gas_post_2024():
    prop = {
        "heizungsart": "Gas-Zentralheizung",
        "heizung_installation_year": 2024,
    }
    alerts = geg_alerts(prop, today=date(2026, 5, 15))
    assert not any(a["id"] == "geg_heating" for a in alerts)


# --- mietspiegel_alert ---


def test_mietspiegel_alert_none_when_at_or_above_mietspiegel():
    prop = {
        "kaltmiete_monthly": 900,
        "wohnflaeche_sqm": 50,
        "mietspiegel_eur_per_sqm": 18.0,
    }
    # current = 18.0/sqm == mietspiegel → gap = 0
    assert mietspiegel_alert(prop) is None


def test_mietspiegel_alert_none_for_gap_below_5_pct():
    prop = {
        "kaltmiete_monthly": 700,
        "wohnflaeche_sqm": 50,
        "mietspiegel_eur_per_sqm": 14.5,
    }
    # current = 14.0/sqm, mietspiegel = 14.5, gap ≈ 3.4 %
    assert mietspiegel_alert(prop) is None


def test_mietspiegel_alert_triggers_above_5_pct_gap():
    prop = {
        "kaltmiete_monthly": 600,
        "wohnflaeche_sqm": 50,
        "mietspiegel_eur_per_sqm": 14.0,
    }
    # current = 12.0/sqm, gap = 2/14 ≈ 14.29 %, uplift = 2 × 50 = 100 €/Monat
    alert = mietspiegel_alert(prop)
    assert alert is not None
    assert alert["gap_pct"] == pytest.approx(2 / 14 * 100, abs=0.01)
    assert alert["monthly_uplift_potential"] == pytest.approx(100, abs=0.01)


# --- all_alerts integration ---


def test_all_alerts_combines_sources_and_sorts_by_severity():
    prop = {
        "kaltmiete_monthly": 700,
        "wohnflaeche_sqm": 50,
        "heizungsart": "Gas-Zentralheizung",
        "heizung_installation_year": 2015,
        "energieausweis_date": "2015-01-01",  # expired
        "mietspiegel_eur_per_sqm": 18.0,
    }
    loan = dict(SAMPLE_LOAN, zinsbindung_end="2026-09-01")
    alerts = all_alerts(prop, loan, today=date(2026, 5, 15))
    ids = [a["id"] for a in alerts]
    assert "prolongation" in ids
    assert "energieausweis_expired" in ids
    assert "geg_heating" in ids
    assert "mietspiegel" in ids
    severities = [a["severity"] for a in alerts]
    severity_rank = {"urgent": 0, "warning": 1, "info": 2}
    ranks = [severity_rank[s] for s in severities]
    assert ranks == sorted(ranks)
