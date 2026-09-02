import os
import logging
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.auth.exceptions import DefaultCredentialsError

# Load local environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT", "rakshith-0408")
SECRET_ID = "GEMINI_API_KEY"
SECRET_VERSION = "latest"

def get_secret(project_id, secret_id, version_id="latest"):
    """
    Attempts to fetch a secret from Google Cloud Secret Manager.
    """
    try:
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully retrieved secret '{secret_id}' from Google Cloud Secret Manager.")
        return secret_value.strip()
    except DefaultCredentialsError:
        logger.warning("DefaultCredentialsError: Google Application Default Credentials not found. Skipping Secret Manager.")
    except Exception as e:
        logger.warning(f"Failed to retrieve secret '{secret_id}' from Secret Manager: {e}")
    return None

def get_gemini_api_key():
    """
    Resolves GEMINI_API_KEY. First attempts Secret Manager, then falls back to local environment variables or Streamlit secrets.
    """
    # 1. Try Secret Manager
    api_key = get_secret(PROJECT_ID, SECRET_ID, SECRET_VERSION)
    
    # 2. If Secret Manager failed, fall back to environment variable
    if not api_key:
        logger.info("Secret Manager lookup failed or skipped. Falling back to local environment variables.")
        api_key = os.environ.get("GEMINI_API_KEY")
    
    # 3. Fallback to Streamlit secrets if running in Streamlit
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key:
                logger.info("Successfully loaded GEMINI_API_KEY from Streamlit secrets.")
        except Exception:
            pass

    return api_key

# Global configuration variables resolved at runtime
GEMINI_API_KEY = get_gemini_api_key()

# Path to the Firebase service account JSON key for local development
FIREBASE_KEY_PATH = os.environ.get("FIREBASE_APPLICATION_CREDENTIALS")

# Check if environment is production (e.g. running on Cloud Run)
IS_PRODUCTION = os.environ.get("K_SERVICE") is not None or os.environ.get("GAE_ENV") is not None
