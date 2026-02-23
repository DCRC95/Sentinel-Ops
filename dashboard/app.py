from __future__ import annotations

import os
from datetime import UTC, datetime

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("SENTINEL_API_BASE", "http://localhost:8000")
MANUAL_REVIEW_TYPES = {"CONFLICTED", "ESCALATED", "REQUEST_MORE_EVIDENCE"}

st.set_page_config(page_title="Sentinel-Ops", layout="wide")
st.title("Sentinel-Ops Dashboard")


def _get_json(path: str):
    response = requests.get(f"{API_BASE}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def _post_json(path: str, payload: dict):
    response = requests.post(f"{API_BASE}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def _leaderboard_frame(submissions: list[dict], contractors: list[dict]) -> pd.DataFrame:
    if not submissions:
        return pd.DataFrame(
            columns=["contractor", "acceptance_rate", "conflict_rate", "review_burden"]
        )

    contractor_name = {c["contractor_id"]: c["handle"] for c in contractors}
    df = pd.DataFrame(submissions)
    grouped = []
    for contractor_id, group in df.groupby("contractor_id"):
        total = len(group)
        accepted = int((group["latest_event_type"] == "APPROVED").sum())
        rejected = int((group["latest_event_type"] == "REJECTED").sum())
        conflicted = int(group["is_conflicted"].sum())
        review_burden = int(group["latest_event_type"].isin(MANUAL_REVIEW_TYPES).sum())
        acceptance_den = accepted + rejected
        acceptance_rate = (accepted / acceptance_den) if acceptance_den > 0 else 0.0
        conflict_rate = conflicted / total if total > 0 else 0.0
        grouped.append(
            {
                "contractor": contractor_name.get(contractor_id, contractor_id[:8]),
                "acceptance_rate": round(acceptance_rate, 4),
                "conflict_rate": round(conflict_rate, 4),
                "review_burden": review_burden,
            }
        )
    out = pd.DataFrame(grouped)
    return out.sort_values(["review_burden", "acceptance_rate"], ascending=[False, False])


cases = _get_json("/cases")
if not cases:
    st.info("No cases found. Create one using API first.")
    st.stop()

case_map = {f"{c['title']} ({c['case_id']})": c for c in cases}
selected_label = st.selectbox("Select Case", list(case_map.keys()))
selected_case = case_map[selected_label]

contractors = _get_json("/contractors")
submissions = _get_json(f"/cases/{selected_case['case_id']}/submissions")
df = pd.DataFrame(submissions)

tab_overview, tab_queue, tab_leaderboard = st.tabs(
    ["Case Overview", "Review Queue", "Contractor Leaderboard"]
)

col1, col2, col3, col4 = tab_overview.columns(4)
deadline = datetime.fromisoformat(selected_case["deadline_time"])
remaining = deadline - datetime.now(UTC)
col1.metric("Time Remaining", str(remaining).split(".")[0])
col2.metric("Submissions", len(df))

elapsed_hours = max(
    1.0,
    (datetime.now(UTC) - datetime.fromisoformat(selected_case["start_time"])).total_seconds()
    / 3600,
)
throughput = len(df) / elapsed_hours
pass_rate = (
    f"{(100 * (df['latest_event_type'] != 'REJECTED').mean()):.1f}%" if not df.empty else "0%"
)
pending_review = (
    int(df["latest_event_type"].isin(["CONFLICTED", "VALIDATED", "INGESTED"]).sum())
    if not df.empty
    else 0
)
col3.metric("Pass Rate", pass_rate)
col4.metric("Pending Review", pending_review)
tab_overview.metric("Throughput / hour", f"{throughput:.2f}")

tab_queue.subheader("Review Queue")
if df.empty:
    tab_queue.write("No submissions yet.")
else:
    queue = df.sort_values(
        ["is_conflicted", "confidence_score", "triage_priority"],
        ascending=[False, False, False],
    )
    display_cols = [
        "submission_id",
        "chain",
        "address",
        "scam_type",
        "confidence_score",
        "latest_event_type",
        "triage_priority",
    ]
    tab_queue.dataframe(queue[display_cols], use_container_width=True)

    selected_submission_id = tab_queue.selectbox(
        "Submission Detail",
        options=queue["submission_id"].tolist(),
    )
    detail = _get_json(f"/submissions/{selected_submission_id}")
    tab_queue.json(detail["item"])
    with tab_queue.expander("Event Audit Trail", expanded=False):
        tab_queue.json(detail["events"])

    action_col1, action_col2, action_col3, action_col4 = tab_queue.columns(4)
    notes = tab_queue.text_input("Action Notes", value="")
    actor = tab_queue.text_input("Actor", value="manager")

    if action_col1.button("Approve", use_container_width=True):
        _post_json(
            f"/submissions/{selected_submission_id}/actions",
            {"action": "approve", "actor": actor, "notes": notes},
        )
        st.rerun()
    if action_col2.button("Reject", use_container_width=True):
        _post_json(
            f"/submissions/{selected_submission_id}/actions",
            {"action": "reject", "actor": actor, "notes": notes},
        )
        st.rerun()
    if action_col3.button("Escalate", use_container_width=True):
        _post_json(
            f"/submissions/{selected_submission_id}/actions",
            {"action": "escalate", "actor": actor, "notes": notes},
        )
        st.rerun()
    if action_col4.button("Request More Evidence", use_container_width=True):
        _post_json(
            f"/submissions/{selected_submission_id}/actions",
            {"action": "request_more_evidence", "actor": actor, "notes": notes},
        )
        st.rerun()

tab_leaderboard.subheader("Contractor Leaderboard")
leaderboard_df = _leaderboard_frame(submissions, contractors)
if leaderboard_df.empty:
    tab_leaderboard.write("No contractor data yet.")
else:
    tab_leaderboard.dataframe(leaderboard_df, use_container_width=True)

with st.expander("Export Approved Records"):
    export_format = st.radio("Format", options=["json", "csv"], horizontal=True)
    export_url = f"{API_BASE}/cases/{selected_case['case_id']}/export?format={export_format}"
    if st.button("Run Export"):
        response = requests.get(export_url, timeout=30)
        response.raise_for_status()
        if export_format == "json":
            st.json(response.json())
        else:
            st.download_button(
                label="Download CSV",
                data=response.text,
                file_name="sentinel_export.csv",
                mime="text/csv",
            )
