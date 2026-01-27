import streamlit as st
import asyncio
import magi_core
import json
import base64
import time
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

# デザイン (CSS)
CSS = """
<style>
    .stApp { background-color: #000000; color: #FF8C00; font-family: 'Times New Roman', 'Yu Mincho', serif; }
    
    /* Security Overlay */
    .auth-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: black; z-index: 1000; display: flex; flex-direction: column;
        justify-content: center; align-items: center; text-align: center;
    }
    .auth-header { font-size: 3em; letter-spacing: 0.5em; color: #FF0000; border: 2px solid #FF0000; padding: 20px; margin-bottom: 50px; }
    .stButton { position: relative; z-index: 1001; }

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
    st.markdown('<div class="auth-overlay"><div class="auth-header">NERV TOP SECRET MATERIAL</div><p style="color: #FF8C00; letter-spacing: 0.2em;">SYSTEM MAGI: SYNAPTIC LINK INITIALIZATION REQUIRED</p></div>', unsafe_allow_html=True)
    if st.button("INITIATE SYNCHRONIZATION", use_container_width=True):
        st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. ナビゲーション ---
def show_nav():
    cols = st.columns([4, 1, 1])
    with cols[0]:
        t = "MAGI SYSTEM INTERFACE" if st.session_state.page == "main" else ("ADMIN CONSOLE" if st.session_state.page == "admin" else "CENTRAL LOGS")
        st.markdown(f'<h1 class="main-title">{t}</h1>', unsafe_allow_html=True)
    with cols[1]:
        if st.button("HISTORY", use_container_width=True): st.session_state.page = "history"; st.rerun()
    with cols[2]:
        if st.session_state.page == "admin":
            if st.button("RETURN", use_container_width=True): st.session_state.page = "main"; st.rerun()
        else:
            if st.button("ADMIN ▶", use_container_width=True): st.session_state.page = "admin"; st.rerun()
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
            st.markdown(f'<div style="border:2px double #FF4500; background:#0a0500; padding:25px; margin-top:30px;"><h2 style="color:#FF4500; text-align:center;">SEELE SUMMARY</h2><p style="white-space:pre-wrap; color:#FF8C00;">{res["seele_summary"]}</p></div>', unsafe_allow_html=True)

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
    t_persona, t_api, t_sys = st.tabs(["🧬 PERSONA", "🔌 API / SEELE", "⚙️ SYSTEM"])
    api_config = magi_core.load_api_config()

    with t_persona:
        config = magi_core.load_persona_config()
        api_providers = api_config["providers"]
        p_tabs = st.tabs(["MELCHIOR", "BALTHASAR", "CASPER"])
        for pid in ["MELCHIOR", "BALTHASAR", "CASPER"]:
            with p_tabs[["MELCHIOR", "BALTHASAR", "CASPER"].index(pid)]:
                d = config[pid]
                c1, c2 = st.columns(2)
                with c1:
                    d["name"] = st.text_input("Name", d["name"], key=f"n_{pid}")
                    d["model_provider"] = st.selectbox("Provider", list(api_providers.keys()), index=list(api_providers.keys()).index(d["model_provider"]) if d["model_provider"] in api_providers else 0, key=f"pv_{pid}")
                with c2:
                    m_list = api_providers.get(d["model_provider"], {}).get("models", [d["model_name"]])
                    if not m_list: m_list = [d["model_name"]]
                    if d["model_name"] not in m_list: m_list.append(d["model_name"])
                    d["model_name"] = st.selectbox("Model", m_list, index=m_list.index(d["model_name"]), key=f"m_{pid}")
                    d["temperature"] = st.slider("Temp", 0.0, 1.0, float(d.get("temperature", 0.7)), key=f"t_{pid}")
                d["prompt"] = st.text_area("System Prompt", d["prompt"], height=250, key=f"sp_{pid}")
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
        
        p_info = {
            "google": {"t": "GOOGLE GEMINI", "fetch": magi_core.fetch_models_google},
            "groq": {"t": "GROQ", "fetch": magi_core.fetch_models_groq},
            "openai": {"t": "OPENAI", "fetch": magi_core.fetch_models_openai},
            "anthropic": {"t": "ANTHROPIC", "fetch": magi_core.fetch_models_anthropic},
            "local": {"t": "LOCAL / CUSTOM (Ollama etc.)", "fetch": magi_core.fetch_models_local}
        }
        
        for pid, info in p_info.items():
            providers = api_config["providers"]
            is_active = bool(providers[pid].get("api_key") or providers[pid].get("base_url"))
            status = f'<span class="status-badge status-active">ACTIVE</span>' if is_active else f'<span class="status-badge status-inactive">INACTIVE</span>'
            
            st.markdown(f'<div class="provider-section"><h4>{info["t"]} {status}</h4>', unsafe_allow_html=True)
            if pid == "local":
                url = st.text_input(f"BASE URL (OpenAI compatible)", providers[pid].get("base_url", "http://localhost:11434/v1"), key=f"url_{pid}")
                key = st.text_input(f"API KEY (Optional)", providers[pid].get("api_key", "sk-xxx"), type="password", key=f"ak_{pid}")
                if st.button(f"Sync Models from {pid.upper()}"):
                    models = asyncio.run(info["fetch"](url, key))
                    providers[pid] = {"base_url": url, "api_key": key, "models": models}
                    magi_core.save_api_config(api_config); st.success("Synced."); st.rerun()
            else:
                key = st.text_input(f"API KEY ({pid.upper()})", providers[pid].get("api_key", ""), type="password", key=f"ak_{pid}")
                if st.button(f"Validate & Sync {pid}"):
                    models = asyncio.run(info["fetch"](key))
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

# --- 5. 実行 ---
show_nav()
if st.session_state.page == "main": render_main()
elif st.session_state.page == "history": render_history()
else: render_admin()