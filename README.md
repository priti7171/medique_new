# 🏥 MediQueue – Multi-Department Hospital Patient Queue Management System

A modern, professional, and secure **Data Structures & Algorithms (DSA)** healthcare application in Python & Streamlit, fully prepared for local execution and deployment to **Streamlit Community Cloud**.

---

## 📌 Project Overview

In multi-specialty hospitals, patient flow must balance outpatient efficiency across various medical departments while providing immediate triage for life-threatening emergencies.

**MediQueue** is an enterprise-grade hospital patient queue engine featuring:
- **15 Standard Multi-Specialty Departments** (Cardiology, Neurology, Orthopedics, Pediatrics, Dentistry, etc.) with configurable administrative controls.
- **Doctor Management & Real-Time Availability Engine** (Available, Currently Consulting, Fully Booked, On Leave, Unavailable).
- **5-Step Patient Intake Workflow** (Select Dept ➔ Select Doctor ➔ Choose Slot ➔ Enter Patient Demographics ➔ Auto-Generate Identifiers).
- **Permanent Sequential Patient IDs** (`MQ-YYYY-XXXXXX`) managed by SQLite atomic counter table (**Never reused**).
- **Department-Specific Daily Queue Tokens** (`CARD-001`, `DENT-001`, `ORTH-002`).
- **Doctor-Specific Min-Heap Priority Queues** ($O(\log n)$) with emergency precedence and FIFO tie-breaking.
- **Protected Longitudinal Patient Visit History** permanently archived in SQLite.
- **Cryptographic Staff Authentication** (**PBKDF2-HMAC-SHA256** with 16-byte random salts).
- **Handcrafted DSA Algorithms** (Min-Heap, FIFO Queue, Binary Search, Linear Search, Bubble Sort, Insertion Sort, Hash Maps).

---

## 🚀 Key Features

| Feature | Details |
|---|---|
| 🏢 **15 Configurable Departments** | General Medicine, Cardiology, Neurology, Orthopedics, Dermatology, Pediatrics, Gynecology, ENT, Ophthalmology, Dentistry, General Surgery, Psychiatry, Gastroenterology, Pulmonology, Urology. Admins can add, edit, or toggle status. |
| 👨‍⚕️ **Doctor Availability Engine** | Calculates real-time status: Available, Consulting, Fully Booked, On Leave, or Unavailable based on active queue loads, schedules, and capacity limits. |
| 🆔 **Permanent Patient IDs vs Queue Numbers** | Permanent ID (`MQ-YYYY-XXXXXX`) uniquely tracks the patient for life; Queue Number (`CARD-001`) assigns their daily department position. |
| 🗄️ **SQLite Database Persistence** | Stored in `mediqueue.db` with structured tables: `departments`, `doctors`, `patients`, `patient_visits`, `patient_counter`, `doctor_queue_counter`, `users`, `audit_logs`, `backups`. |
| 🔒 **Staff & Admin Authentication** | Secure login with **PBKDF2-HMAC-SHA256 password hashing and random cryptographic salts**. No plain text passwords. |
| 📜 **Permanent Visit History Archive** | Complete longitudinal record of every patient consultation, retaining doctor notes, diagnosis, dates, and times even when removed from today's queue. |
| 🛡️ **Patient Privacy Protection** | Public queue display restricts sensitive diagnostic symptoms, showing only necessary triage indicators (Queue #, ID, Name, Dept, Doctor, Priority). |
| 📋 **Real-Time Audit Trail** | Logs all patient registrations, triage calls, status transitions, doctor modifications, logins, and backups. |
| 💾 **Instant Database Backups** | Atomic snapshot backups saved to the `backups/` directory with browser download support. |

---

## 🧠 Core DSA Implementation

| DSA Concept | File | Real-World Hospital Role | Time Complexity | Space Complexity |
|---|---|---|---|---|
| **Priority Queue (Min-Heap)** | `queue_manager.py` | Emergency cases (Rank 1) jump ahead of Normal cases (Rank 2) per doctor; Tokens break ties (FIFO). | Push: $O(\log n)$, Pop: $O(\log n)$ | $O(n)$ |
| **FIFO Queue** | `queue_manager.py` | Preserves arrival sequence for standard outpatients. | Enqueue: $O(1)$, Dequeue: $O(n)$ | $O(n)$ |
| **Hash Map (Dictionary)** | `queue_manager.py` | Instantaneous $O(1)$ indexing of departments by `dept_id` and doctors by `doc_id`. | Lookup: $O(1)$, Insert: $O(1)$ | $O(n)$ |
| **Binary Search** | `search_sort.py` | Divide-and-conquer search for Permanent Patient IDs (`MQ-YYYY-XXXXXX`) and Doctor IDs (`DOC001`). | Search: $O(\log n)$ | $O(1)$ |
| **Linear Search** | `search_sort.py` | Scans records across patient names, doctors, departments, symptoms, or queue numbers. | Search: $O(n)$ | $O(1)$ |
| **Bubble Sort** | `search_sort.py` | Reorders records by Priority, Age, Queue Number, Doctor, or Department. | Sorting: $O(n^2)$ | $O(1)$ |
| **Insertion Sort** | `search_sort.py` | Sorts records by Name, Age, Experience, or Room with element shift metrics. | Sorting: $O(n^2)$ | $O(1)$ |

---

## 📂 Project Structure

```text
MediQueue/
├── app.py                  # Main Streamlit application & navigation entry point
├── db_manager.py           # SQLite database engine, tables, migrations, PBKDF2 hashing & backups
├── queue_manager.py        # Patient class, FIFOQueue, Min-Heap PriorityQueue, Hash Maps & Controller
├── search_sort.py          # Custom Linear & Binary Search, Bubble & Insertion Sort
├── data_manager.py         # Persistence bridge module
├── test_dsa.py             # Automated unit tests for all DSA operations & clinical flows
├── assets/                 # High-resolution clinical imagery
│   ├── hospital_hero.jpg
│   └── doctor_consulting.jpg
├── backups/                # Database snapshot archive directory
├── requirements.txt        # Minimal Python dependencies (streamlit, pandas)
├── .gitignore              # Git ignore rules for clean repository
├── README.md               # Project & deployment documentation
└── VIVA_NOTES.md           # Comprehensive Viva Q&As + Architecture Guide
```

---

## 💻 Local Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run DSA Test Suite
```bash
python test_dsa.py
```

### 3. Run Streamlit App
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## ☁️ Deploying to Streamlit Community Cloud

### Step 1: Push Code to GitHub
Ensure all files (`app.py`, `requirements.txt`, `assets/`, `db_manager.py`, `queue_manager.py`, `search_sort.py`, `data_manager.py`, `test_dsa.py`) are committed and pushed to your GitHub repository.

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
2. Click **"New app"**.
3. Select your **Repository**, **Branch** (`main`), and set:
   - **Main file path:** `app.py`
4. Click **"Deploy!"**.

### Step 3: (Optional) Custom Secrets Configuration
If you wish to configure custom administrator and staff passwords in Streamlit Cloud, go to **App Settings > Secrets** and add:
```toml
[credentials]
admin_password = "YourCustomAdminPassword"
staff_password = "YourCustomStaffPassword"
```
*(If no secrets are configured, default demo credentials below will be used automatically).*

---

## 🔑 Default Staff Demo Credentials
| Role | Username | Default Password | Access Level |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full Access (Queue, Triage, Department/Doctor Admin, Audit Logs, Backups) |
| **Staff Nurse / Reception** | `staff` | `staff123` | Queue Intake, Doctor Desk, Patient Triage Management |
