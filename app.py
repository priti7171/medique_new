"""
app.py
======
MediQueue – Hospital Patient Queue Management System
Department-Wise Doctor Availability, Triage, and Multi-Specialty Queue System.

DSA & SYSTEM ARCHITECTURE:
- Permanent Unique Patient IDs (MQ-YYYY-XXXXXX) with strict sequential SQLite counter.
- Department-Wise & Doctor-Wise Queue Numbers (e.g. CARD-001, ORTH-002, DENT-001).
- 15 Standard Hospital Departments with configurable administrative management.
- Multi-Doctor Database with Real-Time Availability (Available, On Leave, Fully Booked, Consulting).
- Min-Heap Priority Queue triage per doctor (Emergency Rank 1 Precedence + FIFO Token tie-breaking).
- Hash Maps (Dictionary O(1)) for instant Department & Doctor lookups.
- Linear Search O(n) & Binary Search O(log n) with step-by-step execution metrics.
- Bubble Sort O(n^2) & Insertion Sort O(n^2) workbench.
- Permanent Protected Patient Visit History Archive (Never deleted on queue completion).
- Cryptographic Staff Authentication (PBKDF2-HMAC-SHA256) & Full Audit Logs.
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Import custom DSA backend & SQLite Database manager
from queue_manager import Patient, HospitalQueueController, PriorityQueue, FIFOQueue
from search_sort import (
    linear_search_patients,
    binary_search_by_id,
    linear_search_doctors,
    binary_search_doctor_by_id,
    bubble_sort_patients,
    insertion_sort_patients,
    bubble_sort_doctors,
    insertion_sort_doctors
)
import db_manager

# Ensure database tables, counters, departments, and doctors are initialized
db_manager.init_db()

# Page configuration
st.set_page_config(
    page_title="MediQueue | Hospital Queue Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if "controller" not in st.session_state:
    st.session_state.controller = HospitalQueueController()

if "current_user" not in st.session_state:
    st.session_state.current_user = None  # None = Public Visitor, Dict = Authenticated Staff/Admin

if "selected_doc_cabin" not in st.session_state:
    st.session_state.selected_doc_cabin = "DOC001"

if "quick_book_dept" not in st.session_state:
    st.session_state.quick_book_dept = "DEP002"

if "quick_book_doc" not in st.session_state:
    st.session_state.quick_book_doc = "DOC001"

controller: HospitalQueueController = st.session_state.controller

# Image paths (Cross-platform Linux/Windows compatible)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HERO_IMG_PATH = os.path.join(BASE_DIR, "assets", "hospital_hero.jpg")
DOCTOR_IMG_PATH = os.path.join(BASE_DIR, "assets", "doctor_consulting.jpg")

# ==============================================================================
# CUSTOM CSS STYLING (Modern Professional Hospital Theme)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
        color: #0f172a;
    }

    /* Top Hero Header Card */
    .hero-container {
        background: linear-gradient(135deg, #042f2e 0%, #0f766e 50%, #0d9488 100%);
        border-radius: 20px;
        padding: 28px 34px;
        color: #ffffff;
        margin-bottom: 22px;
        box-shadow: 0 18px 38px -15px rgba(13, 148, 136, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.15);
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-size: 27px;
        font-weight: 800;
        letter-spacing: -0.7px;
        margin: 0;
        color: #ffffff;
    }
    .hero-tagline {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(8px);
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.4px;
        margin-top: 8px;
        color: #ccfbf1;
        border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .hero-desc {
        font-size: 14px;
        color: #e6fffa;
        margin: 8px 0 0 0;
        line-height: 1.5;
        max-width: 900px;
    }

    /* Modern Metric Cards */
    .metric-card {
        background: #ffffff;
        padding: 18px 20px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 6px 20px -5px rgba(15, 23, 42, 0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.25s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 28px -6px rgba(15, 23, 42, 0.10);
        border-color: #cbd5e1;
    }
    .metric-label {
        font-size: 11px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-num {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.1;
        margin-top: 4px;
    }
    .metric-icon-box {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }

    /* Status Badges */
    .badge-avail {
        background: #f0fdf4;
        color: #16a34a;
        border: 1px solid #bbf7d0;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-consulting {
        background: #f0f9ff;
        color: #0284c7;
        border: 1px solid #bae6fd;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-booked {
        background: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-leave {
        background: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-unavail {
        background: #f1f5f9;
        color: #64748b;
        border: 1px solid #cbd5e1;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-emergency {
        background: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-normal {
        background: #f0f9ff;
        color: #0284c7;
        border: 1px solid #bae6fd;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Doctor Card in Discovery */
    .doctor-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px -3px rgba(15, 23, 42, 0.05);
        transition: all 0.25s ease;
    }
    .doctor-card:hover {
        border-color: #0d9488;
        box-shadow: 0 8px 24px -4px rgba(13, 148, 136, 0.12);
        transform: translateY(-2px);
    }
    .doc-name {
        font-size: 18px;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
    }
    .doc-spec {
        font-size: 13px;
        font-weight: 600;
        color: #0f766e;
        margin: 2px 0 6px 0;
    }

    /* Doctor Desk Active Card */
    .desk-card-active {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        border-left: 6px solid #16a34a;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 20px -6px rgba(22, 163, 74, 0.15);
    }

    .next-up-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 20px -6px rgba(15, 23, 42, 0.06);
    }

    /* Patient Card in Queue */
    .patient-queue-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04);
        transition: all 0.2s ease;
    }
    .patient-queue-card-emergency {
        background: #fffafa;
        border: 1px solid #fecaca;
        border-left: 5px solid #dc2626;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 6px 16px -4px rgba(220, 38, 38, 0.08);
    }

    /* Modern Buttons */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        padding: 8px 18px;
        letter-spacing: 0.2px;
        transition: all 0.2s ease;
    }
    
    /* Sidebar Brand */
    .sidebar-brand {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
        padding: 16px;
        border-radius: 14px;
        color: white;
        text-align: center;
        margin-bottom: 14px;
        box-shadow: 0 6px 16px -4px rgba(13, 148, 136, 0.3);
    }
    
    .auth-badge {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 14px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# HELPER: STATUS BADGE RENDERER
# ==============================================================================
def render_status_badge(status: str) -> str:
    s = status.strip()
    if s == "Available":
        return "<span class='badge-avail'>🟢 Available</span>"
    elif s == "Currently Consulting":
        return "<span class='badge-consulting'>🩺 Consulting</span>"
    elif s == "Fully Booked":
        return "<span class='badge-booked'>⏳ Fully Booked</span>"
    elif s == "On Leave":
        return "<span class='badge-leave'>🔴 On Leave</span>"
    else:
        return f"<span class='badge-unavail'>⚪ {s}</span>"


# ==============================================================================
# SIDEBAR NAVIGATION & AUTHENTICATION
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <h2 style='color: #ffffff; margin: 0; font-size: 19px; font-weight: 800;'>🏥 MediQueue</h2>
        <p style='color: #ccfbf1; font-size: 11px; font-weight: 600; margin: 3px 0 0 0; letter-spacing: 0.5px;'>
            MULTI-SPECIALTY HOSPITAL QUEUE
        </p>
    </div>
    """, unsafe_allow_html=True)

    current_user = st.session_state.current_user
    if current_user:
        st.markdown(f"""
        <div class="auth-badge" style="border-left: 4px solid #16a34a;">
            <div style="font-weight: 700; color: #166534;">🟢 Authenticated Staff</div>
            <div style="color: #334155; margin-top: 2px;">👤 {current_user['full_name']}</div>
            <div style="color: #64748b; font-size: 11px;">Role: <strong>{current_user['role'].upper()}</strong></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Staff Logout", use_container_width=True):
            db_manager.log_audit_event(current_user['username'], "STAFF_LOGOUT", f"User '{current_user['username']}' logged out.")
            st.session_state.current_user = None
            st.toast("Logged out successfully!", icon="ℹ️")
            st.rerun()
    else:
        st.markdown("""
        <div class="auth-badge">
            <div style="font-weight: 600; color: #475569;">🔒 Patient / Public Mode</div>
            <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Log in as Staff/Admin for doctor desk, department config, and audit logs.</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🔑 Staff / Admin Login"):
            login_user = st.text_input("Username", key="sidebar_user", placeholder="admin or staff")
            login_pass = st.text_input("Password", type="password", key="sidebar_pass", placeholder="admin123 / staff123")
            
            if st.button("🔓 Login", type="primary", use_container_width=True):
                auth_result = db_manager.authenticate_staff(login_user, login_pass)
                if auth_result:
                    st.session_state.current_user = auth_result
                    st.toast(f"Welcome, {auth_result['full_name']}!", icon="👋")
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            st.caption("💡 Default demo: `admin` / `admin123`")

    st.markdown("---")

    nav_options = [
        "🏥 Dashboard",
        "🩺 Find a Doctor",
        "📝 Patient Registration",
        "📋 Department Queues",
        "👨‍⚕️ Doctor Cabin",
        "🔍 Search & Lookup",
        "📊 Sorting Workbench",
        "📜 Patient History"
    ]
    if current_user:
        nav_options.append("🏢 Admin: Depts & Doctors")
        nav_options.append("🛡️ Audit Logs & Backups")

    menu = st.radio("Navigation Menu", nav_options, index=0)

    st.markdown("---")

    # Live summary metrics
    metrics = controller.get_metrics()
    st.markdown("#### 🚦 Hospital Queue Status")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("⏳ Waiting", metrics['waiting'])
    with col_s2:
        st.metric("🚨 Emergency", metrics['emergency_waiting'])

    st.markdown(f"• **Departments Active:** `{metrics['total_departments']}`")
    st.markdown(f"• **Available Doctors:** `{metrics['doctors_available']}/{metrics['total_doctors']}`")

    st.markdown("---")

    if st.button("🔄 Reset Master Sample Data", use_container_width=True):
        actor_name = current_user['username'] if current_user else "System"
        db_manager.reset_database_to_sample(actor=actor_name)
        controller.refresh_from_storage()
        st.toast("Clean master sample records restored!", icon="🔄")
        time.sleep(0.4)
        st.rerun()

    st.markdown(
        "<div style='font-size: 11px; color: #94a3b8; text-align: center; margin-top: 15px;'>"
        "MediQueue Multi-Specialty • Min-Heap Triage</div>",
        unsafe_allow_html=True
    )


# ==============================================================================
# 1. HOSPITAL DASHBOARD
# ==============================================================================
if menu == "🏥 Dashboard":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">MediQueue – Hospital Patient Queue Management</h1>
        <div class="hero-tagline">✨ Multi-Department • Doctor-Wise Availability • Min-Heap Priority Triage</div>
        <p class="hero-desc">
            Next-generation healthcare patient flow management. Seamlessly routing outpatients across 15 hospital departments and multi-specialty doctors with permanent ID tracking and emergency precedence.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Hero visual
    if os.path.exists(HERO_IMG_PATH):
        col_img, col_hero_text = st.columns([1.4, 1])
        with col_img:
            st.image(HERO_IMG_PATH, use_container_width=True, caption="MediQueue Multi-Specialty Hospital Center")
        with col_hero_text:
            st.markdown("""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; height: 100%; box-shadow: 0 4px 14px rgba(0,0,0,0.04); display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin: 0 0 8px 0; color: #0f766e; font-size: 18px; font-weight: 800;">🏥 Automated Queue & Doctor Engine</h3>
                <p style="color: #475569; font-size: 13px; margin: 0 0 10px 0; line-height: 1.5;">
                    • <strong>Permanent Patient ID:</strong> <code>MQ-YYYY-XXXXXX</code> (Never reused)<br>
                    • <strong>Doctor Queue Number:</strong> <code>C-001</code>, <code>D-001</code>, <code>S-001</code><br>
                    • <strong>Min-Heap Priority Queue:</strong> Emergency patients (Rank 1) automatically precede Normal patients (Rank 2).
                </p>
                <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px 12px; border-radius: 8px;">
                    <span style="font-size: 12px; font-weight: 700; color: #166534;">🛡️ Complete Patient Privacy & History:</span>
                    <span style="font-size: 12px; color: #15803d;"><br>Historical records permanently archived in SQLite.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # 5 Key Metrics
    metrics = controller.get_metrics()
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">Departments</div>
                <div class="metric-num">{metrics['total_departments']}</div>
            </div>
            <div class="metric-icon-box" style="background:#e0f2fe; color:#0284c7;">🏢</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">Active Doctors</div>
                <div class="metric-num" style="color:#0f766e;">{metrics['doctors_available']}</div>
            </div>
            <div class="metric-icon-box" style="background:#ccfbf1; color:#0f766e;">👨‍⚕️</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">Patients Waiting</div>
                <div class="metric-num" style="color:#d97706;">{metrics['waiting']}</div>
            </div>
            <div class="metric-icon-box" style="background:#fef3c7; color:#d97706;">⏳</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">Emergency Cases</div>
                <div class="metric-num" style="color:#dc2626;">{metrics['emergency_waiting']}</div>
            </div>
            <div class="metric-icon-box" style="background:#fee2e2; color:#dc2626;">🚨</div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">Consulted Today</div>
                <div class="metric-num" style="color:#16a34a;">{metrics['consulted']}</div>
            </div>
            <div class="metric-icon-box" style="background:#dcfce7; color:#16a34a;">✅</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Department Quick Overview Grid
    st.markdown("### 🏢 Department-Wise Queue Status Overview")
    active_depts = db_manager.get_active_departments()
    
    col_d1, col_d2, col_d3 = st.columns(3)
    dept_cols = [col_d1, col_d2, col_d3]

    for idx, d in enumerate(active_depts[:9]):
        col = dept_cols[idx % 3]
        d_waiting = len(controller.get_waiting_patients_for_dept(d["dept_id"]))
        d_docs = len(db_manager.get_doctors_by_department(d["dept_id"]))
        with col:
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:14px 18px; margin-bottom:12px; box-shadow:0 3px 10px rgba(0,0,0,0.03);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; color:#0f766e; font-size:15px;">{d['dept_name']}</span>
                    <span style="background:#f1f5f9; color:#475569; font-weight:700; font-size:11px; padding:2px 8px; border-radius:12px;">{d['dept_code']}</span>
                </div>
                <div style="font-size:12px; color:#64748b; margin-top:3px;">📍 {d['floor_location']}</div>
                <div style="margin-top:8px; display:flex; justify-content:space-between; font-size:13px;">
                    <span>👨‍⚕️ <strong>{d_docs}</strong> Doctor(s)</span>
                    <span style="color:#d97706; font-weight:700;">⏳ <strong>{d_waiting}</strong> Waiting</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Global Live Queue Table (Privacy Safe)
    st.markdown("### 📋 Live Hospital Waiting Queue (Public Privacy Display)")
    st.caption("🔒 Patient Privacy: Public monitors show Token, Queue #, Permanent ID, Name, Department, Doctor, and Priority.")
    
    waiting_all = controller.get_waiting_patients()
    if waiting_all:
        table_rows = []
        for idx, p in enumerate(waiting_all, start=1):
            table_rows.append({
                "Queue Pos": f"#{idx}",
                "Queue No.": p.queue_number,
                "Patient ID": p.patient_id,
                "Patient Name": p.name,
                "Department": p.dept_name,
                "Doctor": p.doctor_name,
                "Room": p.room_number,
                "Priority": p.priority,
                "Slot Time": p.slot_time,
                "Status": p.status
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.info("The waiting queue is currently clear across all departments.")


# ==============================================================================
# 2. FIND A DOCTOR (PATIENT-FACING DISCOVERY)
# ==============================================================================
elif menu == "🩺 Find a Doctor":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Find a Doctor & Check Availability</h1>
        <div class="hero-tagline">🩺 Specialist Search • Real-Time Consultation Hours • Instant Slot Booking</div>
        <p class="hero-desc">
            Browse multi-specialty doctors across all hospital departments. Check real-time room availability, consultation schedules, and join the queue directly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_depts = db_manager.get_active_departments()
    dept_options = {d["dept_id"]: f"{d['dept_name']} ({d['dept_code']}) - {d['floor_location']}" for d in all_depts}
    
    c_f1, c_f2 = st.columns([1.5, 2])
    with c_f1:
        selected_dept_id = st.selectbox(
            "Select Department:",
            options=list(dept_options.keys()),
            format_func=lambda x: dept_options[x],
            index=1 if "DEP002" in dept_options else 0
        )
    with c_f2:
        search_kw = st.text_input("🔍 Search Doctor by Name or Specialization:", placeholder="e.g. Cardiologist, Dr. Anjali, Knee")

    # Get doctors for selected department
    dept_docs = db_manager.get_doctors_by_department(selected_dept_id)
    if search_kw.strip():
        dept_docs, _, _ = linear_search_doctors(dept_docs, search_kw, search_by="all")

    dept_obj = controller.departments_map.get(selected_dept_id, {})
    st.markdown(f"#### 🏥 {dept_obj.get('dept_name', 'Department')} Specialist Doctors ({len(dept_docs)} Found)")
    st.caption(f"📍 Location: {dept_obj.get('floor_location', '')} • {dept_obj.get('description', '')}")

    if not dept_docs:
        st.warning("No doctors found matching your criteria in this department.")
    else:
        for doc in dept_docs:
            doc_id = doc["doc_id"]
            avail_status, avail_msg, is_bookable = controller.get_doctor_availability_status(doc_id)
            status_badge_html = render_status_badge(avail_status)
            waiting_cnt = len(controller.get_waiting_patients_for_doctor(doc_id))
            
            with st.container():
                st.markdown(f"""
                <div class="doctor-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                        <div>
                            <h3 class="doc-name">{doc['name']}</h3>
                            <div class="doc-spec">{doc['specialization']} &nbsp;•&nbsp; <span style="color:#64748b; font-weight:500;">{doc['qualification']}</span></div>
                            <div style="font-size:13px; color:#475569; margin-top:4px;">
                                🚪 <strong>{doc['room_number']}</strong> &nbsp;|&nbsp; 
                                📅 <strong>Days:</strong> {doc['available_days']} &nbsp;|&nbsp; 
                                ⏰ <strong>Time:</strong> {doc['available_time_start']} – {doc['available_time_end']}
                            </div>
                            <div style="font-size:12px; color:#64748b; margin-top:4px;">
                                🎓 <strong>Experience:</strong> {doc['experience_years']} Years &nbsp;|&nbsp;
                                👥 <strong>Current Queue:</strong> {waiting_cnt}/{doc['max_patients_per_slot']} Patients
                            </div>
                        </div>
                        <div style="text-align:right;">
                            {status_badge_html}
                            <div style="font-size:11px; color:#64748b; margin-top:4px;">ID: <code>{doc['doc_id']}</code></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_act1, col_act2 = st.columns([1.5, 4])
                with col_act1:
                    if is_bookable:
                        if st.button(f"➕ Book / Join Queue with {doc['name']}", key=f"book_{doc_id}", type="primary", use_container_width=True):
                            st.session_state.quick_book_dept = selected_dept_id
                            st.session_state.quick_book_doc = doc_id
                            st.toast(f"Selected {doc['name']}. Proceeding to Registration...", icon="📝")
                            time.sleep(0.3)
                            # Redirect to Registration by setting session state
                            st.session_state["nav_redirect"] = "📝 Patient Registration"
                            st.rerun()
                    else:
                        st.button(f"🚫 {avail_status}", key=f"dis_{doc_id}", disabled=True, use_container_width=True)
                with col_act2:
                    st.caption(f"ℹ️ {avail_msg}")


# ==============================================================================
# 3. PATIENT REGISTRATION (DEPARTMENT & DOCTOR SELECTION WORKFLOW)
# ==============================================================================
elif menu == "📝 Patient Registration":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Patient Intake & Queue Registration</h1>
        <div class="hero-tagline">📝 Step-by-Step Department & Doctor Selection • Permanent Patient ID Generation</div>
        <p class="hero-desc">
            Follow the 5-step clinical intake workflow: Select Department ➔ Select Doctor ➔ Choose Available Slot ➔ Enter Patient Demographics ➔ Auto-Generate Permanent ID and Doctor Queue Number.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_side = st.columns([1.6, 1])

    with col_side:
        if os.path.exists(DOCTOR_IMG_PATH):
            st.image(DOCTOR_IMG_PATH, use_container_width=True, caption="MediQueue Clinical Intake Desk")
        
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:16px; box-shadow:0 4px 12px rgba(0,0,0,0.04);">
            <h4 style="margin:0 0 6px 0; color:#0f766e; font-size:15px; font-weight:800;">⚡ Quick Demo Triage Autofills</h4>
            <p style="font-size:12px; color:#64748b; margin-bottom:10px;">Pre-fill instant cases across departments:</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⚡ Fill Cardiology Emergency (Dr. Anjali Sharma)", use_container_width=True):
            st.session_state["reg_name"] = "Sneha Patil"
            st.session_state["reg_age"] = 45
            st.session_state["reg_gender"] = "Female"
            st.session_state["reg_problem"] = "Severe Acute Chest Pain & Palpitations"
            st.session_state["reg_priority"] = "Emergency"
            st.session_state.quick_book_dept = "DEP002"
            st.session_state.quick_book_doc = "DOC001"
            st.rerun()

        if st.button("⚡ Fill Dentistry Outpatient (Dr. Sneha Joshi)", use_container_width=True):
            st.session_state["reg_name"] = "Ramesh Gupta"
            st.session_state["reg_age"] = 36
            st.session_state["reg_gender"] = "Male"
            st.session_state["reg_problem"] = "Severe Toothache & Cavity Inspection"
            st.session_state["reg_priority"] = "Normal"
            st.session_state.quick_book_dept = "DEP010"
            st.session_state.quick_book_doc = "DOC015"
            st.rerun()

        if st.button("⚡ Fill Orthopedics Fracture Case", use_container_width=True):
            st.session_state["reg_name"] = "Pooja Hegde"
            st.session_state["reg_age"] = 29
            st.session_state["reg_gender"] = "Female"
            st.session_state["reg_problem"] = "Right Wrist Fracture & Swelling"
            st.session_state["reg_priority"] = "Emergency"
            st.session_state.quick_book_dept = "DEP004"
            st.session_state.quick_book_doc = "DOC007"
            st.rerun()

    with col_form:
        # Calculate Next Permanent Patient ID preview
        curr_year = datetime.now().year
        conn = db_manager.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT last_number FROM patient_counter WHERE year = ?", (curr_year,))
        row = c.fetchone()
        next_num = (row["last_number"] + 1) if row else 1
        preview_pid = f"MQ-{curr_year}-{next_num:06d}"
        conn.close()

        # Step 1: Select Department
        all_depts = db_manager.get_active_departments()
        dept_ids = [d["dept_id"] for d in all_depts]
        default_dept_idx = dept_ids.index(st.session_state.quick_book_dept) if st.session_state.quick_book_dept in dept_ids else 0
        
        st.markdown("### STEP 1: Select Hospital Department")
        selected_dept_id = st.selectbox(
            "Department *",
            options=dept_ids,
            format_func=lambda x: f"{controller.departments_map.get(x, {}).get('dept_name', x)} ({controller.departments_map.get(x, {}).get('floor_location', '')})",
            index=default_dept_idx
        )

        # Step 2: Select Doctor from that department
        dept_docs = db_manager.get_doctors_by_department(selected_dept_id)
        if not dept_docs:
            st.error("No doctors currently assigned to this department.")
        else:
            doc_ids = [d["doc_id"] for d in dept_docs]
            default_doc_idx = doc_ids.index(st.session_state.quick_book_doc) if st.session_state.quick_book_doc in doc_ids else 0
            
            st.markdown("### STEP 2: Select Consulting Doctor")
            selected_doc_id = st.selectbox(
                "Doctor *",
                options=doc_ids,
                format_func=lambda x: f"{controller.doctors_map.get(x, {}).get('name', x)} - {controller.doctors_map.get(x, {}).get('specialization', '')} ({controller.doctors_map.get(x, {}).get('room_number', '')})",
                index=default_doc_idx
            )

            # Check Doctor Availability Status
            avail_status, avail_msg, is_bookable = controller.get_doctor_availability_status(selected_doc_id)
            selected_doc = controller.doctors_map.get(selected_doc_id, {})
            
            st.markdown(f"""
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:12px; padding:12px 16px; margin:10px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>{selected_doc.get('name')}</strong> &nbsp;|&nbsp; 
                        🚪 {selected_doc.get('room_number')} &nbsp;|&nbsp; 
                        📅 {selected_doc.get('available_days')}
                    </div>
                    <div>{render_status_badge(avail_status)}</div>
                </div>
                <div style="font-size:12px; color:#64748b; margin-top:4px;">{avail_msg}</div>
            </div>
            """, unsafe_allow_html=True)

            # Step 3 & 4: Time Slot & Patient Details Form
            with st.form("patient_registration_full_form", clear_on_submit=False):
                st.markdown("### STEP 3 & 4: Select Time Slot & Patient Demographics")
                
                c_slot1, c_slot2 = st.columns(2)
                with c_slot1:
                    slot_options = [
                        f"{selected_doc.get('available_time_start', '10:00 AM')} – {selected_doc.get('available_time_end', '02:00 PM')} (Regular Slot)",
                        "Immediate Emergency Triage Slot"
                    ]
                    slot_choice = st.selectbox("Preferred Consultation Slot *", slot_options)
                
                with c_slot2:
                    priority = st.selectbox(
                        "Priority Category *",
                        ["Normal", "Emergency"],
                        index=["Normal", "Emergency"].index(st.session_state.get("reg_priority", "Normal")),
                        help="Emergency cases are placed into Rank 1 in Min-Heap and jump ahead of normal outpatients."
                    )

                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    st.text_input("Permanent Patient ID (Auto-Assigned)", value=preview_pid, disabled=True)
                    patient_name = st.text_input("Patient Full Name *", value=st.session_state.get("reg_name", ""), placeholder="e.g. Ramesh Kumar")
                    age = st.number_input("Age (Years) *", min_value=1, max_value=120, value=st.session_state.get("reg_age", 28))
                
                with c_p2:
                    gender = st.selectbox("Gender *", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(st.session_state.get("reg_gender", "Male")))
                    problem = st.text_input("Primary Symptoms / Medical Problem *", value=st.session_state.get("reg_problem", ""), placeholder="e.g. Acute chest pain, fracture, toothache")

                st.markdown("<br>", unsafe_allow_html=True)
                submit_reg = st.form_submit_button("➕ Register Patient & Assign Queue Number", type="primary", use_container_width=True)

                if submit_reg:
                    if not patient_name.strip():
                        st.error("⚠️ Please enter the Patient's Full Name.")
                    elif not problem.strip():
                        st.error("⚠️ Please enter the Symptoms / Medical Problem.")
                    elif not is_bookable and priority != "Emergency":
                        st.error(f"❌ Cannot register: {avail_msg}")
                    else:
                        try:
                            actor_name = current_user['username'] if current_user else "Receptionist"
                            new_patient = controller.register_patient(
                                name=patient_name,
                                age=age,
                                gender=gender,
                                problem=problem,
                                priority=priority,
                                dept_id=selected_dept_id,
                                doctor_id=selected_doc_id,
                                slot_time=slot_choice,
                                custom_id=None,
                                actor=actor_name
                            )

                            prio_text = "🚨 **EMERGENCY PRIORITY** (Advanced to head of Min-Heap)" if new_patient.priority == "Emergency" else "🔵 **NORMAL PRIORITY** (Enqueued in arrival FIFO sequence)"

                            st.success(f"""
                            🎉 **Patient Successfully Registered in SQLite!**  
                            • **Permanent Patient ID:** `{new_patient.patient_id}` *(Unique & Permanent)*  
                            • **Doctor Queue Number:** `{new_patient.queue_number}` *(Assigned for {new_patient.doctor_name})*  
                            • **Hospital Department:** `{new_patient.dept_name}` *(Room {new_patient.room_number})*  
                            • **Assigned Doctor:** `{new_patient.doctor_name}`  
                            • **Triage Category:** {prio_text}
                            """)

                            # Clear session state autofills
                            for k in ["reg_name", "reg_age", "reg_problem", "reg_priority"]:
                                if k in st.session_state:
                                    del st.session_state[k]

                        except Exception as e:
                            st.error(f"❌ Registration Failed: {str(e)}")


# ==============================================================================
# 4. DEPARTMENT & DOCTOR QUEUES
# ==============================================================================
elif menu == "📋 Department Queues":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Department-Wise & Doctor-Wise Live Queues</h1>
        <div class="hero-tagline">📋 Strict Queue Separation • Isolated Min-Heap Streams Per Doctor</div>
        <p class="hero-desc">
            Each doctor and department maintains a distinct queue stream. A cardiology patient is never placed into a dentistry or general surgery queue.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_depts = db_manager.get_active_departments()
    dept_map = {d["dept_id"]: d["dept_name"] for d in all_depts}
    
    col_sel1, col_sel2, col_btn = st.columns([1.5, 2, 1])
    with col_sel1:
        sel_dept = st.selectbox("Filter Department:", list(dept_map.keys()), format_func=lambda x: dept_map[x])
    with col_sel2:
        dept_docs = db_manager.get_doctors_by_department(sel_dept)
        doc_opts = {"ALL": "👥 All Doctors in Department"}
        for d in dept_docs:
            doc_opts[d["doc_id"]] = f"{d['name']} ({d['specialization']})"
        sel_doc = st.selectbox("Filter Doctor:", list(doc_opts.keys()), format_func=lambda x: doc_opts[x])
    with col_btn:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Queue"):
            controller.refresh_from_storage()
            st.rerun()

    # Filter waiting patients
    if sel_doc == "ALL":
        doc_waiting = controller.get_waiting_patients_for_dept(sel_dept)
    else:
        doc_waiting = controller.get_waiting_patients_for_doctor(sel_doc)

    st.markdown(f"**Total Patients Waiting in Selected Queue:** `{len(doc_waiting)}`")

    if not doc_waiting:
        st.markdown("""
        <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 16px; padding: 40px 20px; text-align: center; color: #64748b;">
            <span style="font-size: 38px;">📋</span>
            <h4 style="margin: 10px 0 4px 0; color: #334155;">No Patients Waiting in This Queue</h4>
            <p style="margin: 0; font-size: 13px;">Registered patients for this department/doctor will appear here automatically.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, p in enumerate(doc_waiting, start=1):
            is_emergency = p.priority == "Emergency"
            badge_html = "<span class='badge-emergency'>🚨 Emergency Priority</span>" if is_emergency else "<span class='badge-normal'>🔵 Normal Priority</span>"
            card_class = "patient-queue-card-emergency" if is_emergency else "patient-queue-card"

            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span style="font-weight:800; color:#0f766e; font-size:16px;">Queue #{p.queue_number}</span>
                        &nbsp;|&nbsp;
                        <span style="font-weight:700; color:#0f172a; font-size:14px;">Pos #{idx}</span>
                        &nbsp;|&nbsp;
                        <span style="color:#64748b; font-size:13px;">Permanent ID: <strong>{p.patient_id}</strong></span>
                    </div>
                    <div>{badge_html}</div>
                </div>
                <div style="margin-top:8px;">
                    <span style="font-size:17px; font-weight:800; color:#0f172a;">{p.name}</span>
                    <span style="color:#64748b; font-size:13px;"> ({p.age} yrs, {p.gender})</span>
                    <br>
                    <span style="color:#334155; font-size:13px; margin-top:3px; display:inline-block;">
                        👨‍⚕️ <strong>Doctor:</strong> {p.doctor_name} ({p.dept_name}, {p.room_number})
                    </span>
                    <br>
                    <span style="color:#1e293b; font-size:13px;">🩺 <strong>Symptoms / Reason:</strong> {p.problem}</span>
                    <br>
                    <span style="color:#94a3b8; font-size:11px;">Registered at: {p.registration_time} &nbsp;|&nbsp; Slot: {p.slot_time}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_act1, c_act2 = st.columns([1, 6])
            with c_act1:
                if st.button("❌ Cancel", key=f"q_cancel_{p.patient_id}"):
                    actor_name = current_user['username'] if current_user else "Staff"
                    controller.cancel_patient(p.patient_id, actor=actor_name)
                    st.toast(f"Cancelled {p.name} from queue", icon="ℹ️")
                    time.sleep(0.3)
                    st.rerun()


# ==============================================================================
# 5. DOCTOR CONSULTATION CABIN
# ==============================================================================
elif menu == "👨‍⚕️ Doctor Cabin":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Doctor Consultation Cabin & Patient Dispatch</h1>
        <div class="hero-tagline">👨‍⚕️ Active Doctor's Desk • Min-Heap Priority Dispatch • Clinical Note Archiving</div>
        <p class="hero-desc">
            Dedicated interface for doctors and duty nurses. Call next patients in priority order, review clinical symptoms, complete consultations, and record permanent medical notes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_docs = db_manager.get_all_doctors()
    doc_dict = {d["doc_id"]: f"{d['name']} – {d['specialization']} ({d['dept_name']}, {d['room_number']})" for d in all_docs}
    
    doc_keys = list(doc_dict.keys())
    default_cabin_idx = doc_keys.index(st.session_state.selected_doc_cabin) if st.session_state.selected_doc_cabin in doc_keys else 0

    col_c1, col_c2 = st.columns([2.5, 1])
    with col_c1:
        sel_doc_id = st.selectbox(
            "Select Doctor's Consultation Room:",
            options=doc_keys,
            format_func=lambda x: doc_dict[x],
            index=default_cabin_idx
        )
        st.session_state.selected_doc_cabin = sel_doc_id

    doc_info = controller.doctors_map.get(sel_doc_id, {})
    avail_status, avail_msg, _ = controller.get_doctor_availability_status(sel_doc_id)
    
    with col_c2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.markdown(f"**Status:** {render_status_badge(avail_status)}", unsafe_allow_html=True)

    st.markdown("---")

    col_active, col_next = st.columns([1.1, 1])

    with col_active:
        st.markdown("### 🩺 Currently In Consultation")
        active_patient = controller.get_current_in_consultation_for_doctor(sel_doc_id)

        if active_patient:
            badge_html = "<span class='badge-emergency'>🚨 Emergency Priority</span>" if active_patient.priority == "Emergency" else "<span class='badge-normal'>🔵 Normal Priority</span>"
            st.markdown(f"""
            <div class="desk-card-active">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:22px;">🩺</span>
                        <h3 style="margin:0; color:#15803d; font-size:17px; font-weight:800;">Inside Cabin Now</h3>
                    </div>
                    <span style="background:#15803d; color:white; font-weight:800; font-size:13px; padding:4px 10px; border-radius:20px;">
                        Queue #{active_patient.queue_number}
                    </span>
                </div>
                <hr style="margin:10px 0; border-color:#86efac;">
                <h2 style="margin:0 0 4px 0; color:#0f172a; font-size:20px;">{active_patient.name} <span style="font-size:13px; color:#475569; font-weight:500;">({active_patient.patient_id})</span></h2>
                <p style="margin:4px 0; color:#1e293b; font-size:14px;"><strong>Diagnosis / Symptoms:</strong> {active_patient.problem}</p>
                <p style="margin:4px 0; color:#475569; font-size:13px;">Age: {active_patient.age} yrs | Gender: {active_patient.gender} | {badge_html}</p>
                <p style="margin:4px 0; color:#64748b; font-size:12px;">Slot: {active_patient.slot_time} | Registered: {active_patient.registration_time}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("complete_consult_form"):
                doc_notes = st.text_area("Doctor's Clinical Notes / Prescription:", placeholder="e.g. Blood pressure stabilized. Prescribed medications. Review in 2 weeks.", height=80)
                submit_complete = st.form_submit_button("✅ Complete Consultation & Save to History", type="primary", use_container_width=True)

                if submit_complete:
                    actor_name = current_user['username'] if current_user else "Doctor"
                    controller.complete_consultation(active_patient.patient_id, doctor_notes=doc_notes, actor=actor_name)
                    st.toast(f"Consultation completed for {active_patient.name} [{active_patient.patient_id}]!", icon="✅")
                    time.sleep(0.4)
                    st.rerun()
        else:
            st.markdown("""
            <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 16px; padding: 40px 20px; text-align: center; color: #64748b;">
                <span style="font-size: 38px;">🛋️</span>
                <h4 style="margin: 10px 0 4px 0; color: #334155;">Cabin Desk Is Free</h4>
                <p style="margin: 0; font-size: 13px;">No patient is currently inside the cabin. Click 'Call Next Patient' to admit.</p>
            </div>
            """, unsafe_allow_html=True)

    with col_next:
        st.markdown("### 🔔 Next Patient in Queue (Min-Heap)")
        next_patient = controller.get_next_patient_for_doctor(sel_doc_id)

        if next_patient:
            badge_html = "<span class='badge-emergency'>🚨 Emergency Priority</span>" if next_patient.priority == "Emergency" else "<span class='badge-normal'>🔵 Normal Priority</span>"
            st.markdown(f"""
            <div class="next-up-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>{badge_html}</div>
                    <span style="font-weight:800; font-size:15px; color:#0f766e; background:#f0fdfa; padding:4px 12px; border-radius:20px; border:1px solid #ccfbf1;">
                        Queue #{next_patient.queue_number}
                    </span>
                </div>
                <h2 style="margin:10px 0 4px 0; color:#0f172a; font-size:20px; font-weight:800;">
                    {next_patient.name} <span style="font-size:14px; color:#64748b; font-weight:500;">({next_patient.patient_id})</span>
                </h2>
                <p style="margin:4px 0; color:#1e293b; font-size:13px;"><strong>Symptoms:</strong> {next_patient.problem}</p>
                <p style="margin:4px 0; color:#64748b; font-size:13px;">Age: {next_patient.age} yrs | Gender: {next_patient.gender} | Arrival: {next_patient.registration_time}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            
            c_b1, c_b2 = st.columns([1.5, 1])
            with c_b1:
                if st.button("📢 Call Next Patient to Cabin", type="primary", use_container_width=True):
                    actor_name = current_user['username'] if current_user else "Doctor"
                    called = controller.call_next_patient_for_doctor(sel_doc_id, actor=actor_name)
                    if called:
                        st.success(f"Dispatched {called.name} (Queue #{called.queue_number}) to Cabin!")
                        st.toast(f"Calling {called.name}", icon="📢")
                        time.sleep(0.4)
                        st.rerun()
            with c_b2:
                if st.button("⏭️ Skip / Cancel", key=f"skip_{next_patient.patient_id}", use_container_width=True):
                    controller.cancel_patient(next_patient.patient_id)
                    st.toast(f"Skipped {next_patient.name}", icon="⏭️")
                    time.sleep(0.3)
                    st.rerun()
        else:
            st.markdown("""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 16px; padding: 40px 20px; text-align: center; color: #166534;">
                <span style="font-size: 38px;">🎉</span>
                <h4 style="margin: 10px 0 4px 0; color: #15803d;">Doctor's Queue Is Empty</h4>
                <p style="margin: 0; font-size: 13px;">All waiting patients for this doctor have been attended to.</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Doctor's Waiting Queue List
    st.markdown(f"### 📋 Full Waiting Queue for {doc_info.get('name', 'Doctor')}")
    waiting_doc_list = controller.get_waiting_patients_for_doctor(sel_doc_id)
    if waiting_doc_list:
        table_d = []
        for idx, p in enumerate(waiting_doc_list, start=1):
            table_d.append({
                "Queue Pos": f"#{idx}",
                "Queue No.": p.queue_number,
                "Permanent ID": p.patient_id,
                "Patient Name": p.name,
                "Age / Gender": f"{p.age} yrs / {p.gender}",
                "Symptoms / Reason": p.problem,
                "Priority": p.priority,
                "Slot Time": p.slot_time,
                "Arrival Time": p.registration_time
            })
        st.dataframe(pd.DataFrame(table_d), use_container_width=True, hide_index=True)
    else:
        st.info("No patients currently waiting in line for this doctor.")


# ==============================================================================
# 6. SEARCH & LOOKUP (PATIENTS & DOCTORS)
# ==============================================================================
elif menu == "🔍 Search & Lookup":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Multi-Attribute Search & DSA Algorithms</h1>
        <div class="hero-tagline">🔍 Binary Search O(log n) • Linear Search O(n) • Full Execution Traces</div>
        <p class="hero-desc">
            Search patient medical records and doctor profiles with step-by-step algorithmic comparison traces demonstrating divide-and-conquer and sequential lookup.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_patients = controller.get_all_patients()
    all_docs = db_manager.get_all_doctors()

    tab1, tab2, tab3 = st.tabs(["🔎 Search Patients by Permanent ID", "👤 Search Patients by Name / Doctor / Dept", "👨‍⚕️ Search Doctors"])

    # TAB 1: Binary Search by Patient ID
    with tab1:
        st.markdown("### Search by Permanent Patient ID (MQ-YYYY-XXXXXX)")
        c1, c2 = st.columns([2, 1])
        with c1:
            target_id = st.text_input("Enter Permanent Patient ID:", value="MQ-2026-000002")
        with c2:
            search_algorithm = st.selectbox(
                "Search Algorithm:",
                ["Binary Search (Divide & Conquer)", "Linear Search (Sequential Scan)"],
                key="algo_p_id"
            )

        if st.button("Search Patient ID", type="primary"):
            if not target_id.strip():
                st.warning("Please enter a Patient ID to search.")
            else:
                if "Binary Search" in search_algorithm:
                    found_patient, comps, logs = binary_search_by_id(all_patients, target_id)
                    algo_used = "Binary Search"
                    complexity = "O(log n) Time"
                else:
                    results, comps, logs = linear_search_patients(all_patients, target_id, search_by="patient_id")
                    found_patient = results[0] if results else None
                    algo_used = "Linear Search"
                    complexity = "O(n) Time"

                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.metric("Algorithm Used", algo_used)
                with mc2:
                    st.metric("Comparisons Made", f"{comps} step(s)")
                with mc3:
                    st.metric("Time Complexity", complexity)

                if found_patient:
                    st.success(f"🎯 **Patient Record Located!**")
                    prio_badge = "<span class='badge-emergency'>🚨 Emergency</span>" if found_patient.priority == "Emergency" else "<span class='badge-normal'>🔵 Normal</span>"
                    st.markdown(f"""
                    <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:16px; padding:20px; box-shadow:0 8px 24px -4px rgba(15,23,42,0.08);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h2 style="margin:0; color:#0f766e; font-size:20px;">{found_patient.name} <span style="font-size:14px; color:#64748b;">({found_patient.patient_id})</span></h2>
                            <span style="font-weight:700; font-size:13px; color:#0284c7; background:#e0f2fe; padding:4px 12px; border-radius:20px;">Queue: {found_patient.queue_number} | Status: {found_patient.status}</span>
                        </div>
                        <hr style="margin:10px 0; border-color:#e2e8f0;">
                        <p style="margin:4px 0;"><strong>Department:</strong> {found_patient.dept_name} | <strong>Doctor:</strong> {found_patient.doctor_name} ({found_patient.room_number})</p>
                        <p style="margin:4px 0;"><strong>Age / Gender:</strong> {found_patient.age} yrs | {found_patient.gender}</p>
                        <p style="margin:4px 0;"><strong>Symptoms:</strong> {found_patient.problem}</p>
                        <p style="margin:4px 0;"><strong>Priority:</strong> {prio_badge} | <strong>Slot:</strong> {found_patient.slot_time}</p>
                        <p style="margin:4px 0;"><strong>Registration Time:</strong> {found_patient.registration_time}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"❌ No patient found matching Permanent ID `{target_id}`.")

                with st.expander("🔬 View Algorithmic Step-by-Step Execution Trace"):
                    for step in logs:
                        st.code(step, language="text")

    # TAB 2: Search Patients by Name / Doctor / Dept
    with tab2:
        st.markdown("### Search Patients by Name, Doctor, Department, or Queue Number")
        c_s1, c_s2 = st.columns([2, 1])
        with c_s1:
            name_query = st.text_input("Enter Search Term:", value="Rahul")
        with c_s2:
            search_by_field = st.selectbox("Search By:", ["all", "name", "doctor", "department", "queue_number"])

        if st.button("Search Records", type="primary"):
            if not name_query.strip():
                st.warning("Please enter a search query.")
            else:
                matches, comps, logs = linear_search_patients(all_patients, name_query, search_by=search_by_field)
                
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.metric("Total Matches Found", f"{len(matches)} patient(s)")
                with mc2:
                    st.metric("Total Comparisons", f"{comps} records scanned")

                if matches:
                    st.markdown("#### Matching Records:")
                    df_m = pd.DataFrame([p.to_dict() for p in matches])
                    st.dataframe(df_m, use_container_width=True, hide_index=True)
                else:
                    st.error(f"No patients found matching '{name_query}'.")

                with st.expander("🔬 View Search Steps"):
                    for step in logs:
                        st.code(step, language="text")

    # TAB 3: Search Doctors
    with tab3:
        st.markdown("### Search Doctor Database")
        doc_q = st.text_input("Search Doctor by Name / Specialization / ID (e.g. DOC001, Cardiologist, Anjali):", value="DOC001")
        
        if st.button("Search Doctor", type="primary"):
            if not doc_q.strip():
                st.warning("Please enter a doctor name or ID.")
            else:
                if doc_q.strip().upper().startswith("DOC"):
                    found_doc, comps, logs = binary_search_doctor_by_id(all_docs, doc_q)
                    matches = [found_doc] if found_doc else []
                    algo = "Binary Search O(log n)"
                else:
                    matches, comps, logs = linear_search_doctors(all_docs, doc_q, search_by="all")
                    algo = "Linear Search O(n)"

                st.markdown(f"**Algorithm:** `{algo}` &nbsp;|&nbsp; **Comparisons:** `{comps}` &nbsp;|&nbsp; **Matches:** `{len(matches)}`")

                if matches:
                    st.dataframe(pd.DataFrame(matches), use_container_width=True, hide_index=True)
                else:
                    st.error(f"No doctors found matching '{doc_q}'.")


# ==============================================================================
# 7. SORTING WORKBENCH
# ==============================================================================
elif menu == "📊 Sorting Workbench":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">DSA Sorting Workbench</h1>
        <div class="hero-tagline">📊 Handcrafted Bubble Sort & Insertion Sort • Multi-Attribute Ordering</div>
        <p class="hero-desc">
            Benchmark and visualize Bubble Sort and Insertion Sort algorithms sorting patient queues and doctor directories by various clinical attributes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_sort_p, tab_sort_d = st.tabs(["👤 Sort Patients", "👨‍⚕️ Sort Doctors"])

    with tab_sort_p:
        all_patients = controller.get_all_patients()
        c1, c2, c3 = st.columns(3)
        with c1:
            sort_key = st.selectbox(
                "Sort Patient By:",
                ["Priority (Emergency First)", "Age", "Name", "Queue Number", "Token (Arrival Order)", "Doctor", "Department"],
                key="p_sort_key"
            )
        with c2:
            sort_algorithm = st.selectbox("Algorithm:", ["Bubble Sort", "Insertion Sort"], key="p_sort_algo")
        with c3:
            order = st.selectbox("Direction:", ["Ascending (Low to High)", "Descending (High to Low)"], key="p_sort_dir")

        key_map = {
            "Priority (Emergency First)": "priority",
            "Age": "age",
            "Name": "name",
            "Queue Number": "queue_number",
            "Token (Arrival Order)": "token",
            "Doctor": "doctor",
            "Department": "department"
        }
        sel_key = key_map[sort_key]
        is_asc = "Ascending" in order

        if st.button("🚀 Run Patient Sorting", type="primary"):
            if "Bubble Sort" in sort_algorithm:
                sorted_list, comps, ops = bubble_sort_patients(all_patients, sort_key=sel_key, ascending=is_asc)
                op_label = "Total Swaps"
                algo_title = "Bubble Sort O(n^2)"
            else:
                sorted_list, comps, ops = insertion_sort_patients(all_patients, sort_key=sel_key, ascending=is_asc)
                op_label = "Total Shifts"
                algo_title = "Insertion Sort O(n^2)"

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Sorting Algorithm", algo_title)
            with m2:
                st.metric("Total Records", len(sorted_list))
            with m3:
                st.metric("Comparisons Made", f"{comps}")
            with m4:
                st.metric(op_label, f"{ops}")

            st.markdown("### 📋 Sorted Patient Records")
            df_sorted = pd.DataFrame([p.to_dict() for p in sorted_list])
            st.dataframe(df_sorted, use_container_width=True, hide_index=True)

    with tab_sort_d:
        all_docs = db_manager.get_all_doctors()
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            doc_sort_key = st.selectbox("Sort Doctor By:", ["Experience (Years)", "Name", "Department", "Room"], key="d_sort_k")
        with dc2:
            doc_sort_algo = st.selectbox("Algorithm:", ["Bubble Sort", "Insertion Sort"], key="d_sort_a")
        with dc3:
            doc_order = st.selectbox("Direction:", ["Descending (Highest First)", "Ascending (Lowest First)"], key="d_sort_d")

        d_key_map = {"Experience (Years)": "experience", "Name": "name", "Department": "department", "Room": "room"}
        d_sel_key = d_key_map[doc_sort_key]
        d_is_asc = "Ascending" in doc_order

        if st.button("🚀 Run Doctor Sorting", type="primary"):
            if "Bubble Sort" in doc_sort_algo:
                sorted_docs, comps, ops = bubble_sort_doctors(all_docs, sort_key=d_sel_key, ascending=d_is_asc)
                op_label = "Total Swaps"
            else:
                sorted_docs, comps, ops = insertion_sort_doctors(all_docs, sort_key=d_sel_key, ascending=d_is_asc)
                op_label = "Total Shifts"

            st.markdown(f"**Sorted {len(sorted_docs)} Doctors** &nbsp;|&nbsp; Comparisons: `{comps}` &nbsp;|&nbsp; {op_label}: `{ops}`")
            st.dataframe(pd.DataFrame(sorted_docs), use_container_width=True, hide_index=True)


# ==============================================================================
# 8. PATIENT HISTORY (PERMANENT & PROTECTED)
# ==============================================================================
elif menu == "📜 Patient History":
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">Permanent Patient Visit History Archive</h1>
        <div class="hero-tagline">📜 Immutable Medical Records • Complete Longitudinal Visit Archive</div>
        <p class="hero-desc">
            Every completed consultation is permanently archived in SQLite with doctor notes, diagnosis, department, date, and time. Records are never deleted when a patient leaves today's active queue.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_history = db_manager.get_all_visit_history()

    tab_h1, tab_h2 = st.tabs(["🔎 Look Up Single Patient Visit History", "📋 All Historical Hospital Consultations"])

    with tab_h1:
        st.markdown("### Look Up Patient Longitudinal History by Permanent ID")
        srch_pid = st.text_input("Enter Permanent Patient ID (e.g. MQ-2026-000000, MQ-2026-000001):", value="MQ-2026-000000")
        
        if st.button("Search Patient History", type="primary"):
            if not srch_pid.strip():
                st.warning("Please enter a Patient ID.")
            else:
                p_history = db_manager.get_patient_history_by_id(srch_pid)
                if p_history:
                    st.success(f"Found **{len(p_history)}** historical consultation visit(s) for `{srch_pid}`:")
                    df_ph = pd.DataFrame(p_history)
                    st.dataframe(df_ph, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No previous visit history recorded yet for `{srch_pid}`.")

    with tab_h2:
        st.markdown(f"**Total Historical Consultations in SQLite Archive:** `{len(all_history)}`")
        
        if all_history:
            df_all_h = pd.DataFrame(all_history)
            st.dataframe(df_all_h, use_container_width=True, hide_index=True)

            csv_data = df_all_h.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Historical Report (CSV)",
                data=csv_data,
                file_name=f"mediqueue_patient_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No consultation history records found.")


# ==============================================================================
# 9. ADMIN: DEPARTMENT & DOCTOR MANAGEMENT (AUTHENTICATED)
# ==============================================================================
elif menu == "🏢 Admin: Depts & Doctors":
    if not current_user:
        st.warning("🔒 Staff Authentication Required. Please log in from the sidebar to manage departments and doctors.")
    else:
        st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">Hospital Department & Doctor Management</h1>
            <div class="hero-tagline">🏢 Department Configuration • Doctor Availability • Timings & Leave Control</div>
            <p class="hero-desc">
                Administrative control suite to add, edit, activate/deactivate departments, set doctor leave status, update consultation schedules, and manage slot limits.
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_m_dept, tab_m_doc = st.tabs(["🏢 Department Management", "👨‍⚕️ Doctor Directory & Availability Management"])

        # TAB 1: Department Management
        with tab_m_dept:
            st.markdown("### 🏢 Hospital Departments")
            all_depts = db_manager.get_all_departments()
            st.dataframe(pd.DataFrame(all_depts), use_container_width=True, hide_index=True)

            col_ad1, col_ad2 = st.columns(2)
            
            with col_ad1:
                with st.expander("➕ Add New Department"):
                    with st.form("add_dept_form"):
                        new_dept_id = st.text_input("Department ID *", placeholder="e.g. DEP016")
                        new_dept_name = st.text_input("Department Name *", placeholder="e.g. Oncology")
                        new_dept_code = st.text_input("Queue Code *", placeholder="e.g. ONCO")
                        new_dept_floor = st.text_input("Floor / Location", placeholder="e.g. Floor 4, Wing D")
                        new_dept_desc = st.text_area("Description", placeholder="Specialty description...")
                        submit_dept = st.form_submit_button("Save Department", type="primary")

                        if submit_dept:
                            if not new_dept_id.strip() or not new_dept_name.strip() or not new_dept_code.strip():
                                st.error("Please fill in ID, Name, and Code.")
                            else:
                                success = db_manager.add_department({
                                    "dept_id": new_dept_id,
                                    "dept_name": new_dept_name,
                                    "dept_code": new_dept_code,
                                    "floor_location": new_dept_floor,
                                    "description": new_dept_desc,
                                    "status": "Active"
                                }, actor=current_user['username'])
                                if success:
                                    controller.refresh_from_storage()
                                    st.success(f"Added {new_dept_name} successfully!")
                                    time.sleep(0.3)
                                    st.rerun()

            with col_ad2:
                with st.expander("✏️ Activate / Deactivate Department"):
                    dept_to_edit = st.selectbox("Select Department to Toggle:", [d["dept_id"] for d in all_depts], format_func=lambda x: f"{x} - {controller.departments_map.get(x, {}).get('dept_name')}")
                    current_dept_st = controller.departments_map.get(dept_to_edit, {}).get("status", "Active")
                    new_st = "Inactive" if current_dept_st == "Active" else "Active"
                    
                    if st.button(f"Switch Status to '{new_st}'", type="primary"):
                        db_manager.toggle_department_status(dept_to_edit, new_st, actor=current_user['username'])
                        controller.refresh_from_storage()
                        st.success(f"Status of [{dept_to_edit}] updated to {new_st}!")
                        time.sleep(0.3)
                        st.rerun()

        # TAB 2: Doctor Management
        with tab_m_doc:
            st.markdown("### 👨‍⚕️ Doctor Directory & Availability Controls")
            all_docs = db_manager.get_all_doctors()
            st.dataframe(pd.DataFrame(all_docs), use_container_width=True, hide_index=True)

            col_doc1, col_doc2 = st.columns(2)

            with col_doc1:
                with st.expander("🩺 Update Doctor Status & Leaves"):
                    doc_sel_edit = st.selectbox("Select Doctor:", [d["doc_id"] for d in all_docs], format_func=lambda x: f"{x} - {controller.doctors_map.get(x, {}).get('name')}")
                    doc_obj = controller.doctors_map.get(doc_sel_edit, {})
                    
                    st.write(f"**Current Status:** `{doc_obj.get('status')}`")
                    new_status_choice = st.selectbox("New Availability Status:", ["Available", "On Leave", "Unavailable"])
                    new_max_slot = st.number_input("Max Patients Per Slot:", min_value=1, max_value=50, value=int(doc_obj.get('max_patients_per_slot', 10)))
                    
                    if st.button("Update Doctor Status & Capacity", type="primary"):
                        db_manager.update_doctor(doc_sel_edit, {
                            "status": new_status_choice,
                            "max_patients_per_slot": new_max_slot
                        }, actor=current_user['username'])
                        controller.refresh_from_storage()
                        st.success(f"Updated {doc_obj.get('name')} to '{new_status_choice}'!")
                        time.sleep(0.3)
                        st.rerun()

            with col_doc2:
                with st.expander("➕ Add New Doctor"):
                    with st.form("add_doc_form"):
                        n_doc_id = st.text_input("Doctor ID *", placeholder="e.g. DOC021")
                        n_doc_name = st.text_input("Doctor Name *", placeholder="e.g. Dr. Aryan Khan")
                        n_dept_id = st.selectbox("Department *", [d["dept_id"] for d in db_manager.get_active_departments()], format_func=lambda x: f"{x} - {controller.departments_map.get(x, {}).get('dept_name')}")
                        n_spec = st.text_input("Specialization *", placeholder="e.g. Interventional Cardiologist")
                        n_qual = st.text_input("Qualification", value="MBBS, MD")
                        n_exp = st.number_input("Experience (Years)", min_value=1, max_value=50, value=8)
                        n_room = st.text_input("Room Number", value="Room 205")
                        n_days = st.text_input("Available Days", value="Monday, Wednesday, Friday")
                        n_t_start = st.text_input("Start Time", value="10:00 AM")
                        n_t_end = st.text_input("End Time", value="02:00 PM")
                        n_max_p = st.number_input("Max Patients Per Slot", min_value=1, max_value=50, value=10)
                        
                        submit_doc = st.form_submit_button("Save Doctor", type="primary")

                        if submit_doc:
                            if not n_doc_id.strip() or not n_doc_name.strip() or not n_spec.strip():
                                st.error("Please fill in ID, Name, and Specialization.")
                            else:
                                success = db_manager.add_doctor({
                                    "doc_id": n_doc_id,
                                    "name": n_doc_name,
                                    "dept_id": n_dept_id,
                                    "specialization": n_spec,
                                    "qualification": n_qual,
                                    "experience_years": n_exp,
                                    "room_number": n_room,
                                    "available_days": n_days,
                                    "available_time_start": n_t_start,
                                    "available_time_end": n_t_end,
                                    "max_patients_per_slot": n_max_p,
                                    "status": "Available"
                                }, actor=current_user['username'])
                                if success:
                                    controller.refresh_from_storage()
                                    st.success(f"Added {n_doc_name} successfully!")
                                    time.sleep(0.3)
                                    st.rerun()


# ==============================================================================
# 10. AUDIT LOGS & BACKUPS (AUTHENTICATED)
# ==============================================================================
elif menu == "🛡️ Audit Logs & Backups":
    if not current_user:
        st.warning("🔒 Staff Authentication Required to view Audit Logs & Backups.")
    else:
        st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">System Audit Trail & Database Backups</h1>
            <div class="hero-tagline">🛡️ Real-Time Audit Trail • Atomic SQLite Snapshots • Security Controls</div>
            <p class="hero-desc">
                Protected audit logs recording all clinical triage, patient registrations, doctor updates, and atomic SQLite snapshot backups.
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_audit, tab_backup = st.tabs(["📋 System Audit Trail", "💾 Database Snapshot Backups"])

        with tab_audit:
            st.markdown("### 📋 Activity & Audit Trail (Last 50 Events)")
            logs = db_manager.get_audit_logs(limit=50)
            if logs:
                st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs recorded yet.")

        with tab_backup:
            st.markdown("### 💾 Native SQLite Snapshot Backups")
            st.caption("Create instant atomic snapshots of `mediqueue.db` stored in the `backups/` directory.")

            if st.button("📦 Create Instant Database Backup Now", type="primary"):
                try:
                    fname, count = db_manager.create_database_backup(actor=current_user['username'])
                    st.success(f"✅ Backup snapshot created: `{fname}` ({count} patient records captured).")
                    time.sleep(0.3)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Could not create backup snapshot: {str(e)}")

            st.markdown("#### Past Backups Archive:")
            backups_list = db_manager.get_backups_list()
            if backups_list:
                st.dataframe(pd.DataFrame(backups_list), use_container_width=True, hide_index=True)
                
                latest_backup = backups_list[0]
                latest_path = os.path.join(BASE_DIR, "backups", latest_backup["filename"])
                if os.path.exists(latest_path):
                    with open(latest_path, "rb") as bf:
                        st.download_button(
                            label=f"📥 Download Latest Backup ({latest_backup['filename']})",
                            data=bf.read(),
                            file_name=latest_backup["filename"],
                            mime="application/x-sqlite3"
                        )
            else:
                st.info("No backups created yet.")
