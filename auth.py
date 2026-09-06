import os
import re
import urllib.parse
import logging
from dotenv import load_dotenv
import streamlit as st
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Ensure environment variables from .env are fresh
load_dotenv(override=True)

logger = logging.getLogger(__name__)

THEME_OPTIONS = ["🍂 Warm Charcoal & Amber", "🔥 Obsidian Flame"]

def get_client_id() -> str:
    val = os.environ.get("GOOGLE_CLIENT_ID", "").strip('\'" \t\n')
    return val

def get_client_secret() -> str:
    val = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip('\'" \t\n')
    return val

def get_redirect_uri() -> str:
    val = os.environ.get("REDIRECT_URI", "").strip('\'" \t\n')
    return val or "http://localhost:8501"

def get_google_auth_url(redirect_uri: str = None) -> str:
    client_id = get_client_id()
    r_uri = redirect_uri or get_redirect_uri()
    params = {
        "client_id": client_id,
        "redirect_uri": r_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

def exchange_code_for_user(code: str, redirect_uri: str = None) -> dict:
    client_id = get_client_id()
    client_secret = get_client_secret()
    r_uri = redirect_uri or get_redirect_uri()
    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": r_uri,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_endpoint, data=data, timeout=10)
    if response.status_code != 200:
        logger.error(f"Google OAuth token exchange failed: {response.text}")
        raise ValueError(f"Authentication exchange failed: {response.text}")
        
    tokens = response.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise ValueError("No identity token returned from Google.")
        
    # Verify and decode the id_token
    id_info = None
    try:
        request_adapter = google_requests.Request()
        id_info = id_token.verify_oauth2_token(id_token_str, request_adapter, client_id, clock_skew_in_seconds=10)
    except Exception as e:
        logger.warning(f"id_token.verify_oauth2_token: {e}. Trying Google tokeninfo endpoint.")
        tokeninfo_resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}",
            timeout=10
        )
        if tokeninfo_resp.status_code == 200:
            id_info = tokeninfo_resp.json()
        else:
            raise ValueError(f"Could not verify id_token: {e}")
    
    email = id_info.get("email", "")
    name = id_info.get("name") or (email.split("@")[0].capitalize() if email else "Google User")
    picture = id_info.get("picture", "")
    sub = id_info.get("sub", "")
    
    return {
        "id": sub or f"goog_{email.replace('@', '_').replace('.', '_')}",
        "email": email,
        "name": name,
        "picture": picture,
        "sub": sub
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
            st.error(f"Google authentication failed: {e}")
            st.query_params.clear()
    return False

def get_auth_theme_css(theme: str) -> str:
    """
    Returns the CSS tokens for the active dark theme in auth UI.
    """
    if "Obsidian" in theme or "Flame" in theme:
        return """
            :root {
                --bg-main: #050404;
                --surface-main: #0C0C0E;
                --surface-container: #151518;
                --surface-container-high: #1E1E22;
                --primary-color: #FF4C00;
                --on-primary-color: #FFFFFF;
                --accent-blue: #FF7A33;
                --text-primary: #F5F5F7;
                --text-secondary: #A1A1AA;
                --border-color: rgba(255, 76, 0, 0.3);
                --input-bg: #0C0C0E;
                --font-heading: 'Playfair Display', Georgia, serif;
                --font-body: 'Inter', sans-serif;
            }
        """
    else:  # 🍂 Warm Charcoal & Amber (Default)
        return """
            :root {
                --bg-main: linear-gradient(135deg, #1C1917 0%, #241F1B 100%);
                --surface-main: #2A2420;
                --surface-container: #2F2822;
                --surface-container-high: #38302A;
                --primary-color: #E8B25C;
                --on-primary-color: #1C1917;
                --accent-blue: #E8B25C;
                --text-primary: #EAE3D8;
                --text-secondary: #B0A695;
                --border-color: #443A2E;
                --input-bg: #2A2420;
                --font-heading: 'Roboto', sans-serif;
                --font-body: 'Roboto', sans-serif;
            }
        """

# --- Scaled-Down Viewport-Optimized Authentication Screen ---

def show_auth_ui():
    """
    Renders the authentication screen styled for ReflectPulse dark themes,
    scaled to fit inside a 1080p display at 100% zoom without scrolling.
    """
    if handle_oauth_callback():
        return

    if "theme" not in st.session_state or st.session_state.theme not in THEME_OPTIONS:
        st.session_state.theme = "🍂 Warm Charcoal & Amber"

    current_theme = st.session_state.theme
    theme_css = get_auth_theme_css(current_theme)

    if "Obsidian" in current_theme or "Flame" in current_theme:
        theme_scoped_css = """
        .stApp {
            background-color: #050404 !important;
            color: #F5F5F7 !important;
        }
        .stApp div[data-baseweb="select"],
        .stApp div[data-baseweb="select"] * {
            background-color: #151518 !important;
            color: #F5F5F7 !important;
            fill: #F5F5F7 !important;
        }
        .stApp div[data-baseweb="select"] > div {
            background-color: #151518 !important;
            border: 1px solid rgba(255, 76, 0, 0.3) !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] *,
        div[data-baseweb="menu"],
        div[data-baseweb="menu"] *,
        ul[role="listbox"],
        ul[role="listbox"] *,
        li[role="option"],
        li[role="option"] * {
            background-color: #0C0C0E !important;
            color: #F5F5F7 !important;
        }
        li[role="option"]:hover,
        li[role="option"]:hover *,
        li[aria-selected="true"],
        li[aria-selected="true"] * {
            background-color: #151518 !important;
            color: #FF4C00 !important;
        }
        .auth-card {
            background: #0C0C0E !important;
            border: 1px solid rgba(255, 76, 0, 0.3) !important;
        }
        .auth-feature-box {
            background: #151518 !important;
            border: 1px solid rgba(255, 76, 0, 0.2) !important;
        }
        .auth-status-pill {
            background: #151518 !important;
            border: 1px solid rgba(255, 76, 0, 0.3) !important;
            color: #FF7A33 !important;
        }
        .auth-hero-accent {
            background: linear-gradient(135deg, #FF4C00 0%, #FF7A33 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }
        div[data-testid="stLinkButton"] a {
            background: linear-gradient(135deg, #FF4C00 0%, #FF7A33 100%) !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
        }
        """
    else:  # 🍂 Warm Charcoal & Amber
        theme_scoped_css = """
        .stApp {
            background: linear-gradient(135deg, #1C1917 0%, #241F1B 100%) !important;
            background-color: #1C1917 !important;
            color: #EAE3D8 !important;
        }
        .stApp div[data-baseweb="select"],
        .stApp div[data-baseweb="select"] * {
            background-color: #2A2420 !important;
            color: #EAE3D8 !important;
            fill: #EAE3D8 !important;
        }
        .stApp div[data-baseweb="select"] > div {
            background-color: #2A2420 !important;
            border: 1px solid #443A2E !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] *,
        div[data-baseweb="menu"],
        div[data-baseweb="menu"] *,
        ul[role="listbox"],
        ul[role="listbox"] *,
        li[role="option"],
        li[role="option"] * {
            background-color: #2A2420 !important;
            background: #2A2420 !important;
            color: #EAE3D8 !important;
        }
        li[role="option"]:hover,
        li[role="option"]:hover *,
        li[aria-selected="true"],
        li[aria-selected="true"] * {
            background-color: #38302A !important;
            background: #38302A !important;
            color: #E8B25C !important;
        }
        .auth-card {
            background: #2A2420 !important;
            border: 1px solid #443A2E !important;
        }
        .auth-feature-box {
            background: #2F2822 !important;
            border: 1px solid #443A2E !important;
        }
        .auth-status-pill {
            background: #2F2822 !important;
            border: 1px solid #443A2E !important;
            color: #E8B25C !important;
        }
        .auth-hero-accent {
            background: linear-gradient(135deg, #C9852F 0%, #E8B25C 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
        }
        div[data-testid="stLinkButton"] a {
            background: linear-gradient(135deg, #C9852F 0%, #E8B25C 100%) !important;
            color: #1C1917 !important;
            font-weight: 600 !important;
            border: none !important;
        }
        """

    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap');

        /* Hide default Streamlit top header completely */
        header[data-testid="stHeader"] {{
            display: none !important;
            height: 0px !important;
        }}
        footer {{
            visibility: hidden;
        }}

        /* Reset block-container padding to ensure true horizontal & vertical centering */
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 960px !important;
            width: 100% !important;
            margin: 0 auto !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            box-sizing: border-box !important;
        }}

        /* Completely hide sidebar on Login Page */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"][aria-expanded="false"],
        [data-testid="stSidebar"][aria-expanded="true"],
        section[data-testid="stSidebar"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0px !important;
            min-width: 0px !important;
            max-width: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
            pointer-events: none !important;
        }}

        /* Full display viewport flex centering for all screen sizes */
        html, body, .stApp {{
            overflow-x: hidden !important;
        }}
        [data-testid="stAppViewContainer"] {{
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: flex-start !important;
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 auto !important;
            min-height: 100dvh !important;
        }}
        section.main, [data-testid="stMain"] {{
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 auto !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: flex-start !important;
            min-height: 100dvh !important;
        }}

        {theme_css}

        .stApp {{
            background-color: var(--bg-main) !important;
            font-family: var(--font-body) !important;
            color: var(--text-primary) !important;
        }}

        /* Compact Hero Container */
        .auth-hero-shell {{
            max-width: 640px;
            margin: 2px auto 6px auto;
            text-align: center;
            padding: 0 10px;
        }}

        .auth-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--surface-container);
            color: var(--accent-blue);
            font-size: 0.65rem;
            font-weight: 500;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            padding: 3px 10px;
            border-radius: 9999px;
            margin-bottom: 4px;
            border: 1px solid var(--border-color);
        }}

        .auth-hero-title {{
            font-family: var(--font-heading) !important;
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.15;
            color: var(--text-primary);
            letter-spacing: -0.01em;
            margin-bottom: 4px;
        }}

        .auth-hero-accent {{
            color: var(--accent-blue);
        }}

        .auth-hero-subtitle {{
            font-size: 0.85rem;
            line-height: 1.3;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 12px auto;
            font-weight: 400;
        }}

        /* Theme Selectbox Mini Dropdown */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
            min-height: 28px !important;
            padding: 2px 8px !important;
            font-size: 0.78rem !important;
            border-radius: 8px !important;
        }}
        div[data-baseweb="select"] > div {{
            background-color: var(--input-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
        }}
        div[data-baseweb="select"] span, div[data-baseweb="select"] div {{
            color: var(--text-primary) !important;
        }}
        div[data-baseweb="popover"], ul[role="listbox"] {{
            background-color: var(--input-bg) !important;
            color: var(--text-primary) !important;
        }}
        li[role="option"] {{
            color: var(--text-primary) !important;
            background-color: var(--input-bg) !important;
        }}
        li[role="option"]:hover {{
            background-color: var(--surface-container-high) !important;
        }}

        /* Compact Google Sign-In Button */
        div[data-testid="stLinkButton"] {{
            max-width: 360px !important;
            margin: 0 auto !important;
        }}
        div[data-testid="stLinkButton"] a {{
            padding: 8px 16px !important;
            font-size: 0.88rem !important;
            border-radius: 9999px !important;
            font-weight: 600 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border: none !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2) !important;
            transition: opacity 0.2s ease, transform 0.2s ease !important;
        }}
        div[data-testid="stLinkButton"] a:hover {{
            opacity: 0.92 !important;
            transform: translateY(-1px) !important;
        }}

        /* Clickable Google 'G' Icon Badge */
        .google-badge-link {{
            text-decoration: none !important;
            border: none !important;
            outline: none !important;
            cursor: pointer !important;
            display: inline-block !important;
        }}
        .google-badge-circle {{
            transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        .google-badge-link:hover .google-badge-circle {{
            transform: scale(1.12) !important;
            box-shadow: 0 0 14px var(--accent-blue) !important;
        }}

        /* Compact Divider */
        .auth-divider-line {{
            display: flex;
            align-items: center;
            text-align: center;
            margin: 8px auto 6px auto;
            max-width: 360px;
            color: var(--text-secondary);
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            font-weight: 500;
        }}
        .auth-divider-line::before, .auth-divider-line::after {{
            content: '';
            flex: 1;
            border-bottom: 1px solid var(--border-color);
        }}
        .auth-divider-line::before {{ margin-right: 0.8em; }}
        .auth-divider-line::after {{ margin-left: 0.8em; }}

        /* 3 Bottom Feature Cards Responsive Grid */
        .auth-feature-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            max-width: 880px;
            width: 100%;
            margin: 12px auto 0 auto;
            padding: 0 4px;
            align-items: stretch;
            box-sizing: border-box;
        }}
        .auth-feature-card {{
            background: var(--surface-main);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 14px;
            text-align: left;
            display: flex;
            flex-direction: column;
            height: 100%;
            box-sizing: border-box;
            transition: background-color 0.2s ease;
        }}
        .auth-feature-card:hover {{
            background: var(--surface-container);
        }}
        .auth-feature-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            border-radius: 9999px;
            background: rgba(232, 178, 92, 0.12);
            color: var(--primary-color);
            font-size: 0.95rem;
            margin-bottom: 4px;
        }}
        .auth-feature-title {{
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 2px;
            font-family: var(--font-heading) !important;
        }}
        .auth-feature-desc {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            line-height: 1.35;
            flex-grow: 1;
        }}

        /* Responsive Breakpoints: Tablet, Mobile, Laptop, Monitor */
        @media (max-width: 860px) {{
            .auth-feature-grid {{
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 12px !important;
            }}
            .auth-hero-title {{
                font-size: 1.6rem !important;
            }}
        }}

        @media (max-width: 600px) {{
            .block-container {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 0.8rem !important;
            }}
            .auth-feature-grid {{
                grid-template-columns: 1fr !important;
                gap: 10px !important;
            }}
            .auth-hero-title {{
                font-size: 1.35rem !important;
            }}
            .auth-hero-subtitle {{
                font-size: 0.8rem !important;
                margin-bottom: 8px !important;
            }}
            .auth-card-wrapper {{
                padding: 12px 14px !important;
            }}
        }}
        {theme_scoped_css}
        </style>
    """, unsafe_allow_html=True)

    # Compact Hero Section

    st.markdown("""
        <div style="text-align: center; margin-bottom: 4px;">
            <span style="font-size: 1.4rem;">🔮</span>
            <span style="font-size: 2rem; font-weight: 700; color: var(--text-primary); margin-left: 6px;">ReflectPulse</span>
            <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 2px;">Your private daily journal, reflected back with clarity.</div>
        </div>
    """, unsafe_allow_html=True)    

    st.markdown("""
        <div class="auth-hero-shell">
            <div class="auth-status-pill">
                <span>🔒</span> PRIVATE, VERIFIED & SECURE LOG-IN
            </div>
            <div class="auth-hero-title">
                Turn scattered thoughts into clarity with <span class="auth-hero-accent">Gemini</span>.
            </div>
            <div class="auth-hero-subtitle">
                Capture what's on your mind through text, voice, or a photo — and let your private AI companion turn it into structured insight, gentle follow-ups, and a clearer perspective.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Center Surface Container: Authentic Google OAuth 2.0 Sign-In
    _, col_center, _ = st.columns([0.15, 0.7, 0.15], vertical_alignment="center")

    with col_center:
        auth_url = get_google_auth_url()
        st.markdown(f"""
            <div class="auth-card-wrapper" style="background: var(--surface-main); border: 1px solid var(--border-color); border-radius: 14px; padding: 14px 20px; max-width: 360px; margin: 0 auto 12px auto; text-align: center; box-shadow: 0 4px 16px rgba(0,0,0,0.2);">
                <div style="display: flex; justify-content: center; margin-bottom: 6px;">
                    <a href="{auth_url}" class="google-badge-link" title="Sign In with Google Account" style="text-decoration: none; border: none; outline: none; cursor: pointer; display: inline-block;">
                        <div class="google-badge-circle" style="width: 32px; height: 32px; border-radius: 9999px; background: rgba(232, 178, 92, 0.12); display: flex; align-items: center; justify-content: center;">
                            <svg style="width:18px;height:18px;" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                            </svg>
                        </div>
                    </a>
                </div>
                <div style="font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">
                    Continue with Your Google Account
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.35;">
                    No passwords, no separate account — just your existing Google identity, verified by GOOGLE.
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.link_button("Sign In with Google Account", url=auth_url, use_container_width=True, type="primary")

        # Local development mock authentication isolated strictly behind APP_ENV check
        is_dev = os.environ.get("APP_ENV", "").lower() == "development"
        if is_dev:
            st.markdown('<div class="auth-divider-line">LOCAL DEV TESTING ONLY</div>', unsafe_allow_html=True)
            if st.button("🧪 Local Dev Sandbox Login", use_container_width=True):
                set_authenticated_user(
                    email="developer@example.com",
                    name="Developer Sandbox",
                    picture="https://api.dicebear.com/7.x/bottts/svg?seed=Dev"
                )
                st.rerun()

    # 3 Bottom Feature Cards in Balanced 3-Column Alignment
    st.markdown("""
        <div class="auth-feature-grid">
            <div class="auth-feature-card">
                <div class="auth-feature-icon">🛡️</div>
                <div class="auth-feature-title">Your Data, Your Vault</div>
                <div class="auth-feature-desc">Every entry lives in its own owner-locked path in Firestore — enforced by security rules, not just app logic. No one else can ever read it.</div>
            </div>
            <div class="auth-feature-card">
                <div class="auth-feature-icon">💬</div>
                <div class="auth-feature-title">Speak, Type, or Show</div>
                <div class="auth-feature-desc">Drop in voice notes, photos, or free-form text — Gemini reads across all of it to understand mood, themes, and context together.</div>
            </div>
            <div class="auth-feature-card">
                <div class="auth-feature-icon">⚡</div>
                <div class="auth-feature-title">Always-On AI</div>
                <div class="auth-feature-desc">Runs on latest Gemini models with Cloud Run's serverless scaling, pulling credentials securely at runtime — never baked into the code.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
