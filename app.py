import streamlit as st

from seed_portfolio import PORTFOLIO

st.set_page_config(page_title="Portivo", layout="wide")

pages = [st.Page("views/portfolio.py", title="Portfolio", default=True)]

selected_id = st.session_state.get("selected_property_id") or st.query_params.get(
    "property_id"
)
if selected_id:
    address = next(
        (p["address"] for p in PORTFOLIO if p["property_id"] == selected_id),
        "Wohnung",
    )
    pages.append(st.Page("views/wohnung.py", title=f"Wohnung — {address}"))
else:
    pages.append(st.Page("views/wohnung.py", title="Wohnung"))

nav = st.navigation(pages)
nav.run()
