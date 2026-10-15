"""
queue_manager.py
================
Implementation of Queue, Priority Queue, Hash Maps, and Controller for
the Hospital Patient Management System.

DATA STRUCTURES DEMONSTRATED:
1. Patient Object: Encapsulates patient details with comparison logic (__lt__) for Min-Heap.
2. FIFOQueue: Standard First-In-First-Out Queue for normal outpatients.
3. PriorityQueue: Min-Heap based Priority Queue for emergency & normal triage per doctor.
4. Hash Maps (Dictionary Lookups): O(1) instantaneous indexing for Departments and Doctors.
5. HospitalQueueController: Coordinates department-wise and doctor-wise queues, availability,
   and permanent SQLite persistence.

DESIGNED FOR: 1st Year AI & Data Science DSA Mini-Project / Viva Examination.
"""

import heapq
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import db_manager


class Patient:
    """
    Represents a patient in the hospital system.
    
    DSA CONCEPTS:
    - Encapsulation: Bundles patient demographics, triage priority, department, and doctor assignment.
    - Custom comparison logic (__lt__) enables automatic ordering inside Min-Heap:
      1. Emergency (Priority Rank 1) comes BEFORE Normal (Priority Rank 2).
      2. If Priority is identical, lower Token number comes FIRST (FIFO principle).
    """

    def __init__(
        self,
        patient_id: str,
        name: str,
        age: int,
        gender: str,
        problem: str,
        priority: str = "Normal",
        token: int = 1,
        registration_time: Optional[str] = None,
        consultation_time: str = "",
        status: str = "Waiting",
        dept_id: str = "DEP001",
        dept_name: str = "General Medicine",
        doctor_id: str = "DOC001",
        doctor_name: str = "Doctor",
        queue_number: str = "GEN-001",
        slot_time: str = "10:00 AM - 02:00 PM",
        visit_date: str = "",
        doctor_notes: str = "",
        room_number: str = "Room 101"
    ):
        self.patient_id = patient_id.strip().upper()
        self.name = name.strip()
        self.age = int(age)
        self.gender = gender.strip()
        self.problem = problem.strip()
        self.priority = priority.strip().capitalize()  # "Emergency" or "Normal"
        self.token = int(token)
        self.registration_time = registration_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.consultation_time = consultation_time
        self.status = status.strip().capitalize()  # "Waiting", "In Consultation", "Consulted", "Cancelled"
        self.dept_id = dept_id.strip().upper()
        self.dept_name = dept_name.strip()
        self.doctor_id = doctor_id.strip().upper()
        self.doctor_name = doctor_name.strip()
        self.queue_number = queue_number.strip().upper()
        self.slot_time = slot_time.strip()
        self.visit_date = visit_date or datetime.now().strftime("%Y-%m-%d")
        self.doctor_notes = doctor_notes.strip()
        self.room_number = room_number.strip()

    @property
    def priority_rank(self) -> int:
        """
        Numeric rank for priority ordering:
        Emergency -> Rank 1 (Highest priority, jumps to head of queue)
        Normal    -> Rank 2 (Standard outpatient priority)
        """
        return 1 if self.priority == "Emergency" else 2

    def __lt__(self, other: "Patient") -> bool:
        """
        Min-Heap comparison operator:
        - Primary key: priority_rank (1 < 2, so Emergency comes first)
        - Secondary key: token (lower token arrived earlier -> maintains FIFO order)
        """
        if self.priority_rank != other.priority_rank:
            return self.priority_rank < other.priority_rank
        return self.token < other.token

    def __repr__(self) -> str:
        return f"<Patient {self.patient_id} | {self.name} | Queue: {self.queue_number} | Doc: {self.doctor_name} | {self.priority} | {self.status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert Patient instance to dictionary format."""
        return {
            "Patient_ID": self.patient_id,
            "Name": self.name,
            "Age": self.age,
            "Gender": self.gender,
            "Problem": self.problem,
            "Priority": self.priority,
            "Token": self.token,
            "Registration_Time": self.registration_time,
            "Consultation_Time": self.consultation_time,
            "Status": self.status,
            "Dept_ID": self.dept_id,
            "Dept_Name": self.dept_name,
            "Doctor_ID": self.doctor_id,
            "Doctor_Name": self.doctor_name,
            "Queue_Number": self.queue_number,
            "Slot_Time": self.slot_time,
            "Visit_Date": self.visit_date,
            "Doctor_Notes": self.doctor_notes,
            "Room_Number": self.room_number
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Patient":
        """Create Patient instance from dictionary data."""
        return cls(
            patient_id=str(data.get("Patient_ID", "")),
            name=str(data.get("Name", "")),
            age=int(data.get("Age", 0)),
            gender=str(data.get("Gender", "Other")),
            problem=str(data.get("Problem", "General Consultation")),
            priority=str(data.get("Priority", "Normal")),
            token=int(data.get("Token", 1)),
            registration_time=str(data.get("Registration_Time", "")),
            consultation_time=str(data.get("Consultation_Time", "")),
            status=str(data.get("Status", "Waiting")),
            dept_id=str(data.get("Dept_ID", "DEP001")),
            dept_name=str(data.get("Dept_Name", "General Medicine")),
            doctor_id=str(data.get("Doctor_ID", "DOC001")),
            doctor_name=str(data.get("Doctor_Name", "Doctor")),
            queue_number=str(data.get("Queue_Number", f"#{data.get('Token', 1)}")),
            slot_time=str(data.get("Slot_Time", "10:00 AM - 02:00 PM")),
            visit_date=str(data.get("Visit_Date", "")),
            doctor_notes=str(data.get("Doctor_Notes", "")),
            room_number=str(data.get("Room_Number", "Room 101"))
        )


class FIFOQueue:
    """
    Standard First-In-First-Out (FIFO) Queue implementation.
    
    DSA CONCEPTS:
    - Enqueue: Adds element at the rear / back (O(1)).
    - Dequeue: Removes element from the front (O(1)).
    - Peek: Returns element at front without removing (O(1)).
    - Used to maintain pure arrival-order queue for standard outpatients.
    """

    def __init__(self):
        self._items: List[Patient] = []

    def enqueue(self, patient: Patient) -> None:
        """Add patient to the rear of the queue (FIFO). Time: O(1)."""
        self._items.append(patient)

    def dequeue(self) -> Optional[Patient]:
        """Remove and return the front patient. Time: O(n) for list.pop(0)."""
        if self.is_empty():
            return None
        return self._items.pop(0)

    def peek(self) -> Optional[Patient]:
        """Look at the front patient without removing. Time: O(1)."""
        if self.is_empty():
            return None
        return self._items[0]

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return number of patients currently in queue."""
        return len(self._items)

    def to_list(self) -> List[Patient]:
        """Return a shallow copy of items in queue."""
        return list(self._items)


class PriorityQueue:
    """
    Min-Heap based Priority Queue implementation.
    
    DSA CONCEPTS:
    - Elements are ordered automatically by Patient.__lt__ (Priority Rank, then Token).
    - Emergency patients (Rank 1) are always at the root of the heap.
    - Normal patients (Rank 2) wait behind Emergency patients.
    - Tie-breaking on Token guarantees FIFO order within the same priority level.
    - Push: Insert new patient into heap in O(log n) time.
    - Pop: Remove and return highest-priority patient in O(log n) time.
    - Peek: Access highest-priority patient in O(1) time.
    """

    def __init__(self):
        self._heap: List[Patient] = []

    def push(self, patient: Patient) -> None:
        """Insert patient into the min-heap. Time: O(log n)."""
        heapq.heappush(self._heap, patient)

    def pop(self) -> Optional[Patient]:
        """Remove and return the highest-priority patient. Time: O(log n)."""
        if self.is_empty():
            return None
        return heapq.heappop(self._heap)

    def peek(self) -> Optional[Patient]:
        """Return the next patient to be called without removing. Time: O(1)."""
        if self.is_empty():
            return None
        return self._heap[0]

    def is_empty(self) -> bool:
        """Check if priority queue has no waiting patients."""
        return len(self._heap) == 0

    def size(self) -> int:
        """Return count of waiting patients."""
        return len(self._heap)

    def get_sorted_list(self) -> List[Patient]:
        """
        Returns all waiting patients in strict priority order.
        Time: O(n log n) by sorting a copy of the heap.
        """
        return sorted(self._heap)


class HospitalQueueController:
    """
    Central Coordinator for Multi-Department & Doctor-Wise Queues.
    
    DSA INTEGRATION:
    1. Hash Map (Dictionary): Fast O(1) indexing of Departments and Doctors.
    2. Per-Doctor Priority Queues: Dedicated Min-Heap per doctor to ensure
       emergency cases take precedence while maintaining doctor queue separation.
    3. Global Priority Queue: Hospital-wide triage view.
    """

    def __init__(self):
        # Hash Maps for O(1) lookups
        self.departments_map: Dict[str, Dict[str, Any]] = {}
        self.doctors_map: Dict[str, Dict[str, Any]] = {}
        
        # Per-Doctor Min-Heap Priority Queues: doc_id -> PriorityQueue
        self.doctor_queues: Dict[str, PriorityQueue] = {}
        
        # Global Priority Queue for all waiting patients across the hospital
        self.global_priority_queue = PriorityQueue()
        
        self.refresh_from_storage()

    def refresh_from_storage(self) -> None:
        """
        Reloads all departments, doctors, and active patient queues from SQLite.
        Reconstructs memory Hash Maps and per-doctor Min-Heap Priority Queues.
        """
        # 1. Load Departments into Hash Map
        depts = db_manager.get_all_departments()
        self.departments_map = {d["dept_id"]: d for d in depts}

        # 2. Load Doctors into Hash Map & Initialize per-doctor priority queues
        docs = db_manager.get_all_doctors()
        self.doctors_map = {d["doc_id"]: d for d in docs}
        self.doctor_queues = {d["doc_id"]: PriorityQueue() for d in docs}

        # 3. Load Active Patients into Doctor Queues & Global Queue
        self.global_priority_queue = PriorityQueue()
        all_records = db_manager.get_all_patients_from_db()
        for r in all_records:
            if r.get("Status") == "Waiting":
                patient = Patient.from_dict(r)
                doc_id = patient.doctor_id
                if doc_id not in self.doctor_queues:
                    self.doctor_queues[doc_id] = PriorityQueue()
                self.doctor_queues[doc_id].push(patient)
                self.global_priority_queue.push(patient)

    # ==========================================================================
    # DOCTOR AVAILABILITY CALCULATION ENGINE
    # ==========================================================================

    def get_doctor_availability_status(
        self,
        doc_id: str,
        selected_slot: Optional[str] = None
    ) -> Tuple[str, str, bool]:
        """
        Evaluates real-time availability of a doctor.
        
        Returns:
            Tuple of (status_badge, explanation_message, is_bookable)
            - "Available" (Green, is_bookable=True)
            - "Currently Consulting" (Blue, is_bookable=True if slots remain)
            - "Fully Booked" (Orange, is_bookable=False)
            - "On Leave" (Red, is_bookable=False)
            - "Unavailable" (Gray, is_bookable=False)
        """
        doc = self.doctors_map.get(doc_id)
        if not doc:
            return "Unavailable", "Doctor record not found.", False

        doc_status = doc.get("status", "Available")
        doc_name = doc.get("name", "Doctor")

        # 1. Check Leave or Administrative Unavailable Status
        if doc_status == "On Leave":
            return "On Leave", f"{doc_name} is currently on approved leave.", False
        elif doc_status == "Unavailable":
            return "Unavailable", f"{doc_name} is currently unavailable for consultations.", False

        # 2. Check Capacity & Current Queue Load
        active_queue_count = len(self.get_waiting_patients_for_doctor(doc_id))
        max_slots = doc.get("max_patients_per_slot", 10)
        
        # Check if doctor is currently consulting a patient
        active_consulting = self.get_current_in_consultation_for_doctor(doc_id)

        if active_queue_count >= max_slots:
            return "Fully Booked", f"This time slot is fully booked ({active_queue_count}/{max_slots} patients). Please select another doctor or slot.", False

        if active_consulting:
            remaining = max_slots - active_queue_count
            return "Currently Consulting", f"{doc_name} is currently consulting (Active Queue: {active_queue_count}, {remaining} slots remaining).", True

        remaining = max_slots - active_queue_count
        return "Available", f"{doc_name} is available for consultation ({remaining} slots available).", True

    # ==========================================================================
    # REGISTRATION & QUEUE OPERATIONS
    # ==========================================================================

    def register_patient(
        self,
        name: str,
        age: int,
        gender: str,
        problem: str,
        priority: str,
        dept_id: str,
        doctor_id: str,
        slot_time: str,
        custom_id: Optional[str] = None,
        actor: str = "Receptionist"
    ) -> Patient:
        """
        Registers a patient for a specific department and doctor:
        1. Auto-generates permanent unique Patient ID (MQ-YYYY-XXXXXX) via atomic SQLite counter.
        2. Auto-generates department-specific Queue Number (e.g. CARD-001, ORTH-002).
        3. Enforces doctor availability check (blocks On Leave / Fully Booked).
        4. Saves to SQLite persistent database.
        5. Enqueues into the Doctor's specific Min-Heap Priority Queue.
        """
        # Validate doctor availability
        avail_status, msg, is_bookable = self.get_doctor_availability_status(doctor_id, selected_slot=slot_time)
        if not is_bookable and priority != "Emergency":
            raise ValueError(msg)

        # Retrieve department and doctor names from Hash Maps
        dept = self.departments_map.get(dept_id, {})
        dept_name = dept.get("dept_name", "General Medicine")
        dept_code = dept.get("dept_code", "GEN")

        doc = self.doctors_map.get(doctor_id, {})
        doctor_name = doc.get("name", "Doctor")
        room_number = doc.get("room_number", "Room 101")

        # Generate Identifiers
        patient_id = custom_id.strip().upper() if custom_id and custom_id.strip() else db_manager.generate_permanent_patient_id()
        queue_number = db_manager.generate_doctor_queue_number(doctor_id, dept_code)
        token = db_manager.generate_next_token()
        reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        visit_date = datetime.now().strftime("%Y-%m-%d")

        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=age,
            gender=gender,
            problem=problem,
            priority=priority,
            token=token,
            registration_time=reg_time,
            status="Waiting",
            dept_id=dept_id,
            dept_name=dept_name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            queue_number=queue_number,
            slot_time=slot_time,
            visit_date=visit_date,
            doctor_notes="",
            room_number=room_number
        )

        # Save to SQLite Database
        db_manager.insert_patient(patient.to_dict(), actor=actor)

        # Push to in-memory priority queues
        if doctor_id not in self.doctor_queues:
            self.doctor_queues[doctor_id] = PriorityQueue()
        self.doctor_queues[doctor_id].push(patient)
        self.global_priority_queue.push(patient)

        return patient

    def get_waiting_patients_for_doctor(self, doc_id: str) -> List[Patient]:
        """Returns all currently waiting patients for a specific doctor in priority order."""
        self.refresh_from_storage()
        queue = self.doctor_queues.get(doc_id)
        if queue:
            return queue.get_sorted_list()
        return []

    def get_waiting_patients_for_dept(self, dept_id: str) -> List[Patient]:
        """Returns all waiting patients for a specific department."""
        self.refresh_from_storage()
        waiting_all = self.global_priority_queue.get_sorted_list()
        return [p for p in waiting_all if p.dept_id == dept_id]

    def get_waiting_patients(self) -> List[Patient]:
        """Returns all currently waiting patients across all departments in priority order."""
        self.refresh_from_storage()
        return self.global_priority_queue.get_sorted_list()

    def get_next_patient_for_doctor(self, doc_id: str) -> Optional[Patient]:
        """Peeks at the next highest-priority patient waiting for this doctor."""
        self.refresh_from_storage()
        queue = self.doctor_queues.get(doc_id)
        if queue:
            return queue.peek()
        return None

    def get_next_patient_preview(self) -> Optional[Patient]:
        """Global preview of the next highest-priority patient across the hospital."""
        self.refresh_from_storage()
        return self.global_priority_queue.peek()

    def get_current_in_consultation_for_doctor(self, doc_id: str) -> Optional[Patient]:
        """Finds any patient currently marked as 'In Consultation' with this specific doctor."""
        records = db_manager.get_all_patients_from_db()
        for r in records:
            if r.get("Status") == "In Consultation" and r.get("Doctor_ID") == doc_id:
                return Patient.from_dict(r)
        return None

    def get_current_in_consultation(self) -> Optional[Patient]:
        """Finds any patient currently marked as 'In Consultation' hospital-wide."""
        records = db_manager.get_all_patients_from_db()
        for r in records:
            if r.get("Status") == "In Consultation":
                return Patient.from_dict(r)
        return None

    def call_next_patient_for_doctor(self, doc_id: str, actor: str = "Doctor") -> Optional[Patient]:
        """
        Dispatches the next highest-priority patient for a specific doctor:
        - If an existing patient is in consultation with this doctor, auto-completes their consultation.
        - Updates the next patient's status to 'In Consultation' in SQLite.
        """
        self.refresh_from_storage()

        # If a patient is already in consultation with this doctor, finish them
        active_patient = self.get_current_in_consultation_for_doctor(doc_id)
        if active_patient:
            self.complete_consultation(active_patient.patient_id, doctor_notes="Consultation concluded.", actor=actor)

        # Pop from doctor's specific priority queue
        queue = self.doctor_queues.get(doc_id)
        if not queue or queue.is_empty():
            return None

        next_patient = queue.pop()
        if not next_patient:
            return None

        next_patient.status = "In Consultation"
        db_manager.update_patient_status_db(next_patient.patient_id, "In Consultation", actor=actor)
        self.refresh_from_storage()
        return next_patient

    def call_next_patient(self, actor: str = "Doctor") -> Optional[Patient]:
        """Global call next patient dispatcher for backward compatibility."""
        next_p = self.get_next_patient_preview()
        if next_p:
            return self.call_next_patient_for_doctor(next_p.doctor_id, actor=actor)
        return None

    def complete_consultation(
        self,
        patient_id: str,
        doctor_notes: str = "",
        actor: str = "Doctor"
    ) -> bool:
        """
        Marks patient as 'Consulted' and archives permanent visit record.
        """
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = db_manager.update_patient_status_db(
            patient_id,
            "Consulted",
            consultation_time=now_time,
            doctor_notes=doctor_notes,
            actor=actor
        )
        self.refresh_from_storage()
        return success

    def cancel_patient(self, patient_id: str, actor: str = "Receptionist") -> bool:
        """Cancels a waiting patient from active queue."""
        success = db_manager.update_patient_status_db(patient_id, "Cancelled", actor=actor)
        self.refresh_from_storage()
        return success

    def get_consultation_history(self) -> List[Patient]:
        """Returns all patients who have completed consultation."""
        records = db_manager.get_all_patients_from_db()
        return [Patient.from_dict(r) for r in records if r.get("Status") == "Consulted"]

    def get_all_patients(self) -> List[Patient]:
        """Returns all patient records across all statuses."""
        records = db_manager.get_all_patients_from_db()
        return [Patient.from_dict(r) for r in records]

    def get_patient_past_visits(self, patient_id: str) -> List[Dict[str, Any]]:
        """Retrieves permanent historical visit records for a patient ID."""
        return db_manager.get_patient_history_by_id(patient_id)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Calculates hospital-wide analytics and live queue metrics:
        - Total Departments
        - Total Doctors & Available Doctors
        - Doctors on Leave
        - Total Patients
        - Currently Waiting & Emergency Waiting
        - Consultations Completed Today
        """
        records = db_manager.get_all_patients_from_db()
        total = len(records)
        waiting = 0
        emergency_waiting = 0
        consulted = 0
        in_consultation = 0

        for r in records:
            st = r.get("Status")
            prio = r.get("Priority")
            if st == "Waiting":
                waiting += 1
                if prio == "Emergency":
                    emergency_waiting += 1
            elif st == "Consulted":
                consulted += 1
            elif st == "In Consultation":
                in_consultation += 1

        all_docs = db_manager.get_all_doctors()
        total_docs = len(all_docs)
        docs_avail = sum(1 for d in all_docs if d.get("status") == "Available")
        docs_on_leave = sum(1 for d in all_docs if d.get("status") == "On Leave")
        total_depts = len(self.departments_map)

        return {
            "total": total,
            "waiting": waiting,
            "emergency_waiting": emergency_waiting,
            "consulted": consulted,
            "in_consultation": in_consultation,
            "total_departments": total_depts,
            "total_doctors": total_docs,
            "doctors_available": docs_avail,
            "doctors_on_leave": docs_on_leave
        }
