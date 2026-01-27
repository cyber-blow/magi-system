import streamlit as st
import importlib
import magi_core

# Force reload core logic to ensure latest changes are picked up
importlib.reload(magi_core)

# Import UI Modules
from ui import common, main_panel, history_panel, admin_panel

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="MAGI SYSTEM | NERV HQ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. State Initialization ---
if "page" not in st.session_state: st.session_state.page = "main"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "results" not in st.session_state: st.session_state.results = None

# --- 3. Style & Authentication ---
common.load_css()

# Session Persistence check
if not st.session_state.authenticated:
    token = st.query_params.get("sync_token")
    if token:
        user_info = magi_core.validate_session(token)
        if user_info:
            st.session_state.authenticated = True
            st.session_state.user = user_info

# Render Authentication (Stops execution if not authenticated)
common.render_auth()

# --- 4. Navigation & Main Execution ---
common.show_nav()

if st.session_state.page == "main":
    main_panel.render_main()
elif st.session_state.page == "history":
    history_panel.render_history()
elif st.session_state.page == "admin":
    admin_panel.render_admin()