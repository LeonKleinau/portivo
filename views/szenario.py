from datetime import date

import plotly.graph_objects as go
import streamlit as st

from calculations import irr, scenario_projection
from seed_portfolio import PORTFOLIO
from utils import euro, get_loan, get_property, percent, stat

if st.button("← Zurück zum Portfolio"):
    st.switch_page("views/portfolio.py")

st.title("Szenario-Rechner")
st.caption(
    "Spiele mit Annahmen für Haltedauer, Wertsteigerung, Mietwachstum und "
    "Anschlussfinanzierung. Berechnet IRR, Exit-Eigenkapital und kumulierten "
    "Cashflow pro Wohnung oder über das gesamte Portfolio."
)

resolved = [get_property(p["property_id"]) for p in PORTFOLIO]
all_ids = [p["property_id"] for p in resolved]
id_to_address = {p["property_id"]: p["address"].split(",")[0] for p in resolved}

selected_ids = st.multiselect(
    "Wohnungen auswählen",
    options=all_ids,
    default=all_ids,
    format_func=lambda pid: id_to_address.get(pid, pid),
)

if not selected_ids:
    st.warning("Wähle mindestens eine Wohnung, um eine Analyse zu starten.")
    st.stop()

st.divider()
st.markdown("##### Annahmen")

a1, a2 = st.columns(2)
with a1:
    holding_years = st.slider("Haltedauer (Jahre ab heute)", 1, 30, value=10)
with a2:
    appreciation = st.slider(
        "Wertsteigerung p.a. (%)",
        min_value=0.0,
        max_value=6.0,
        value=2.0,
        step=0.25,
        format="%.2f %%",
    )

a3, a4 = st.columns(2)
with a3:
    rent_growth = st.slider(
        "Mietwachstum p.a. (%)",
        min_value=0.0,
        max_value=5.0,
        value=1.5,
        step=0.25,
        format="%.2f %%",
    )
with a4:
    opex_growth = st.slider(
        "Kostenwachstum p.a. (%)",
        min_value=0.0,
        max_value=5.0,
        value=2.0,
        step=0.25,
        format="%.2f %%",
    )

a5, a6 = st.columns(2)
with a5:
    anschluss = st.slider(
        "Anschluss-Zinssatz nach Zinsbindung (%)",
        min_value=0.0,
        max_value=8.0,
        value=3.8,
        step=0.1,
        format="%.2f %%",
    )
with a6:
    sell_costs = st.slider(
        "Verkaufsnebenkosten (% vom Exit-Preis)",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
        format="%.2f %%",
    )

today = date.today()
projections = []
for pid in selected_ids:
    p = next(prop for prop in resolved if prop["property_id"] == pid)
    loan = get_loan(pid)
    proj = scenario_projection(
        p,
        loan,
        holding_years=holding_years,
        today=today,
        annual_appreciation_pct=appreciation,
        annual_rent_growth_pct=rent_growth,
        annual_opex_growth_pct=opex_growth,
        anschluss_rate_pct=anschluss,
        selling_costs_pct=sell_costs,
    )
    projections.append((p, proj))

total_eq_t0 = sum(pr["equity_t0"] for _, pr in projections)
total_eq_exit = sum(pr["equity_at_exit"] for _, pr in projections)
total_cum_cf = sum(pr["cumulative_cashflow"] for _, pr in projections)
total_exit_price = sum(pr["exit_price"] for _, pr in projections)

aggregated_cashflows = [0.0] * (holding_years + 1)
for _, pr in projections:
    for i, cf in enumerate(pr["irr_cashflows"]):
        aggregated_cashflows[i] += cf

portfolio_irr = irr(aggregated_cashflows)
total_return = total_cum_cf + total_eq_exit - total_eq_t0
equity_multiple = (total_cum_cf + total_eq_exit) / total_eq_t0 if total_eq_t0 > 0 else 0

st.divider()
st.markdown("##### Ergebnis")

