from datetime import date

import plotly.graph_objects as go
import streamlit as st

from calculations import (
    amortisation_schedule,
    breakeven_rate_pct,
    cash_on_cash,
    cashflow_at_new_rate,
    current_restschuld,
    gesamtrendite_components,
    gross_yield,
    net_yield,
    realized_return,
    restschuld_is_projection,
    true_total_return,
)
from engagement import all_alerts
from utils import (
    euro,
    format_german_number,
    german_date,
    get_loan,
    get_property,
    is_sold,
    parse_german_number,
    percent,
    save_user_loan,
    save_user_property,
    stat,
)


def _render_analytics(p, loan, total_acq):
    st.subheader("Cashflow (monatlich)")
    monthly_rent = p["kaltmiete_monthly"]
    monthly_opex = p["opex_monthly_total"]
    if loan:
        monthly_interest = loan["darlehenssumme"] * loan["zinssatz_pct"] / 100 / 12
        monthly_tilgung = (
            loan["darlehenssumme"] * loan["tilgung_anfang_pct"] / 100 / 12
        )
    else:
        monthly_interest = 0
        monthly_tilgung = 0

    net_cashflow = monthly_rent - monthly_opex - monthly_interest - monthly_tilgung
    cashflow_total_color = "#8b0000" if net_cashflow < 0 else "#1b5e20"
    wf = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["Kaltmiete", "Bewirtschaftung", "Zinsen", "Tilgung", "Netto"],
            y=[monthly_rent, -monthly_opex, -monthly_interest, -monthly_tilgung, 0],
            text=[
                euro(monthly_rent),
                euro(-monthly_opex),
                euro(-monthly_interest),
                euro(-monthly_tilgung),
                "",
            ],
            textposition="outside",
            connector={"line": {"color": "#30363d"}},
            increasing={"marker": {"color": "#00d09c"}},
            decreasing={"marker": {"color": "#ff5252"}},
            totals={"marker": {"color": cashflow_total_color}},
        )
    )
    wf.update_layout(
        yaxis_title="€",
        height=400,
        margin=dict(t=20, b=40, l=20, r=20),
        showlegend=False,
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
    )
    st.plotly_chart(wf, use_container_width=True)

    if loan:
        st.divider()
        st.subheader("Tilgungsplan")

        schedule = amortisation_schedule(
            loan["darlehenssumme"],
            loan["zinssatz_pct"],
            loan["tilgung_anfang_pct"],
            years=40,
        )
        years_axis = [0] + [s["year"] for s in schedule]
        balances = [loan["darlehenssumme"]] + [s["closing_balance"] for s in schedule]

        purchase_d = date.fromisoformat(p["purchase_date"])
        zb_d = date.fromisoformat(loan["zinsbindung_end"])
        zinsbindung_years = (zb_d - purchase_d).days / 365.25

        zb_year_idx = min(int(round(zinsbindung_years)), len(schedule))
        if zb_year_idx >= 1:
            zb_balance = schedule[zb_year_idx - 1]["closing_balance"]
        else:
            zb_balance = loan["darlehenssumme"]
        tilgung_pct_done = (
            (loan["darlehenssumme"] - zb_balance) / loan["darlehenssumme"] * 100
        )

        amort = go.Figure()
        amort.add_trace(
            go.Scatter(
                x=years_axis,
                y=balances,
                mode="lines+markers",
                line={"color": "#1976d2", "width": 3},
                marker={"size": 5},
                hovertemplate="Jahr %{x}<br>Restschuld: € %{y:,.0f}<extra></extra>",
                name="Restschuld",
            )
        )
        amort.add_vline(
            x=zinsbindung_years,
            line_dash="dash",
            line_color="#f44336",
            annotation_text="Zinsbindung-Ende",
            annotation_position="top right",
        )
        amort.update_layout(
            xaxis_title="Jahre seit Kauf",
            yaxis_title="Restschuld (€)",
            height=400,
            margin=dict(t=20, b=40, l=20, r=20),
            showlegend=False,
            template="plotly_dark",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
        )
        st.plotly_chart(amort, use_container_width=True)

        st.caption(
            f"Bei Zinsbindung-Ende ({german_date(loan['zinsbindung_end'])}): "
            f"projizierte Restschuld {euro(zb_balance)} — {percent(tilgung_pct_done)} getilgt. "
            f"Nach diesem Zeitpunkt benötigt das Darlehen eine Anschlussfinanzierung zum dann gültigen Marktzins."
        )

    st.divider()
    st.subheader("Renditezerlegung")

    rent_for_decomp = p["kaltmiete_monthly"] * 12
    opex_for_decomp = p["opex_monthly_total"] * 12
    if loan:
        debt_for_decomp = (
            loan["darlehenssumme"]
            * (loan["zinssatz_pct"] + loan["tilgung_anfang_pct"])
            / 100
        )
        tilgung_for_decomp = (
            loan["darlehenssumme"] * loan["tilgung_anfang_pct"] / 100
        )
        ek_for_decomp = total_acq - loan["darlehenssumme"]
    else:
        debt_for_decomp = 0
        tilgung_for_decomp = 0
        ek_for_decomp = total_acq

    parts = gesamtrendite_components(
        annual_rent=rent_for_decomp,
        annual_opex=opex_for_decomp,
        annual_debt_service=debt_for_decomp,
        annual_tilgung=tilgung_for_decomp,
        kaufnebenkosten=p["kaufnebenkosten_total"],
        eigenkapital=ek_for_decomp,
        holding_period_years=10,
    )

    decomp_total_color = "#8b0000" if parts["total"] < 0 else "#1b5e20"
    rd = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Cashflow", "Tilgung", "KNK-Abschlag", "Gesamtrendite"],
            y=[parts["cashflow"], parts["tilgung"], parts["knk_amort"], 0],
            text=[
                percent(parts["cashflow"]),
                percent(parts["tilgung"]),
                percent(parts["knk_amort"]),
                "",
            ],
            textposition="outside",
            connector={"line": {"color": "#30363d"}},
            increasing={"marker": {"color": "#00d09c"}},
            decreasing={"marker": {"color": "#ff5252"}},
            totals={"marker": {"color": decomp_total_color}},
        )
    )
    rd.update_layout(
        yaxis_title="% p.a. auf Eigenkapital",
        height=400,
        margin=dict(t=20, b=40, l=20, r=20),
        showlegend=False,
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#e6edf3"),
    )
    st.plotly_chart(rd, use_container_width=True)
    st.caption(
        "Cashflow + Eigenkapitalaufbau durch Tilgung − Kaufnebenkosten amortisiert (10 J.) = Gesamtrendite. "
        "Ohne Wertsteigerung."
    )


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

