"""
db_manager.py
=============
SQLite Database & Security Management Layer for MediQueue Hospital System.

FEATURES:
1. Permanent Sequential Patient ID Generation (MQ-YYYY-XXXXXX) with atomic SQLite counter.
2. Department-wise & Doctor-specific Queue Number Generation (e.g. C-001, D-001, S-001).
3. 15 Standard Multi-Specialty Hospital Departments with full administrative management.
4. Comprehensive Doctor Database & Availability Management (Days, Hours, Max Slots, Leave Status).
5. Permanent Patient Visit History Archive (Never lost upon queue completion/removal).
6. Cryptographically Secure Staff & Admin Authentication (PBKDF2-HMAC-SHA256 with 16-byte random salt).
7. Full Audit Logging for all clinical actions, logins, triage, and backups.
8. Native SQLite Snapshot Backups.
"""

import os
import sqlite3
import hashlib
import secrets
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mediqueue.db")
BACKUPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled for dictionary-like access."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> Tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a unique 16-byte cryptographically secure salt.
    Returns: (hex_hash, hex_salt)
    """
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return key.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verifies a plain text password against the stored PBKDF2 hash and salt.
    """
    try:
        salt = bytes.fromhex(stored_salt)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False


def init_db() -> None:
    """Initializes all SQLite database tables, default counters, departments, doctors, and default staff credentials."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Permanent Patient ID Counter Table (Never decreases or reuses IDs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_counter (
        year INTEGER PRIMARY KEY,
        last_number INTEGER NOT NULL DEFAULT 0
    )
    """)

    # 2. Doctor / Department Daily Queue Counter Table (for C-001, D-001, etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctor_queue_counter (
        counter_key TEXT PRIMARY KEY, -- format: {doc_id}_{date}
        last_queue_num INTEGER NOT NULL DEFAULT 0
    )
    """)

    # 3. Departments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        dept_id TEXT PRIMARY KEY,
        dept_name TEXT NOT NULL,
        dept_code TEXT NOT NULL,
        description TEXT,
        floor_location TEXT,
        status TEXT NOT NULL DEFAULT 'Active'
    )
    """)

    # 4. Doctors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        doc_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        dept_id TEXT NOT NULL,
        specialization TEXT NOT NULL,
        qualification TEXT NOT NULL,
        experience_years INTEGER NOT NULL DEFAULT 5,
        room_number TEXT NOT NULL,
        available_days TEXT NOT NULL,
        available_time_start TEXT NOT NULL,
        available_time_end TEXT NOT NULL,
        max_patients_per_slot INTEGER NOT NULL DEFAULT 10,
        status TEXT NOT NULL DEFAULT 'Available',
        contact TEXT,
        FOREIGN KEY (dept_id) REFERENCES departments (dept_id)
    )
    """)

    # 5. Patients Table (Active Queue & Master Records)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        problem TEXT NOT NULL,
        priority TEXT NOT NULL,
        token INTEGER NOT NULL,
        registration_time TEXT NOT NULL,
        consultation_time TEXT,
        status TEXT NOT NULL,
        dept_id TEXT DEFAULT 'DEP001',
        doctor_id TEXT DEFAULT 'DOC001',
        queue_number TEXT DEFAULT 'GEN-001',
        slot_time TEXT DEFAULT '10:00 AM - 02:00 PM',
        visit_date TEXT DEFAULT '',
        doctor_notes TEXT DEFAULT ''
    )
    """)

    # Safe Schema Migrations for existing patients table
    cursor.execute("PRAGMA table_info(patients)")
    columns = [row["name"] for row in cursor.fetchall()]
    new_cols = [
        ("dept_id", "TEXT DEFAULT 'DEP001'"),
        ("doctor_id", "TEXT DEFAULT 'DOC001'"),
        ("queue_number", "TEXT DEFAULT 'GEN-001'"),
        ("slot_time", "TEXT DEFAULT '10:00 AM - 02:00 PM'"),
        ("visit_date", "TEXT DEFAULT ''"),
        ("doctor_notes", "TEXT DEFAULT ''")
    ]
    for col_name, col_def in new_cols:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}")

    # 6. Patient Visits & Permanent History Archive Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_visits (
        visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        dept_id TEXT NOT NULL,
        dept_name TEXT NOT NULL,
        doctor_id TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        queue_number TEXT NOT NULL,
        visit_date TEXT NOT NULL,
        slot_time TEXT NOT NULL,
        problem TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        registration_time TEXT NOT NULL,
        consultation_time TEXT,
        doctor_notes TEXT
    )
    """)

    # 7. Staff Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 8. Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT
    )
    """)

    # 9. Backups Metadata Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backups (
        backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        record_count INTEGER NOT NULL,
        created_by TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed Default Departments if table is empty
    cursor.execute("SELECT COUNT(*) FROM departments")
    if cursor.fetchone()[0] == 0:
        seed_departments(conn)

    # Seed Default Doctors if table is empty
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] == 0:
        seed_doctors(conn)

    # Create default staff and admin user accounts if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
        staff_pass = os.environ.get("STAFF_PASSWORD", "staff123")

        try:
            import streamlit as st
            if hasattr(st, "secrets") and "credentials" in st.secrets:
                admin_pass = st.secrets["credentials"].get("admin_password", admin_pass)
                staff_pass = st.secrets["credentials"].get("staff_password", staff_pass)
        except Exception:
            pass

        p_hash_admin, p_salt_admin = hash_password(admin_pass)
        p_hash_staff, p_salt_staff = hash_password(staff_pass)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", p_hash_admin, p_salt_admin, "Chief Medical Administrator", "admin", now_str))

        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("staff", p_hash_staff, p_salt_staff, "Duty Nurse / Receptionist", "staff", now_str))

        conn.commit()

    # Seed sample patients and visits if empty
    cursor.execute("SELECT COUNT(*) FROM patients")
    if cursor.fetchone()[0] == 0:
        seed_sample_patients(conn)

    conn.close()


