import streamlit as st

from seed_portfolio import PORTFOLIO, LOANS_BY_PROPERTY_ID
from utils import euro, german_date, percent

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

loan = LOANS_BY_PROPERTY_ID.get(p["property_id"])

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
        st.write("Keine Finanzierungsdaten hinterlegt.")
