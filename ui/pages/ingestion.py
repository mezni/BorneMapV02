import streamlit as st
import requests
import time
from datetime import datetime
from typing import Optional, Dict, Any

API_BASE_URL = "http://localhost:8000/api/v1"


def run_ingestion_pipeline(trigger_type: str = "MANUAL") -> Optional[Dict[str, Any]]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/ingestion/run",
            json={"trigger_type": trigger_type},
            timeout=10,
        )
        if response.status_code == 202:
            return response.json()
        else:
            st.error(f"Failed to start pipeline: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure the FastAPI server is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Error starting pipeline: {str(e)}")
        return None


def get_pipeline_run(run_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(f"{API_BASE_URL}/ingestion/runs/{run_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            st.error(f"Failed to get pipeline run: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching pipeline run: {str(e)}")
        return None


def get_pipeline_runs_history(limit: int = 5) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{API_BASE_URL}/ingestion/runs", params={"limit": limit, "skip": 0}, timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get pipeline runs: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching pipeline runs history: {str(e)}")
        return None


def format_datetime(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str


def render_status_badge(status: str) -> str:
    colors = {
        "PENDING": "🟡",
        "COMPLETED": "🟢",
        "FAILED": "🔴",
    }
    return f"{colors.get(status, '⚪')} {status}"


def render_pipeline_run_card(run: Dict[str, Any], is_current: bool = False):
    if is_current:
        st.markdown("### 🔄 Current Run")
        st.info("Pipeline is running...")
    else:
        st.markdown(f"### {render_status_badge(run.get('status', 'UNKNOWN'))} Run #{run.get('id', '')[:8]}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Trigger", run.get("trigger_type", "—"))
        st.metric("Documents Discovered", run.get("documents_discovered", 0))
    with col2:
        st.metric("Documents Processed", run.get("documents_processed", 0))
        st.metric("Documents Skipped", run.get("documents_skipped", 0))
    with col3:
        st.metric("Chunks Created", run.get("chunks_created", 0))
        st.metric("Cost (USD)", f"${run.get('estimated_cost_usd', 0):.4f}")

    st.markdown(f"**Embedding Model:** {run.get('embedding_model', '—')}")
    st.markdown(f"**Total Tokens:** {run.get('total_embedding_tokens', 0):,}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Started:** {format_datetime(run.get('started_at'))}")
    with col2:
        st.markdown(f"**Completed:** {format_datetime(run.get('completed_at'))}")

    if run.get("error_message"):
        st.error(f"Error: {run['error_message']}")

    if run.get("metadata"):
        with st.expander("Metadata"):
            st.json(run["metadata"])

    st.markdown("---")


def render_ingestion_dashboard():
    st.title("📊 Ingestion Pipeline Dashboard")
    st.markdown("Monitor and trigger document ingestion pipelines.")

    if "current_run_id" not in st.session_state:
        st.session_state.current_run_id = None
    if "polling" not in st.session_state:
        st.session_state.polling = False

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Trigger New Ingestion")
        trigger_type = st.selectbox(
            "Trigger Type",
            ["MANUAL", "SCHEDULED", "WEBHOOK"],
            index=0,
        )

        if st.button("🚀 Run Ingestion Pipeline", type="primary", use_container_width=True):
            with st.spinner("Starting pipeline..."):
                result = run_ingestion_pipeline(trigger_type)
                if result:
                    st.session_state.current_run_id = result["id"]
                    st.session_state.polling = True
                    st.success(f"Pipeline started! Run ID: {result['id']}")
                    st.rerun()

    with col2:
        st.subheader("Quick Stats")
        history = get_pipeline_runs_history(limit=1)
        if history and history.get("runs"):
            latest = history["runs"][0]
            st.metric("Last Run Status", render_status_badge(latest.get("status", "UNKNOWN")))
            st.metric("Last Run Time", format_datetime(latest.get("started_at")))
        else:
            st.info("No runs yet")

    st.markdown("---")

    if st.session_state.current_run_id and st.session_state.polling:
        st.subheader("Current Run Progress")
        run = get_pipeline_run(st.session_state.current_run_id)
        if run:
            render_pipeline_run_card(run, is_current=True)

            if run.get("status") in ["COMPLETED", "FAILED"]:
                st.session_state.polling = False
                st.success(f"Pipeline {run['status'].lower()}!" if run["status"] == "COMPLETED" else "Pipeline failed!")
                time.sleep(1)
                st.rerun()
            else:
                with st.empty():
                    st.info("Pipeline running... Auto-refreshing in 3 seconds")
                    time.sleep(3)
                    st.rerun()
        else:
            st.warning("Run not found")
            st.session_state.polling = False

    st.markdown("---")
    st.subheader("📜 Recent Runs (Last 5)")

    history = get_pipeline_runs_history(limit=5)
    if history and history.get("runs"):
        for run in history["runs"]:
            render_pipeline_run_card(run)
    else:
        st.info("No pipeline runs yet. Click 'Run Ingestion Pipeline' to start one.")

    if st.button("🔄 Refresh History"):
        st.rerun()