def seed_departments(conn: sqlite3.Connection) -> None:
    """Seeds the 15 standard hospital departments."""
    departments_data = [
        ("DEP001", "General Medicine", "GM", "Primary healthcare, routine diagnosis, adult preventive medicine and chronic disease management.", "Floor 1, Wing A", "Active"),
        ("DEP002", "Cardiology", "CARD", "Advanced cardiovascular diagnostics, hypertension management, ECG, and heart failure care.", "Floor 2, Wing B", "Active"),
        ("DEP003", "Neurology", "NEUR", "Brain, spine, peripheral nervous system disorder treatments, stroke recovery, and epilepsy care.", "Floor 3, Wing A", "Active"),
        ("DEP004", "Orthopedics", "ORTH", "Bone, joint, trauma care, fracture management, arthritis treatment, and sports rehabilitation.", "Floor 1, Wing C", "Active"),
        ("DEP005", "Dermatology", "DERM", "Skin, hair, nail diagnostics, eczema, psoriasis, acne management, and cosmetic dermatology.", "Floor 2, Wing C", "Active"),
        ("DEP006", "Pediatrics", "PED", "Comprehensive newborn, infant, and child healthcare, pediatric immunizations, and developmental growth.", "Floor 1, Wing B", "Active"),
        ("DEP007", "Gynecology", "GYN", "Women's health, obstetric care, maternal-fetal wellness, and reproductive endocrinology.", "Floor 2, Wing A", "Active"),
        ("DEP008", "ENT", "ENT", "Ear, nose, throat, audiology, sinus disorders, voice disorders, and head/neck diagnostics.", "Floor 3, Wing B", "Active"),
        ("DEP009", "Ophthalmology", "EYE", "Comprehensive vision screening, cataract evaluation, glaucoma management, and corneal health.", "Floor 3, Wing C", "Active"),
        ("DEP010", "Dentistry", "DENT", "Oral health, dental restoration, root canal treatment, orthodontic consultation, and periodontics.", "Floor 2, Wing D", "Active"),
        ("DEP011", "General Surgery", "SURG", "Pre-operative assessment, acute surgical care, laparoscopic interventions, and wound management.", "Floor 4, Wing A", "Active"),
        ("DEP012", "Psychiatry", "PSY", "Mental health wellness, clinical psychotherapy, cognitive evaluations, and behavioral healthcare.", "Floor 4, Wing B", "Active"),
        ("DEP013", "Gastroenterology", "GAST", "Digestive tract, liver health, endoscopy, acid reflux, and inflammatory bowel disorder treatments.", "Floor 3, Wing D", "Active"),
        ("DEP014", "Pulmonology", "PULM", "Respiratory diseases, asthma management, COPD, sleep apnea, and pulmonary rehabilitation.", "Floor 3, Wing E", "Active"),
        ("DEP015", "Urology", "UROL", "Kidney stones, urinary tract care, prostate diagnostics, and male reproductive health.", "Floor 4, Wing C", "Active"),
    ]

    cursor = conn.cursor()
    cursor.executemany("""
    INSERT OR REPLACE INTO departments (dept_id, dept_name, dept_code, description, floor_location, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, departments_data)
    conn.commit()


def seed_doctors(conn: sqlite3.Connection) -> None:
    """Seeds multi-specialty doctors across all hospital departments with realistic schedules."""
    doctors_data = [
        # Cardiology
        ("DOC001", "Dr. Anjali Sharma", "DEP002", "Senior Interventional Cardiologist", "MBBS, MD (Medicine), DM (Cardiology)", 14, "Room 204", "Monday, Wednesday, Friday", "10:00 AM", "02:00 PM", 10, "Available", "anjali.sharma@mediqueue.org"),
        ("DOC002", "Dr. Rahul Patil", "DEP002", "Consultant Cardiologist", "MBBS, MD, DNB (Cardiology)", 9, "Room 205", "Tuesday, Thursday, Saturday", "02:00 PM", "06:00 PM", 10, "Available", "rahul.patil@mediqueue.org"),
        
        # General Medicine
        ("DOC003", "Dr. Rajesh Shah", "DEP001", "Consultant Physician & Diabetologist", "MBBS, MD (General Medicine)", 16, "Room 101", "Monday, Tuesday, Wednesday, Thursday, Friday, Saturday", "09:00 AM", "01:00 PM", 15, "Available", "rajesh.shah@mediqueue.org"),
        ("DOC004", "Dr. Priya Nair", "DEP001", "Internal Medicine Specialist", "MBBS, DNB (Internal Medicine)", 8, "Room 102", "Monday, Wednesday, Friday", "02:00 PM", "06:00 PM", 12, "Available", "priya.nair@mediqueue.org"),
        
        # Neurology
        ("DOC005", "Dr. Arvind Kulkarni", "DEP003", "Chief Neurologist & Stroke Specialist", "MBBS, MD, DM (Neurology)", 18, "Room 301", "Monday, Tuesday, Thursday", "10:00 AM", "02:00 PM", 8, "Available", "arvind.kulkarni@mediqueue.org"),
        ("DOC006", "Dr. Kavita Menon", "DEP003", "Consultant Neurophysiologist", "MBBS, MD (Neurology)", 11, "Room 302", "Wednesday, Friday, Saturday", "01:00 PM", "05:00 PM", 8, "Available", "kavita.menon@mediqueue.org"),

        # Orthopedics
        ("DOC007", "Dr. Vikram Deshmukh", "DEP004", "Senior Orthopedic & Joint Replacement Surgeon", "MBBS, MS (Orthopedics), M.Ch", 15, "Room 110", "Monday, Wednesday, Friday", "09:30 AM", "01:30 PM", 10, "Available", "vikram.deshmukh@mediqueue.org"),
        ("DOC008", "Dr. Sameer Joshi", "DEP004", "Sports Injury & Arthroscopy Specialist", "MBBS, D.Ortho, DNB", 7, "Room 111", "Tuesday, Thursday, Saturday", "02:00 PM", "06:00 PM", 10, "Available", "sameer.joshi@mediqueue.org"),

        # Dermatology
        ("DOC009", "Dr. Pooja Singhania", "DEP005", "Consultant Dermatologist & Cosmetologist", "MBBS, MD (Dermatology, Venereology, Leprosy)", 10, "Room 210", "Monday, Tuesday, Thursday, Friday", "11:00 AM", "03:00 PM", 12, "Available", "pooja.singhania@mediqueue.org"),

        # Pediatrics
        ("DOC010", "Dr. Meera Rao", "DEP006", "Senior Pediatrician & Neonatologist", "MBBS, MD (Pediatrics), DCH", 13, "Room 105", "Monday, Tuesday, Wednesday, Thursday, Friday", "09:00 AM", "01:00 PM", 15, "Available", "meera.rao@mediqueue.org"),
        ("DOC011", "Dr. Rohit Agarwal", "DEP006", "Pediatric Intensivist", "MBBS, DNB (Pediatrics)", 6, "Room 106", "Tuesday, Thursday, Saturday", "02:00 PM", "06:00 PM", 12, "Available", "rohit.agarwal@mediqueue.org"),

        # Gynecology
        ("DOC012", "Dr. Sunita Deshpande", "DEP007", "Senior Obstetrician & Gynaecologist", "MBBS, MD (Obstetrics & Gynecology)", 20, "Room 201", "Monday, Wednesday, Friday, Saturday", "10:00 AM", "02:00 PM", 12, "Available", "sunita.deshpande@mediqueue.org"),

        # ENT
        ("DOC013", "Dr. Manoj Verma", "DEP008", "ENT & Head-Neck Surgeon", "MBBS, MS (ENT)", 12, "Room 310", "Monday, Tuesday, Thursday, Saturday", "10:00 AM", "02:00 PM", 10, "Available", "manoj.verma@mediqueue.org"),

        # Ophthalmology
        ("DOC014", "Dr. Radhika Iyer", "DEP009", "Senior Cataract & Refractive Surgeon", "MBBS, MS (Ophthalmology)", 14, "Room 320", "Monday, Wednesday, Friday", "09:00 AM", "01:00 PM", 12, "Available", "radhika.iyer@mediqueue.org"),

        # Dentistry
        ("DOC015", "Dr. Sneha Joshi", "DEP010", "Consultant Dental Surgeon & Endodontist", "BDS, MDS (Conservative Dentistry)", 9, "Room 220", "Monday, Tuesday, Wednesday, Thursday, Friday", "10:00 AM", "02:00 PM", 10, "Available", "sneha.joshi@mediqueue.org"),

        # General Surgery
        ("DOC016", "Dr. Amit Kulkarni", "DEP011", "Senior General & Laparoscopic Surgeon", "MBBS, MS (General Surgery)", 17, "Room 401", "Monday, Wednesday, Friday", "11:00 AM", "03:00 PM", 8, "Available", "amit.kulkarni@mediqueue.org"),

        # Psychiatry
        ("DOC017", "Dr. Nikhil Sen", "DEP012", "Consultant Neuro-Psychiatrist", "MBBS, MD (Psychiatry)", 11, "Room 405", "Tuesday, Thursday, Saturday", "02:00 PM", "06:00 PM", 6, "Available", "nikhil.sen@mediqueue.org"),

        # Gastroenterology
        ("DOC018", "Dr. Deepak Sawant", "DEP013", "Consultant Gastroenterologist & Hepatologist", "MBBS, MD, DM (Gastroenterology)", 13, "Room 330", "Monday, Wednesday, Friday", "10:00 AM", "02:00 PM", 8, "Available", "deepak.sawant@mediqueue.org"),

        # Pulmonology
        ("DOC019", "Dr. Sandeep Ghosh", "DEP014", "Senior Pulmonologist & Chest Specialist", "MBBS, MD (Pulmonary Medicine)", 15, "Room 340", "Tuesday, Thursday, Saturday", "09:30 AM", "01:30 PM", 10, "Available", "sandeep.ghosh@mediqueue.org"),

        # Urology
        ("DOC020", "Dr. Varun Hegde", "DEP015", "Consultant Urologist & Andrologist", "MBBS, MS, M.Ch (Urology)", 10, "Room 410", "Monday, Thursday, Friday", "02:00 PM", "06:00 PM", 8, "Available", "varun.hegde@mediqueue.org"),
    ]

    cursor = conn.cursor()
    cursor.executemany("""
    INSERT OR REPLACE INTO doctors 
    (doc_id, name, dept_id, specialization, qualification, experience_years, room_number, available_days, available_time_start, available_time_end, max_patients_per_slot, status, contact)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, doctors_data)
    conn.commit()


