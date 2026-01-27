import streamlit as st
import time
import asyncio
import os
import sys
from streamlit_echarts import st_echarts

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import magi_core

def render_decision_graph(res):
    scores = [{"是認":100, "条件付是認":50, "否認":15}.get(r[2], 0) for r in res]
    options = {"backgroundColor":"transparent","radar":{"indicator":[{"name":"MELCHIOR","max":100},{"name":"BALTHASAR","max":100},{"name":"CASPER","max":100}],"splitArea":{"show":False},"splitLine":{"lineStyle":{"color":"#FF8C00","opacity":0.2}},"axisLine":{"lineStyle":{"color":"#FF8C00","opacity":0.4}}},"series":[{"type":"radar","data":[{"value":scores}],"lineStyle":{"color":"#FF8C00","width":3},"areaStyle":{"color":"#FF8C00","opacity":0.2},"itemStyle":{"color":"#FF8C00"}}]}
    st_echarts(options, height="200px")

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
                        st.session_state.results = res
                        st.session_state.show_animation = True # Trigger Animation
                        st.rerun()
                    except magi_core.RateLimitError as e:
                        st.error("【警告】API制限（429）に達しました。別のプロバイダーを使用してください。")
                    except Exception as e: st.error(f"Error: {e}")
            else: st.error("Enter topic.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📜 VIEW HISTORY", use_container_width=True, key="main_hist_btn"):
            st.session_state.page = "history"
            st.rerun()

    if st.session_state.results:
        res = st.session_state.results
        render_decision_graph(res["magi_results"])
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(3); colors = {"是認": "#00FF00", "条件付是認": "#FFFF00", "否認": "#FF0000"}
        
        # Checking if we should animate (newly generated)
        should_animate = st.session_state.get("show_animation", False)
        
        if should_animate:
            # Sequential Animation (Melchior -> Balthasar -> Casper)
            placeholders = [cols[i].empty() for i in range(3)]
            full_texts = [r[1] for r in res["magi_results"]]
            
            # 1. Render Headers first
            for i, r in enumerate(res["magi_results"]):
                c = colors.get(r[2], "#FFF")
                # Initial state: empty body
                html = f'<div class="magi-panel" style="border-color:{c};"><div class="magi-header" style="color:{c};">{r[0]}</div><div style="font-size:0.9em; white-space:pre-wrap; color:#EEE;"></div></div>'
                placeholders[i].markdown(html, unsafe_allow_html=True)
            
            # 2. Animate one by one
            for i, r in enumerate(res["magi_results"]):
                c = colors.get(r[2], "#FFF")
                full_text = r[1]
                # Simulate typing
                chunk_size = 3 # chars per frame
                for char_i in range(0, len(full_text) + 1, chunk_size):
                    current_text = full_text[:char_i]
                    html = f'<div class="magi-panel" style="border-color:{c};"><div class="magi-header" style="color:{c};">{r[0]}</div><div style="font-size:0.9em; white-space:pre-wrap; color:#EEE;">{current_text}_</div></div>' # Add cursor
                    placeholders[i].markdown(html, unsafe_allow_html=True)
                    time.sleep(0.01) # Tuning speed
                
                # Finalize without cursor and with vote/condition
                cond_html = (f'<div style="margin-top:10px; border:1px dashed #FFFF00; padding:5px; font-size:0.8em; color:#FFFF00;">CONDITION: {r[3]}</div>' if r[3] else "")
                final_html = f'<div class="magi-panel" style="border-color:{c};"><div class="magi-header" style="color:{c};">{r[0]}</div><div style="font-size:0.9em; white-space:pre-wrap; color:#EEE;">{full_text}</div>{cond_html}<div class="magi-vote" style="border-color:{c}; color:{c};">{r[2]}</div></div>'
                placeholders[i].markdown(final_html, unsafe_allow_html=True)
            
            st.session_state.show_animation = False # Turn off animation for future re-renders
            
        else:
            # Static Render
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