k1, k2, k3, k4 = st.columns(4)
k1.metric("IRR p.a.", percent(portfolio_irr * 100) if portfolio_irr is not None else "—")
k2.metric("Equity Multiple", f"{equity_multiple:.2f}×".replace(".", ","))
k3.metric("Exit-Eigenkapital", euro(total_eq_exit))
k4.metric("Σ Cashflow Haltedauer", euro(total_cum_cf))

st.caption(
    f"Eingesetztes Eigenkapital heute: {euro(total_eq_t0)} · "
    f"Gesamt-Exit-Preis (nach {holding_years} Jahren): {euro(total_exit_price)} · "
    f"Gesamtrendite über Haltedauer: {euro(total_return)}"
)

cum_cf_axis = [0]
running = 0
for i in range(1, len(aggregated_cashflows)):
    running += aggregated_cashflows[i]
    cum_cf_axis.append(running)

cf_fig = go.Figure()
cf_fig.add_trace(
    go.Scatter(
        x=list(range(0, holding_years + 1)),
        y=cum_cf_axis,
        mode="lines+markers",
        line={"color": "#00d09c", "width": 3},
        marker={"size": 6},
        fill="tozeroy",
        fillcolor="rgba(0, 208, 156, 0.10)",
        name="Kumulierter Cashflow inkl. Exit",
        hovertemplate="Jahr %{x}<br>€ %{y:,.0f}<extra></extra>",
    )
)
cf_fig.add_hline(y=0, line_color="#30363d", line_width=1)
cf_fig.update_layout(
    title="Kumulierter Cashflow inkl. Exit-Equity",
    xaxis_title="Jahre ab heute",
    yaxis_title="€",
    height=380,
    margin=dict(t=50, b=40, l=20, r=20),
    showlegend=False,
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(color="#e6edf3"),
)
st.plotly_chart(cf_fig, use_container_width=True)

with st.expander("Details pro Wohnung", expanded=False):
    for p, pr in projections:
        st.markdown(f"**{p['address'].split(',')[0]}**")
        cols = st.columns(4)
        with cols[0]:
            stat("EK heute", euro(pr["equity_t0"]))
        with cols[1]:
            individual_irr = irr(pr["irr_cashflows"])
            stat("IRR p.a.", percent(individual_irr * 100) if individual_irr is not None else "—")
        with cols[2]:
            stat("Exit-Preis", euro(pr["exit_price"]))
        with cols[3]:
            stat("Exit-EK", euro(pr["equity_at_exit"]))
        st.divider()

with st.expander("Jährliche Cashflows (Aggregat)", expanded=False):
    yearly_rows = []
    for i in range(1, holding_years + 1):
        agg_rent = sum(pr["yearly"][i - 1]["rent"] for _, pr in projections)
        agg_opex = sum(pr["yearly"][i - 1]["opex"] for _, pr in projections)
        agg_debt = sum(pr["yearly"][i - 1]["debt_service"] for _, pr in projections)
        agg_principal = sum(pr["yearly"][i - 1]["principal_paydown"] for _, pr in projections)
        agg_cf = sum(pr["yearly"][i - 1]["net_cashflow"] for _, pr in projections)
        agg_rest = sum(pr["yearly"][i - 1]["rest_end"] for _, pr in projections)
        yearly_rows.append(
            {
                "Jahr": today.year + i,
                "Miete": euro(agg_rent),
                "Bewirtschaftung": euro(agg_opex),
                "Schuldendienst": euro(agg_debt),
                "davon Tilgung": euro(agg_principal),
                "Netto-Cashflow": euro(agg_cf),
                "Restschuld Ende": euro(agg_rest),
            }
        )
    st.dataframe(yearly_rows, use_container_width=True, hide_index=True)

st.caption(
    "Annahmen: Wertsteigerung wirkt ab heute (historische Wertentwicklung "
    "nicht modelliert). Schuldendienst während Zinsbindung mit Originalannuität, "
    "danach neuer Annuitätendarlehen zum Anschlusszins mit gleichbleibender Tilgung. "
    "Keine Vorfälligkeitsentschädigung modelliert. Keine Spekulationssteuer in IRR-Berechnung. "
    "Keine Steuer- oder Anlageberatung."
)
