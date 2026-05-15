import streamlit as st

from seed_portfolio import PORTFOLIO

st.set_page_config(
    page_title="Portivo",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 1.1rem 1.25rem;
        border-radius: 12px;
        border: 1px solid #21262d;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.85rem;
        font-weight: 700;
        color: #e6edf3;
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricLabel"] {
        color: #8b949e;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
    }
    div[data-testid="stContainer"] > div[style*="border"] {
        border-radius: 12px !important;
        border-color: #21262d !important;
        background-color: #0f141a !important;
    }
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
    }
    .stButton > button[kind="tertiary"] {
        text-align: left;
        font-size: 1.1rem;
        font-weight: 600;
        color: #e6edf3;
        padding: 0.4rem 0.6rem;
    }
    .stButton > button[kind="tertiary"]:hover {
        color: #00d09c;
        background-color: rgba(0, 208, 156, 0.08);
    }
    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #21262d;
        background-color: #11161c;
    }
    h1 {
        letter-spacing: -0.02em;
        font-weight: 700;
    }
    h2, h3 {
        letter-spacing: -0.015em;
        font-weight: 600;
    }
    [data-testid="stSidebarNav"] {
        background-color: #0d1117;
    }
    hr {
        border-color: #21262d;
        margin: 1.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
