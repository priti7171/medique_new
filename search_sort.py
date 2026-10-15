"""
search_sort.py
==============
Handcrafted Searching and Sorting Algorithms implemented in pure Python for MediQueue.

ALGORITHMS IMPLEMENTED FROM SCRATCH:
1. Searching:
   - linear_search_patients (O(n)): Sequential scan across patient records.
   - binary_search_by_id (O(log n)): Divide-and-conquer search on sorted Permanent Patient IDs.
   - linear_search_doctors (O(n)): Sequential scan across doctor records (ID, Name, Dept, Specialization, Availability).
   - binary_search_doctor_by_id (O(log n)): Divide-and-conquer search on sorted Doctor IDs (DOC001).
2. Sorting:
   - bubble_sort_patients (O(n^2)): Pairwise comparisons and adjacent element swaps.
   - insertion_sort_patients (O(n^2)): Element insertion via contiguous shifts.
   - bubble_sort_doctors (O(n^2)): Pairwise comparisons and adjacent swaps on doctor records.
   - insertion_sort_doctors (O(n^2)): Element insertion via contiguous shifts on doctor records.

DESIGNED FOR: 1st Year AI & Data Science DSA Mini-Project / Viva Examination.
"""

from typing import List, Any, Tuple, Optional, Dict, Union


# Helper to safely get attribute or dictionary key
def _get_field(item: Any, key: str, default: Any = "") -> Any:
    """Helper to extract field value whether item is a dict or class instance."""
    if isinstance(item, dict):
        # Try direct key, lowercase key, and capitalized key
        if key in item:
            return item[key]
        for k, v in item.items():
            if k.lower() == key.lower():
                return v
        return default
    else:
        return getattr(item, key, default)


# ==============================================================================
# 1. PATIENT SEARCHING ALGORITHMS
# ==============================================================================

def linear_search_patients(
    patients: List[Any],
    query: str,
    search_by: str = "all"
) -> Tuple[List[Any], int, List[str]]:
    """
    Linear Search Algorithm for Patient records:
    Iterates through the patient list sequentially from index 0 to (n-1).
    
    TIME COMPLEXITY:
    - Best Case: O(1)
    - Worst Case: O(n)
    - Average Case: O(n)
    SPACE COMPLEXITY: O(1) auxiliary.

    Args:
        patients: List of Patient objects or dictionaries.
        query: Search string.
        search_by: 'patient_id', 'name', 'doctor', 'department', 'queue_number', or 'all'.

    Returns:
        Tuple of (results_list, total_comparisons, step_log)
    """
    query_clean = str(query).strip().lower()
    matches: List[Any] = []
    comparisons = 0
    step_log: List[str] = []

    for i, p in enumerate(patients):
        comparisons += 1
        matched = False
        
        pid = str(_get_field(p, "patient_id", "")).lower()
        name = str(_get_field(p, "name", "")).lower()
        prob = str(_get_field(p, "problem", "")).lower()
        prio = str(_get_field(p, "priority", "")).lower()
        doc_name = str(_get_field(p, "doctor_name", "")).lower()
        doc_id = str(_get_field(p, "doctor_id", "")).lower()
        dept_name = str(_get_field(p, "dept_name", "")).lower()
        dept_id = str(_get_field(p, "dept_id", "")).lower()
        q_num = str(_get_field(p, "queue_number", "")).lower()

        search_by_clean = search_by.strip().lower()

        if search_by_clean in ["patient_id", "id"]:
            matched = query_clean in pid
        elif search_by_clean == "name":
            matched = query_clean in name
        elif search_by_clean == "doctor":
            matched = (query_clean in doc_name or query_clean in doc_id)
        elif search_by_clean in ["department", "dept"]:
            matched = (query_clean in dept_name or query_clean in dept_id)
        elif search_by_clean in ["queue_number", "queue", "token"]:
            matched = query_clean in q_num
        else:  # Search across all clinical fields
            matched = (
                query_clean in pid
                or query_clean in name
                or query_clean in prob
                or query_clean in prio
                or query_clean in doc_name
                or query_clean in doc_id
                or query_clean in dept_name
                or query_clean in dept_id
                or query_clean in q_num
            )

        display_name = _get_field(p, "name", "Patient")
        display_id = _get_field(p, "patient_id", "ID")
        display_q = _get_field(p, "queue_number", "")

        if matched:
            matches.append(p)
            step_log.append(f"Step {comparisons}: MATCH -> Found [{display_id} - {display_name}] (Queue: {display_q}) at index {i}")
        else:
            step_log.append(f"Step {comparisons}: Checked index {i} [{display_id} - {display_name}] -> No match")

    return matches, comparisons, step_log