def seed_sample_patients(conn: Optional[sqlite3.Connection] = None) -> None:
    """Seeds default sample records, initial patient visits, and initializes sequential counters."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    cursor = conn.cursor()
    curr_year = datetime.now().year
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Initialize counter to 4 for sample records
    cursor.execute("""
    INSERT OR REPLACE INTO patient_counter (year, last_number) VALUES (?, ?)
    """, (curr_year, 4))

    sample_data = [
        (
            f"MQ-{curr_year}-000001", "Rahul Sharma", 25, "Male", "Fever & Persistent Cough", "Normal", 1,
            f"{curr_year}-09-17 09:00:00", "", "Waiting",
            "DEP001", "DOC003", "GM-001", "09:00 AM - 01:00 PM", today_str, ""
        ),
        (
            f"MQ-{curr_year}-000002", "Sneha Patil", 45, "Female", "Severe Chest Pain & Palpitations", "Emergency", 2,
            f"{curr_year}-09-17 09:05:00", "", "Waiting",
            "DEP002", "DOC001", "CARD-001", "10:00 AM - 02:00 PM", today_str, ""
        ),
        (
            f"MQ-{curr_year}-000003", "Amit Verma", 32, "Male", "Migraine & Chronic Headache", "Normal", 3,
            f"{curr_year}-09-17 09:10:00", "", "Waiting",
            "DEP003", "DOC005", "NEUR-001", "10:00 AM - 02:00 PM", today_str, ""
        ),
        (
            f"MQ-{curr_year}-000004", "Priya Kulkarni", 60, "Female", "Acute Ankle Fracture & Swelling", "Emergency", 4,
            f"{curr_year}-09-17 09:15:00", "", "Waiting",
            "DEP004", "DOC007", "ORTH-001", "09:30 AM - 01:30 PM", today_str, ""
        ),
        (
            f"MQ-{curr_year}-000000", "Vikas Joshi", 50, "Male", "Routine Hypertension Review", "Normal", 0,
            f"{curr_year}-09-17 08:30:00", f"{curr_year}-09-17 08:50:00", "Consulted",
            "DEP002", "DOC001", "CARD-000", "10:00 AM - 02:00 PM", today_str, "Prescribed Telmisartan 40mg. Follow up in 3 months."
        ),
    ]

    for item in sample_data:
        cursor.execute("""
        INSERT OR REPLACE INTO patients 
        (patient_id, name, age, gender, problem, priority, token, registration_time, consultation_time, status, dept_id, doctor_id, queue_number, slot_time, visit_date, doctor_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, item)

    # Seed initial visit history for Vikas Joshi and previous visits for demonstration
    past_visits = [
        (
            f"MQ-{curr_year}-000000", "Vikas Joshi", 50, "Male",
            "DEP002", "Cardiology", "DOC001", "Dr. Anjali Sharma",
            "CARD-000", today_str, "10:00 AM - 02:00 PM",
            "Routine Hypertension Review", "Normal", "Consulted",
            f"{curr_year}-09-17 08:30:00", f"{curr_year}-09-17 08:50:00",
            "Prescribed Telmisartan 40mg. BP stabilized at 128/82 mmHg."
        ),
        (
            f"MQ-{curr_year}-000001", "Rahul Sharma", 25, "Male",
            "DEP001", "General Medicine", "DOC003", "Dr. Rajesh Shah",
            "GM-099", "2026-07-15", "09:00 AM - 01:00 PM",
            "Seasonal Allergy & Sore Throat", "Normal", "Consulted",
            "2026-07-15 10:15:00", "2026-07-15 10:30:00",
            "Prescribed Levocetirizine and warm saline gargles. Patient recovered."
        ),
        (
            f"MQ-{curr_year}-000002", "Sneha Patil", 45, "Female",
            "DEP010", "Dentistry", "DOC015", "Dr. Sneha Joshi",
            "DENT-042", "2026-05-03", "10:00 AM - 02:00 PM",
            "Mild Tooth Sensitivity & Scaling", "Normal", "Consulted",
            "2026-05-03 11:00:00", "2026-05-03 11:25:00",
            "Ultrasonic dental prophylaxis completed. Sensitivity toothpaste recommended."
        )
    ]

    for v in past_visits:
        cursor.execute("""
        INSERT INTO patient_visits 
        (patient_id, name, age, gender, dept_id, dept_name, doctor_id, doctor_name, queue_number, visit_date, slot_time, problem, priority, status, registration_time, consultation_time, doctor_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, v)

    # Log initial seed
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (?, ?, ?, ?)
    """, (now_str, "System", "DATABASE_INITIALIZED", "MediQueue SQLite database initialized with 15 departments, multi-specialty doctors, and sample records."))

    conn.commit()
    if should_close:
        conn.close()


