import streamlit as st

st.set_page_config(
    page_title="Aether Wireless RAG Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("🔍 Aether Wireless RAG")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Ingestion Dashboard", "📄 Documents", "💬 Chat", "📈 FinOps", "⚙️ Settings"],
)

if page == "📊 Ingestion Dashboard":
    from ui.pages.ingestion import render_ingestion_dashboard
    render_ingestion_dashboard()
elif page == "📄 Documents":
    st.title("📄 Documents")
    st.info("Documents management coming soon...")
elif page == "💬 Chat":
    st.title("💬 Chat")
    st.info("Chat interface coming soon...")
elif page == "📈 FinOps":
    st.title("📈 FinOps")
    st.info("FinOps dashboard coming soon...")
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.info("Settings panel coming soon...")

st.sidebar.markdown("---")
st.sidebar.caption("Aether Wireless RAG Platform v0.1.4")