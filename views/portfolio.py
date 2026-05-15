import streamlit as st

from seed_portfolio import PORTFOLIO
from utils import euro, german_date

st.title("Portivo")
st.caption("Portfolio-Übersicht")

total_invested = sum(
    p["purchase_price"] + p["kaufnebenkosten_total"] for p in PORTFOLIO
)
monthly_kaltmiete = sum(p["kaltmiete_monthly"] for p in PORTFOLIO)
n_properties = len(PORTFOLIO)

col1, col2, col3 = st.columns(3)
col1.metric("Investiertes Kapital", euro(total_invested))
col2.metric("Kaltmiete pro Monat", euro(monthly_kaltmiete))
col3.metric("Wohnungen", n_properties)

st.divider()

display_rows = [
    {
        "Adresse": p["address"],
        "Wohnfläche": f"{p['wohnflaeche_sqm']} m²",
        "Kaufpreis": euro(p["purchase_price"]),
        "Kaltmiete (mtl.)": euro(p["kaltmiete_monthly"]),
        "Kaufdatum": german_date(p["purchase_date"]),
    }
    for p in PORTFOLIO
]

st.subheader("Wohnungen")
st.caption("Wähle eine Wohnung, um zur Detailansicht zu wechseln.")

event = st.dataframe(
    display_rows,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected = event.selection.rows if event and event.selection else []

if selected:
    selected_id = PORTFOLIO[selected[0]]["property_id"]
    st.query_params["property_id"] = selected_id
    st.switch_page("views/wohnung.py")
