# ReflectPulse 🔮

ReflectPulse is a production-grade, highly secure Personal Gemini Journal web application built for the Google Cloud Gen AI Ideathon. It functions as an empathetic, multi-turn conversational journaling companion, storing journals with strict multi-tenant isolation, analyzing reflections into structured metadata (summary, mood category, mood score, theme tags, and follow-up prompts), and presenting interactive trends and aggregated weekly reports.

## 🏗️ Architecture Overview

The application utilizes a pure Python stack deployed via containerization on Google Cloud Run, communicating with Cloud Firestore and the Gemini API dynamically.

```mermaid
flowchart TD
    subgraph Client Layer
        U[User Web Browser] <-->|HTTPS / WebSockets| ST[Streamlit App Frontend]
    end

    subgraph Service & Application Layer
        ST <--> Auth[auth.py: Authentication / Session State]
        ST <--> FS[firestore_service.py: isolated CRUD]
        ST <--> Gem[gemini_service.py: Gemini Flash Client]
        ST <--> An[analytics.py: Plotly Charts / Streaks]
    end

    subgraph Google Cloud & Firebase Backend
        SM[(GCP Secret Manager)] -.->|GEMINI_API_KEY| ST
        Auth <-->|Verify Google ID Tokens| GAuth[(Google OAuth 2.0 / OpenID Connect)]
        FS <-->|Fetch / Write Journals| DB_Tenant[(Firestore: users/{user_id}/journals/{entry_id})]
        Gem <-->|Generate Reflections & Weekly Digest| GemAPI[Google Gen AI: gemini-3.6-flash]
    end
```

## 🔒 Security Constitution & Tenant Isolation

ReflectPulse implements strict security controls to protect user journal privacy:

1. **Zero Hardcoded Secrets**: Secrets like `GEMINI_API_KEY` are retrieved dynamically at runtime from **Google Cloud Secret Manager** (`projects/rakshith-0408/secrets/GEMINI_API_KEY/versions/latest`). Local execution falls back safely to `.env` variables.
2. **Passwordless Federated Google Identity**: Eliminates all custom password handling and credential tables, relying on Google OAuth 2.0 and OpenID Connect tokens directly.
3. **Strict Tenant Isolation**: All user journals are stored under a subcollection mapping strictly to the authenticated tenant user ID: `users/{user_id}/journals/{entry_id}`. Crucially, every CRUD query in `firestore_service.py` performs a mandatory validation assertion of the `user_id` context to prevent cross-tenant leakage.
4. **AI Security Constitution**: The Gemini model runs with a hardcoded system prompt ensuring:
   - **Strict Sandbox Boundaries**: It will never leak, refer to, or infer other users' entries.
   - **Clinical Boundaries**: It identifies as a journaling companion, not a certified therapist, avoiding medical diagnoses.
   - **Self-Harm Safeguards**: Immediate detection triggers responses listing official crisis support services (e.g., 988 Suicide & Crisis Lifeline).

---

## 📂 File Structure

- [app.py](app.py): The main Streamlit entry point. Configures page layout, glassmorphic dark-mode CSS styling, Tab logic, chat companion integration, and analytics dashboards.
- [auth.py](auth.py): Implements passwordless Federated Google Identity (OAuth 2.0 / OpenID Connect) without storing or hashing passwords.
- [firestore_service.py](firestore_service.py): Encapsulates all Firestore client initialization and CRUD database transactions, validating tenant contexts.
- [gemini_service.py](gemini_service.py): Handles multi-turn chat sessions, structured JSON extraction via Gemini Flash, and Weekly Digest generation.
- [analytics.py](analytics.py): Computes consecutive journaling streaks and generates interactive Plotly visualizations.
- [config.py](config.py): Dynamically loads environment variables and fetches `GEMINI_API_KEY` from Secret Manager.
- [Dockerfile](Dockerfile): Custom instructions for compiling a lightweight Python image optimized for Google Cloud Run (exposing port 8080).
- [requirements.txt](requirements.txt): Pinned python dependencies.

---

## 🚀 Local Development Setup Guide

Follow these steps to run the application on your local machine:

### 1. Prerequisites
Ensure you have **Python 3.10+** and **Git** installed.

### 2. Clone and Setup Environment
Clone the repository and create a virtual environment:
```bash
git clone <repository-url>
cd reflectpulse
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Local Secrets (`.env`)
Create a file named `.env` in the root of the project directory:
```env
# Gemini API Key (Fallback if Secret Manager is not active locally)
GEMINI_API_KEY="your-gemini-api-key"

# Path to the Firebase service account JSON key file
FIREBASE_APPLICATION_CREDENTIALS="service_account_credentials.json"

# Project specifications (optional)
GCP_PROJECT="rakshith-0408"
```

### 5. Setup Firebase Credentials
1. Go to your [Firebase Console](https://console.firebase.google.com/).
2. Select your project `rakshith-0408` (or create a development one).
3. Navigate to **Project Settings** > **Service accounts**.
4. Click **Generate new private key**, and download the JSON file.
5. Place the downloaded JSON file in the project folder and name it `service_account_credentials.json` (ensure this matches the path in `.env` and is ignored in `.gitignore`).

### 6. Run the Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Deployment to Google Cloud Run

To build and deploy ReflectPulse to Google Cloud Run, execute the following commands using the Google Cloud SDK:

```bash
# Set GCP Project
gcloud config set project rakshith-0408

# Submit a build to Google Artifact Registry / Cloud Build
gcloud builds submit --tag gcr.io/rakshith-0408/reflectpulse

# Deploy container to Cloud Run (exposing port 8080)
gcloud run deploy reflectpulse \
    --image gcr.io/rakshith-0408/reflectpulse \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```