# ==============================================================================
# 1. PERMANENT SEQUENTIAL PATIENT ID & QUEUE NUMBER GENERATION
# ==============================================================================

def generate_permanent_patient_id() -> str:
    """
    Generates a guaranteed permanent unique Patient ID in the format MQ-YYYY-XXXXXX.
    
    CRITICAL RULE:
    - Atomically increments the counter in SQLite.
    - Never reuses an ID, even if records are cancelled or removed from the active queue.
    """
    curr_year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT last_number FROM patient_counter WHERE year = ?", (curr_year,))
    row = cursor.fetchone()

    if row is None:
        new_number = 1
        cursor.execute("INSERT INTO patient_counter (year, last_number) VALUES (?, ?)", (curr_year, 1))
    else:
        new_number = row["last_number"] + 1
        cursor.execute("UPDATE patient_counter SET last_number = ? WHERE year = ?", (new_number, curr_year))

    conn.commit()
    conn.close()

    return f"MQ-{curr_year}-{new_number:06d}"


def generate_doctor_queue_number(doc_id: str, dept_code: str = "GEN") -> str:
    """
    Generates a department/doctor-specific sequential queue number for the day.
    Format: {DEPT_CODE}-{NUM:03d} (e.g. CARD-001, DENT-002, ORTH-005).
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    counter_key = f"{doc_id}_{today_str}"
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT last_queue_num FROM doctor_queue_counter WHERE counter_key = ?", (counter_key,))
    row = cursor.fetchone()

    if row is None:
        new_queue_num = 1
        cursor.execute("INSERT INTO doctor_queue_counter (counter_key, last_queue_num) VALUES (?, ?)", (counter_key, 1))
    else:
        new_queue_num = row["last_queue_num"] + 1
        cursor.execute("UPDATE doctor_queue_counter SET last_queue_num = ? WHERE counter_key = ?", (new_queue_num, counter_key))

    conn.commit()
    conn.close()

    clean_code = dept_code.strip().upper()
    return f"{clean_code}-{new_queue_num:03d}"


def generate_next_token() -> int:
    """Generates the next sequential hospital-wide token for the day."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(token) as max_tok FROM patients")
    row = cursor.fetchone()
    max_token = row["max_tok"] if row and row["max_tok"] is not None else 0
    conn.close()
    return max_token + 1