p = get_property(property_id)
if not p:
    st.error(f"Wohnung {property_id} nicht gefunden.")
    st.stop()

loan = get_loan(property_id)
edit_mode_key = f"edit_mode_{property_id}"
edit_mode = st.session_state.get(edit_mode_key, False)

st.title(p["address"])
st.caption(p["property_id"])

if is_sold(p):
    rr = realized_return(p, loan)
    st.success(
        f"🏆 **Verkauft am {german_date(p['verkaufs_datum'])}**"
        if p.get("verkaufs_datum")
        else "🏆 **Verkauft**"
    )
    if rr is not None:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Verkaufspreis", euro(rr["verkaufspreis"]))
        k2.metric("Netto-Erlös", euro(rr["netto_erlos"]))
        k3.metric(
            "Wealth Multiple",
            f"{rr['wealth_multiple']:.2f}×".replace(".", ","),
        )
        k4.metric(
            "Haltedauer",
            f"{rr['holding_years']:.1f} Jahre".replace(".", ","),
        )

        if rr["spek_frist_passed"]:
            st.info(
                f"🟢 **Spekulationsfrist bestanden** — Veräußerungsgewinn "
                f"von {euro(rr['veraeusserungsgewinn'])} steuerfrei."
            )
        else:
            st.warning(
                f"🟠 **Spekulationsfrist nicht erreicht** — Veräußerungsgewinn "
                f"von {euro(rr['veraeusserungsgewinn'])} unterliegt der "
                f"Einkommensteuer (kein Privileg nach § 23 EStG)."
            )

        st.divider()
        st.markdown("##### Verkaufsdetails")
        v1, v2, v3 = st.columns(3)
        with v1:
            stat("Kaufdatum", german_date(p["purchase_date"]))
            stat("Kaufpreis", euro(p["purchase_price"]))
            stat("Kaufnebenkosten", euro(p["kaufnebenkosten_total"]))
        with v2:
            stat("Verkaufsdatum", german_date(p["verkaufs_datum"]))
            stat("Verkaufspreis", euro(rr["verkaufspreis"]))
            stat("Verkaufsnebenkosten", euro(rr["verkaufsnebenkosten"]))
        with v3:
            stat("Eingesetztes Eigenkapital", euro(rr["initial_eigenkapital"]))
            stat("Restschuld bei Verkauf", euro(rr["rest_at_sale"]))
            stat("Veräußerungsgewinn", euro(rr["veraeusserungsgewinn"]))
    st.stop()

