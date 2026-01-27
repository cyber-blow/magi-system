import streamlit as st
import asyncio
import magi_core
import json
import base64
import time
import csv
import io
from streamlit_echarts import st_echarts

# --- 1. ページ構成 ---
st.set_page_config(
    page_title="MAGI SYSTEM | NERV HQ",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 状態管理：初期化
if "page" not in st.session_state: st.session_state.page = "main"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "results" not in st.session_state: st.session_state.results = None

# 自動ログイン処理 (Session Persistence)
if not st.session_state.authenticated:
    token = st.query_params.get("sync_token")
    if token:
        user_info = magi_core.validate_session(token)
        if user_info:
            st.session_state.authenticated = True
            st.session_state.user = user_info

# デザイン (CSS)
CSS = """
<style>
    .stApp { background-color: #000000; color: #FF8C00; font-family: 'Times New Roman', 'Yu Mincho', serif; }
    
    /* Security Overlay & Login */
    .auth-bg {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: black; z-index: 0;
    }
    .auth-header { 
        font-size: 3em; letter-spacing: 0.5em; color: #FF0000; 
        border: 2px solid #FF0000; padding: 20px; margin-bottom: 30px; 
        text-align: center; font-weight: bold;
    }
    .auth-card {
        background: rgba(15, 0, 0, 0.85);
        border: 1px solid #FF0000;
        padding: 40px;
        margin-top: 10vh;
        box-shadow: 0 0 40px rgba(255, 0, 0, 0.3);
    }
    
    .header-container { border-bottom: 4px double #FF8C00; padding-bottom: 10px; margin-bottom: 25px; }
    .main-title { font-size: 3em; letter-spacing: 0.3em; text-align: center; margin: 0; width: 100%; text-shadow: 0 0 10px #FF8C00; }

    /* HUD Effects */
    .stApp::after {
        content: " "; display: block; position: absolute; top:0; left:0; bottom:0; right:0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(32, 32, 32, 0.25) 50%), linear-gradient(90deg, rgba(255,0,0,0.03), rgba(0,255,0,0.01), rgba(0,0,255,0.03));
        z-index: 999; background-size: 100% 2px, 3px 100%; pointer-events: none;
    }

    /* MAGI Result Panels */
    .magi-panel { border: 2px solid #FF8C00; padding: 15px; background: #050505; height: 480px; overflow-y: auto; position: relative; }
    .magi-header { font-size: 1.4em; border-bottom: 1px solid #FF8C00; margin-bottom: 10px; font-weight: 900; }
    .magi-vote { font-size: 1.5em; text-align: center; margin-top: 15px; border: 2px solid; padding: 5px; }

    .stTextArea > div > div > textarea { background-color: #080808; color: #00FF00; border: 1px solid #FF8C00; font-family: 'Courier New', monospace; }
    
    /* Provider Section */
    .provider-section {
        background-color: #0d0d0d; border: 1px solid #FF8C0033; padding: 18px; margin-bottom: 15px; border-radius: 4px; transition: 0.3s;
    }
    .provider-section:hover { border-color: #FF8C00; }
    .status-badge { font-size: 0.6em; padding: 2px 8px; border-radius: 20px; font-weight: 900; margin-left:10px; }
    .status-active { background-color: #00FF0011; color: #00FF00; border: 1px solid #00FF00; }
    .status-inactive { background-color: #FF000011; color: #FF0000; border: 1px solid #FF0000; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- 2. 認証画面 ---
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
                token = magi_core.create_session(user)
                st.query_params["sync_token"] = token
                st.success("SYNCHRONIZATION COMPLETE.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("ACCESS DENIED: PATTEN BLUE (IMPOSTOR)")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 3. ナビゲーション ---
def show_nav():
    cols = st.columns([3, 1.5, 1.5])
    with cols[0]:
        t = "MAGI SYSTEM INTERFACE" if st.session_state.page == "main" else ("ADMIN CONSOLE" if st.session_state.page == "admin" else "CENTRAL LOGS")
        st.markdown(f'<h1 class="main-title">{t}</h1>', unsafe_allow_html=True)
    with cols[1]:
        # Fixed height for operator text to prevent jumping/overlap
        st.markdown(f'<div style="text-align:right; font-size:0.7em; color:#00FF00; height:18px; margin-bottom:5px; overflow:hidden; white-space:nowrap;">Operator: {st.session_state.user["name"]}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.session_state.page == "history":
                if st.button("◀ RETURN", use_container_width=True): st.session_state.page = "main"; st.rerun()
            else:
                if st.button("HISTORY", use_container_width=True): st.session_state.page = "history"; st.rerun()
        with c2:
            if st.button("LOGOUT", use_container_width=True):
                if "sync_token" in st.query_params:
                    token = st.query_params["sync_token"]
                    magi_core.clear_session(token)
                    st.query_params.clear()
                st.session_state.authenticated = False
                st.rerun()
    with cols[2]:
        st.markdown('<div style="height:23px;"></div>', unsafe_allow_html=True)
        is_admin = st.session_state.user["role"] in ["Commander", "Sub-Commander"] or "Admin" in st.session_state.user["role"]
        
        if st.session_state.page == "admin":
            if not is_admin:
                st.session_state.page = "main"
                st.rerun()
            if st.button("RETURN", use_container_width=True, key="admin_ret"): st.session_state.page = "main"; st.rerun()
        elif is_admin:
            if st.button("ADMIN ▶", use_container_width=True, key="admin_nav"): st.session_state.page = "admin"; st.rerun()
    st.markdown('<div class="header-container"></div>', unsafe_allow_html=True)

# --- 4. メイン画面 ---
def render_main():
    templates = magi_core.load_json(magi_core.TEMPLATES_PATH, {})
    if templates:
        st.markdown('<div style="font-size:0.75em; opacity:0.8; margin-bottom:5px;">📂 MODE SELECTOR:</div>', unsafe_allow_html=True)
        t_cols = st.columns(max(len(templates), 5))
        for i, tname in enumerate(templates.keys()):
            if t_cols[i].button(f"[{tname}]", key=f"tload_{tname}"):
                magi_core.save_persona_config(templates[tname])
                st.success(f"Configured: {tname}"); time.sleep(0.5); st.rerun()

    col_input, col_opt = st.columns([2, 1])
    with col_input:
        question = st.text_area("TOPIC", height=130, placeholder="審議事項を入力...", label_visibility="collapsed")
        uploaded_file = st.file_uploader("ATTACH MATERIAL (PDF/TXT)", type=["pdf", "txt"])
    
    with col_opt:
        st.markdown('<div style="padding-top:20px;"></div>', unsafe_allow_html=True)
        debate = st.toggle("DEEP SIMULATION", value=False)
        synthesis = st.toggle("SEELE SYNTHESIS", value=True)
        if st.button("START JUDGMENT", type="primary", use_container_width=True):
            if question:
                context = ""
                if uploaded_file: context = magi_core.extract_text_from_file(uploaded_file.read(), uploaded_file.name)
                with st.spinner("MAGI: ANALYZING..."):
                    try:
                        res = asyncio.run(magi_core.ask_magi_system(question, context, debate, synthesis, uploaded_file.name if uploaded_file else ""))
                        # Record history with user context
                        magi_core.add_history_with_user(
                            st.session_state.user["username"], 
                            question, res["magi_results"], res["final_score"], 
                            res["seele_summary"], uploaded_file.name if uploaded_file else ""
                        )
                        st.session_state.results = res; st.rerun()
                    except magi_core.RateLimitError as e:
                        st.error("【警告】API制限（429）に達しました。別のプロバイダーを使用してください。")
                    except Exception as e: st.error(f"Error: {e}")
            else: st.error("Enter topic.")

    if st.session_state.results:
        res = st.session_state.results
        render_decision_graph(res["magi_results"])
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(3); colors = {"是認": "#00FF00", "条件付是認": "#FFFF00", "否認": "#FF0000"}
        for i, r in enumerate(res["magi_results"]):
            c = colors.get(r[2], "#FFF")
            cols[i].markdown(f'<div class="magi-panel" style="border-color:{c};"><div class="magi-header" style="color:{c};">{r[0]}</div><div style="font-size:0.9em; white-space:pre-wrap; color:#EEE;">{r[1]}</div>' + (f'<div style="margin-top:10px; border:1px dashed #FFFF00; padding:5px; font-size:0.8em; color:#FFFF00;">CONDITION: {r[3]}</div>' if r[3] else "") + f'<div class="magi-vote" style="border-color:{c}; color:{c};">{r[2]}</div></div>', unsafe_allow_html=True)
        if res["seele_summary"]:
            st.markdown(f'<div style="border:2px double #FF4500; background:#0a0500; padding:25px; margin-bottom:20px; margin-top:30px;"><h2 style="color:#FF4500; text-align:center;">SEELE SUMMARY</h2><p style="white-space:pre-wrap; color:#FF8C00;">{res["seele_summary"]}</p></div>', unsafe_allow_html=True)
            
            # Action Buttons
            st.markdown("### ⚡ ACTION EXECUTION")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("EXECUTE: SEND TO SLACK", use_container_width=True):
                    if magi_core.execute_webhook_action("slack", question, res["seele_summary"]):
                        st.success("TRANSMISSION COMPLETE: SLACK")
                    else: st.error("TRANSMISSION FAILED: CHECK SLACK CONFIG")
            with c2:
                if st.button("EXECUTE: SEND TO DISCORD", use_container_width=True):
                    if magi_core.execute_webhook_action("discord", question, res["seele_summary"]):
                        st.success("TRANSMISSION COMPLETE: DISCORD")
                    else: st.error("TRANSMISSION FAILED: CHECK DISCORD CONFIG")

def render_decision_graph(res):
    scores = [{"是認":100, "条件付是認":50, "否認":15}.get(r[2], 0) for r in res]
    options = {"backgroundColor":"transparent","radar":{"indicator":[{"name":"MELCHIOR","max":100},{"name":"BALTHASAR","max":100},{"name":"CASPER","max":100}],"splitArea":{"show":False},"splitLine":{"lineStyle":{"color":"#FF8C00","opacity":0.2}},"axisLine":{"lineStyle":{"color":"#FF8C00","opacity":0.4}}},"series":[{"type":"radar","data":[{"value":scores}],"lineStyle":{"color":"#FF8C00","width":3},"areaStyle":{"color":"#FF8C00","opacity":0.2},"itemStyle":{"color":"#FF8C00"}}]}
    st_echarts(options, height="200px")

def render_history():
    history = magi_core.load_json(magi_core.HISTORY_PATH, [])
    if not history: st.info("No records."); return
    for item in history:
        with st.expander(f"[{item['timestamp'][:16]}] {item['question'][:40]}..."):
            st.markdown(f"**Topic:** {item['question']}")
            for r in item["results"]: st.markdown(f"- **{r['name']}**: {r['vote']}")
            md = f"# REPORT\n\nTopic: {item['question']}\n\n"
            for r in item['results']: md += f"## {r['name']}\n{r['vote']}\n{r['reason']}\n\n"
            st.download_button("Export Report", md, file_name=f"MAGI_{item['id']}.md", key=f"dl_{item['id']}")

def render_admin():
    t_persona, t_api, t_sys, t_int, t_usr = st.tabs(["🧬 PERSONA", "🔌 API / SEELE", "⚙️ SYSTEM", "🛰️ INTEGRATIONS", "👥 USERS"])
    api_config = magi_core.load_api_config()

    with t_persona:
        config = magi_core.load_persona_config()
        for pid, d in config.items():
            if not isinstance(d, dict): continue
            with st.expander(f"MAGI {pid.upper()}: {d.get('name', pid)}", expanded=True):
                d["name"] = st.text_input("Name", d.get("name", pid), key=f"n_{pid}")
                
                # Support role_desc as the primary 'Role' field
                r_key = "role_desc" if "role_desc" in d else ("role" if "role" in d else "role_desc")
                d[r_key] = st.text_input("Role / Persona Description", d.get(r_key, ""), key=f"r_{pid}")
                
                cur_prov = d.get("model_provider", d.get("provider", "google"))
                c_prov = st.selectbox("Provider", list(api_config["providers"].keys()), 
                                    index=list(api_config["providers"].keys()).index(cur_prov) if cur_prov in api_config["providers"] else 0, 
                                    key=f"p_{pid}")
                d["model_provider"] = c_prov # standardizing on one key for later save
                
                m_list = api_config["providers"].get(c_prov, {}).get("models", ["gemini-1.5-flash"])
                cur_model = d.get("model_name", "gemini-1.5-flash")
                if cur_model not in m_list: m_list.append(cur_model)
                d["model_name"] = st.selectbox("Model", m_list, index=m_list.index(cur_model), key=f"m_{pid}")
                d["temperature"] = st.slider("Temp", 0.0, 1.0, float(d.get("temperature", 0.7)), key=f"t_{pid}")
                d["prompt"] = st.text_area("System Prompt", d.get("prompt", ""), height=250, key=f"sp_{pid}")
                if st.button(f"Save {pid} Settings"):
                    magi_core.save_persona_config(config); st.success("Updated.")

    with t_api:
        st.markdown("### 👁️ SEELE CONFIG")
        c1, c2 = st.columns(2)
        with c1:
            api_config["seele_model"]["provider"] = st.selectbox("Provider (SEELE)", list(api_config["providers"].keys()), index=list(api_config["providers"].keys()).index(api_config["seele_model"]["provider"]))
        with c2:
            s_models = api_config["providers"].get(api_config["seele_model"]["provider"], {}).get("models", ["gemini-2.0-flash"])
            if api_config["seele_model"]["name"] not in s_models: s_models.append(api_config["seele_model"]["name"])
            api_config["seele_model"]["name"] = st.selectbox("Model (SEELE)", s_models, index=s_models.index(api_config["seele_model"]["name"]))
        if st.button("Save SEELE Config"): magi_core.save_api_config(api_config); st.success("SEELE updated.")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### 🔌 API PROVIDER CONNECTIONS")
        p_info = {"google": "GOOGLE GEMINI", "groq": "GROQ", "openai": "OPENAI", "anthropic": "ANTHROPIC", "local": "LOCAL (Ollama etc.)"}
        for pid, label in p_info.items():
            providers = api_config["providers"]
            is_active = bool(providers[pid].get("api_key") or providers[pid].get("base_url"))
            status = f'<span class="status-badge status-active">ACTIVE</span>' if is_active else f'<span class="status-badge status-inactive">INACTIVE</span>'
            st.markdown(f'<div class="provider-section"><h4>{label} {status}</h4>', unsafe_allow_html=True)
            if pid == "local":
                url = st.text_input(f"BASE URL", providers[pid].get("base_url", ""), key=f"url_{pid}")
                key = st.text_input(f"API KEY (Optional)", providers[pid].get("api_key", ""), type="password", key=f"ak_{pid}")
                if st.button(f"Sync Models {pid.upper()}"):
                    models = asyncio.run(magi_core.fetch_models_local(url, key))
                    providers[pid] = {"base_url": url, "api_key": key, "models": models}
                    magi_core.save_api_config(api_config); st.success("Synced."); st.rerun()
            else:
                key = st.text_input(f"API KEY", providers[pid].get("api_key", ""), type="password", key=f"ak_{pid}")
                if st.button(f"Sync Models {pid.upper()}"):
                    fetch_map = {"google": magi_core.fetch_models_google, "groq": magi_core.fetch_models_groq, "openai": magi_core.fetch_models_openai, "anthropic": magi_core.fetch_models_anthropic}
                    models = asyncio.run(fetch_map[pid](key))
                    providers[pid] = {"api_key": key, "models": models}
                    magi_core.save_api_config(api_config); st.success("Synced."); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with t_sys:
        tn = st.text_input("Template Name to Save:")
        if st.button("Save Current Personas") and tn:
            tps = magi_core.load_json(magi_core.TEMPLATES_PATH, {})
            tps[tn] = magi_core.load_persona_config()
            magi_core.save_json(magi_core.TEMPLATES_PATH, tps); st.success("Saved.")
        if st.button("Clear History"): magi_core.save_json(magi_core.HISTORY_PATH, []); st.rerun()

    with t_int:
        st.markdown("### 🛰️ EXTERNAL INTEGRATIONS (WEBHOOKS)")
        webhooks_data = magi_core.load_json(magi_core.WEBHOOKS_PATH, {"webhooks": {}})
        wh = webhooks_data.get("webhooks", {})
        
        for wid, cfg in wh.items():
            with st.expander(f"{wid.upper()} - {cfg['name']}", expanded=True):
                new_url = st.text_input("WEBHOOK URL", value=cfg['url'], key=f"wh_url_{wid}")
                if st.button(f"SAVE {wid.upper()} CONFIG"):
                    wh[wid]["url"] = new_url
                    magi_core.save_json(magi_core.WEBHOOKS_PATH, webhooks_data)
                    st.success("CONFIGURATION UPDATED.")

    with t_usr:
        st.markdown("### 👥 NERV PERSONNEL MANAGEMENT")
        
        # Add User Form
        with st.expander("➕ REGISTER NEW PERSONNEL", expanded=False):
            with st.form("add_user_form"):
                new_uid = st.text_input("USER ID (CODE NAME)")
                new_name = st.text_input("FULL NAME")
                new_pass = st.text_input("SECRET KEY / PASSWORD", type="password")
                new_role = st.selectbox("ROLE", ["Commander", "Sub-Commander", "Operations Director", "Chief Scientist", "Operator"])
                if st.form_submit_button("REGISTER TO NERV DATABASE"):
                    if new_uid and new_pass and new_name:
                        if magi_core.add_user(new_uid, new_pass, new_name, new_role):
                            st.success(f"User {new_uid} registered successfully.")
                            # time.sleep(1) # Optional UI delay
                            st.rerun()
                        else: st.error("User ID already exists.")
                    else: st.error("Please fill all fields.")

        # Bulk Operations (CSV)
        with st.expander("📂 BULK OPERATIONS (CSV IMPORT/EXPORT)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**EXPORT PERSONNEL**")
                all_users = magi_core.get_all_users()
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["id", "password", "name", "role"])
                for uid, info in all_users.items():
                    writer.writerow([uid, info.get("password", ""), info.get("name", ""), info.get("role", "")])
                st.download_button("DOWNLOAD CSV", output.getvalue(), file_name="magi_personnel.csv", mime="text/csv")
            
            with c2:
                st.markdown("**IMPORT PERSONNEL**")
                uploaded_csv = st.file_uploader("Upload CSV (id,password,name,role)", type="csv", key="user_csv")
                if uploaded_csv:
                    if st.button("EXECUTE IMPORT"):
                        try:
                            stream = io.StringIO(uploaded_csv.getvalue().decode("utf-8"))
                            reader = csv.DictReader(stream)
                            count = 0
                            for row in reader:
                                if magi_core.add_user(row["id"], row["password"], row["name"], row["role"]):
                                    count += 1
                            st.success(f"Imported {count} users.")
                            time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"Import failed: {e}")

        st.markdown("---")
        # List Users
        users = magi_core.get_all_users()
        for uid, info in users.items():
            ucols = st.columns([3, 2, 1])
            ucols[0].markdown(f"**{info['name']}** (`{uid}`)")
            ucols[1].markdown(f"Role: {info['role']}")
            if uid != "nerv_admin":
                if ucols[2].button("DELETE", key=f"del_{uid}"):
                    if magi_core.delete_user(uid):
                        st.success(f"User {uid} deleted.")
                        st.rerun()

# --- 5. 実行 ---
show_nav()
if st.session_state.page == "main": render_main()
elif st.session_state.page == "history": render_history()
else: render_admin()