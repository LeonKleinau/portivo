import streamlit as st

from seed_portfolio import LOANS_BY_PROPERTY_ID, PROPERTIES_BY_ID


def euro(amount, decimals=0):
    s = f"{amount:,.{decimals}f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value, decimals=2):
    return f"{value:.{decimals}f} %".replace(".", ",")


def german_date(iso):
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def format_german_number(value, decimals=0):
    if decimals == 0:
        return f"{int(round(value)):,}".replace(",", ".")
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_german_number(text):
    if text is None:
        return None
    s = str(text).strip()
    for ch in "€%$ ":
        s = s.replace(ch, "")
    if not s:
        return 0
    has_comma = "," in s
    if has_comma:
        s = s.replace(".", "").replace(",", ".")
    else:
        dot_count = s.count(".")
        if dot_count == 1:
            after = s.split(".")[1]
            if len(after) in (1, 2):
                pass
            else:
                s = s.replace(".", "")
        elif dot_count > 1:
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def get_property(property_id):
    user_props = st.session_state.get("user_properties", {})
    if property_id in user_props:
        return user_props[property_id]
    return PROPERTIES_BY_ID.get(property_id)


def save_user_property(property_id, prop_dict):
    user_props = st.session_state.get("user_properties", {})
    user_props[property_id] = prop_dict
    st.session_state["user_properties"] = user_props


def get_loan(property_id):
    user_loans = st.session_state.get("user_loans", {})
    if property_id in user_loans:
        return user_loans[property_id]
    return LOANS_BY_PROPERTY_ID.get(property_id)


def save_user_loan(property_id, loan_dict):
    user_loans = st.session_state.get("user_loans", {})
    user_loans[property_id] = loan_dict
    st.session_state["user_loans"] = user_loans