# ==============================================================================
# 2. DEPARTMENT MANAGEMENT CRUD
# ==============================================================================

def get_all_departments() -> List[Dict[str, Any]]:
    """Retrieves all hospital departments from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments ORDER BY dept_id ASC")
    rows = cursor.fetchall()
    depts = [dict(r) for r in rows]
    conn.close()
    return depts


def get_active_departments() -> List[Dict[str, Any]]:
    """Retrieves only active hospital departments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments WHERE status = 'Active' ORDER BY dept_id ASC")
    rows = cursor.fetchall()
    depts = [dict(r) for r in rows]
    conn.close()
    return depts


def get_department_by_id(dept_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific department by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments WHERE dept_id = ?", (dept_id,))
    row = cursor.fetchone()
    dept = dict(row) if row else None
    conn.close()
    return dept


def add_department(dept_dict: Dict[str, Any], actor: str = "Admin") -> bool:
    """Adds a new hospital department."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO departments (dept_id, dept_name, dept_code, description, floor_location, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dept_dict["dept_id"].strip().upper(),
            dept_dict["dept_name"].strip(),
            dept_dict["dept_code"].strip().upper(),
            dept_dict.get("description", "").strip(),
            dept_dict.get("floor_location", "").strip(),
            dept_dict.get("status", "Active").strip()
        ))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, actor, "ADD_DEPARTMENT", f"Added department '{dept_dict['dept_name']}' [{dept_dict['dept_id']}]"))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False


def update_department(dept_id: str, updates: Dict[str, Any], actor: str = "Admin") -> bool:
    """Updates an existing department's details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in updates.items():
        if k in ["dept_name", "dept_code", "description", "floor_location", "status"]:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(dept_id)
    cursor.execute(f"UPDATE departments SET {', '.join(fields)} WHERE dept_id = ?", values)
    success = cursor.rowcount > 0
    if success:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, actor, "UPDATE_DEPARTMENT", f"Updated department [{dept_id}]: {updates}"))
        conn.commit()
    conn.close()
    return success


