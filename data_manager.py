"""
data_manager.py
================
Persistence bridge module connecting the application layer with the SQLite database (db_manager.py).
Ensures permanent Patient ID generation (MQ-YYYY-XXXXXX), doctor queue numbering, departments,
doctors, audit logs, and permanent patient visit history.
"""

from typing import List, Dict, Optional, Any
import db_manager


def load_all_patients() -> List[Dict[str, Any]]:
    """Loads all patient records from SQLite."""
    return db_manager.get_all_patients_from_db()


def save_all_patients(patients: List[Dict[str, Any]]) -> None:
    """Batch save/update helper."""
    pass


def generate_next_patient_id() -> str:
    """Generates the permanent unique Patient ID in format MQ-YYYY-XXXXXX."""
    return db_manager.generate_permanent_patient_id()


def generate_next_token() -> int:
    """Generates the next sequential Token number."""
    return db_manager.generate_next_token()


def generate_doctor_queue_number(doc_id: str, dept_code: str = "GEN") -> str:
    """Generates the doctor-specific daily queue token (e.g. CARD-001)."""
    return db_manager.generate_doctor_queue_number(doc_id, dept_code)


def add_patient_record(patient_dict: Dict[str, Any], actor: str = "Staff") -> Dict[str, Any]:
    """Adds a new patient record to SQLite."""
    return db_manager.insert_patient(patient_dict, actor=actor)


def update_patient_status(
    patient_id: str,
    new_status: str,
    consultation_time: Optional[str] = None,
    doctor_notes: Optional[str] = None,
    actor: str = "Doctor"
) -> bool:
    """Updates status in SQLite and archives completed consultations."""
    return db_manager.update_patient_status_db(patient_id, new_status, consultation_time, doctor_notes, actor=actor)


def get_patient_history(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves all past visits for a patient ID."""
    return db_manager.get_patient_history_by_id(patient_id)


def get_all_departments() -> List[Dict[str, Any]]:
    """Retrieves all departments."""
    return db_manager.get_all_departments()


def get_all_doctors() -> List[Dict[str, Any]]:
    """Retrieves all doctors."""
    return db_manager.get_all_doctors()


def reset_sample_data(actor: str = "Staff") -> None:
    """Resets database to initial sample dataset."""
    db_manager.reset_database_to_sample(actor=actor)