def binary_search_by_id(
    patients: List[Any],
    target_id: str
) -> Tuple[Optional[Any], int, List[str]]:
    """
    Binary Search Algorithm for Permanent Patient ID (MQ-YYYY-XXXXXX):
    Searches using Divide-and-Conquer on a sorted patient array.
    
    PRECONDITION: Array sorted by patient_id.
    
    TIME COMPLEXITY:
    - Best Case: O(1)
    - Worst Case: O(log n)
    - Average Case: O(log n)
    SPACE COMPLEXITY: O(1) iterative.
    """
    sorted_patients = sorted(patients, key=lambda p: str(_get_field(p, "patient_id", "")).upper())
    target_clean = target_id.strip().upper()
    low = 0
    high = len(sorted_patients) - 1
    comparisons = 0
    step_log: List[str] = []

    while low <= high:
        comparisons += 1
        mid = (low + high) // 2
        mid_patient = sorted_patients[mid]
        mid_id = str(_get_field(mid_patient, "patient_id", "")).upper()

        step_log.append(
            f"Step {comparisons}: Search Range [{low}..{high}], Mid Index = {mid}, Mid ID = '{mid_id}'"
        )

        if mid_id == target_clean:
            step_log.append(f" SUCCESS: Found '{target_clean}' at index {mid} after {comparisons} comparison(s)!")
            return mid_patient, comparisons, step_log
        elif mid_id < target_clean:
            step_log.append(f" '{mid_id}' < '{target_clean}' -> Discard left half, search right range [{mid+1}..{high}]")
            low = mid + 1
        else:
            step_log.append(f" '{mid_id}' > '{target_clean}' -> Discard right half, search left range [{low}..{mid-1}]")
            high = mid - 1

    step_log.append(f" NOT FOUND: Target ID '{target_clean}' is not present in database after {comparisons} comparisons.")
    return None, comparisons, step_log


# ==============================================================================
# 2. DOCTOR SEARCHING ALGORITHMS (LINEAR & BINARY)
# ==============================================================================

def linear_search_doctors(
    doctors: List[Dict[str, Any]],
    query: str,
    search_by: str = "all"
) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """
    Linear Search Algorithm for Doctor records:
    Iterates through the doctor list sequentially from index 0 to (n-1).
    
    Supports searching by:
    - Doctor ID (doc_id)
    - Doctor Name (name)
    - Department (dept_name, dept_id, dept_code)
    - Specialization (specialization)
    - Availability Status (status: Available, On Leave, Unavailable)
    
    TIME COMPLEXITY:
    - Best Case: O(1)
    - Worst Case: O(n)
    - Average Case: O(n)
    SPACE COMPLEXITY: O(1) auxiliary.

    Args:
        doctors: List of Doctor dictionaries or objects.
        query: String search term.
        search_by: 'all', 'id'/'doc_id', 'name', 'department'/'dept',
                   'specialization'/'spec', 'availability'/'status'.

    Returns:
        Tuple of (matches_list, total_comparisons, step_log)
    """
    query_clean = str(query).strip().lower()
    matches: List[Dict[str, Any]] = []
    comparisons = 0
    step_log: List[str] = []

    for i, d in enumerate(doctors):
        comparisons += 1
        matched = False
        
        doc_id = str(_get_field(d, "doc_id", "")).lower()
        doc_name = str(_get_field(d, "name", "")).lower()
        doc_spec = str(_get_field(d, "specialization", "")).lower()
        doc_dept = str(_get_field(d, "dept_name", "")).lower()
        doc_dept_id = str(_get_field(d, "dept_id", "")).lower()
        doc_dept_code = str(_get_field(d, "dept_code", "")).lower()
        doc_status = str(_get_field(d, "status", "")).lower()
        doc_room = str(_get_field(d, "room_number", "")).lower()
        doc_qual = str(_get_field(d, "qualification", "")).lower()
        doc_days = str(_get_field(d, "available_days", "")).lower()

        search_by_clean = search_by.strip().lower()

        if search_by_clean in ["id", "doc_id", "doctor_id"]:
            matched = query_clean in doc_id
        elif search_by_clean == "name":
            matched = query_clean in doc_name
        elif search_by_clean in ["specialization", "spec"]:
            matched = query_clean in doc_spec
        elif search_by_clean in ["department", "dept"]:
            matched = (query_clean in doc_dept or query_clean in doc_dept_id or query_clean in doc_dept_code)
        elif search_by_clean in ["availability", "status", "avail"]:
            matched = query_clean in doc_status
        else:  # Search across all relevant doctor fields
            matched = (
                query_clean in doc_id
                or query_clean in doc_name
                or query_clean in doc_spec
                or query_clean in doc_dept
                or query_clean in doc_dept_id
                or query_clean in doc_dept_code
                or query_clean in doc_status
                or query_clean in doc_room
                or query_clean in doc_qual
                or query_clean in doc_days
            )

        display_name = _get_field(d, "name", "Doctor")
        display_id = _get_field(d, "doc_id", "DOC")
        display_spec = _get_field(d, "specialization", "")

        if matched:
            matches.append(d)
            step_log.append(f"Step {comparisons}: MATCH -> Found [{display_id} - {display_name}] ({display_spec}) at index {i}")
        else:
            step_log.append(f"Step {comparisons}: Checked index {i} [{display_id} - {display_name}] -> No match")

    return matches, comparisons, step_log