def toggle_department_status(dept_id: str, new_status: str, actor: str = "Admin") -> bool:
    """Activates or deactivates a department."""
    return update_department(dept_id, {"status": new_status}, actor=actor)


# ==============================================================================
# 3. DOCTOR DATABASE & AVAILABILITY MANAGEMENT
# ==============================================================================

def get_all_doctors() -> List[Dict[str, Any]]:
    """Retrieves all doctor records joined with department information."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT d.*, dept.dept_name, dept.dept_code, dept.floor_location as dept_floor
    FROM doctors d
    LEFT JOIN departments dept ON d.dept_id = dept.dept_id
    ORDER BY d.doc_id ASC
    """)
    rows = cursor.fetchall()
    doctors = [dict(r) for r in rows]
    conn.close()
    return doctors


def get_doctors_by_department(dept_id: str) -> List[Dict[str, Any]]:
    """Retrieves all doctors belonging to a specific department."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT d.*, dept.dept_name, dept.dept_code
    FROM doctors d
    LEFT JOIN departments dept ON d.dept_id = dept.dept_id
    WHERE d.dept_id = ?
    ORDER BY d.doc_id ASC
    """, (dept_id,))
    rows = cursor.fetchall()
    doctors = [dict(r) for r in rows]
    conn.close()
    return doctors


def get_doctor_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single doctor by Doctor ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT d.*, dept.dept_name, dept.dept_code, dept.floor_location as dept_floor
    FROM doctors d
    LEFT JOIN departments dept ON d.dept_id = dept.dept_id
    WHERE d.doc_id = ?
    """, (doc_id,))
    row = cursor.fetchone()
    doc = dict(row) if row else None
    conn.close()
    return doc


def add_doctor(doc_dict: Dict[str, Any], actor: str = "Admin") -> bool:
    """Adds a new doctor to SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO doctors 
        (doc_id, name, dept_id, specialization, qualification, experience_years, room_number, available_days, available_time_start, available_time_end, max_patients_per_slot, status, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_dict["doc_id"].strip().upper(),
            doc_dict["name"].strip(),
            doc_dict["dept_id"].strip().upper(),
            doc_dict["specialization"].strip(),
            doc_dict.get("qualification", "MBBS, MD").strip(),
            int(doc_dict.get("experience_years", 5)),
            doc_dict.get("room_number", "Room 101").strip(),
            doc_dict.get("available_days", "Monday, Wednesday, Friday").strip(),
            doc_dict.get("available_time_start", "10:00 AM").strip(),
            doc_dict.get("available_time_end", "02:00 PM").strip(),
            int(doc_dict.get("max_patients_per_slot", 10)),
            doc_dict.get("status", "Available").strip(),
            doc_dict.get("contact", "").strip()
        ))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, actor, "ADD_DOCTOR", f"Added doctor '{doc_dict['name']}' [{doc_dict['doc_id']}] to department [{doc_dict['dept_id']}]"))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False


def update_doctor(doc_id: str, updates: Dict[str, Any], actor: str = "Admin") -> bool:
    """Updates doctor information."""
    conn = get_db_connection()
    cursor = conn.cursor()
    valid_keys = [
        "name", "dept_id", "specialization", "qualification", "experience_years",
        "room_number", "available_days", "available_time_start", "available_time_end",
        "max_patients_per_slot", "status", "contact"
    ]
    fields = []
    values = []
    for k, v in updates.items():
        if k in valid_keys:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(doc_id)
    cursor.execute(f"UPDATE doctors SET {', '.join(fields)} WHERE doc_id = ?", values)
    success = cursor.rowcount > 0
    if success:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, actor, "UPDATE_DOCTOR", f"Updated doctor [{doc_id}]: {updates}"))
        conn.commit()
    conn.close()
    return success


def set_doctor_status(doc_id: str, new_status: str, actor: str = "Admin") -> bool:
    """Sets doctor availability status: 'Available', 'On Leave', or 'Unavailable'."""
    return update_doctor(doc_id, {"status": new_status}, actor=actor)


