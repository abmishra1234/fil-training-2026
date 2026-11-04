"""FR-18 Streamlit UI (three pages only): Chat, Sources/trace panel, Review queue.  >>> YOU BUILD THIS (Day 6) <<<
Run: streamlit run ui/app.py
"""
import os

import httpx
import streamlit as st

API = os.getenv("FUNDLENS_API_URL", "http://localhost:8000")
st.set_page_config(page_title="FundLens", layout="wide")
page = st.sidebar.radio("Page", ["Chat", "Draft a reply", "Review queue"])
st.sidebar.caption("SYNTHETIC training data only")

try:
    st.sidebar.json(httpx.get(f"{API}/health", timeout=5).json())
except Exception:
    st.sidebar.error("API not reachable - start it with `make api`")

st.title(page)
st.info("TODO: build this page. Show the answer, the route, tools called, cited chunks with as-of dates, and any freshness warning.")
