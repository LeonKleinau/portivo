import streamlit as st

from seed_portfolio import PORTFOLIO
from utils import euro, german_date, get_loan, get_property

st.title("Portivo")
st.caption("Portfolio-Übersicht")

resolved = [get_property(p["property_id"]) for p in PORTFOLIO]

total_invested = sum(
    p["purchase_price"] + p["kaufnebenkosten_total"] for p in resolved
)
monthly_kaltmiete = sum(p["kaltmiete_monthly"] for p in resolved)
n_properties = len(resolved)

col1, col2, col3 = st.columns(3)
col1.metric("Investiertes Kapital", euro(total_invested))
col2.metric("Kaltmiete pro Monat", euro(monthly_kaltmiete))
col3.metric("Wohnungen", n_properties)

st.divider()

display_rows = []
for p in resolved:
    loan = get_loan(p["property_id"])
    finanzierung_label = loan["bank"] if loan else "⚠️ Daten fehlen"
    display_rows.append(
        {
            "Adresse": p["address"],
            "Wohnfläche": f"{p['wohnflaeche_sqm']} m²",
            "Kaufpreis": euro(p["purchase_price"]),
            "Kaltmiete (mtl.)": euro(p["kaltmiete_monthly"]),
            "Kaufdatum": german_date(p["purchase_date"]),
            "Finanzierung": finanzierung_label,
        }
    )

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
    selected_id = resolved[selected[0]]["property_id"]
    st.session_state["selected_property_id"] = selected_id
    st.query_params["property_id"] = selected_id
    st.switch_page("views/wohnung.py")
