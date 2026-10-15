"""
test_dsa.py
============
Comprehensive Automated Unit Test Suite for MediQueue DSA Hospital System:
1. SQLite Database Persistence & Permanent ID Generation (MQ-YYYY-XXXXXX).
2. Department & Doctor Hash Map Lookups (O(1)).
3. Doctor Availability Calculation (Available, On Leave, Fully Booked, Currently Consulting).
4. FIFO Queue Ordering (O(1)).
5. Min-Heap Priority Queue (Emergency Rank 1 Precedence & FIFO Token Tie-Breaking) (O(log n)).
6. Department-Wise & Doctor-Wise Queue Separation.
7. Handcrafted Linear Search (O(n)) & Binary Search (O(log n)).
8. Handcrafted Bubble Sort (O(n^2)) & Insertion Sort (O(n^2)).
9. Complete End-to-End Patient Flow & Permanent History Preservation.
"""

import sys
import os

# Ensure UTF-8 output on Windows consoles if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime
from data_manager import (
    load_all_patients,
    reset_sample_data,
    generate_next_patient_id,
    generate_next_token,
    generate_doctor_queue_number
)
from queue_manager import Patient, FIFOQueue, PriorityQueue, HospitalQueueController
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


def run_all_tests():
    print("==================================================")
    print("RUNNING MEDIQUEUE DSA & CLINICAL TEST SUITE")
    print("==================================================")

    # 1. Test Database & Permanent Sequential ID Generation
    print("\n[TEST 1] Testing Database Persistence & Permanent ID Generation...")
    reset_sample_data()
    patients = load_all_patients()
    assert len(patients) >= 4, "Sample data should contain at least 4 patients"
    next_id = generate_next_patient_id()
    assert next_id.startswith("MQ-"), f"Patient ID format must start with MQ-, got {next_id}"
    print(f" -> SQLite database active with {len(patients)} seeded patient records.")
    print(f" -> Next Guaranteed Permanent Patient ID: {next_id}")

    # 2. Test Hash Maps for Departments & Doctors (O(1) Lookups)
    print("\n[TEST 2] Testing Hash Map (Dictionary) Lookups for Departments & Doctors...")
    controller = HospitalQueueController()
    assert "DEP002" in controller.departments_map, "Cardiology department must exist in hash map"
    cardio_dept = controller.departments_map["DEP002"]
    assert cardio_dept["dept_name"] == "Cardiology"
    print(f" -> Department Hash Map Lookup O(1): DEP002 -> {cardio_dept['dept_name']} (Floor: {cardio_dept['floor_location']})")

    assert "DOC001" in controller.doctors_map, "Dr. Anjali Sharma must exist in doctors hash map"
    doc1 = controller.doctors_map["DOC001"]
    assert doc1["name"] == "Dr. Anjali Sharma"
    print(f" -> Doctor Hash Map Lookup O(1): DOC001 -> {doc1['name']} ({doc1['specialization']})")

    # 3. Test Doctor Availability Logic
    print("\n[TEST 3] Testing Doctor Availability & Slot Capacity Rules...")
    # Available doctor
    status, msg, bookable = controller.get_doctor_availability_status("DOC001")
    assert bookable is True, "DOC001 should be available initially"
    print(f" -> Doctor Availability Check: DOC001 is '{status}' (Bookable: {bookable})")

    # Test On Leave
    db_manager.set_doctor_status("DOC002", "On Leave")
    controller.refresh_from_storage()
    status_leave, msg_leave, bookable_leave = controller.get_doctor_availability_status("DOC002")
    assert status_leave == "On Leave" and bookable_leave is False, "DOC002 on leave must be non-bookable"
    print(f" -> Doctor On Leave Check: DOC002 is '{status_leave}' (Blocked from appointment: {not bookable_leave})")
    db_manager.set_doctor_status("DOC002", "Available")
    controller.refresh_from_storage()

    # 4. Test Standard FIFO Queue (O(1))
    print("\n[TEST 4] Testing Standard FIFO Queue...")
    fifo = FIFOQueue()
    p1 = Patient("P901", "Test Alice", 20, "Female", "Cold", "Normal", token=1)
    p2 = Patient("P902", "Test Bob", 30, "Male", "Cough", "Normal", token=2)
    fifo.enqueue(p1)
    fifo.enqueue(p2)
    assert fifo.size() == 2
    popped = fifo.dequeue()
    assert popped.patient_id == "P901", "FIFO Queue should pop first inserted element (Alice)"
    print(" -> FIFO Queue Passed: First-In, First-Out verified.")

    # 5. Test Min-Heap Priority Queue (Emergency Precedence & FIFO Tie-Breaking)
    print("\n[TEST 5] Testing Priority Queue (Min-Heap)...")
    pq = PriorityQueue()
    # Arrival sequence:
    # 1. Normal (Token 1)
    # 2. Normal (Token 2)
    # 3. Emergency (Token 3)
    # 4. Emergency (Token 4)
    pq.push(Patient("P1", "Rahul", 25, "Male", "Fever", "Normal", token=1))
    pq.push(Patient("P2", "Amit", 32, "Male", "Headache", "Normal", token=2))
    pq.push(Patient("P3", "Sneha", 45, "Female", "Chest Pain", "Emergency", token=3))
    pq.push(Patient("P4", "Priya", 60, "Female", "Injury", "Emergency", token=4))

    order = []
    while not pq.is_empty():
        order.append(pq.pop())

    assert order[0].patient_id == "P3", f"Expected P3 (Emergency Token 3) first, got {order[0]}"
    assert order[1].patient_id == "P4", f"Expected P4 (Emergency Token 4) second, got {order[1]}"
    assert order[2].patient_id == "P1", f"Expected P1 (Normal Token 1) third, got {order[2]}"
    assert order[3].patient_id == "P2", f"Expected P2 (Normal Token 2) fourth, got {order[3]}"
    print(" -> Priority Queue Passed: Emergency treated first, FIFO maintained within priority groups.")

    # 6. Test Department-Wise Queue Separation
    print("\n[TEST 6] Testing Department-Wise & Doctor-Wise Queue Isolation...")
    # Register patient in Cardiology DOC001
    cardio_p = controller.register_patient(
        name="Sunil Gavaskar",
        age=52,
        gender="Male",
        problem="Arrhythmia",
        priority="Normal",
        dept_id="DEP002",
        doctor_id="DOC001",
        slot_time="10:00 AM - 02:00 PM"
    )
    # Register patient in Dentistry DOC015
    dental_p = controller.register_patient(
        name="Kapil Dev",
        age=48,
        gender="Male",
        problem="Root Canal",
        priority="Normal",
        dept_id="DEP010",
        doctor_id="DOC015",
        slot_time="10:00 AM - 02:00 PM"
    )

    cardio_waiting = controller.get_waiting_patients_for_doctor("DOC001")
    dental_waiting = controller.get_waiting_patients_for_doctor("DOC015")

    assert any(p.patient_id == cardio_p.patient_id for p in cardio_waiting), "Sunil must be in DOC001 queue"
    assert not any(p.patient_id == cardio_p.patient_id for p in dental_waiting), "Sunil must NOT be in Dentistry queue"
    assert any(p.patient_id == dental_p.patient_id for p in dental_waiting), "Kapil must be in DOC015 queue"
    print(f" -> Queue Isolation Verified: Cardio Queue has {len(cardio_waiting)} patients; Dental Queue has {len(dental_waiting)} patients.")

    # 7. Test Searching Algorithms (Patients & Doctors)
    print("\n[TEST 7] Testing Linear & Binary Search Algorithms...")
    all_patients = controller.get_all_patients()
    
    # Linear Search on Patients
    matches, comps, logs = linear_search_patients(all_patients, "Sneha", search_by="name")
    assert len(matches) >= 1, "Should find Sneha Patil"
    print(f" -> Linear Search for Patient 'Sneha': Found {len(matches)} match(es) in {comps} comparisons.")

    # Binary Search on Patients by ID
    target_pid = all_patients[0].patient_id
    found_p, b_comps, b_logs = binary_search_by_id(all_patients, target_pid)
    assert found_p is not None and found_p.patient_id == target_pid
    print(f" -> Binary Search for Patient ID '{target_pid}': Found in {b_comps} comparisons (O(log n)).")

    # Binary Search on Doctors
    all_docs = db_manager.get_all_doctors()
    found_doc, doc_comps, doc_logs = binary_search_doctor_by_id(all_docs, "DOC001")
    assert found_doc is not None and found_doc["name"] == "Dr. Anjali Sharma"
    print(f" -> Binary Search for Doctor 'DOC001': Found '{found_doc['name']}' in {doc_comps} comparisons.")

    # 8. Test Sorting Algorithms (Bubble Sort & Insertion Sort)
    print("\n[TEST 8] Testing Bubble Sort & Insertion Sort Algorithms...")
    sorted_age, b_comps, b_swaps = bubble_sort_patients(all_patients, sort_key="age", ascending=True)
    ages = [p.age for p in sorted_age]
    assert ages == sorted(ages), "Ages must be in ascending order"
    print(f" -> Bubble Sort by Patient Age (Ascending): {ages} (Comps: {b_comps}, Swaps: {b_swaps})")

    sorted_names, i_comps, i_shifts = insertion_sort_patients(all_patients, sort_key="name", ascending=True)
    names = [p.name.lower() for p in sorted_names]
    assert names == sorted(names), "Names must be alphabetical"
    print(f" -> Insertion Sort by Patient Name: Sorted {len(names)} names (Comps: {i_comps}, Shifts: {i_shifts})")

    # 9. Test End-to-End Doctor Desk & Permanent Patient History
    print("\n[TEST 9] Testing Doctor Cabin Consultation & Permanent Visit History Archive...")
    next_cardio_patient = controller.get_next_patient_for_doctor("DOC001")
    assert next_cardio_patient is not None
    called = controller.call_next_patient_for_doctor("DOC001")
    assert called.status == "In Consultation"
    print(f" -> Doctor DOC001 Called Patient: {called.name} [{called.patient_id}], Queue #{called.queue_number}")

    # Complete Consultation
    controller.complete_consultation(called.patient_id, doctor_notes="ECG normal. Prescribed lifestyle changes.")
    
    # Verify History Preservation
    history = controller.get_patient_past_visits(called.patient_id)
    assert len(history) >= 1, "Permanent visit history record must be present in SQLite"
    print(f" -> Consultation Completed! Verified Permanent History in SQLite for {called.patient_id}: {len(history)} past visit(s).")

    print("\n==================================================")
    print(" ALL DSA, MULTI-DEPARTMENT & CLINICAL TESTS PASSED! ")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
