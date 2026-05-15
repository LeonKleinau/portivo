import streamlit as st

st.title("Hello Portivo")
st.write("Built by Leon Kleinau")

col1, col2, col3 = st.columns(3)
col1.metric("Portfolio Value", "€1,250,000", "+3.2%")
col2.metric("Monthly Cashflow", "€2,840", "+€120")
col3.metric("Weighted Yield", "4.1%", "-0.2%")
