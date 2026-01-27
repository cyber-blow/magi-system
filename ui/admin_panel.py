import streamlit as st
import time
import asyncio
import csv
import io
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import magi_core

def render_admin():
    t_persona, t_api, t_sys, t_int, t_usr = st.tabs(["🧬 PERSONA", "🔌 API / SEELE", "⚙️ SYSTEM", "🛰️ INTEGRATIONS", "👥 USERS"])
    api_config = magi_core.load_api_config()

    with t_persona:
        config = magi_core.load_persona_config()
        # Nested tabs for each persona (Melchior, Balthasar, Casper)
        pids = [p for p in config.keys() if isinstance(config[p], dict)]
        tabs_p = st.tabs([f"MAGI {p.upper()}" for p in pids])
        
        for i, pid in enumerate(pids):
            d = config[pid]
            with tabs_p[i]:
                st.markdown(f"#### 🧠 {pid.upper()} CORE CONFIGURATION")
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
