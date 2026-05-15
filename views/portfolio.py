import plotly.graph_objects as go
import streamlit as st

from calculations import cash_on_cash, gross_yield, net_yield
from seed_portfolio import PORTFOLIO
from utils import euro, german_date, get_loan, get_property, percent

st.title("Portivo")
st.caption("Portfolio-Übersicht")

resolved = [get_property(p["property_id"]) for p in PORTFOLIO]

total_purchase_price = sum(p["purchase_price"] for p in resolved)
total_invested = sum(
    p["purchase_price"] + p["kaufnebenkosten_total"] for p in resolved
)
total_annual_rent = sum(p["kaltmiete_monthly"] * 12 for p in resolved)
total_annual_opex = sum(p["opex_monthly_total"] * 12 for p in resolved)
monthly_kaltmiete = sum(p["kaltmiete_monthly"] for p in resolved)
n_properties = len(resolved)

total_eigenkapital = 0
total_annual_debt = 0
for p in resolved:
    loan = get_loan(p["property_id"])
    total_acq = p["purchase_price"] + p["kaufnebenkosten_total"]
    if loan:
        total_eigenkapital += total_acq - loan["darlehenssumme"]
        total_annual_debt += (
            loan["darlehenssumme"]
            * (loan["zinssatz_pct"] + loan["tilgung_anfang_pct"])
            / 100
        )
    else:
        total_eigenkapital += total_acq

portfolio_brutto = gross_yield(total_annual_rent, total_purchase_price)
portfolio_netto = net_yield(total_annual_rent, total_annual_opex, total_invested)
portfolio_coc = cash_on_cash(
    total_annual_rent, total_annual_opex, total_annual_debt, total_eigenkapital
)

row1 = st.columns(3)
row1[0].metric("Investiertes Kapital", euro(total_invested))
row1[1].metric("Eigenkapital", euro(total_eigenkapital))
row1[2].metric("Wohnungen", n_properties)

row2 = st.columns(3)
row2[0].metric("Bruttomietrendite (Ø)", percent(portfolio_brutto))
row2[1].metric("Nettomietrendite (Ø)", percent(portfolio_netto))
row2[2].metric("Cash-on-Cash (Ø)", percent(portfolio_coc))

st.divider()

chart_labels = []
chart_rent = []
chart_opex_neg = []
chart_annuity_neg = []
for p in resolved:
    chart_labels.append(p["address"].split(",")[0])
    chart_rent.append(p["kaltmiete_monthly"])
    chart_opex_neg.append(-p["opex_monthly_total"])
    loan = get_loan(p["property_id"])
    if loan:
        monthly_annuity = (
            loan["darlehenssumme"]
            * (loan["zinssatz_pct"] + loan["tilgung_anfang_pct"])
            / 100
            / 12
        )
    else:
        monthly_annuity = 0
    chart_annuity_neg.append(-monthly_annuity)

fig = go.Figure()
fig.add_trace(
    go.Bar(name="Kaltmiete", x=chart_labels, y=chart_rent, marker_color="#4caf50")
)
fig.add_trace(
    go.Bar(name="Bewirtschaftung", x=chart_labels, y=chart_opex_neg, marker_color="#ff9800")
)
fig.add_trace(
    go.Bar(name="Annuität", x=chart_labels, y=chart_annuity_neg, marker_color="#f44336")
)
fig.update_layout(
    title="Monatlicher Cashflow pro Wohnung",
    barmode="relative",
    yaxis_title="€",
    height=400,
    margin=dict(t=50, b=40, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig.add_hline(y=0, line_color="black", line_width=1)
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Wohnungen")
st.caption("Klicke auf eine Adresse, um zur Detailansicht zu wechseln.")

for p in resolved:
    loan = get_loan(p["property_id"])
    with st.container(border=True):
        if st.button(
            p["address"],
            key=f"open_{p['property_id']}",
            type="tertiary",
            use_container_width=True,
        ):
            st.session_state["selected_property_id"] = p["property_id"]
            st.query_params["property_id"] = p["property_id"]
            st.switch_page("views/wohnung.py")

        cols = st.columns(5)
        with cols[0]:
            st.caption("Wohnfläche")
            st.write(f"**{p['wohnflaeche_sqm']} m²**")
        with cols[1]:
            st.caption("Kaufdatum")
            st.write(f"**{german_date(p['purchase_date'])}**")
        with cols[2]:
            st.caption("Kaufpreis")
            st.write(f"**{euro(p['purchase_price'])}**")
        with cols[3]:
            st.caption("Kaltmiete (mtl.)")
            st.write(f"**{euro(p['kaltmiete_monthly'])}**")
        with cols[4]:
            st.caption("Finanzierung")
            if loan:
                st.write(f"**{loan['bank']}**")
            else:
                st.write("⚠️ **Daten fehlen**")
