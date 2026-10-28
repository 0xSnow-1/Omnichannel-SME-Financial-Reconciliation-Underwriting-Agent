import streamlit as st
import httpx

API_URL = "http://localhost:8000"

st.title("SME Underwriting Copilot — Review")

resp = httpx.get(f"{API_URL}/applications", timeout=10)
if resp.status_code == 200:
    st.write("Connected to API")
else:
    st.error("API unavailable")