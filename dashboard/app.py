from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("SENTINEL_API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Sentinel-Ops", layout="wide")
st.title("Sentinel-Ops Dashboard")


def _get_json(path: str):
    response = requests.get(f"{API_BASE}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


cases = _get_json("/cases")
if not cases:
    st.info("No cases found. Create one using API first.")
    st.stop()

case_map = {f"{c['title']} ({c['case_id']})": c for c in cases}
selected_label = st.selectbox("Select Case", list(case_map.keys()))
selected_case = case_map[selected_label]

submissions = _get_json(f"/cases/{selected_case['case_id']}/submissions")
df = pd.DataFrame(submissions)

col1, col2, col3, col4 = st.columns(4)
deadline = datetime.fromisoformat(selected_case["deadline_time"])
remaining = deadline - datetime.now(timezone.utc)
col1.metric("Time Remaining", str(remaining).split(".")[0])
col2.metric("Submissions", len(df))
col3.metric("Pass Rate", f"{(100 * (df['latest_event_type'] != 'REJECTED').mean()):.1f}%" if not df.empty else "0%")
col4.metric("Pending Review", int((df["latest_event_type"].isin(["CONFLICTED", "VALIDATED", "INGESTED"]).sum())) if not df.empty else 0)

st.subheader("Review Queue")
if df.empty:
    st.write("No submissions yet.")
else:
    queue = df.sort_values(["is_conflicted", "confidence_score"], ascending=[False, False])
    st.dataframe(queue[["submission_id", "chain", "address", "scam_type", "confidence_score", "latest_event_type", "triage_priority"]], use_container_width=True)
