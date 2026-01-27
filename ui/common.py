import streamlit as st
import time
import os
import sys

# Ensure parent directory is in path to import magi_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import magi_core

def load_css():
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_auth():
    if not st.session_state.authenticated:
        st.markdown('<div class="auth-bg"></div>', unsafe_allow_html=True)
        
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown('<div class="auth-card">', unsafe_allow_html=True)
            st.markdown('<div class="auth-header">NERV TOP SECRET</div>', unsafe_allow_html=True)
            st.markdown('<p style="color: #FF8C00; text-align:center; letter-spacing:0.2em; margin-bottom:30px;">SYSTEM MAGI: SYNAPTIC LINK INITIALIZATION</p>', unsafe_allow_html=True)
            
            user_id = st.text_input("ID / CODE NAME", key="login_user")
            password = st.text_input("PASSWORD / SYNC KEY", type="password", key="login_pass")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("INITIATE SYNCHRONIZATION", use_container_width=True, type="primary"):
                user = magi_core.authenticate_user(user_id, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    # セッション永続化用トークン発行
                    if hasattr(magi_core, "create_session"):
                        token = magi_core.create_session(user)
                        st.query_params["sync_token"] = token
                    st.success("SYNCHRONIZATION COMPLETE.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("ACCESS DENIED: PATTEN BLUE (IMPOSTOR)")
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

def show_nav():
    is_admin = st.session_state.user["role"] in ["Commander", "Sub-Commander"] or "Admin" in st.session_state.user["role"]
    
    # Role-based security check for Admin page
    if st.session_state.page == "admin" and not is_admin:
        st.session_state.page = "main"
        st.rerun()

    # Layout for Header
    h_cols = st.columns([1.5, 4, 2])
    
    with h_cols[1]: # CENTER: Title
        t = "MAGI SYSTEM INTERFACE" if st.session_state.page == "main" else ("ADMIN CONSOLE" if st.session_state.page == "admin" else "CENTRAL LOGS")
        st.markdown(f'<h1 class="main-title">{t}</h1>', unsafe_allow_html=True)
    
    with h_cols[2]: # RIGHT: Operator, Logout, Admin
        st.markdown(f'<div style="text-align:right; font-size:0.75em; color:#00FF00; height:18px; margin-bottom:5px; overflow:hidden; white-space:nowrap;">Operator: {st.session_state.user["name"]}</div>', unsafe_allow_html=True)
        r_cols = st.columns(2)
        with r_cols[0]: # Logout
            if st.button("LOGOUT", use_container_width=True, key="h_logout"):
                if "sync_token" in st.query_params:
                    token = st.query_params["sync_token"]
                    magi_core.clear_session(token)
                    st.query_params.clear()
                st.session_state.authenticated = False
                st.rerun()
        with r_cols[1]: # Admin / Return
            if st.session_state.page == "main":
                if is_admin:
                    if st.button("ADMIN ⚙️", use_container_width=True, key="h_admin"):
                        st.session_state.page = "admin"
                        st.rerun()
            else: # Admin or History page
                if st.button("◀ RETURN", use_container_width=True, key="h_return"):
                    st.session_state.page = "main"
                    st.rerun()
    st.markdown('<div class="header-container"></div>', unsafe_allow_html=True)