if edit_mode:
    st.caption(
        "Zahlen können im deutschen Format eingegeben werden: 200.000 für Tausender, 1,50 für Dezimalwerte."
    )

    with st.form(key=f"edit_form_{property_id}"):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**Stammdaten**")
            new_address = st.text_input("Adresse", value=p["address"])
            new_wohnflaeche_str = st.text_input(
                "Wohnfläche (m²)",
                value=format_german_number(p["wohnflaeche_sqm"]),
            )
            new_purchase_date = st.date_input(
                "Kaufdatum", value=date.fromisoformat(p["purchase_date"])
            )

        with c2:
            st.markdown("**Wirtschaft**")
            new_purchase_price_str = st.text_input(
                "Kaufpreis (€)",
                value=format_german_number(p["purchase_price"]),
                help="z.B. 420.000",
            )
            new_kaufnebenkosten_str = st.text_input(
                "Kaufnebenkosten (€)",
                value=format_german_number(p["kaufnebenkosten_total"]),
                help="z.B. 42.000",
            )
            new_kaltmiete_str = st.text_input(
                "Kaltmiete (mtl., €)",
                value=format_german_number(p["kaltmiete_monthly"]),
            )
            new_opex_str = st.text_input(
                "Bewirtschaftung (mtl., €)",
                value=format_german_number(p["opex_monthly_total"]),
            )

        with c3:
            st.markdown("**Finanzierung**")
            loan_default = loan or {}
            new_bank = st.text_input("Bank", value=loan_default.get("bank", ""))
            new_darlehen_str = st.text_input(
                "Darlehenssumme (€)",
                value=format_german_number(loan_default.get("darlehenssumme", 0)),
                help="z.B. 336.000",
            )
            new_zins_str = st.text_input(
                "Zinssatz (%)",
                value=format_german_number(loan_default.get("zinssatz_pct", 2.0), 2),
                help="z.B. 1,50",
            )
            zb_default = (
                date.fromisoformat(loan_default["zinsbindung_end"])
                if loan_default.get("zinsbindung_end")
                else date(date.today().year + 10, 1, 1)
            )
            new_zinsbindung = st.date_input("Zinsbindung bis", value=zb_default)
            new_tilgung_str = st.text_input(
                "Tilgung (%, anfänglich)",
                value=format_german_number(loan_default.get("tilgung_anfang_pct", 2.0), 2),
                help="z.B. 2,00",
            )
            current_override = loan_default.get("restschuld_current")
            new_restschuld_str = st.text_input(
                "Restschuld laut Bank (optional)",
                value=format_german_number(current_override) if current_override is not None else "",
                help=(
                    "Lasse leer, um die Restschuld automatisch aus dem Tilgungsplan "
                    "zu projizieren. Trage den Wert vom letzten Bankauszug ein, "
                    "wenn Du Sondertilgungen gemacht hast oder den exakten Stand kennst."
                ),
            )

        st.divider()
        st.markdown("##### Mietvertrag")
        mv_c1, mv_c2, mv_c3 = st.columns(3)
        with mv_c1:
            new_mieter = st.text_input(
                "Mieter", value=p.get("mieter_name", "") or ""
            )
            new_mietbeginn = st.date_input(
                "Mietbeginn",
                value=(
                    date.fromisoformat(p["mietbeginn_date"])
                    if p.get("mietbeginn_date")
                    else date.today()
                ),
            )
        with mv_c2:
            mietart_options = ["Unbefristet", "Indexmiete", "Staffelmiete", "Befristet"]
            cur_mietart = p.get("mietart") or "Unbefristet"
            if cur_mietart not in mietart_options:
                cur_mietart = "Unbefristet"
            new_mietart = st.selectbox(
                "Mietart",
                mietart_options,
                index=mietart_options.index(cur_mietart),
            )
            new_letzte_erhoehung = st.date_input(
                "Letzte Mieterhöhung",
                value=(
                    date.fromisoformat(p["letzte_mieterhoehung_date"])
                    if p.get("letzte_mieterhoehung_date")
                    else date.today()
                ),
            )
        with mv_c3:
            new_nk_str = st.text_input(
                "NK-Vorauszahlung (mtl., €)",
                value=format_german_number(
                    p.get("nebenkosten_vorauszahlung_monthly", 0)
                ),
            )
            new_kaution_str = st.text_input(
                "Kaution (€)",
                value=format_german_number(p.get("kaution_eur", 0)),
            )

        st.divider()
        save_col, cancel_col = st.columns(2)
        with save_col:
            save_clicked = st.form_submit_button("💾 Speichern", type="primary")
        with cancel_col:
            cancel_clicked = st.form_submit_button("Abbrechen")

    if save_clicked:
        errors = []
        if not new_address.strip():
            errors.append("Adresse darf nicht leer sein.")

        def parse_or_error(text, label):
            v = parse_german_number(text)
            if v is None:
                errors.append(f"{label} ist keine gültige Zahl.")
            return v

        wohnflaeche = parse_or_error(new_wohnflaeche_str, "Wohnfläche")
        purchase_price = parse_or_error(new_purchase_price_str, "Kaufpreis")
        kaufnebenkosten = parse_or_error(new_kaufnebenkosten_str, "Kaufnebenkosten")
        kaltmiete = parse_or_error(new_kaltmiete_str, "Kaltmiete")
        opex = parse_or_error(new_opex_str, "Bewirtschaftung")
        darlehen = parse_or_error(new_darlehen_str, "Darlehenssumme")
        zins = parse_or_error(new_zins_str, "Zinssatz")
        tilgung = parse_or_error(new_tilgung_str, "Tilgung")
        nk_vorauszahlung = parse_or_error(new_nk_str, "NK-Vorauszahlung")
        kaution = parse_or_error(new_kaution_str, "Kaution")
        if new_restschuld_str.strip():
            restschuld_override = parse_or_error(new_restschuld_str, "Restschuld laut Bank")
        else:
            restschuld_override = None

        if errors:
            for e in errors:
                st.error(e)
        else:
            existing_prop = get_property(property_id) or {}
            save_user_property(
                property_id,
                {
                    **existing_prop,
                    "property_id": property_id,
                    "address": new_address.strip(),
                    "purchase_price": int(round(purchase_price)),
                    "kaufnebenkosten_total": int(round(kaufnebenkosten)),
                    "purchase_date": new_purchase_date.strftime("%Y-%m-%d"),
                    "kaltmiete_monthly": int(round(kaltmiete)),
                    "opex_monthly_total": int(round(opex)),
                    "wohnflaeche_sqm": int(round(wohnflaeche)),
                    "mieter_name": new_mieter.strip() or None,
                    "mietbeginn_date": new_mietbeginn.strftime("%Y-%m-%d"),
                    "mietart": new_mietart,
                    "letzte_mieterhoehung_date": new_letzte_erhoehung.strftime("%Y-%m-%d"),
                    "nebenkosten_vorauszahlung_monthly": int(round(nk_vorauszahlung)),
                    "kaution_eur": int(round(kaution)),
                },
            )
            if new_bank.strip() and darlehen and darlehen > 0:
                existing_loan = get_loan(property_id) or {}
                loan_dict = {
                    **existing_loan,
                    "loan_id": existing_loan.get("loan_id", f"USER-{property_id}"),
                    "property_id": property_id,
                    "bank": new_bank.strip(),
                    "darlehenssumme": int(round(darlehen)),
                    "zinssatz_pct": float(zins),
                    "zinsbindung_end": new_zinsbindung.strftime("%Y-%m-%d"),
                    "tilgung_anfang_pct": float(tilgung),
                }
                if restschuld_override is not None and restschuld_override > 0:
                    loan_dict["restschuld_current"] = int(round(restschuld_override))
                else:
                    loan_dict.pop("restschuld_current", None)
                save_user_loan(property_id, loan_dict)
            st.session_state[edit_mode_key] = False
            st.rerun()

    if cancel_clicked:
        st.session_state[edit_mode_key] = False
        st.rerun()

