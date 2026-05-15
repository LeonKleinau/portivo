from datetime import date

import plotly.graph_objects as go
import streamlit as st

from calculations import cash_on_cash, gross_yield, net_yield, tax_summary
from engagement import all_alerts
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

all_property_alerts = []
for p in resolved:
    loan = get_loan(p["property_id"])
    alerts = all_alerts(p, loan)
    for alert in alerts:
        all_property_alerts.append(
            {
                **alert,
                "property_id": p["property_id"],
                "property_address": p["address"],
                "property_short": p["address"].split(",")[0],
            }
        )

severity_order = {"urgent": 0, "warning": 1, "info": 2}
all_property_alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))

n_urgent = sum(1 for a in all_property_alerts if a["severity"] == "urgent")
n_warning = sum(1 for a in all_property_alerts if a["severity"] == "warning")
n_info = sum(1 for a in all_property_alerts if a["severity"] == "info")

st.subheader("Hinweise & Termine im Portfolio")
if not all_property_alerts:
    st.success("Keine offenen Hinweise im Portfolio.")
else:
    summary_parts = []
    if n_urgent:
        summary_parts.append(f"{n_urgent} dringend")
    if n_warning:
        summary_parts.append(f"{n_warning} Warnungen")
    if n_info:
        summary_parts.append(f"{n_info} Hinweise")
    summary_text = " · ".join(summary_parts) if summary_parts else f"{len(all_property_alerts)} Einträge"
    st.caption(f"{len(all_property_alerts)} offene Einträge: {summary_text}")

    for a in all_property_alerts:
        sev = a["severity"]
        if sev == "urgent":
            box = st.error
            badge = "🔴"
        elif sev == "warning":
            box = st.warning
            badge = "🟠"
        else:
            box = st.info
            badge = "🔵"
        box(
            f"{badge} **{a['property_short']}** — {a['title']}\n\n{a['detail']}"
        )
        if st.button(
            f"→ Zur Detailansicht ({a['property_short']})",
            key=f"alert_nav_{a['property_id']}_{a['id']}",
            type="tertiary",
        ):
            st.session_state["selected_property_id"] = a["property_id"]
            st.query_params["property_id"] = a["property_id"]
            st.switch_page("views/wohnung.py")

st.divider()

chart_labels = []
chart_net = []
chart_rents = []
chart_opex = []
chart_annuity = []
for p in resolved:
    chart_labels.append(p["address"].split(",")[0])
    monthly_rent = p["kaltmiete_monthly"]
    monthly_opex = p["opex_monthly_total"]
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
    net = monthly_rent - monthly_opex - monthly_annuity
    chart_net.append(net)
    chart_rents.append(monthly_rent)
    chart_opex.append(monthly_opex)
    chart_annuity.append(monthly_annuity)

bar_colors = ["#2e7d32" if v >= 0 else "#c62828" for v in chart_net]
bar_text = [euro(v) for v in chart_net]
customdata = list(zip(chart_rents, chart_opex, chart_annuity))

fig = go.Figure(
    go.Bar(
        x=chart_labels,
        y=chart_net,
        marker_color=bar_colors,
        text=bar_text,
        textposition="outside",
        customdata=customdata,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Kaltmiete: € %{customdata[0]:,.0f}<br>"
            "− Bewirtschaftung: € %{customdata[1]:,.0f}<br>"
            "− Annuität: € %{customdata[2]:,.0f}<br>"
            "<b>= Netto: € %{y:,.0f}</b>"
            "<extra></extra>"
        ),
    )
)
fig.update_layout(
    title="Monatlicher Netto-Cashflow pro Wohnung",
    yaxis_title="€",
    height=400,
    margin=dict(t=50, b=40, l=20, r=20),
    showlegend=False,
)
fig.add_hline(y=0, line_color="#666", line_width=1)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Grün = positiver Cashflow, rot = negativer Cashflow. Hover für die Aufschlüsselung in Kaltmiete, Bewirtschaftung und Annuität."
)

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


