import streamlit as st

from typing import Dict, Optional, List, Any

import requests

API_BASE_URL = "http://localhost:8000/api/v1"


def hybrid_search(query: str, top_k: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Call the /api/v1/search hybrid retrieval endpoint."""
    try:
        payload = {"query": query}
        if top_k:
            payload["top_k"] = top_k
        response = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Search failed: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure the FastAPI server is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Error during search: {str(e)}")
        return None


def render_result_card(result: Dict[str, Any], rank: int) -> None:
    score = result.get("score", 0.0)
    document_id = str(result.get("document_id", ""))
    chunk_id = str(result.get("chunk_id", ""))
    st.markdown(f"### #{rank} — Score: `{score:.4f}`")
    st.markdown(
        f"**Chunk:`{chunk_id[:8]}...` • Document:`{document_id[:8]}...` • "
        f"Index:`{result.get('chunk_index', 0)}`"
    )
    st.write(result.get("content", ""))
    if result.get("metadata"):
        with st.expander("Metadata"):
            st.json(result["metadata"])
    st.markdown("---")


def render_search_page():
    st.title("🔍 Hybrid Search")
    st.markdown("Search ingested documents with dense + sparse hybrid retrieval and re-ranking.")

    query = st.text_input("Search query", placeholder="e.g. 5G network resilience")
    top_k = st.slider("Top K results", min_value=1, max_value=20, value=5)

    if st.button("🔎 Search", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Enter a search query first.")
        else:
            with st.spinner("Searching..."):
                result = hybrid_search(query, top_k)
                if result:
                    st.session_state.search_results = result["results"]
                    st.session_state.search_query = result["query"]

    st.markdown("---")

    results: List[Dict[str, Any]] = st.session_state.get("search_results")
    if results is not None:
        st.subheader(f"Results for '{st.session_state.get('search_query', '')}' ({len(results)})")
        if not results:
            st.info("No results found.")
        for rank, result in enumerate(results, start=1):
            render_result_card(result, rank)

    if st.button("🔄 Clear Results"):
        st.session_state.pop("search_results", None)
        st.session_state.pop("search_query", None)
        st.rerun()