else:
    if st.button("✏️ Bearbeiten"):
        st.session_state[edit_mode_key] = True
        st.rerun()

    total_acq = p["purchase_price"] + p["kaufnebenkosten_total"]
    rent_per_sqm = p["kaltmiete_monthly"] / p["wohnflaeche_sqm"]
    price_per_sqm = p["purchase_price"] / p["wohnflaeche_sqm"]

    heizungsart = p.get("heizungsart")
    install_year = p.get("heizung_installation_year")
    if heizungsart and install_year:
        heizung_str = f"{heizungsart} (Einbau {install_year})"
    elif heizungsart:
        heizung_str = heizungsart
    else:
        heizung_str = None

    ea_date_str = p.get("energieausweis_date")
    if ea_date_str:
        ea_issue = date.fromisoformat(ea_date_str)
        ea_expiry_iso = f"{ea_issue.year + 10}-{ea_issue.month:02d}-{ea_issue.day:02d}"
        ea_expiry_de = german_date(ea_expiry_iso)
    else:
        ea_expiry_de = None

    mietspiegel = p.get("mietspiegel_eur_per_sqm")
    baujahr = p.get("baujahr")

    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown("##### Stammdaten")
        stat("Adresse", p["address"])
        stat("Wohnfläche", f"{p['wohnflaeche_sqm']} m²")
        if baujahr:
            stat("Baujahr", baujahr)
        if heizung_str:
            stat("Heizung", heizung_str)
        if ea_expiry_de:
            stat("Energieausweis gültig bis", ea_expiry_de)
        stat("Kaufdatum", german_date(p["purchase_date"]))
        stat("€/m² (Kaufpreis)", euro(price_per_sqm, 2))
        stat("€/m² (Kaltmiete)", euro(rent_per_sqm, 2))

    with d2:
        st.markdown("##### Wirtschaft")
        stat("Kaufpreis", euro(p["purchase_price"]))
        stat("Kaufnebenkosten", euro(p["kaufnebenkosten_total"]))
        stat("Gesamterwerbskosten", euro(total_acq))
        stat("Kaltmiete (mtl.)", euro(p["kaltmiete_monthly"]))
        if mietspiegel:
            stat("Mietspiegel", f"{euro(mietspiegel, 2)} /m²")
        stat("Bewirtschaftung (mtl.)", euro(p["opex_monthly_total"]))

        annual_rent = p["kaltmiete_monthly"] * 12
        annual_opex = p["opex_monthly_total"] * 12
        stat(
            "Bruttomietrendite",
            percent(gross_yield(annual_rent, p["purchase_price"])),
        )
        stat(
            "Nettomietrendite",
            percent(net_yield(annual_rent, annual_opex, total_acq)),
        )

    with d3:
        st.markdown("##### Finanzierung")
        annual_rent = p["kaltmiete_monthly"] * 12
        annual_opex = p["opex_monthly_total"] * 12
        if loan:
            eigenkapital = total_acq - loan["darlehenssumme"]
            annual_debt = (
                loan["darlehenssumme"]
                * (loan["zinssatz_pct"] + loan["tilgung_anfang_pct"])
                / 100
            )
            annual_tilgung = loan["darlehenssumme"] * loan["tilgung_anfang_pct"] / 100
            current_rest = current_restschuld(loan, p["purchase_date"])

            stat("Bank", loan["bank"])
            stat("Darlehenssumme", euro(loan["darlehenssumme"]))
            stat("Zinssatz", percent(loan["zinssatz_pct"]))
            stat("Tilgung (anfänglich)", percent(loan["tilgung_anfang_pct"]))
            stat("Zinsbindung bis", german_date(loan["zinsbindung_end"]))
            restschuld_label = (
                "Restschuld (Projektion)"
                if restschuld_is_projection(loan)
                else "Restschuld (laut Bank)"
            )
            stat(restschuld_label, euro(current_rest))
            stat("Eigenkapital eingesetzt", euro(eigenkapital))
            stat(
                "Cash-on-Cash",
                percent(
                    cash_on_cash(annual_rent, annual_opex, annual_debt, eigenkapital)
                ),
            )
            stat(
                "Gesamtrendite",
                percent(
                    true_total_return(
                        annual_rent,
                        annual_opex,
                        annual_debt,
                        annual_tilgung,
                        p["kaufnebenkosten_total"],
                        eigenkapital,
                    )
                ),
            )
            st.caption(
                "Gesamtrendite: ohne Wertsteigerung, KNK über 10 Jahre amortisiert, Tilgung als Eigenkapitalaufbau."
            )
        else:
            st.info(
                "Keine Finanzierungsdaten hinterlegt. Klicke oben auf Bearbeiten, um sie zu erfassen."
            )
            stat(
                "Cash-on-Cash (ohne Finanzierung)",
                percent(cash_on_cash(annual_rent, annual_opex, 0, total_acq)),
            )
            stat(
                "Gesamtrendite (ohne Finanzierung)",
                percent(
                    true_total_return(
                        annual_rent,
                        annual_opex,
                        0,
                        0,
                        p["kaufnebenkosten_total"],
                        total_acq,
                    )
                ),
            )

    st.divider()
    st.markdown("##### Mietvertrag")
    mv1, mv2, mv3 = st.columns(3)
    with mv1:
        stat("Mieter", p.get("mieter_name"))
        stat(
            "Mietbeginn",
            german_date(p["mietbeginn_date"]) if p.get("mietbeginn_date") else None,
        )
    with mv2:
        stat("Mietart", p.get("mietart"))
        stat(
            "Letzte Mieterhöhung",
            german_date(p["letzte_mieterhoehung_date"])
            if p.get("letzte_mieterhoehung_date")
            else None,
        )
    with mv3:
        nk = p.get("nebenkosten_vorauszahlung_monthly")
        stat("NK-Vorauszahlung (mtl.)", euro(nk) if nk else None)
        kaution = p.get("kaution_eur")
        stat("Kaution", euro(kaution) if kaution else None)

    st.divider()
    st.subheader("Hinweise & Termine")
    alerts = all_alerts(p, loan)
    if not alerts:
        st.success("Keine offenen Hinweise zu dieser Wohnung.")
    else:
        for alert in alerts:
            sev = alert["severity"]
            if sev == "urgent":
                st.error(f"**{alert['title']}**\n\n{alert['detail']}")
            elif sev == "warning":
                st.warning(f"**{alert['title']}**\n\n{alert['detail']}")
            else:
                st.info(f"**{alert['title']}**\n\n{alert['detail']}")

    if loan:
        st.divider()
        st.subheader("Cashflow-Sensitivität")
        st.caption(
            "Wie verändert sich der monatliche Cashflow nach Anschlussfinanzierung? "
            "Zinssatz und Refi-Datum frei wählbar — die projizierte Restschuld wird "
            "anhand des Tilgungsplans automatisch angepasst."
        )

        sens_purchase_d = date.fromisoformat(p["purchase_date"])
        sens_zb_d = date.fromisoformat(loan["zinsbindung_end"])
        sens_min_date = max(date.today(), sens_purchase_d)
        sens_max_date = date(
            sens_purchase_d.year + 35,
            sens_purchase_d.month,
            sens_purchase_d.day,
        )
        sens_default_date = sens_zb_d if sens_min_date <= sens_zb_d <= sens_max_date else sens_min_date

        ctrl_left, ctrl_right = st.columns(2)
        with ctrl_left:
            refi_date = st.date_input(
                "Refinanzierung am",
                value=sens_default_date,
                min_value=sens_min_date,
                max_value=sens_max_date,
                key=f"refi_date_{property_id}",
            )
        with ctrl_right:
            new_rate = st.slider(
                "Anschluss-Zinssatz",
                min_value=0.0,
                max_value=8.0,
                value=3.8,
                step=0.1,
                format="%.2f %%",
                key=f"refi_rate_{property_id}",
            )

        sens_schedule = amortisation_schedule(
            loan["darlehenssumme"],
            loan["zinssatz_pct"],
            loan["tilgung_anfang_pct"],
            years=40,
        )
        years_to_refi = (refi_date - sens_purchase_d).days / 365.25
        year_idx = max(1, int(round(years_to_refi)))
        if year_idx <= len(sens_schedule):
            projected_rest = sens_schedule[year_idx - 1]["closing_balance"]
        else:
            projected_rest = 0

        cf_at_slider = cashflow_at_new_rate(
            p["kaltmiete_monthly"],
            p["opex_monthly_total"],
            projected_rest,
            new_rate,
            loan["tilgung_anfang_pct"],
        )
        breakeven = breakeven_rate_pct(
            p["kaltmiete_monthly"],
            p["opex_monthly_total"],
            projected_rest,
            loan["tilgung_anfang_pct"],
        )

        kpi_l, kpi_r = st.columns(2)
        kpi_l.metric(
            "Projizierte Restschuld bei Refi", euro(projected_rest)
        )
        kpi_r.metric(
            f"Monatl. Cashflow @ {percent(new_rate)}",
            euro(cf_at_slider),
            delta=None,
        )

        if breakeven is not None:
            if breakeven <= 0:
                st.error(
                    f"**Break-Even-Zinssatz: {percent(breakeven)}** — selbst bei einem Zinssatz "
                    f"von 0 % ist der Cashflow negativ; operative Kosten und Tilgung "
                    f"zehren die Miete auf."
                )
            elif breakeven < loan["zinssatz_pct"]:
                st.warning(
                    f"**Break-Even-Zinssatz: {percent(breakeven)}** — bereits unter dem aktuellen "
                    f"Zinssatz; das Objekt arbeitet schon heute mit negativem Cashflow."
                )
            else:
                st.info(
                    f"**Break-Even-Zinssatz: {percent(breakeven)}** — oberhalb dieses Werts "
                    f"wird der monatliche Cashflow negativ."
                )

    st.divider()
    with st.expander("📊 Analytik & Diagramme", expanded=False):
        _render_analytics(p, loan, total_acq)