def binary_search_doctor_by_id(
    doctors: List[Dict[str, Any]],
    target_id: str
) -> Tuple[Optional[Dict[str, Any]], int, List[str]]:
    """
    Binary Search Algorithm for Doctor by Doctor ID (e.g. DOC001):
    Searches using Divide-and-Conquer on a sorted doctor array.
    
    PRECONDITION: Array sorted by doc_id.
    
    TIME COMPLEXITY:
    - Best Case: O(1)
    - Worst Case: O(log n)
    - Average Case: O(log n)
    SPACE COMPLEXITY: O(1) iterative.
    """
    sorted_docs = sorted(doctors, key=lambda d: str(_get_field(d, "doc_id", "")).upper())
    target_clean = target_id.strip().upper()
    low = 0
    high = len(sorted_docs) - 1
    comparisons = 0
    step_log: List[str] = []

    while low <= high:
        comparisons += 1
        mid = (low + high) // 2
        mid_doc = sorted_docs[mid]
        mid_id = str(_get_field(mid_doc, "doc_id", "")).upper()

        step_log.append(f"Step {comparisons}: Range [{low}..{high}], Mid Index = {mid}, Checking Mid Doc ID = '{mid_id}'")

        if mid_id == target_clean:
            step_log.append(f" SUCCESS: Found Doctor '{target_clean}' ({_get_field(mid_doc, 'name', '')}) at index {mid}!")
            return mid_doc, comparisons, step_log
        elif mid_id < target_clean:
            low = mid + 1
        else:
            high = mid - 1

    step_log.append(f" NOT FOUND: Doctor ID '{target_clean}' not found.")
    return None, comparisons, step_log


# ==============================================================================
# 3. PATIENT SORTING ALGORITHMS
# ==============================================================================

def _get_patient_sort_val(patient: Any, sort_key: str) -> Any:
    """Extracts comparison key from Patient object or dictionary."""
    key = sort_key.lower().strip()
    if key == "priority":
        prio = str(_get_field(patient, "priority", "Normal")).strip().capitalize()
        return 1 if prio == "Emergency" else 2
    elif key == "age":
        try:
            return int(_get_field(patient, "age", 0))
        except (ValueError, TypeError):
            return 0
    elif key == "name":
        return str(_get_field(patient, "name", "")).lower()
    elif key == "token":
        try:
            return int(_get_field(patient, "token", 1))
        except (ValueError, TypeError):
            return 1
    elif key == "queue_number":
        return str(_get_field(patient, "queue_number", "")).lower()
    elif key == "doctor":
        return str(_get_field(patient, "doctor_name", "")).lower()
    elif key == "department":
        return str(_get_field(patient, "dept_name", "")).lower()
    elif key in ["id", "patient_id"]:
        return str(_get_field(patient, "patient_id", "")).upper()
    elif key in ["time", "registration_time"]:
        return str(_get_field(patient, "registration_time", ""))
    return _get_field(patient, "token", 1)