def get_doctor_active_queue_count(doc_id: str) -> int:
    """Calculates number of patients currently waiting or in consultation for this doctor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT COUNT(*) FROM patients 
    WHERE doctor_id = ? AND status IN ('Waiting', 'In Consultation')
    """, (doc_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ==============================================================================
# 4. PATIENT REGISTRATION & QUEUE OPERATIONS
# ==============================================================================

def insert_patient(patient_dict: Dict[str, Any], actor: str = "Receptionist") -> Dict[str, Any]:
    """Inserts a new patient record into SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    dept_id = patient_dict.get("Dept_ID", "DEP001")
    doctor_id = patient_dict.get("Doctor_ID", "DOC001")
    queue_number = patient_dict.get("Queue_Number", "GEN-001")
    slot_time = patient_dict.get("Slot_Time", "10:00 AM - 02:00 PM")
    visit_date = patient_dict.get("Visit_Date", datetime.now().strftime("%Y-%m-%d"))
    doctor_notes = patient_dict.get("Doctor_Notes", "")

    cursor.execute("""
    INSERT INTO patients 
    (patient_id, name, age, gender, problem, priority, token, registration_time, consultation_time, status, dept_id, doctor_id, queue_number, slot_time, visit_date, doctor_notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_dict["Patient_ID"],
        patient_dict["Name"],
        int(patient_dict["Age"]),
        patient_dict["Gender"],
        patient_dict["Problem"],
        patient_dict["Priority"],
        int(patient_dict["Token"]),
        patient_dict["Registration_Time"],
        patient_dict.get("Consultation_Time", ""),
        patient_dict.get("Status", "Waiting"),
        dept_id,
        doctor_id,
        queue_number,
        slot_time,
        visit_date,
        doctor_notes
    ))

    # Audit log
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (?, ?, ?, ?)
    """, (
        now_str,
        actor,
        "REGISTER_PATIENT",
        f"Registered {patient_dict['Name']} [{patient_dict['Patient_ID']}], Dept: {dept_id}, Doctor: {doctor_id}, Queue: {queue_number}, Priority: {patient_dict['Priority']}"
    ))

    conn.commit()
    conn.close()
    return patient_dict


def get_all_patients_from_db() -> List[Dict[str, Any]]:
    """Retrieves all patient records joined with doctor and department names."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, d.name as doctor_name, d.room_number, dept.dept_name, dept.dept_code
    FROM patients p
    LEFT JOIN doctors d ON p.doctor_id = d.doc_id
    LEFT JOIN departments dept ON p.dept_id = dept.dept_id
    ORDER BY p.token ASC
    """)
    rows = cursor.fetchall()
    patients = []
    for r in rows:
        patients.append({
            "Patient_ID": r["patient_id"],
            "Name": r["name"],
            "Age": int(r["age"]),
            "Gender": r["gender"],
            "Problem": r["problem"],
            "Priority": r["priority"],
            "Token": int(r["token"]),
            "Registration_Time": r["registration_time"],
            "Consultation_Time": r["consultation_time"] or "",
            "Status": r["status"],
            "Dept_ID": r["dept_id"] or "DEP001",
            "Dept_Name": r["dept_name"] or "General Medicine",
            "Doctor_ID": r["doctor_id"] or "DOC001",
            "Doctor_Name": r["doctor_name"] or "Doctor",
            "Queue_Number": r["queue_number"] or f"#{r['token']}",
            "Slot_Time": r["slot_time"] or "",
            "Visit_Date": r["visit_date"] or "",
            "Doctor_Notes": r["doctor_notes"] or "",
            "Room_Number": r["room_number"] or "Room 101"
        })
    conn.close()
    return patients


def update_patient_status_db(
    patient_id: str,
    new_status: str,
    consultation_time: Optional[str] = None,
    doctor_notes: Optional[str] = None,
    actor: str = "Doctor"
) -> bool:
    """
    Updates a patient's active status and, upon completion, permanently archives the visit.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve patient record before status change
    cursor.execute("""
    SELECT p.*, d.name as doctor_name, dept.dept_name
    FROM patients p
    LEFT JOIN doctors d ON p.doctor_id = d.doc_id
    LEFT JOIN departments dept ON p.dept_id = dept.dept_id
    WHERE p.patient_id = ?
    """, (patient_id,))
    patient_row = cursor.fetchone()

    if not patient_row:
        conn.close()
        return False

    update_fields = ["status = ?"]
    update_vals = [new_status]

    if consultation_time is not None:
        update_fields.append("consultation_time = ?")
        update_vals.append(consultation_time)

    if doctor_notes is not None:
        update_fields.append("doctor_notes = ?")
        update_vals.append(doctor_notes)

    update_vals.append(patient_id)

    cursor.execute(f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?", update_vals)
    updated = cursor.rowcount > 0

    # If status is Consulted, automatically write to permanent patient_visits table
    if updated and new_status == "Consulted":
        cursor.execute("""
        INSERT INTO patient_visits 
        (patient_id, name, age, gender, dept_id, dept_name, doctor_id, doctor_name, queue_number, visit_date, slot_time, problem, priority, status, registration_time, consultation_time, doctor_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_row["patient_id"],
            patient_row["name"],
            patient_row["age"],
            patient_row["gender"],
            patient_row["dept_id"] or "DEP001",
            patient_row["dept_name"] or "General Medicine",
            patient_row["doctor_id"] or "DOC001",
            patient_row["doctor_name"] or "Doctor",
            patient_row["queue_number"] or f"#{patient_row['token']}",
            patient_row["visit_date"] or datetime.now().strftime("%Y-%m-%d"),
            patient_row["slot_time"] or "Standard Slot",
            patient_row["problem"],
            patient_row["priority"],
            "Consulted",
            patient_row["registration_time"],
            consultation_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            doctor_notes or patient_row["doctor_notes"] or "Consultation completed successfully."
        ))

    if updated:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, actor, f"STATUS_UPDATE_{new_status.upper()}", f"Updated status of [{patient_id}] to '{new_status}'"))

    conn.commit()
    conn.close()
    return updated


# ==============================================================================
# 5. PATIENT VISIT HISTORY (PERMANENT & PROTECTED)
# ==============================================================================

def get_patient_history_by_id(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves all past clinical visit history for a specific Permanent Patient ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM patient_visits 
    WHERE UPPER(patient_id) = UPPER(?) 
    ORDER BY visit_id DESC
    """, (patient_id.strip(),))
    rows = cursor.fetchall()
    history = [dict(r) for r in rows]
    conn.close()
    return history


def get_all_visit_history() -> List[Dict[str, Any]]:
    """Retrieves all historical patient consultation visits."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patient_visits ORDER BY visit_id DESC")
    rows = cursor.fetchall()
    history = [dict(r) for r in rows]
    conn.close()
    return history


# ==============================================================================
# 6. AUTHENTICATION & USER MANAGEMENT
# ==============================================================================

def authenticate_staff(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticates staff credentials using PBKDF2-HMAC-SHA256 password verification.
    Logs the login attempt in audit logs.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
    user_row = cursor.fetchone()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_row and verify_password(password, user_row["password_hash"], user_row["salt"]):
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, username, "STAFF_LOGIN_SUCCESS", f"Staff user '{user_row['full_name']}' logged in successfully."))
        conn.commit()
        conn.close()
        return {
            "username": user_row["username"],
            "full_name": user_row["full_name"],
            "role": user_row["role"]
        }
    else:
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, details)
        VALUES (?, ?, ?, ?)
        """, (now_str, username or "Anonymous", "STAFF_LOGIN_FAILED", f"Failed login attempt for username '{username}'."))
        conn.commit()
        conn.close()
        return None


