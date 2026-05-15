from datetime import date

import streamlit as st

from utils import (
    euro,
    format_german_number,
    german_date,
    get_loan,
    get_property,
    parse_german_number,
    percent,
    save_user_loan,
    save_user_property,
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
            new_restschuld_str = st.text_input(
                "Restschuld aktuell (€)",
                value=format_german_number(loan_default.get("restschuld_current", 0)),
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
        restschuld = parse_or_error(new_restschuld_str, "Restschuld")

        if errors:
            for e in errors:
                st.error(e)
        else:
            save_user_property(
                property_id,
                {
                    "property_id": property_id,
                    "address": new_address.strip(),
                    "purchase_price": int(round(purchase_price)),
                    "kaufnebenkosten_total": int(round(kaufnebenkosten)),
                    "purchase_date": new_purchase_date.strftime("%Y-%m-%d"),
                    "kaltmiete_monthly": int(round(kaltmiete)),
                    "opex_monthly_total": int(round(opex)),
                    "wohnflaeche_sqm": int(round(wohnflaeche)),
                },
            )
            if new_bank.strip() and darlehen and darlehen > 0:
                save_user_loan(
                    property_id,
                    {
                        "loan_id": f"USER-{property_id}",
                        "property_id": property_id,
                        "bank": new_bank.strip(),
                        "darlehenssumme": int(round(darlehen)),
                        "zinssatz_pct": float(zins),
                        "zinsbindung_end": new_zinsbindung.strftime("%Y-%m-%d"),
                        "tilgung_anfang_pct": float(tilgung),
                        "restschuld_current": int(round(restschuld)),
                    },
                )
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
            st.info("Keine Finanzierungsdaten hinterlegt. Klicke oben auf Bearbeiten, um sie zu erfassen.")
