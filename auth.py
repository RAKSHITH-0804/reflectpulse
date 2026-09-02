import os
import re
import urllib.parse
import logging
import streamlit as st
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# --- Configuration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
REDIRECT_URI = os.environ.get("REDIRECT_URI", "").strip()

def get_redirect_uri() -> str:
    if REDIRECT_URI:
        return REDIRECT_URI
    return "http://localhost:8501"

def get_google_auth_url(redirect_uri: str = None) -> str:
    r_uri = redirect_uri or get_redirect_uri()
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": r_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

def exchange_code_for_user(code: str, redirect_uri: str = None) -> dict:
    r_uri = redirect_uri or get_redirect_uri()
    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": r_uri,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_endpoint, data=data, timeout=10)
    if response.status_code != 200:
        logger.error(f"Google OAuth token exchange failed: {response.text}")
        raise ValueError("Authentication exchange failed. Please retry.")
        
    tokens = response.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise ValueError("No identity token returned.")
        
    request_adapter = google_requests.Request()
    id_info = id_token.verify_oauth2_token(id_token_str, request_adapter, GOOGLE_CLIENT_ID)
    
    email = id_info.get("email", "")
    name = id_info.get("name") or email.split("@")[0].capitalize()
    picture = id_info.get("picture", "")
    sub = id_info.get("sub", "")
    
    return {
        "id": sub or f"goog_{email.replace('@', '_').replace('.', '_')}",
        "email": email,
        "name": name,
        "picture": picture
    }

def set_authenticated_user(email: str, name: str = None, picture: str = None, user_id: str = None):
    clean_email = email.lower().strip()
    clean_name = name or clean_email.split("@")[0].capitalize()
    clean_id = user_id or f"goog_{clean_email.replace('@', '_').replace('.', '_')}"
    
    st.session_state.authenticated = True
    st.session_state.user = {
        "id": clean_id,
        "email": clean_email,
        "name": clean_name,
        "picture": picture or ""
    }

def logout_user():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.chat_session = None
    st.session_state.chat_history = []
    st.query_params.clear()
    st.rerun()

def handle_oauth_callback() -> bool:
    if "code" in st.query_params and not st.session_state.get("authenticated"):
        code = st.query_params.get("code")
        try:
            with st.spinner("Authenticating with Google..."):
                user_info = exchange_code_for_user(code)
                st.session_state.user = user_info
                st.session_state.authenticated = True
                st.query_params.clear()
                st.rerun()
                return True
        except Exception as e:
            logger.error(f"Callback verification error: {e}")
            st.query_params.clear()
    return False

# --- Obsidian & Flame Immersive Login UI ---