st.divider()
st.subheader("Steuerberater-Export")
st.caption(
    "Anlage-V-Daten als CSV für deinen Steuerberater. Pro Objekt und Jahr: "
    "Mieteinnahmen, Schuldzinsen, Bewirtschaftungskosten und AfA Gebäude — direkt importfähig in Excel oder DATEV."
)

current_year = date.today().year
year_options = list(range(current_year, current_year - 9, -1))
selected_year = st.selectbox(
    "Steuerjahr",
    year_options,
    index=1 if len(year_options) > 1 else 0,
    key="tax_year_selector",
)

tax_rows = []
for p in resolved:
    loan_for_tax = get_loan(p["property_id"])
    s = tax_summary(p, loan_for_tax, year=selected_year)
    if s:
        tax_rows.append(s)

if not tax_rows:
    st.info(
        f"Keine Objekte im Steuerjahr {selected_year} verfügbar — alle wurden später erworben."
    )
else:
    preview = []
    for s in tax_rows:
        preview.append(
            {
                "Objekt": s["address"].split(",")[0],
                "Mieteinnahmen": euro(s["mieteinnahmen"]),
                "Schuldzinsen": euro(s["schuldzinsen"]),
                "Bewirtschaftung": euro(s["bewirtschaftungskosten"]),
                "AfA Gebäude": euro(s["afa_gebaeude"]),
                "Σ Werbungskosten": euro(s["summe_werbungskosten"]),
                "Überschuss/Verlust": euro(s["ueberschuss_verlust"]),
            }
        )
    st.dataframe(preview, use_container_width=True, hide_index=True)

    total_einnahmen = sum(s["mieteinnahmen"] for s in tax_rows)
    total_werbungskosten = sum(s["summe_werbungskosten"] for s in tax_rows)
    total_ueberschuss = total_einnahmen - total_werbungskosten
    color = "#1b5e20" if total_ueberschuss >= 0 else "#8b0000"
    st.markdown(
        f"**Portfolio gesamt {selected_year}**: "
        f"Mieteinnahmen {euro(total_einnahmen)} − "
        f"Werbungskosten {euro(total_werbungskosten)} = "
        f"<span style='color: {color}; font-weight: bold;'>{euro(total_ueberschuss)}</span> "
        f"Überschuss / Verlust",
        unsafe_allow_html=True,
    )

    def _fmt_de(value):
        return f"{value:.2f}".replace(".", ",")

    csv_lines = [
        "Objekt-ID;Adresse;Jahr;Mieteinnahmen (EUR);Schuldzinsen (EUR);"
        "Bewirtschaftungskosten (EUR);AfA-Satz (%);AfA Gebaeude (EUR);"
        "Summe Werbungskosten (EUR);Ueberschuss/Verlust (EUR)"
    ]
    for s in tax_rows:
        csv_lines.append(
            ";".join(
                [
                    s["property_id"],
                    s["address"],
                    str(s["year"]),
                    _fmt_de(s["mieteinnahmen"]),
                    _fmt_de(s["schuldzinsen"]),
                    _fmt_de(s["bewirtschaftungskosten"]),
                    _fmt_de(s["afa_rate_pct"]),
                    _fmt_de(s["afa_gebaeude"]),
                    _fmt_de(s["summe_werbungskosten"]),
                    _fmt_de(s["ueberschuss_verlust"]),
                ]
            )
        )
    csv_text = "\n".join(csv_lines)

    st.download_button(
        label=f"📥 Anlage-V-Daten {selected_year} als CSV herunterladen",
        data=("﻿" + csv_text).encode("utf-8"),
        file_name=f"portivo_anlage_v_{selected_year}.csv",
        mime="text/csv",
    )

    st.caption(
        "Vereinfachungen: AfA-Basis = 80 % des Gesamterwerbskosten (Gebäudeanteil), "
        "AfA-Satz 2 % (Bj. < 2023) bzw. 3 % (Bj. ≥ 2023), Bewirtschaftungskosten als "
        "Lump-Sum. Bei abweichendem Bodenrichtwert-Anteil oder Sondersituationen "
        "manuell verfeinern. **Keine Steuerberatung — bitte mit deinem Steuerberater abstimmen.**"
    )
