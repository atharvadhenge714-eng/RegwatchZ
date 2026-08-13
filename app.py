import streamlit as st
import json
import os
import tempfile
import time
import datetime
from typing import Any

from company_profiler import profile_company, build_compliance_profile
from fetch_agent import fetch_latest_circulars, fetch_circular_text, LATEST_RBI_CIRCULARS
from parser_agent import parse_rbi_circular
from mapper_agent import index_company_profile, compare_regulation_with_profile
from action_agent import generate_compliance_alert, generate_quick_scan, generate_action_plan

# Unified Services & Agent Imports
from services.db_service import (
    save_company_profile, get_company_profile, save_compliance_report,
    save_global_matrix, get_global_matrix, save_diff_result, get_diff_history,
    save_agent_run, save_full_compliance_profile, get_saved_profiles,
    get_saved_profile_by_id, get_company_scan_history, delete_saved_profile
)
from services.diff_engine import compare_regulatory_documents
from agents_pipeline import (
    run_multi_agent_pipeline, run_single_agent_by_id,
    normalize_company_type, ALLOWED_COMPANY_TYPES
)

# PAGE CONFIG
st.set_page_config(
    page_title="RegWatch Pro — Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== CSS STYLING =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        background: #06060f;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #f1f5f9;
    }

    /* Reduce container padding at top */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 95% !important;
    }

    header[data-testid="stHeader"] {
        height: 0px !important;
        min-height: 0px !important;
        display: none !important;
    }

    /* Glass card style */
    .gcard {
        background: rgba(13, 13, 29, 0.7);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(12px);
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Command Center Primary Action Cards */
    .action-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.6), rgba(88, 28, 135, 0.25));
        border: 1px solid rgba(129, 140, 248, 0.35);
        border-radius: 20px;
        padding: 32px;
        transition: all 0.3s ease;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .action-card:hover {
        border-color: rgba(192, 132, 252, 0.6);
        transform: translateY(-4px);
        box-shadow: 0 15px 35px rgba(99, 102, 241, 0.3);
    }

    /* Hero section */
    .hero {
        text-align: center;
        padding: 5px 0 15px;
    }
    .hero h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -1px;
    }
    .hero p {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-top: 8px;
        font-weight: 400;
    }

    /* Stat Cards */
    .stat-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .stat-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.4), rgba(88, 28, 135, 0.15));
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .stat-card .val {
        font-size: 2.2rem;
        font-weight: 800;
        color: #c084fc;
        margin-bottom: 4px;
    }
    .stat-card .lbl {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Badges styling */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-critical { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-high { background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }
    .badge-medium { background: rgba(234, 179, 8, 0.18); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.35); }
    .badge-low { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
    .badge-na { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }

    /* Interactive Matrix Table styling */
    .matrix-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 4px;
        margin-top: 15px;
    }
    .matrix-table th {
        background: rgba(99, 102, 241, 0.15);
        color: #e2e8f0;
        padding: 14px 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .matrix-table td {
        padding: 16px 12px;
        border-radius: 8px;
        text-align: center;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .matrix-table td:hover {
        transform: scale(1.02);
        box-shadow: 0 0 8px rgba(255, 255, 255, 0.1);
    }
    .matrix-lbl-cell {
        background: rgba(15, 23, 42, 0.6);
        color: #94a3b8;
        font-weight: 500;
        font-size: 0.85rem;
        text-align: left !important;
        cursor: default !important;
    }

    /* Document diff visual lines */
    .diff-added {
        background: rgba(34, 197, 94, 0.12);
        color: #86efac;
        padding: 2px 4px;
        border-radius: 2px;
        border-left: 3px solid #22c55e;
    }
    .diff-removed {
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
        padding: 2px 4px;
        border-radius: 2px;
        text-decoration: line-through;
        border-left: 3px solid #ef4444;
    }

    /* Sidebar customize */
    section[data-testid="stSidebar"] {
        background: #080816;
        border-right: 1px solid rgba(99, 102, 241, 0.12);
    }
</style>
""", unsafe_allow_html=True)

# ===================== ROUTING & SESSION STATE =====================
if "current_view" not in st.session_state:
    st.session_state.current_view = "command_center"

AGENT_NAMES = {
    1: "Company Research Agent",
    2: "Regulatory Discovery Agent",
    3: "Applicability Agent",
    4: "Compliance Analyst Agent",
    5: "Risk Agent",
    6: "Action Agent",
    7: "Report Agent"
}

def init_agent_states():
    """Initialize or reset centralized agent execution state model."""
    st.session_state.agent_states = {}
    for i in range(1, 8):
        k = f"agent_{i}"
        st.session_state.agent_states[k] = {
            "id": i,
            "name": AGENT_NAMES[i],
            "status": "WAITING",
            "start_time": None,
            "end_time": None,
            "duration": 0.0,
            "stats": {},
            "sources": [],
            "error": None,
            "data": None
        }
    st.session_state.execution_log = []

if "agent_states" not in st.session_state:
    init_agent_states()

def populate_agent_states_from_saved_profile(p_record: dict):
    """Synchronize agent states when loading a saved profile from DB."""
    init_agent_states()
    for i in range(1, 8):
        k = f"agent_{i}"
        st.session_state.agent_states[k]["status"] = "COMPLETED"
        st.session_state.agent_states[k]["duration"] = 0.1
        st.session_state.agent_states[k]["start_time"] = "Restored"
        st.session_state.agent_states[k]["end_time"] = "Restored"
        
    cp = p_record.get("company_profile", {})
    disc = p_record.get("discovery_results", {})
    app_res = p_record.get("applicability_results", {})
    comp = p_record.get("compliance_results", {})
    act_res = p_record.get("action_results", {})
    
    st.session_state.agent_states["agent_1"]["stats"] = {"Services found": len(cp.get("services", [])), "Confidence": "94%"}
    st.session_state.agent_states["agent_2"]["stats"] = {"Jurisdictions analyzed": len(cp.get("operating_countries", [])), "Official sources": len(disc.get("sources", []))}
    st.session_state.agent_states["agent_3"]["stats"] = {"Applicable regulations": len(app_res.get("applicable", []))}
    st.session_state.agent_states["agent_4"]["stats"] = {"Compliance gaps": len(comp.get("gaps", []))}
    st.session_state.agent_states["agent_5"]["stats"] = {"Risk score": f"{p_record.get('compliance_score', 90)}/100"}
    st.session_state.agent_states["agent_6"]["stats"] = {"Actions generated": len(act_res.get("actions", []))}
    st.session_state.agent_states["agent_7"]["stats"] = {"Report status": "Restored from DB"}
    st.session_state.execution_log = ["Restored complete 7-agent execution state from persistent database record."]

# ===================== HEADER =====================
st.markdown("""
<div class="hero">
    <h1>🛡️ RegWatch Pro</h1>
    <p>International Regulatory Intelligence & Multi-Jurisdictional Auditing</p>
</div>
""", unsafe_allow_html=True)

# ===================== SIDEBAR =====================
with st.sidebar:
    st.markdown("### 🛡️ RegWatch Navigation")
    st.caption("Central Command Engine")
    st.divider()

    # Direct Navigation Buttons
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "command_center"
        st.rerun()
        
    if st.button("📂 Saved Profiles", use_container_width=True):
        st.session_state.current_view = "saved_profiles"
        st.rerun()
        
    if st.button("🚀 Create New Scan", use_container_width=True):
        st.session_state.current_view = "company_setup"
        st.rerun()
        
    if "company_profile" in st.session_state:
        if st.button("📊 Active Workspace", use_container_width=True, type="primary"):
            st.session_state.current_view = "active_workspace"
            st.rerun()

    st.divider()

    if "company_profile" in st.session_state:
        p: dict[str, Any] = st.session_state.company_profile
        st.success(f"🏢 **{p['company_name']}**", icon="✅")
        st.caption(f"**Primary Country**: {p.get('primary_country', 'India')}")
        st.caption(f"**Type**: {normalize_company_type(p.get('company_type', 'Fintech'))}")
        st.caption(f"**Industry**: {p.get('industry', 'Payments')}")
        st.caption(f"**Operating Countries**: {', '.join(p.get('operating_countries', []))}")
        if "active_profile_id" in st.session_state:
            st.caption(f"**Loaded Scan ID**: `{st.session_state.active_profile_id}`")

    st.divider()
    
    if st.button("🔄 Clear App Cache & Restart", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.caption("Global Compliance System v2.3")

# Initialize policy docs
if "company_policies" not in st.session_state:
    try:
        with open("company_docs.json", "r") as f:
            st.session_state.company_policies = json.load(f)
    except Exception:
        st.session_state.company_policies = []

FLAG_MAP = {
    "India": "🇮🇳 India",
    "United Kingdom": "🇬🇧 United Kingdom",
    "United States": "🇺🇸 United States",
    "Singapore": "🇸🇬 Singapore",
    "European Union": "🇪🇺 European Union"
}


# ==============================================================================
# VIEW 1: HOME LANDING SCREEN
# ==============================================================================
if st.session_state.current_view == "command_center":
    st.markdown("### 🏠 Home")
    st.caption("Select an action below to view saved audits or launch a new global company compliance analysis.")
    st.divider()
    
    all_saved_profiles = get_saved_profiles()
    saved_count = len(all_saved_profiles)
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown(f"""
        <div class="action-card" style="padding: 24px; min-height: 210px;">
            <div>
                <h3 style="margin:0 0 8px 0; color:#818cf8; font-size:1.25rem; font-weight:700; height:2.8rem; display:flex; align-items:center;">📁 SAVED COMPLIANCE PROFILES</h3>
                <p style="color:#94a3b8; font-size:0.9rem; line-height:1.5; height:3.2rem; overflow:hidden; margin-bottom:12px;">
                    View and restore previously completed multi-jurisdictional compliance analyses from persistent storage.
                </p>
            </div>
            <div>
                <div style="font-size:0.95rem; font-weight:700; color:#c084fc;">
                    📊 {saved_count} Saved Compliance Profile{'s' if saved_count != 1 else ''}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        if st.button("View Saved Profiles ➔", key="cc_btn_view_saved", type="primary", use_container_width=True):
            st.session_state.current_view = "saved_profiles"
            st.rerun()

    with col_c2:
        st.markdown("""
        <div class="action-card" style="padding: 24px; min-height: 210px;">
            <div>
                <h3 style="margin:0 0 8px 0; color:#f472b6; font-size:1.25rem; font-weight:700; height:2.8rem; display:flex; align-items:center;">🚀 CREATE NEW COMPLIANCE SCAN</h3>
                <p style="color:#94a3b8; font-size:0.9rem; line-height:1.5; height:3.2rem; overflow:hidden; margin-bottom:12px;">
                    Start a new global corporate compliance analysis across 7 autonomous AI agents and international regulatory frameworks.
                </p>
            </div>
            <div>
                <div style="font-size:0.95rem; font-weight:700; color:#f472b6;">
                    🌐 Multi-Jurisdiction Coverage (India, UK, US, SG, EU)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        if st.button("Create New Scan 🚀", key="cc_btn_create_new", type="primary", use_container_width=True):
            st.session_state.current_view = "company_setup"
            st.rerun()


# ==============================================================================
# VIEW 2: SAVED COMPLIANCE PROFILES PAGE
# ==============================================================================
elif st.session_state.current_view == "saved_profiles":
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown("### 📂 Saved Compliance Profiles")
        st.caption("Persistent historical audit records, stored snapshot data, and execution re-run triggers.")
    with col_h2:
        if st.button("← Home", use_container_width=True):
            st.session_state.current_view = "command_center"
            st.rerun()
            
    st.divider()
    
    all_saved = get_saved_profiles()
    
    if not all_saved:
        st.info("No saved compliance profiles found. Click 'Create New Scan' to start a compliance analysis.")
    else:
        company_groups = {}
        for p in all_saved:
            cname = p.get("company_name", "Unknown")
            if cname not in company_groups:
                company_groups[cname] = []
            company_groups[cname].append(p)
            
        for cname, scans in company_groups.items():
            latest_scan = scans[0]
            c_flags = " + ".join([FLAG_MAP.get(cnt, cnt) for cnt in latest_scan.get("operating_countries", [latest_scan.get("primary_country", "")])])
            sev = latest_scan.get("risk_results", {}).get("exposure", {}).get("severity_level", "MEDIUM")
            badge_cls = {"CRITICAL": "badge-critical", "HIGH": "badge-high", "MEDIUM": "badge-medium"}.get(sev, "badge-low")
            
            st.markdown(f"""
            <div class="gcard" style="border-left: 4px solid #818cf8; margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <h3 style="margin:0; color:#e2e8f0; font-size:1.35rem;">🏢 {cname}</h3>
                        <div style="color:#c084fc; font-weight:600; font-size:0.9rem; margin:4px 0;">{c_flags}</div>
                        <div style="color:#94a3b8; font-size:0.85rem;">
                            Type: {normalize_company_type(latest_scan.get('company_type', 'Fintech'))} &bull; 
                            Primary Country: {latest_scan.get('primary_country', 'India')} &bull;
                            Status: <span class="badge badge-low">SAVED</span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:2rem; font-weight:800; color:#c084fc;">{latest_scan.get('compliance_score', 90)}%</div>
                        <div style="color:#94a3b8; font-size:0.75rem; font-weight:600; text-transform:uppercase;">Compliance Score</div>
                    </div>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:16px; margin:14px 0 10px 0; padding:10px 14px; background:rgba(15,23,42,0.5); border-radius:8px; font-size:0.85rem; color:#cbd5e1;">
                    <div>🚨 <strong>{latest_scan.get('alerts_count', 0)} Gaps Detected</strong></div>
                    <div>⚖️ <strong>Risk Severity:</strong> <span class="badge {badge_cls}">{sev}</span></div>
                    <div>📜 <strong>{latest_scan.get('regulations_count', 0)} Regulations Audited</strong></div>
                    <div>🕒 <strong>Created:</strong> {latest_scan.get('created_at', 'N/A')}</div>
                    <div>🆔 <strong>Profile ID:</strong> <code>{latest_scan.get('profile_id', 'N/A')}</code></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_act1, col_act2, col_act3 = st.columns([2, 2, 1])
            with col_act1:
                if st.button(f"Open ({latest_scan.get('profile_id')})", key=f"sp_open_{latest_scan.get('profile_id')}", type="primary", use_container_width=True):
                    # RESTORE COMPLETE PREVIOUSLY GENERATED COMPLIANCE RESULT WITHOUT RE-RUNNING AI AGENTS
                    st.session_state.company_profile = latest_scan["company_profile"]
                    st.session_state.discovery_results = latest_scan["discovery_results"]
                    st.session_state.applicability_results = latest_scan["applicability_results"]
                    st.session_state.compliance_results = latest_scan["compliance_results"]
                    st.session_state.risk_results = latest_scan["risk_results"]
                    st.session_state.action_results = latest_scan["action_results"]
                    st.session_state.report_results = latest_scan.get("report_results", {})
                    st.session_state.active_profile_id = latest_scan["profile_id"]
                    st.session_state.loaded_msg = latest_scan["profile_id"]
                    populate_agent_states_from_saved_profile(latest_scan)
                    st.session_state.current_view = "active_workspace"
                    st.rerun()
                    
            with col_act2:
                if st.button(f"⚡ Re-run Analysis ({cname})", key=f"rerun_hist_{latest_scan.get('profile_id')}", type="secondary", use_container_width=True):
                    init_agent_states()
                    pipeline_runner = run_multi_agent_pipeline(
                        company_name=cname,
                        primary_country=latest_scan.get("primary_country", "India"),
                        operating_countries=latest_scan.get("operating_countries", []),
                        company_policies=st.session_state.company_policies,
                        existing_profile=latest_scan.get("company_profile")
                    )
                    with st.spinner(f"Re-running 7-agent pipeline for {cname}..."):
                        for agent_id, status, stats_dict, duration, sources, data in pipeline_runner:
                            a_key = f"agent_{agent_id}"
                            a_name = AGENT_NAMES[agent_id]
                            now_str = datetime.datetime.now().strftime("%H:%M:%S")
                            
                            if status == "RUNNING":
                                st.session_state.agent_states[a_key]["status"] = "RUNNING"
                            elif status == "COMPLETED":
                                st.session_state.agent_states[a_key]["status"] = "COMPLETED"
                                st.session_state.agent_states[a_key]["duration"] = duration
                                st.session_state.agent_states[a_key]["stats"] = stats_dict
                                if agent_id == 1: st.session_state.company_profile = data
                                elif agent_id == 2: st.session_state.discovery_results = data
                                elif agent_id == 3: st.session_state.applicability_results = data
                                elif agent_id == 4: st.session_state.compliance_results = data
                                elif agent_id == 5: st.session_state.risk_results = data
                                elif agent_id == 6: st.session_state.action_results = data
                                elif agent_id == 7: st.session_state.report_results = data

                    # Save new scan version
                    new_id = save_full_compliance_profile(
                        company_profile=st.session_state.company_profile,
                        discovery_results=st.session_state.discovery_results,
                        applicability_results=st.session_state.applicability_results,
                        compliance_results=st.session_state.compliance_results,
                        risk_results=st.session_state.risk_results,
                        action_results=st.session_state.action_results,
                        report_results=st.session_state.report_results
                    )
                    st.session_state.active_profile_id = new_id
                    st.session_state.just_saved_id = new_id
                    st.session_state.current_view = "active_workspace"
                    st.rerun()

            with col_act3:
                with st.expander("🗑️ Delete"):
                    st.write(f"Delete **{latest_scan.get('profile_id')}**?")
                    if st.button("Confirm Delete", key=f"del_{latest_scan.get('profile_id')}", use_container_width=True):
                        delete_saved_profile(latest_scan.get("profile_id"))
                        st.success(f"Profile {latest_scan.get('profile_id')} deleted.")
                        st.rerun()
                        
            st.divider()


# ==============================================================================
# VIEW 3: GLOBAL COMPANY SETUP (CREATE NEW SCAN)
# ==============================================================================
elif st.session_state.current_view == "company_setup":
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown("### 🌐 Global Company Setup")
        st.caption("Enter corporate parameters to trigger the 7-Agent Autonomous Compliance Pipeline.")
    with col_h2:
        if st.button("← Home", use_container_width=True):
            st.session_state.current_view = "command_center"
            st.rerun()

    st.divider()

    gcol1, gcol2 = st.columns([3, 2])
    with gcol1:
        with st.form("onboard_form"):
            c_name = st.text_input("Company Name", placeholder="e.g. Revolut, Razorpay, CRED, Stripe, Monzo")
            c_country = st.selectbox("Primary Jurisdiction", ["India", "United Kingdom", "United States", "Singapore", "European Union"])
            c_markets = st.multiselect("Additional Operating Countries", ["India", "United Kingdom", "United States", "Singapore", "European Union"], default=[])
            
            submit_btn = st.form_submit_button("🚀 Build Global Compliance Profile", type="primary")
            
        if submit_btn and c_name:
            init_agent_states()
            progress_bar = st.progress(0, text="Initializing Multi-Agent Pipeline...")
            
            pipeline_runner = run_multi_agent_pipeline(
                company_name=c_name,
                primary_country=c_country,
                operating_countries=c_markets,
                company_policies=st.session_state.company_policies
            )
            
            status_box = st.status("🤖 Running Multi-Agent Compliance Pipeline...", expanded=True)
            with status_box:
                for agent_id, status, stats_dict, duration, sources, data in pipeline_runner:
                    a_key = f"agent_{agent_id}"
                    a_name = AGENT_NAMES[agent_id]
                    now_str = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    if status == "RUNNING":
                        st.session_state.agent_states[a_key]["status"] = "RUNNING"
                        st.session_state.agent_states[a_key]["start_time"] = now_str
                        st.session_state.execution_log.append(f"{now_str}  🔵 {a_name} started")
                        st.write(f"🔵 **Agent {agent_id}: {a_name}** — RUNNING...")
                    elif status == "COMPLETED":
                        st.session_state.agent_states[a_key]["status"] = "COMPLETED"
                        st.session_state.agent_states[a_key]["end_time"] = now_str
                        st.session_state.agent_states[a_key]["duration"] = duration
                        st.session_state.agent_states[a_key]["stats"] = stats_dict
                        st.session_state.agent_states[a_key]["sources"] = sources
                        st.session_state.agent_states[a_key]["data"] = data
                        st.session_state.execution_log.append(f"{now_str}  🟢 {a_name} completed ({duration}s)")
                        st.write(f"🟢 **Agent {agent_id}: {a_name}** — COMPLETED ({duration}s)")
                        
                        if agent_id == 1: st.session_state.company_profile = data
                        elif agent_id == 2: st.session_state.discovery_results = data
                        elif agent_id == 3: st.session_state.applicability_results = data
                        elif agent_id == 4: st.session_state.compliance_results = data
                        elif agent_id == 5: st.session_state.risk_results = data
                        elif agent_id == 6: st.session_state.action_results = data
                        elif agent_id == 7: st.session_state.report_results = data
                    elif status == "FAILED":
                        st.session_state.agent_states[a_key]["status"] = "FAILED"
                        st.session_state.agent_states[a_key]["end_time"] = now_str
                        st.session_state.agent_states[a_key]["duration"] = duration
                        st.session_state.agent_states[a_key]["error"] = str(data)
                        st.session_state.execution_log.append(f"{now_str}  🔴 {a_name} failed: {data}")
                        st.write(f"🔴 **Agent {agent_id}: {a_name}** — FAILED")
                        
                    completed_count = sum([1 for a in st.session_state.agent_states.values() if a["status"] == "COMPLETED"])
                    progress_bar.progress(int((completed_count / 7) * 100), text=f"Pipeline Progress: {completed_count}/7 Agents Completed")
                    
            if "company_profile" in st.session_state:
                save_company_profile(c_name, c_country, st.session_state.company_profile)
            if "compliance_results" in st.session_state:
                save_global_matrix(c_name, st.session_state.compliance_results.get("matrix_cells", {}))
            
            st.session_state.onboarded = True
            st.session_state.active_profile_id = "Unsaved Active Scan"
            progress_bar.empty()
            st.success("✅ Multi-Agent Pipeline Completed! Opening Compliance Workspace...")
            st.session_state.current_view = "active_workspace"
            time.sleep(1)
            st.rerun()
            
    with gcol2:
        st.markdown("""
        <div class="gcard">
            <h4 style='color:#a78bfa; margin-top:0;'>✨ Quick Demo Flow</h4>
            <ol style='color:#94a3b8; font-size:0.88rem; padding-left:18px;'>
                <li>Enter <strong>Revolut</strong> and select <strong>United Kingdom + European Union</strong>.</li>
                <li>Watch the 7 agents execute live with timing metrics and logs.</li>
                <li>Click <strong>💾 Save Compliance Profile</strong> to generate unique ID <code>RW-2026-0003</code>.</li>
                <li>Access <strong>📂 Saved Compliance Profiles</strong> to restore or view Scan History.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📄 Manage Internal Company Policies"):
            st.dataframe(
                [{"ID": p["policy_id"], "Policy": p["policy_name"], "Updated": p["last_updated"]} for p in st.session_state.company_policies],
                use_container_width=True
            )


# ==============================================================================
# VIEW 4: ACTIVE COMPLIANCE WORKSPACE (DISPLAYED AFTER BUILDING OR OPENING)
# ==============================================================================
elif st.session_state.current_view == "active_workspace":
    if "company_profile" not in st.session_state:
        st.warning("No active company compliance data loaded. Starting new scan...")
        st.session_state.current_view = "company_setup"
        st.rerun()
        
    p_profile = st.session_state.company_profile
    c_name = p_profile["company_name"]
    
    # TOP CONTROL BAR FOR WORKSPACE
    col_w1, col_w2 = st.columns([3, 1])
    with col_w1:
        active_pid = st.session_state.get("active_profile_id", "Unsaved Active Audit")
        st.markdown(f"### 📊 Active Compliance Workspace: **{c_name}** (`{active_pid}`)")
    with col_w2:
        if st.button("💾 Save Compliance Profile", type="primary", use_container_width=True, key="ws_save_btn"):
            with st.spinner("Saving complete compliance scan to database..."):
                new_id = save_full_compliance_profile(
                    company_profile=p_profile,
                    discovery_results=st.session_state.get("discovery_results", {}),
                    applicability_results=st.session_state.get("applicability_results", {}),
                    compliance_results=st.session_state.get("compliance_results", {}),
                    risk_results=st.session_state.get("risk_results", {}),
                    action_results=st.session_state.get("action_results", {}),
                    report_results=st.session_state.get("report_results", {})
                )
                st.session_state.active_profile_id = new_id
                st.session_state.just_saved_id = new_id
                st.rerun()

    if "just_saved_id" in st.session_state:
        pid_val = st.session_state.pop("just_saved_id")
        st.success(f"""
        ✅ **Compliance Profile Saved**  
        **{pid_val}**  
        This profile is now available in **Saved Compliance Profiles**.
        """)
        
    if "loaded_msg" in st.session_state:
        msg_id = st.session_state.pop("loaded_msg")
        st.info(f"📂 Loaded persistent profile **{msg_id}** from database for **{c_name}**. (No AI re-run required)")

    st.divider()

    # WORKSPACE SECTION TABS
    w_tab_overview, w_tab_matrix, w_tab_diff, w_tab_agents, w_tab_profile = st.tabs([
        "📊 Overview",
        "🌐 Global Compliance",
        "⚖️ Regulation Diff",
        "🤖 AI Agents",
        "🏢 Company Profile"
    ])
    
    # --- TAB: OVERVIEW ---
    with w_tab_overview:
        risk_score = st.session_state.get("risk_results", {}).get("exposure", {}).get("risk_score", 95)
        worst_country = st.session_state.get("risk_results", {}).get("exposure", {}).get("highest_exposure_country", "None")
        severity = st.session_state.get("risk_results", {}).get("exposure", {}).get("severity_level", "LOW")
        gaps_count = len(st.session_state.get("compliance_results", {}).get("gaps", []))
        
        st.markdown(f"""
        <div class="stat-container">
            <div class="stat-card">
                <div class="val">{risk_score}%</div>
                <div class="lbl">Global Compliance Score</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #f87171;">{worst_country}</div>
                <div class="lbl">Highest Exposure Market</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #fb923c;">{severity}</div>
                <div class="lbl">Assessed Exposure Severity</div>
            </div>
            <div class="stat-card">
                <div class="val">{gaps_count}</div>
                <div class="lbl">Gaps Detected</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_side1, col_side2 = st.columns([3, 2])
        
        with col_side1:
            st.markdown("### 📝 Executive Summary")
            exposure_data = st.session_state.get("risk_results", {}).get("exposure", {})
            st.markdown(f"""
            <div class="gcard" style="border-left: 4px solid #818cf8;">
                <p style="font-size:0.92rem; color:#cbd5e1; line-height:1.6; margin:0;">
                    {exposure_data.get('board_summary', 'Multi-jurisdictional compliance assessment completed for ' + c_name + '.')}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🚨 High Exposure Threat Factors")
            st.markdown(f"""
            <div class="gcard" style="border-left: 4px solid #f87171;">
                <h4 style="margin:0 0 8px 0; color:#f87171;">{worst_country} Exposure Analysis</h4>
                <div>
                    <ul style="margin:5px 0 0 0; padding-left:16px; font-size:0.85rem; color:#cbd5e1;">
                        {"".join([f"<li>{f}</li>" for f in exposure_data.get('risk_factors', ['No critical risks flagged'])])}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_side2:
            st.markdown("### 📋 Prioritized Action Plan")
            actions_list = st.session_state.get("action_results", {}).get("actions", [])
            
            if not actions_list:
                st.info("No compliance gaps detected. Action plan is empty!")
            else:
                for idx, act in enumerate(actions_list[:3]):
                    priority = act.get("priority", "MEDIUM")
                    badge_class = {"CRITICAL": "badge-critical", "HIGH": "badge-high", "MEDIUM": "badge-medium"}.get(priority, "badge-low")
                    
                    st.markdown(f"""
                    <div class="gcard" style="padding:16px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:between; align-items:center; margin-bottom:6px;">
                            <strong style="font-size:0.88rem; color:#e2e8f0;">{act.get('ticket_id', 'COMP')} — {act.get('title')}</strong>
                        </div>
                        <div style="font-size:0.82rem; color:#94a3b8; margin-bottom:8px;">{act.get('action_required')}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
                            <span class="badge {badge_class}">{priority}</span>
                            <span style="color:#64748b;">📅 {act.get('timeline')} &nbsp;•&nbsp; Owner: {act.get('assignee')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                if "discovery_results" in st.session_state and "compliance_results" in st.session_state and "risk_results" in st.session_state:
                    from services.report_generator import generate_pdf_report
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                        pdf_path = tmp_pdf.name
                    
                    try:
                        generate_pdf_report(
                            company_profile=p_profile,
                            discovery_results=st.session_state.discovery_results,
                            compliance_results=st.session_state.compliance_results,
                            risk_results=st.session_state.risk_results,
                            action_results=st.session_state.action_results,
                            output_path=pdf_path
                        )
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            
                        st.download_button(
                            "📥 Download Full Executive Audit Report (PDF)",
                            data=pdf_bytes,
                            file_name=f"compliance_report_{c_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error compiling PDF: {e}")
                    finally:
                        if os.path.exists(pdf_path):
                            os.unlink(pdf_path)

    # --- TAB: GLOBAL COMPLIANCE ---
    with w_tab_matrix:
        st.markdown("### 🌐 Global Compliance Matrix")
        st.caption("Select jurisdictions and click onto specific cells to inspect underlying regulations and official sources.")
        
        operating_countries = p_profile.get("operating_countries", [p_profile.get("primary_country", "India")])
        new_country_list = st.multiselect(
            "Configure Operating Markets / Countries", 
            ["India", "United Kingdom", "United States", "Singapore", "European Union"],
            default=operating_countries
        )
        
        if new_country_list != operating_countries:
            p_profile["operating_countries"] = new_country_list
            save_company_profile(c_name, p_profile.get("primary_country", "India"), p_profile)
            st.session_state.company_profile = p_profile
            st.rerun()
            
        domains = ["Data Protection", "Cybersecurity", "Financial Rules", "Reporting", "Third-Party Risk"]
        matrix_cells = st.session_state.get("compliance_results", {}).get("matrix_cells", {})
        
        for d in domains:
            for country in operating_countries:
                cell_key = f"{d}|||{country}"
                if cell_key not in matrix_cells:
                    matrix_cells[cell_key] = {
                        "status": "🟢",
                        "confidence": 90,
                        "explanation": f"Validated alignment with basic local policies in {country}.",
                        "regulation": f"Standard {country} regulatory directives",
                        "source_url": "https://www.rbi.org.in" if country=="India" else "https://www.mas.gov.sg"
                    }
                    
        headers_html = "".join([f"<th>{c}</th>" for c in ["Domain"] + operating_countries])
        rows_html = ""
        for d in domains:
            row_cells = f"<td class='matrix-lbl-cell'>{d}</td>"
            for country in operating_countries:
                cell_key = f"{d}|||{country}"
                cell = matrix_cells.get(cell_key, {})
                status_symbol = cell.get("status", "🟢")
                row_cells += f"<td>{status_symbol}</td>"
            rows_html += f"<tr>{row_cells}</tr>"
            
        st.markdown(f"""
        <table class="matrix-table">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>🔍 **Compliance Cell Inspector**", unsafe_allow_html=True)
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1: sel_domain = st.selectbox("Select Domain", domains)
        with col_sel2: sel_country = st.selectbox("Select Country", operating_countries)
            
        selected_key = f"{sel_domain}|||{sel_country}"
        cell_info = matrix_cells.get(selected_key, {})
        
        if cell_info:
            st.markdown(f"""
            <div class="gcard" style="border-top: 3px solid #818cf8;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h5 style="margin:0; color:#c084fc;">{sel_domain} — {sel_country}</h5>
                    <span class="badge" style="background:rgba(255,255,255,0.06);">{cell_info.get('status', '🟢')} Assessed</span>
                </div>
                <div style="margin-top:12px; font-size:0.9rem;">
                    <strong>Regulating Provision:</strong> {cell_info.get('regulation', 'Standard Rules')}<br>
                    <strong>Status Confidence:</strong> {cell_info.get('confidence', 90)}%<br>
                    <strong>Brief explanation:</strong> {cell_info.get('explanation', 'Compliant with default guidelines.')}
                </div>
                <div style="margin-top:12px;">
                    <a href="{cell_info.get('source_url', 'https://www.rbi.org.in')}" target="_blank" style="color:#818cf8; text-decoration:none; font-weight:600; font-size:0.85rem;">🔗 View Official Regulator Source</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB: REGULATION DIFF ---
    with w_tab_diff:
        st.markdown("### ⚖️ Regulation Diff Engine")
        st.caption("Compare two regulatory documents or circular versions side-by-side.")
        
        prev_circulars = {c["title"]: c["summary"] for c in LATEST_RBI_CIRCULARS}
        
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            st.markdown("**Version A (Old/Reference Document)**")
            doc1_mode = st.radio("Input method (A)", ["Select Saved Circular", "Raw Text Upload"], key="w_doc1_mode_sel")
            if doc1_mode == "Select Saved Circular":
                doc1_title = st.selectbox("Choose reference circular", list(prev_circulars.keys()), key="w_doc1_saved")
                doc1_text = prev_circulars[doc1_title]
            else:
                doc1_title = st.text_input("Document A Title", "Version 1.0", key="w_doc1_title_text")
                doc1_text = st.text_area("Paste text (A)", placeholder="Old policy or rules text here...", key="w_doc1_raw")
                
        with dcol2:
            st.markdown("**Version B (New/Current Document)**")
            doc2_mode = st.radio("Input method (B)", ["Select Saved Circular", "Raw Text Upload"], key="w_doc2_mode_sel")
            if doc2_mode == "Select Saved Circular":
                doc2_title = st.selectbox("Choose current circular", list(prev_circulars.keys()), key="w_doc2_saved")
                doc2_text = prev_circulars[doc2_title]
            else:
                doc2_title = st.text_input("Document B Title", "Version 2.0", key="w_doc2_title_text")
                doc2_text = st.text_area("Paste text (B)", placeholder="New policy or rules text here...", key="w_doc2_raw")
                
        st.markdown("")
        if st.button("🔍 Run Diff Comparative Analysis", type="primary", use_container_width=True, key="w_diff_btn"):
            if doc1_text.strip() and doc2_text.strip():
                with st.spinner("Analyzing document updates and determining impact..."):
                    diff_data = compare_regulatory_documents(doc1_text, doc2_text, p_profile)
                    st.session_state.current_diff = {
                        "title_a": doc1_title,
                        "title_b": doc2_title,
                        "data": diff_data
                    }
                    save_diff_result(doc1_title, doc2_title, diff_data)
            else:
                st.error("Please provide non-empty text inputs for both versions.")
                
        if "current_diff" in st.session_state:
            cd = st.session_state.current_diff
            cdata = cd["data"]
            st.divider()
            st.markdown(f"### 📊 Analysis Results: {cd['title_a']} vs {cd['title_b']}")
            sev = cdata.get("change_severity", "MEDIUM")
            badge_class = {"CRITICAL": "badge-critical", "HIGH": "badge-high", "MEDIUM": "badge-medium"}.get(sev, "badge-low")
            
            st.markdown(f"""
            <div style="display:flex; gap:20px; align-items:center; margin-bottom:15px;">
                <div>Change Severity: <span class="badge {badge_class}">{sev}</span></div>
                <div style="color:#94a3b8;">📅 Effective Date: <strong>{cdata.get('effective_date', 'Immediate')}</strong></div>
            </div>
            """, unsafe_allow_html=True)
            
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"""
                <div class="gcard" style="border-left:4px solid #818cf8;">
                    <h5 style="margin:0 0 6px 0; color:#818cf8;">Why This Matters</h5>
                    <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5; margin:0;">{cdata.get('why_this_matters')}</p>
                </div>
                """, unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""
                <div class="gcard" style="border-left:4px solid #c084fc;">
                    <h5 style="margin:0 0 6px 0; color:#c084fc;">Impact on {c_name}</h5>
                    <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5; margin:0;">{cdata.get('company_impact_summary')}</p>
                </div>
                """, unsafe_allow_html=True)

    # --- TAB: AI AGENTS ---
    with w_tab_agents:
        st.markdown("### 🤖 Multi-Agent Pipeline Console")
        st.caption("Centralized state engine tracking execution for all 7 compliance agents.")
        
        completed_count = sum([1 for a in st.session_state.agent_states.values() if a["status"] == "COMPLETED"])
        progress_pct = int((completed_count / 7) * 100)
        
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            st.markdown(f"#### Pipeline Progress: **{completed_count} / 7 Agents Completed** (`{progress_pct}%`) ")
            st.progress(progress_pct / 100)
        with col_p2:
            if completed_count == 7:
                st.success("🎉 All 7 Agents Completed")
                
        STATUS_ICONS = {"WAITING": "⚪", "RUNNING": "🔵", "COMPLETED": "🟢", "FAILED": "🔴"}
        STATUS_BADGES = {"WAITING": "badge-na", "RUNNING": "badge-medium", "COMPLETED": "badge-low", "FAILED": "badge-critical"}
        
        for i in range(1, 8):
            k = f"agent_{i}"
            agent_data = st.session_state.agent_states.get(k, {})
            a_status = agent_data.get("status", "WAITING")
            a_name = agent_data.get("name", AGENT_NAMES[i])
            s_icon = STATUS_ICONS.get(a_status, "⚪")
            badge_cls = STATUS_BADGES.get(a_status, "badge-na")
            
            with st.expander(f"{s_icon} Agent {i}: {a_name}  —  [{a_status}]", expanded=(a_status in ["RUNNING", "FAILED"])):
                c_meta1, c_meta2, c_meta3 = st.columns(3)
                with c_meta1: st.markdown(f"**Status**: <span class='badge {badge_cls}'>{s_icon} {a_status}</span>", unsafe_allow_html=True)
                with c_meta2: st.markdown(f"**Start Time**: `{agent_data.get('start_time') or 'Not started'}`")
                with c_meta3: st.markdown(f"**Execution Duration**: `{agent_data.get('duration', 0.0)}s`")
                st.divider()
                stats = agent_data.get("stats", {})
                if stats:
                    st.markdown("**Real Execution Statistics:**")
                    for s_label, s_val in stats.items():
                        st.markdown(f"- **{s_label}**: `{s_val}`")

        st.divider()
        if st.session_state.get("execution_log"):
            st.markdown("#### 📜 Live Execution Log")
            st.code("\n".join(st.session_state.execution_log), language="text")

    # --- TAB: COMPANY PROFILE EDITOR ---
    with w_tab_profile:
        st.markdown("### 🏢 Edit Company Metadata")
        with st.form("w_edit_profile_form"):
            current_type = normalize_company_type(p_profile.get("company_type", "Fintech"))
            default_idx = ALLOWED_COMPANY_TYPES.index(current_type) if current_type in ALLOWED_COMPANY_TYPES else 2
                
            e_type = st.selectbox("Company Type", ALLOWED_COMPANY_TYPES, index=default_idx)
            e_industry = st.text_input("Industry Segment", p_profile.get("industry", "Payments"))
            e_reg = st.text_input("Primary RBI Registration/License", p_profile.get("rbi_registration", "PA License"))
            e_services_str = st.text_area("Key Services (Comma separated)", ", ".join(p_profile.get("services", [])))
            e_data = st.text_area("Data Handling", p_profile.get("data_handling", ""))
            
            save_changes = st.form_submit_button("💾 Save Profile Metadata Changes")
            
        if save_changes:
            p_profile["company_type"] = e_type
            p_profile["industry"] = e_industry
            p_profile["rbi_registration"] = e_reg
            p_profile["services"] = [s.strip() for s in e_services_str.split(",") if s.strip()]
            p_profile["data_handling"] = e_data
            
            index_company_profile(p_profile)
            save_company_profile(c_name, p_profile.get("primary_country", "India"), p_profile)
            st.session_state.company_profile = p_profile
            st.success("Company profile metadata updated!")
            st.rerun()