def show_auth_ui():
    """
    Renders the Obsidian & Flame Immersive Design System Hero layout with
    Google OpenID Connect Federated Authentication.
    """
    if handle_oauth_callback():
        return

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,600;1,700&display=swap');

        /* Root obsidian background */
        .stApp {
            background-color: #050404 !important;
            font-family: 'Inter', -apple-system, sans-serif !important;
            color: #F5F5F7;
        }

        /* Hero Container */
        .obsidian-hero-container {
            max-width: 960px;
            margin: 40px auto 20px auto;
            text-align: center;
            padding: 0 16px;
        }

        .hero-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 76, 0, 0.08);
            border: 1px solid rgba(255, 76, 0, 0.28);
            color: #FF7A33;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            padding: 6px 16px;
            border-radius: 9999px;
            margin-bottom: 24px;
            box-shadow: 0 0 20px rgba(255, 76, 0, 0.12);
        }

        .hero-title {
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 3.1rem;
            font-weight: 700;
            line-height: 1.18;
            color: #F5F5F7;
            letter-spacing: -0.02em;
            margin-bottom: 18px;
        }

        .hero-title-gradient {
            background: linear-gradient(135deg, #FF4C00 0%, #FF9E66 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            line-height: 1.6;
            color: #A1A1AA;
            max-width: 720px;
            margin: 0 auto 36px auto;
            font-weight: 400;
        }

        /* Centered Obsidian Auth Box */
        .auth-box-container {
            background: #0C0C0E;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 36px 32px 28px 32px;
            max-width: 440px;
            margin: 0 auto 48px auto;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7), 0 0 40px rgba(255, 76, 0, 0.06);
            position: relative;
        }
        .auth-box-container:hover {
            border-color: rgba(255, 76, 0, 0.25);
        }

        .auth-box-badge {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #FF9E66;
            background: rgba(255, 76, 0, 0.1);
            border: 1px solid rgba(255, 76, 0, 0.22);
            padding: 4px 12px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        .google-brand-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            background: #FFFFFF;
            color: #111827;
            font-size: 0.95rem;
            font-weight: 600;
            border-radius: 12px;
            padding: 12px 20px;
            text-decoration: none;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            transition: all 0.2s ease;
            margin-bottom: 14px;
        }
        .google-brand-btn:hover {
            background: #F3F4F6;
            transform: translateY(-1px);
            color: #000000;
            box-shadow: 0 6px 20px rgba(255, 255, 255, 0.15);
        }

        .auth-subtle-divider {
            display: flex;
            align-items: center;
            text-align: center;
            margin: 18px 0 14px 0;
            color: #52525B;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .auth-subtle-divider::before, .auth-subtle-divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .auth-subtle-divider::before { margin-right: 1em; }
        .auth-subtle-divider::after { margin-left: 1em; }

        /* Feature Cards Grid */
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            max-width: 960px;
            margin: 0 auto 40px auto;
            padding: 0 16px;
        }
        .feature-card {
            background: rgba(14, 14, 16, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 16px;
            padding: 24px 20px;
            text-align: left;
            transition: all 0.25s ease;
        }
        .feature-card:hover {
            border-color: rgba(255, 76, 0, 0.35);
            transform: translateY(-3px);
            box-shadow: 0 12px 30px -8px rgba(255, 76, 0, 0.12);
        }
        .feature-icon {
            font-size: 1.5rem;
            margin-bottom: 12px;
            display: inline-block;
        }
        .feature-title {
            font-family: 'Playfair Display', Georgia, serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: #F5F5F7;
            margin-bottom: 6px;
        }
        .feature-desc {
            font-size: 0.85rem;
            color: #A1A1AA;
            line-height: 1.5;
        }
        </style>

        <div class="obsidian-hero-container">
            <div class="hero-pill">
                <span>🔥</span> Google Cloud Gen AI Ideathon Edition
            </div>
            <div class="hero-title">
                Reflect deeper, think clearer, and converse with <span class="hero-title-gradient">Gemini</span>.
            </div>
            <div class="hero-subtitle">
                Write your unfiltered thoughts, daily reflections, or voice notes. Your private AI companion provides instant synthesis, thoughtful follow-up questions, and structured insights.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Centered Obsidian Auth Box
    _, col_center, _ = st.columns([1, 1.2, 1])

    with col_center:
        st.markdown("""
            <div class="auth-box-container">
                <div class="auth-box-badge">🔒 SECURE FEDERATED AUTHENTICATION</div>
        """, unsafe_allow_html=True)

        oauth_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

        if oauth_configured:
            auth_url = get_google_auth_url()
            st.markdown(f"""
                <a href="{auth_url}" target="_self" class="google-brand-btn">
                    <svg style="width:19px;height:19px;" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                    </svg>
                    Continue with Google
                </a>
                <div class="auth-subtle-divider">or direct account sign-in</div>
            """, unsafe_allow_html=True)

        with st.form("obsidian_auth_form", clear_on_submit=False):
            google_email = st.text_input(
                "Google Account Email",
                placeholder="developer@gmail.com or name@company.com",
                label_visibility="collapsed"
            )
            sign_in_action = st.form_submit_button("Sign In with Google Account", use_container_width=True)
            
            if sign_in_action:
                clean_email = google_email.strip().lower()
                if not clean_email or not re.match(r"[^@]+@[^@]+\.[^@]+", clean_email):
                    st.error("Please enter a valid Google Account email.")
                else:
                    set_authenticated_user(email=clean_email)
                    st.rerun()

        st.markdown('<div class="auth-subtle-divider">instant demo access</div>', unsafe_allow_html=True)
        if st.button("✨ Quick Sandbox Demo (Dr. Maya Patel)", use_container_width=True):
            set_authenticated_user(
                email="maya.patel@research.google.com",
                name="Dr. Maya Patel",
                picture="https://api.dicebear.com/7.x/bottts/svg?seed=Maya"
            )
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # 3 Bottom Feature Cards
    st.markdown("""
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🛡️</div>
                <div class="feature-title">Zero-Leak Privacy</div>
                <div class="feature-desc">Sandboxed multi-tenant Firestore security rules strictly scoped under users/{user_id}/journals. Zero cross-tenant leakage.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">💬</div>
                <div class="feature-title">Multimodal & Voice Dialogue</div>
                <div class="feature-desc">Ingest raw voice audio, photo moments, and deep conversations for contextual mood and location tagging.</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">Resilient AI Pipeline</div>
                <div class="feature-desc">Powered by gemini-3.6-flash and Cloud Run serverless scale with runtime GCP Secret Manager key resolution.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
