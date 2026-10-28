"""
SME Underwriting Copilot — Underwriter Review UI
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SME Underwriting Copilot",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 SME Underwriting Copilot — Underwriter Review")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
try:
    health = httpx.get(f"{API_URL}/health", timeout=5)
    if health.status_code == 200:
        st.success("✅ API connected")
    else:
        st.error(f"❌ API returned {health.status_code}")
        st.stop()
except Exception as exc:
    st.error(f"❌ Cannot reach API at {API_URL}: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — submit new application
# ---------------------------------------------------------------------------
st.sidebar.header("Submit New Application")
with st.sidebar.form("new_app"):
    merchant_name = st.text_input("Merchant name", placeholder="Aling Rosa Sari-Sari Store")
    loan_amount = st.number_input("Loan amount (₱)", min_value=1000.0, value=100000.0, step=1000.0)
    uploaded_files = st.file_uploader(
        "Upload documents (PDF, CSV, XLSX, PNG, JPG)",
        accept_multiple_files=True,
        type=["pdf", "csv", "xlsx", "png", "jpg", "jpeg"],
    )
    submitted = st.form_submit_button("Submit")

if submitted:
    if not merchant_name.strip():
        st.sidebar.error("Merchant name is required.")
    else:
        form_data = {"merchant_name": merchant_name, "loan_amount": str(loan_amount)}
        files = []
        for uf in uploaded_files or []:
            files.append(("files", (uf.name, uf.read(), uf.type or "application/octet-stream")))
        try:
            resp = httpx.post(
                f"{API_URL}/applications",
                data=form_data,
                files=files if files else None,
                timeout=30,
            )
            if resp.status_code == 201:
                data = resp.json()
                st.sidebar.success(f"Created application `{data['id']}`")
                st.session_state["selected_app_id"] = data["id"]
            else:
                st.sidebar.error(f"Error {resp.status_code}: {resp.text}")
        except Exception as exc:
            st.sidebar.error(f"Request failed: {exc}")

# ---------------------------------------------------------------------------
# Application ID input
# ---------------------------------------------------------------------------
st.header("Review Application")
app_id_input = st.text_input(
    "Application ID",
    value=st.session_state.get("selected_app_id", ""),
    placeholder="Paste application UUID here",
)

if not app_id_input.strip():
    st.info("Enter an application ID above to review it.")
    st.stop()

app_id = app_id_input.strip()

# ---------------------------------------------------------------------------
# Fetch status & evidence
# ---------------------------------------------------------------------------
col_refresh, _ = st.columns([1, 5])
with col_refresh:
    refresh = st.button("🔄 Refresh")

try:
    status_resp = httpx.get(f"{API_URL}/applications/{app_id}/status", timeout=10)
    if status_resp.status_code == 404:
        st.error("Application not found.")
        st.stop()
    status_data = status_resp.json()
except Exception as exc:
    st.error(f"Failed to fetch status: {exc}")
    st.stop()

try:
    evid_resp = httpx.get(f"{API_URL}/applications/{app_id}/evidence", timeout=10)
    evid_data = evid_resp.json() if evid_resp.status_code == 200 else {}
except Exception:
    evid_data = {}

# ---------------------------------------------------------------------------
# Status banner
# ---------------------------------------------------------------------------
status = status_data.get("status", "unknown")
processing = status_data.get("processing_status", "unknown")
STATUS_COLORS = {
    "approved": "🟢",
    "denied": "🔴",
    "countered": "🟡",
    "awaiting_review": "🟠",
    "processing": "🔵",
    "pending": "⚪",
    "failed": "🔴",
}
icon = STATUS_COLORS.get(status, "⚪")
st.subheader(f"Status: {icon} `{status}`  |  Processing: `{processing}`")

# ---------------------------------------------------------------------------
# KYC result
# ---------------------------------------------------------------------------
kyc = status_data.get("kyc_result")
if kyc:
    passed = kyc.get("passed", False)
    reason = kyc.get("reason", "")
    if passed:
        st.success(f"KYC: ✅ {reason}")
    else:
        st.error(f"KYC: ❌ {reason}")

# ---------------------------------------------------------------------------
# Confidence & fraud flags
# ---------------------------------------------------------------------------
confidence = status_data.get("confidence", 1.0)
fraud_flags = evid_data.get("fraud_flags", [])
col_conf, col_flags = st.columns(2)
with col_conf:
    color = "normal" if confidence >= 0.7 else "inverse"
    st.metric("Confidence", f"{confidence:.0%}")
with col_flags:
    if fraud_flags:
        st.warning(f"⚠️ Fraud flags: {', '.join(fraud_flags)}")
    else:
        st.success("No fraud flags")

# ---------------------------------------------------------------------------
# Validation results
# ---------------------------------------------------------------------------
validation_results = status_data.get("validation_results", [])
if validation_results:
    st.subheader("Validation Results")
    for vr in validation_results:
        for check in vr.get("checks", []):
            passed = check.get("passed", False)
            name = check.get("check_name", "")
            details = check.get("details", "")
            if passed:
                st.success(f"✅ {name}: {details}")
            else:
                st.error(f"❌ {name}: {details}")

# ---------------------------------------------------------------------------
# Extracted documents
# ---------------------------------------------------------------------------
documents = evid_data.get("documents", [])
if documents:
    st.subheader("Extracted Documents")
    for doc in documents:
        doc_type = doc.get("document_type", "unknown")
        conf = doc.get("confidence", 1.0)
        status_doc = doc.get("extraction_status", "")
        with st.expander(f"📄 {doc_type} — confidence {conf:.0%} [{status_doc}]"):
            txns = doc.get("transactions", [])
            if txns:
                st.write(f"**Transactions ({len(txns)})**")
                st.dataframe(
                    [
                        {
                            "Date": t.get("date"),
                            "Description": t.get("description"),
                            "Amount": t.get("amount"),
                            "Balance": t.get("balance"),
                        }
                        for t in txns
                    ]
                )
            summary = doc.get("summary_fields", {})
            if summary:
                st.write("**Summary fields**")
                st.json(summary)
else:
    st.info("No extracted documents yet.")

# ---------------------------------------------------------------------------
# Review action (only if awaiting_review)
# ---------------------------------------------------------------------------
if status == "awaiting_review":
    st.divider()
    st.subheader("Underwriter Decision")
    with st.form("review_form"):
        decision = st.radio(
            "Decision",
            options=["approve", "deny", "counter"],
            horizontal=True,
        )
        notes = st.text_area("Notes (optional)")
        submit_review = st.form_submit_button("Submit Decision")

    if submit_review:
        payload: dict[str, str] = {"decision": decision}
        if notes.strip():
            payload["notes"] = notes.strip()
        try:
            rev_resp = httpx.post(
                f"{API_URL}/applications/{app_id}/review",
                json=payload,
                timeout=10,
            )
            if rev_resp.status_code == 200:
                new_status = rev_resp.json().get("status", "")
                st.success(f"Decision submitted! New status: **{new_status}**")
                st.rerun()
            else:
                st.error(f"Error {rev_resp.status_code}: {rev_resp.text}")
        except Exception as exc:
            st.error(f"Request failed: {exc}")
elif status in ("approved", "denied", "countered"):
    st.info(f"This application has already been decided: **{status}**.")