def bubble_sort_patients(
    patients: List[Any],
    sort_key: str = "priority",
    ascending: bool = True
) -> Tuple[List[Any], int, int]:
    """
    Bubble Sort Algorithm for Patients:
    Repeatedly steps through the list, compares adjacent elements, and swaps them if in wrong order.
    TIME COMPLEXITY: O(n^2) Worst/Average, O(n) Best (with swapped flag).
    STABILITY: Stable.
    """
    arr = list(patients)
    n = len(arr)
    comparisons = 0
    swaps = 0

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            comparisons += 1
            val_a = _get_patient_sort_val(arr[j], sort_key)
            val_b = _get_patient_sort_val(arr[j + 1], sort_key)

            should_swap = (val_a > val_b) if ascending else (val_a < val_b)

            if should_swap:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swaps += 1
                swapped = True

        if not swapped:
            break

    return arr, comparisons, swaps


def insertion_sort_patients(
    patients: List[Any],
    sort_key: str = "age",
    ascending: bool = True
) -> Tuple[List[Any], int, int]:
    """
    Insertion Sort Algorithm for Patients:
    Builds sorted list one item at a time by shifting elements to the right.
    TIME COMPLEXITY: O(n^2) Worst/Average, O(n) Best.
    STABILITY: Stable.
    """
    arr = list(patients)
    n = len(arr)
    comparisons = 0
    shifts = 0

    for i in range(1, n):
        key_item = arr[i]
        key_val = _get_patient_sort_val(key_item, sort_key)
        j = i - 1

        while j >= 0:
            comparisons += 1
            current_val = _get_patient_sort_val(arr[j], sort_key)
            
            should_shift = (current_val > key_val) if ascending else (current_val < key_val)

            if should_shift:
                arr[j + 1] = arr[j]
                shifts += 1
                j -= 1
            else:
                break

        arr[j + 1] = key_item

    return arr, comparisons, shifts


# ==============================================================================
# 4. DOCTOR SORTING ALGORITHMS
# ==============================================================================

def _get_doctor_sort_val(doctor: Dict[str, Any], sort_key: str) -> Any:
    """Extracts comparison key from Doctor record."""
    key = sort_key.lower().strip()
    if key in ["experience", "experience_years", "exp"]:
        try:
            return int(_get_field(doctor, "experience_years", 0))
        except (ValueError, TypeError):
            return 0
    elif key == "name":
        return str(_get_field(doctor, "name", "")).lower()
    elif key in ["department", "dept", "dept_name"]:
        return str(_get_field(doctor, "dept_name", "")).lower()
    elif key in ["room", "room_number"]:
        return str(_get_field(doctor, "room_number", "")).lower()
    elif key in ["status", "availability"]:
        return str(_get_field(doctor, "status", "")).lower()
    return str(_get_field(doctor, "doc_id", ""))


def bubble_sort_doctors(
    doctors: List[Dict[str, Any]],
    sort_key: str = "experience",
    ascending: bool = False
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Bubble Sort Algorithm for Doctors:
    Sorts doctor records by experience, name, department, or room.
    TIME COMPLEXITY: O(n^2).
    """
    arr = list(doctors)
    n = len(arr)
    comparisons = 0
    swaps = 0

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            comparisons += 1
            val_a = _get_doctor_sort_val(arr[j], sort_key)
            val_b = _get_doctor_sort_val(arr[j + 1], sort_key)

            should_swap = (val_a > val_b) if ascending else (val_a < val_b)

            if should_swap:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swaps += 1
                swapped = True

        if not swapped:
            break

    return arr, comparisons, swaps


def insertion_sort_doctors(
    doctors: List[Dict[str, Any]],
    sort_key: str = "name",
    ascending: bool = True
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Insertion Sort Algorithm for Doctors:
    Builds sorted doctor array incrementally with shift metrics.
    TIME COMPLEXITY: O(n^2).
    """
    arr = list(doctors)
    n = len(arr)
    comparisons = 0
    shifts = 0

    for i in range(1, n):
        key_item = arr[i]
        key_val = _get_doctor_sort_val(key_item, sort_key)
        j = i - 1

        while j >= 0:
            comparisons += 1
            current_val = _get_doctor_sort_val(arr[j], sort_key)
            
            should_shift = (current_val > key_val) if ascending else (current_val < key_val)

            if should_shift:
                arr[j + 1] = arr[j]
                shifts += 1
                j -= 1
            else:
                break

        arr[j + 1] = key_item

    return arr, comparisons, shifts
