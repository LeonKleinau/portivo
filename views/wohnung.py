from datetime import date

import streamlit as st

from utils import (
    euro,
    german_date,
    get_loan,
    get_property,
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
    with st.form(key=f"edit_form_{property_id}"):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**Stammdaten**")
            new_address = st.text_input("Adresse", value=p["address"])
            new_wohnflaeche = st.number_input(
                "Wohnfläche (m²)",
                min_value=1,
                value=int(p["wohnflaeche_sqm"]),
            )
            new_purchase_date = st.date_input(
                "Kaufdatum", value=date.fromisoformat(p["purchase_date"])
            )

        with c2:
            st.markdown("**Wirtschaft**")
            new_purchase_price = st.number_input(
                "Kaufpreis (€)",
                min_value=0,
                value=int(p["purchase_price"]),
                step=1000,
            )
            new_kaufnebenkosten = st.number_input(
                "Kaufnebenkosten (€)",
                min_value=0,
                value=int(p["kaufnebenkosten_total"]),
                step=500,
            )
            new_kaltmiete = st.number_input(
                "Kaltmiete (mtl., €)",
                min_value=0,
                value=int(p["kaltmiete_monthly"]),
                step=10,
            )
            new_opex = st.number_input(
                "Bewirtschaftung (mtl., €)",
                min_value=0,
                value=int(p["opex_monthly_total"]),
                step=10,
            )

        with c3:
            st.markdown("**Finanzierung**")
            loan_default = loan or {}
            new_bank = st.text_input("Bank", value=loan_default.get("bank", ""))
            new_darlehen = st.number_input(
                "Darlehenssumme (€)",
                min_value=0,
                value=int(loan_default.get("darlehenssumme", 0)),
                step=1000,
            )
            new_zins = st.number_input(
                "Zinssatz (%)",
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                value=float(loan_default.get("zinssatz_pct", 2.0)),
                format="%.2f",
            )
            zb_default = (
                date.fromisoformat(loan_default["zinsbindung_end"])
                if loan_default.get("zinsbindung_end")
                else date(date.today().year + 10, 1, 1)
            )
            new_zinsbindung = st.date_input("Zinsbindung bis", value=zb_default)
            new_tilgung = st.number_input(
                "Tilgung (%, anfänglich)",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                value=float(loan_default.get("tilgung_anfang_pct", 2.0)),
                format="%.2f",
            )
            new_restschuld = st.number_input(
                "Restschuld aktuell (€)",
                min_value=0,
                value=int(loan_default.get("restschuld_current", 0)),
                step=1000,
            )

        st.divider()
        save_col, cancel_col = st.columns(2)
        with save_col:
            save_clicked = st.form_submit_button("💾 Speichern", type="primary")
        with cancel_col:
            cancel_clicked = st.form_submit_button("Abbrechen")

    if save_clicked:
        if not new_address.strip():
            st.error("Adresse darf nicht leer sein.")
        else:
            save_user_property(
                property_id,
                {
                    "property_id": property_id,
                    "address": new_address.strip(),
                    "purchase_price": new_purchase_price,
                    "kaufnebenkosten_total": new_kaufnebenkosten,
                    "purchase_date": new_purchase_date.strftime("%Y-%m-%d"),
                    "kaltmiete_monthly": new_kaltmiete,
                    "opex_monthly_total": new_opex,
                    "wohnflaeche_sqm": new_wohnflaeche,
                },
            )
            if new_bank.strip() and new_darlehen > 0:
                save_user_loan(
                    property_id,
                    {
                        "loan_id": f"USER-{property_id}",
                        "property_id": property_id,
                        "bank": new_bank.strip(),
                        "darlehenssumme": new_darlehen,
                        "zinssatz_pct": new_zins,
                        "zinsbindung_end": new_zinsbindung.strftime("%Y-%m-%d"),
                        "tilgung_anfang_pct": new_tilgung,
                        "restschuld_current": new_restschuld,
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
