import streamlit as st

from seed_portfolio import PORTFOLIO

st.set_page_config(page_title="Portivo", layout="wide")


def euro(amount, decimals=0):
    s = f"{amount:,.{decimals}f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def german_date(iso):
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


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
st.caption("Wähle eine Wohnung für Details.")

event = st.dataframe(
    display_rows,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

selected = event.selection.rows if event and event.selection else []

if selected:
    p = PORTFOLIO[selected[0]]
    total_acq = p["purchase_price"] + p["kaufnebenkosten_total"]
    rent_per_sqm = p["kaltmiete_monthly"] / p["wohnflaeche_sqm"]
    price_per_sqm = p["purchase_price"] / p["wohnflaeche_sqm"]

    st.divider()
    st.subheader(f"Details — {p['address']}")

    d1, d2 = st.columns(2)

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
else:
    st.info("Klicke eine Zeile in der Tabelle, um Details zu sehen.")
