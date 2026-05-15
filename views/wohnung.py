from datetime import date

import streamlit as st

from seed_portfolio import PORTFOLIO
from utils import euro, german_date, get_loan, percent, save_user_loan

if st.button("← Zurück zum Portfolio"):
    st.session_state.pop("selected_property_id", None)
    st.query_params.clear()
    st.switch_page("views/portfolio.py")

property_id = st.session_state.get("selected_property_id") or st.query_params.get(
    "property_id"
)
if not property_id:
    st.warning("Keine Wohnung ausgewählt.")
    st.stop()

lookup = {p["property_id"]: p for p in PORTFOLIO}
p = lookup.get(property_id)
if not p:
    st.error(f"Wohnung {property_id} nicht gefunden.")
    st.stop()

loan = get_loan(p["property_id"])

total_acq = p["purchase_price"] + p["kaufnebenkosten_total"]
rent_per_sqm = p["kaltmiete_monthly"] / p["wohnflaeche_sqm"]
price_per_sqm = p["purchase_price"] / p["wohnflaeche_sqm"]

st.title(p["address"])
st.caption(p["property_id"])

d1, d2, d3 = st.columns(3)

with d1:
    st.markdown("**Stammdaten**")
    st.write(f"**Adresse:** {p['address']}")
    st.write(f"**Wohnfläche:** {p['wohnflaeche_sqm']} m²")
    st.write(f"**Kaufdatum:** {german_date(p['purchase_date'])}")
    st.write(f"**€/m² (Kaufpreis):** {euro(price_per_sqm, 2)}")
    st.write(f"**€/m² (Kaltmiete):** {euro(rent_per_sqm, 2)}")

with d2:
    st.markdown("**Wirtschaft**")
    st.write(f"**Kaufpreis:** {euro(p['purchase_price'])}")
    st.write(f"**Kaufnebenkosten:** {euro(p['kaufnebenkosten_total'])}")
    st.write(f"**Gesamterwerbskosten:** {euro(total_acq)}")
    st.write(f"**Kaltmiete (mtl.):** {euro(p['kaltmiete_monthly'])}")
    st.write(f"**Bewirtschaftungskosten (mtl.):** {euro(p['opex_monthly_total'])}")

with d3:
    st.markdown("**Finanzierung**")
    if loan:
        eigenkapital = total_acq - loan["darlehenssumme"]
        st.write(f"**Bank:** {loan['bank']}")
        st.write(f"**Darlehenssumme:** {euro(loan['darlehenssumme'])}")
        st.write(f"**Zinssatz:** {percent(loan['zinssatz_pct'])}")
        st.write(f"**Tilgung (anfänglich):** {percent(loan['tilgung_anfang_pct'])}")
        st.write(f"**Zinsbindung bis:** {german_date(loan['zinsbindung_end'])}")
        st.write(f"**Restschuld aktuell:** {euro(loan['restschuld_current'])}")
        st.write(f"**Eigenkapital eingesetzt:** {euro(eigenkapital)}")
    else:
        st.info("Keine Finanzierungsdaten hinterlegt.")
        with st.form(key=f"loan_form_{property_id}"):
            bank = st.text_input("Bank")
            darlehenssumme = st.number_input(
                "Darlehenssumme (€)", min_value=0, step=1000, value=0
            )
            zinssatz_pct = st.number_input(
                "Zinssatz (%)",
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                value=2.0,
                format="%.2f",
            )
            zinsbindung_end = st.date_input(
                "Zinsbindung bis",
                value=date(date.today().year + 10, 1, 1),
            )
            tilgung_anfang_pct = st.number_input(
                "Anfängliche Tilgung (%)",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                value=2.0,
                format="%.2f",
            )
            restschuld_current = st.number_input(
                "Aktuelle Restschuld (€)", min_value=0, step=1000, value=0
            )
            submitted = st.form_submit_button("Finanzierung speichern")

        if submitted:
            if not bank.strip():
                st.error("Bank muss ausgefüllt sein.")
            elif darlehenssumme <= 0:
                st.error("Darlehenssumme muss größer als 0 sein.")
            else:
                save_user_loan(
                    property_id,
                    {
                        "loan_id": f"USER-{property_id}",
                        "property_id": property_id,
                        "bank": bank.strip(),
                        "darlehenssumme": darlehenssumme,
                        "zinssatz_pct": zinssatz_pct,
                        "zinsbindung_end": zinsbindung_end.strftime("%Y-%m-%d"),
                        "tilgung_anfang_pct": tilgung_anfang_pct,
                        "restschuld_current": restschuld_current,
                    },
                )
                st.rerun()
