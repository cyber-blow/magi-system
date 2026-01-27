import streamlit as st
import os
import sys
from streamlit_echarts import st_echarts

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import magi_core

def render_history():
    t_list, t_dash = st.tabs(["📜 LOGS", "📊 ANALYTICS"])
    
    history = magi_core.load_json(magi_core.HISTORY_PATH, [])
    # History Isolation
    is_privileged = st.session_state.user["role"] in ["Commander", "Sub-Commander"]
    user_id = st.session_state.user["username"]
    filtered_history = [item for item in history if is_privileged or item.get("user_id") == user_id]

    with t_dash:
        if not filtered_history:
            st.info("No data for analytics.")
        else:
            # 1. Approval Rate (Pie Chart)
            votes = [r["vote"] for item in filtered_history for r in item.get("results", [])]
            approval = votes.count("是認")
            conditional = votes.count("条件付是認")
            denial = votes.count("否認")
            
            pie_options = {
                "backgroundColor": "transparent",
                "title": {"text": "TOTAL DECISION RATIO", "left": "center", "textStyle": {"color": "#FF8C00"}},
                "tooltip": {"trigger": "item"},
                "series": [{
                    "name": "Decision",
                    "type": "pie",
                    "radius": "50%",
                    "data": [
                        {"value": approval, "name": "是認", "itemStyle": {"color": "#00FF00"}},
                        {"value": conditional, "name": "条件付是認", "itemStyle": {"color": "#FFFF00"}},
                        {"value": denial, "name": "否認", "itemStyle": {"color": "#FF0000"}},
                    ],
                    "label": {"color": "#FF8C00"}
                }]
            }
            st_echarts(options=pie_options, height="300px")
            
            # 2. Magi Bias (Radar Chart)
            # Calculate 'strictness' average score per Magi (Melchior, Balthasar, Casper)
            magi_scores = {"MELCHIOR": [], "BALTHASAR": [], "CASPER": []}
            score_map = {"是認": 100, "条件付是認": 50, "否認": 0}
            
            for item in filtered_history:
                for r in item.get("results", []):
                    name = r["name"].upper() # Ensure upper case matching
                    vote = r.get("vote", "否認")
                    # Try to match name to key
                    for key in magi_scores:
                        if key in name: magi_scores[key].append(score_map.get(vote, 0))
            
            avg_scores = [
                sum(magi_scores["MELCHIOR"])/len(magi_scores["MELCHIOR"]) if magi_scores["MELCHIOR"] else 0,
                sum(magi_scores["BALTHASAR"])/len(magi_scores["BALTHASAR"]) if magi_scores["BALTHASAR"] else 0,
                sum(magi_scores["CASPER"])/len(magi_scores["CASPER"]) if magi_scores["CASPER"] else 0
            ]
            
            radar_options = {
                "backgroundColor": "transparent",
                "title": {"text": "MAGI BIAS ANALYSIS (Avg Approval Score)", "left": "center", "textStyle": {"color": "#FF8C00"}},
                "radar": {"indicator": [{"name": "MELCHIOR", "max": 100}, {"name": "BALTHASAR", "max": 100}, {"name": "CASPER", "max": 100}], 
                          "splitLine": {"lineStyle": {"color": "#FF8C00", "opacity": 0.3}},
                          "axisName": {"color": "#FF8C00"}},
                "series": [{
                    "type": "radar",
                    "data": [{"value": [int(s) for s in avg_scores]}],
                    "areaStyle": {"color": "#FF8C00", "opacity": 0.2},
                    "lineStyle": {"color": "#FF8C00"},
                    "itemStyle": {"color": "#FF8C00"}
                }]
            }
            st_echarts(options=radar_options, height="300px")

    with t_list:
        if not filtered_history:
            st.info("No authorized records found.")
            return

        for item in reversed(filtered_history): # Newest first
            u_label = f" | Op: {item.get('user_id', 'Unknown')}" if is_privileged else ""
            with st.expander(f"[{item['timestamp'][:16]}{u_label}] {item['question'][:40]}..."):
                st.markdown(f"**Topic:** {item['question']}")
                if is_privileged:
                    st.markdown(f"**Conducted by:** `{item.get('user_id', 'Unknown')}`")
                
                for r in item["results"]: st.markdown(f"- **{r['name']}**: {r['vote']}")
                
                md = f"# MAGI REPORT\n\n"
                md += f"Topic: {item['question']}\n"
                md += f"Operator: {item.get('user_id', 'Unknown')}\n"
                md += f"Timestamp: {item.get('timestamp', '')}\n\n"
                for r in item['results']: md += f"## {r['name']}\n{r['vote']}\n{r['reason']}\n\n"
                if item.get("seele_summary"):
                    md += f"## SEELE SUMMARY\n{item['seele_summary']}\n"
                
                st.download_button("Export Report", md, file_name=f"MAGI_{item['id']}.md", key=f"dl_{item['id']}")