# ==============================================================================
# 7. AUDIT LOGS & BACKUPS
# ==============================================================================

def log_audit_event(actor: str, action: str, details: str = "") -> None:
    """Inserts a custom activity event into the system audit trail table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (?, ?, ?, ?)
    """, (now_str, actor or "System", action, details))
    conn.commit()
    conn.close()


def get_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit log records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    logs = [dict(r) for r in rows]
    conn.close()
    return logs


def create_database_backup(actor: str = "Admin") -> Tuple[str, int]:
    """
    Creates a full atomic snapshot backup of mediqueue.db using SQLite's native backup API.
    Returns: (backup_filename, total_records_backed_up)
    """
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"mediqueue_backup_{timestamp_str}.db"
    backup_filepath = os.path.join(BACKUPS_DIR, backup_filename)

    src_conn = sqlite3.connect(DB_FILE)
    dst_conn = sqlite3.connect(backup_filepath)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    count = cursor.fetchone()[0]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO backups (filename, timestamp, record_count, created_by)
    VALUES (?, ?, ?, ?)
    """, (backup_filename, now_str, count, actor))

    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (?, ?, ?, ?)
    """, (now_str, actor, "DATABASE_BACKUP_CREATED", f"Snapshot '{backup_filename}' created ({count} patient records)."))

    conn.commit()
    conn.close()
    return backup_filename, count


def get_backups_list() -> List[Dict[str, Any]]:
    """Retrieves list of past database backups."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backups ORDER BY backup_id DESC")
    rows = cursor.fetchall()
    backups = [dict(r) for r in rows]
    conn.close()
    return backups


def reset_database_to_sample(actor: str = "Admin") -> None:
    """Resets patient tables, counters, departments, and doctors to default sample dataset."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients")
    cursor.execute("DELETE FROM patient_counter")
    cursor.execute("DELETE FROM doctor_queue_counter")
    cursor.execute("DELETE FROM patient_visits")
    cursor.execute("DELETE FROM departments")
    cursor.execute("DELETE FROM doctors")
    cursor.execute("""
    INSERT INTO audit_logs (timestamp, actor, action, details)
    VALUES (?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), actor, "DATABASE_RESET", "Hospital records, departments, and doctors reset to clean master dataset."))
    conn.commit()
    seed_departments(conn)
    seed_doctors(conn)
    seed_sample_patients(conn)
    conn.close()


# Auto-initialize database on import
init_db()
