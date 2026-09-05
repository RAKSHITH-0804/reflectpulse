import os
import logging
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.auth.exceptions import DefaultCredentialsError
from config import FIREBASE_KEY_PATH

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK using service account credentials
    or Application Default Credentials (ADC).
    """
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        logger.info("Firebase Admin SDK already initialized.")
    except ValueError:
        # Initialize Firebase Admin SDK
        if FIREBASE_KEY_PATH and os.path.exists(FIREBASE_KEY_PATH):
            logger.info(f"Initializing Firebase with certificate at: {FIREBASE_KEY_PATH}")
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)
        else:
            try:
                logger.info("Initializing Firebase with Application Default Credentials (ADC).")
                firebase_admin.initialize_app()
            except Exception as e:
                logger.warning(
                    f"Could not initialize Firebase via ADC: {e}. "
                    "If running locally, please set FIREBASE_APPLICATION_CREDENTIALS."
                )
                # To prevent blocking the app startup, return None. The application will guide the user.
                return None

    try:
        return firestore.client()
    except Exception as e:
        logger.error(f"Failed to get Firestore client: {e}")
        return None

# Global db client instance
db = initialize_firebase()

# --- Strict Multi-Tenant Scoped Firestore CRUD Operations ---

def verify_tenant_context(user_id: str):
    """
    Validates user_id to ensure tenant isolation.
    """
    if not user_id or not isinstance(user_id, str) or user_id.strip() == "":
        raise ValueError("Security Violation: Invalid or empty tenant context (user_id). Transaction aborted.")

def create_journal_entry(user_id: str, entry_data: dict) -> str:
    """
    Creates a journal entry strictly scoped to the tenant's subcollection.
    Path: users/{user_id}/journals/{entry_id}
    """
    verify_tenant_context(user_id)
    if not db:
        raise ConnectionError("Firestore client is not initialized.")

    # Explicitly append server-side metadata, serialized chat transcript, and multimodal context
    perspective_val = entry_data.get("perspective_note") or entry_data.get("cognitive_reframe")
    chat_transcript_val = entry_data.get("chat_transcript") or []
    doc_data = {
        "location_tag": entry_data.get("location_tag", "Home"),
        "perspective_note": perspective_val,
        "chat_transcript": chat_transcript_val,
        "has_audio": bool(entry_data.get("has_audio", False)),
        "has_image": bool(entry_data.get("has_image", False)),
        **entry_data,
        "perspective_note": perspective_val,
        "chat_transcript": chat_transcript_val,
        "user_id": user_id,  # Redundant verification field
        "created_at": entry_data.get("created_at") or datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # Reference strictly under users/{user_id}/journals
    journals_ref = db.collection("users").document(user_id).collection("journals")
    new_doc_ref = journals_ref.document()
    new_doc_ref.set(doc_data)
    
    logger.info(f"Journal entry {new_doc_ref.id} successfully created for user {user_id}.")
    return new_doc_ref.id

def get_journal_entries(user_id: str):
    """
    Fetches all journal entries strictly for the authenticated user, sorted by date.
    Path: users/{user_id}/journals
    """
    verify_tenant_context(user_id)
    if not db:
        return []

    try:
        journals_ref = db.collection("users").document(user_id).collection("journals")
        # Sort descending by created_at
        docs = journals_ref.order_by("created_at", direction=firestore.Query.DESCENDING).get()
        
        entries = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            if "perspective_note" not in data and "cognitive_reframe" in data:
                data["perspective_note"] = data["cognitive_reframe"]
            entries.append(data)
        
        return entries
    except Exception as e:
        logger.error(f"Error fetching journal entries for user {user_id}: {e}")
        return []

def get_journal_entry(user_id: str, entry_id: str):
    """
    Fetches a specific journal entry, verifying tenant ownership.
    Path: users/{user_id}/journals/{entry_id}
    """
    verify_tenant_context(user_id)
    if not entry_id:
        raise ValueError("Invalid entry_id.")
    if not db:
        return None

    try:
        doc_ref = db.collection("users").document(user_id).collection("journals").document(entry_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            # Double safety verification check
            if data.get("user_id") != user_id:
                raise PermissionError("Security Exception: Access denied to requested tenant data.")
            return data
    except Exception as e:
        logger.error(f"Error retrieving journal entry {entry_id} for user {user_id}: {e}")
    return None

def update_journal_entry(user_id: str, entry_id: str, update_data: dict) -> bool:
    """
    Updates a journal entry, verifying tenant ownership.
    Path: users/{user_id}/journals/{entry_id}
    """
    verify_tenant_context(user_id)
    if not entry_id:
        raise ValueError("Invalid entry_id.")
    if not db:
        raise ConnectionError("Firestore client is not initialized.")

    try:
        doc_ref = db.collection("users").document(user_id).collection("journals").document(entry_id)
        doc = doc_ref.get()
        if not doc.exists:
            logger.warning(f"Journal entry {entry_id} not found for update.")
            return False

        existing_data = doc.to_dict()
        if existing_data.get("user_id") != user_id:
            raise PermissionError("Security Exception: Access denied to modify other tenant's data.")

        # Update metadata
        update_data["updated_at"] = datetime.utcnow()
        doc_ref.update(update_data)
        logger.info(f"Journal entry {entry_id} updated for user {user_id}.")
        return True
    except Exception as e:
        logger.error(f"Error updating journal entry {entry_id} for user {user_id}: {e}")
        return False

def delete_journal_entry(user_id: str, entry_id: str) -> bool:
    """
    Deletes a journal entry, verifying tenant ownership.
    Path: users/{user_id}/journals/{entry_id}
    """
    verify_tenant_context(user_id)
    if not entry_id:
        raise ValueError("Invalid entry_id.")
    if not db:
        raise ConnectionError("Firestore client is not initialized.")

    try:
        doc_ref = db.collection("users").document(user_id).collection("journals").document(entry_id)
        doc = doc_ref.get()
        if not doc.exists:
            logger.warning(f"Journal entry {entry_id} not found for deletion.")
            return False

        existing_data = doc.to_dict()
        if existing_data.get("user_id") != user_id:
            raise PermissionError("Security Exception: Access denied to delete other tenant's data.")

        doc_ref.delete()
        logger.info(f"Journal entry {entry_id} successfully deleted for user {user_id}.")
        return True
    except Exception as e:
        logger.error(f"Error deleting journal entry {entry_id} for user {user_id}: {e}")
        return False
