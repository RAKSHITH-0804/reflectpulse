import streamlit as st
import re
import pandas as pd
from datetime import datetime, timezone
import firestore_service
import gemini_service
import auth
import analytics

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="ReflectPulse - Reflective Journal Studio",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

THEME_OPTIONS = ["🍂 Warm Charcoal", "🔥 Obsidian Flame"]

# --- Theme State Initialization ---
if "theme" not in st.session_state or st.session_state.theme not in THEME_OPTIONS:
    st.session_state.theme = "🍂 Warm Charcoal"

current_theme = st.session_state.theme

def get_app_theme_css(theme: str) -> str:
    """
    Returns the comprehensive CSS variables matching the active dark theme.
    Exclusively supports '🍂 Warm Charcoal & Amber' (default) and '🔥 Obsidian Flame'.
    """
    if "Obsidian" in theme or "Flame" in theme:
        return """
            :root {
                --bg-main: #050404;
                --surface-main: #0C0C0E;
                --surface-container: #151518;
                --surface-container-high: #1E1E22;
                --sidebar-bg: #0C0C0E;
                --primary-color: #FF4C00;
                --primary-gradient: linear-gradient(135deg, #FF4C00 0%, #FF7A33 100%);
                --on-primary-color: #FFFFFF;
                --accent-blue: #FF7A33;
                --emerald-accent: #10B981;
                --emerald-container: #064E3B;
                --text-primary: #F5F5F7;
                --text-secondary: #A1A1AA;
                --border-color: #27272A;
                --card-hover-border: #FF4C00;
                --input-bg: #151518;
                --placeholder-color: #52525B;
                --tab-active-bg: #1E1E22;
                --tab-active-text: #FF4C00;
                --tab-inactive-text: #71717A;
                --chip-bg: #1E1E22;
                --chip-text: #FF7A33;
                --font-heading: 'Playfair Display', Georgia, serif;
                --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }
        """
    else:  # 🍂 Warm Charcoal & Amber (Default)
        return """
            :root {
                --bg-main: #1C1917;
                --surface-main: #24201D;
                --surface-container: #2A2420;
                --surface-container-high: #352E28;
                --sidebar-bg: #24201D;
                --primary-color: #E8B25C;
                --primary-gradient: linear-gradient(135deg, #E8B25C 0%, #F3D19C 100%);
                --on-primary-color: #1C1917;
                --accent-blue: #D97706;
                --emerald-accent: #34D399;
                --emerald-container: #064E3B;
                --text-primary: #EAE3D8;
                --text-secondary: #B0A695;
                --border-color: #443A2E;
                --card-hover-border: #E8B25C;
                --input-bg: #2A2420;
                --placeholder-color: #7D7365;
                --tab-active-bg: #352E28;
                --tab-active-text: #E8B25C;
                --tab-inactive-text: #B0A695;
                --chip-bg: #2F2822;
                --chip-text: #E8B25C;
                --font-heading: 'Roboto', sans-serif;
                --font-body: 'Roboto', sans-serif;
            }
        """

def render_custom_css(current_theme: str):
    theme_css = get_app_theme_css(current_theme)
    is_authenticated = st.session_state.get("authenticated", False)

    if is_authenticated:
        sidebar_layout_css = """
        /* Force Sidebar to be ALWAYS ON / VISIBLE (Always docked on the left) */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"][aria-expanded="false"],
        [data-testid="stSidebar"][aria-expanded="true"],
        section[data-testid="stSidebar"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            transform: none !important;
            margin-left: 0px !important;
            left: 0px !important;
            min-width: 21rem !important;
            max-width: 21rem !important;
            width: 21rem !important;
            position: relative !important;
            flex-shrink: 0 !important;
        }

        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-direction: row !important;
            width: 100vw !important;
        }
        section.main, [data-testid="stMain"] {
            flex: 1 1 auto !important;
            width: calc(100vw - 21rem) !important;
            min-width: 0 !important;
            display: flex !important;
        }

        @media (max-width: 991px) {
            [data-testid="stSidebar"],
            section[data-testid="stSidebar"] {
                min-width: 16rem !important;
                max-width: 16rem !important;
                width: 16rem !important;
            }
            section.main, [data-testid="stMain"] {
                width: calc(100vw - 16rem) !important;
            }
        }
        """
    else:
        sidebar_layout_css = """
        /* Unauthenticated / Login Page: Sidebar is completely hidden & Content is Centered */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"][aria-expanded="false"],
        [data-testid="stSidebar"][aria-expanded="true"],
        section[data-testid="stSidebar"] {
            display: none !important;
            visibility: hidden !important;
            width: 0px !important;
            min-width: 0px !important;
            max-width: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
            pointer-events: none !important;
        }

        html, body, .stApp {
            overflow-x: hidden !important;
        }
        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 auto !important;
        }
        section.main, [data-testid="stMain"] {
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 auto !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
        }
        """

    if "Obsidian" in current_theme or "Flame" in current_theme:
        theme_scoped_css = """
        /* =========================================================
           OBSIDIAN FLAME STRICT SCOPED OVERRIDES
           ========================================================= */
        .stApp { background-color: #050404 !important; color: #F5F5F7 !important; }
        .stApp [data-testid="stSidebar"] { background-color: #0C0C0E !important; }

        /* Unscoped Portal Popover & Dropdown Menu */
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] *,
        div[data-baseweb="menu"],
        div[data-baseweb="menu"] *,
        ul[role="listbox"],
        ul[role="listbox"] *,
        li[role="option"],
        li[role="option"] * {
            background-color: #0C0C0E !important;
            background: #0C0C0E !important;
            color: #F5F5F7 !important;
        }
        li[role="option"]:hover,
        li[role="option"]:hover *,
        li[aria-selected="true"],
        li[aria-selected="true"] * {
            background-color: #151518 !important;
            background: #151518 !important;
            color: #FF4C00 !important;
        }

        .stApp div[data-baseweb="select"], .stApp div[data-baseweb="select"] * {
            background-color: #151518 !important; color: #F5F5F7 !important; fill: #F5F5F7 !important;
        }
        .stApp div[data-baseweb="select"] > div {
            background-color: #151518 !important; border: 1px solid rgba(255, 76, 0, 0.3) !important; border-radius: 8px !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"] p, .stApp [data-testid="stTabs"] [role="tab"] span {
            color: #A1A1AA !important; font-weight: 500 !important; visibility: visible !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] span {
            color: #FF4C00 !important; font-weight: 600 !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"] {
            background: transparent !important; opacity: 1 !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            border-bottom: 2px solid #FF4C00 !important;
        }
        .stApp [data-baseweb="tab-highlight"] {
            background-color: #FF4C00 !important;
        }
        .stApp div[data-testid="stChatInput"] {
            background-color: transparent !important; border: none !important;
        }
        .stApp div[data-testid="stChatInput"] > div {
            background-color: #0C0C0E !important;
            border: 1px solid rgba(255, 76, 0, 0.3) !important;
            border-radius: 24px !important;
            display: flex !important;
            align-items: center !important;
            padding: 3px 8px !important;
        }
        .stApp div[data-testid="stChatInput"] textarea {
            background-color: transparent !important;
            color: #F5F5F7 !important;
            border: none !important;
            padding: 8px 12px !important;
        }
        .stApp div[data-testid="stChatInput"] textarea::placeholder {
            color: #A1A1AA !important;
        }
        .stApp div[data-testid="stChatInput"] button {
            color: #FF4C00 !important;
        }
        .stApp [data-testid="stExpander"] details {
            background-color: #0C0C0E !important; border: 1px solid rgba(255, 76, 0, 0.22) !important;
        }
        div[data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #FF4C00 0%, #FF7A33 100%) !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
        }
        """
    else:  # 🍂 Warm Charcoal & Amber (Default)
        theme_scoped_css = """
        /* =========================================================
           WARM CHARCOAL & AMBER (🍂 DEFAULT) STRICT SCOPED OVERRIDES
           ========================================================= */
        .stApp {
            background: linear-gradient(135deg, #1C1917 0%, #241F1B 100%) !important;
            background-color: #1C1917 !important;
            color: #EAE3D8 !important;
        }
        .stApp [data-testid="stSidebar"] {
            background-color: #181513 !important;
        }

        /* Unscoped React Portal Popover & Dropdown Menu */
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

        /* Dropdown / Selectbox Surfaces */
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
        .stApp div[data-baseweb="select"] svg,
        .stApp div[data-baseweb="select"] path,
        .stApp [data-baseweb="icon"] svg,
        .stApp [data-baseweb="icon"] path {
            fill: #EAE3D8 !important;
            color: #EAE3D8 !important;
        }

        /* Tabs Underline & Highlight */
        .stApp [data-testid="stTabs"] [role="tab"] p,
        .stApp [data-testid="stTabs"] [role="tab"] span {
            color: #B0A695 !important;
            font-weight: 500 !important;
            visibility: visible !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] span {
            color: #E8B25C !important;
            font-weight: 600 !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"] {
            background: transparent !important;
            opacity: 1 !important;
        }
        .stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            border-bottom: 2px solid #E8B25C !important;
        }
        .stApp [data-baseweb="tab-highlight"] {
            background-color: #E8B25C !important;
        }

        /* Chat Input */
        .stApp div[data-testid="stChatInput"] {
            background-color: transparent !important;
            border: none !important;
        }
        .stApp div[data-testid="stChatInput"] > div {
            background-color: #2A2420 !important;
            border: 1px solid #443A2E !important;
            border-radius: 24px !important;
            display: flex !important;
            align-items: center !important;
            padding: 3px 8px !important;
        }
        .stApp div[data-testid="stChatInput"] textarea {
            background-color: #2A2420 !important;
            color: #EAE3D8 !important;
            border: 1px solid #443A2E !important;
            border: none !important;
            padding: 8px 12px !important;
        }
        .stApp div[data-testid="stChatInput"] textarea::placeholder {
            color: #B0A695 !important;
        }
        .stApp div[data-testid="stChatInput"] button,
        .stApp button[data-testid="stChatInputSubmitButton"] {
            color: #E8B25C !important;
        }
        .stApp div[data-testid="stChatInput"] button svg,
        .stApp div[data-testid="stChatInput"] button path,
        .stApp button[data-testid="stChatInputSubmitButton"] svg,
        .stApp button[data-testid="stChatInputSubmitButton"] path {
            fill: #E8B25C !important;
            color: #E8B25C !important;
        }

        /* Expander Headers */
        .stApp [data-testid="stExpander"] details {
            background-color: #2A2420 !important;
            border: 1px solid #443A2E !important;
        }
        .stApp [data-testid="stExpander"] details summary span,
        .stApp [data-testid="stExpander"] details summary p,
        .stApp [data-testid="stExpander"] details summary svg {
            color: #EAE3D8 !important;
            fill: #EAE3D8 !important;
        }

        /* Form Submit Button with Accent Gradient */
        div[data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #C9852F 0%, #E8B25C 100%) !important;
            color: #1C1917 !important;
            font-weight: 600 !important;
            border: none !important;
        }

        /* Chips & Tags */
        .chronicle-tag, .filter-chip {
            background-color: #2F2822 !important;
            color: #E8B25C !important;
            border: 1px solid #443A2E !important;
        }

        /* Chat Message Bubbles */
        .stApp .stChatMessage,
        .stApp div[data-testid="stChatMessage"] {
            background-color: #2A2420 !important;
            color: #EAE3D8 !important;
            border: 1px solid #443A2E !important;
        }
        .stApp div[data-testid="stChatMessage"] * {
            color: #EAE3D8 !important;
        }
        """

    # --- Dynamic Design System CSS Injection ---
    st.markdown(f"""
        <style>
                header[data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
        }
        div[data-testid="stDecoration"] {
            display: none !important;
        }
        div[data-testid="stStatusWidget"] {
            display: none !important;
        }
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&display=swap');

        {sidebar_layout_css}

        {theme_css}

        /* Core Canvas */
        .stApp {{
            background-color: var(--bg-main) !important;
            font-family: var(--font-body) !important;
            color: var(--text-primary) !important;
        }}

    h1, h2, h3, h4 {{
        font-family: var(--font-heading) !important;
        font-weight: 600;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }}

    /* Top App Bar — compact single row */
    .app-top-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 3px 12px;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        min-height: 34px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }}
    .brand-cluster {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .brand-orb {{
        width: 28px;
        height: 28px;
        border-radius: 9999px;
        background: var(--surface-container);
        color: var(--primary-color);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
    }}
    .brand-title {{
        font-family: var(--font-heading);
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.01em;
    }}
    .top-meta-chips {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .state-pill {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: var(--surface-container);
        border: 1px solid var(--border-color);
        color: var(--primary-color);
        font-size: 0.72rem;
        font-weight: 500;
        border-radius: 9999px;
        padding: 2px 9px;
    }}
    .streak-pill {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: var(--surface-container);
        color: var(--text-secondary);
        font-size: 0.72rem;
        font-weight: 500;
        border-radius: 9999px;
        padding: 2px 9px;
        border: 1px solid var(--border-color);
    }}

    /* Top Theme Switcher - Inline Row Alignment */
    .top-theme-container {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-end !important;
        height: 100%;
        margin: 0px !important;
        padding: 0px !important;
    }}
    div[data-testid="stColumn"]:has(#app_theme_dropdown) > [data-testid="stVerticalBlock"],
    div[data-testid="stColumn"]:has([data-baseweb="select"]) > [data-testid="stVerticalBlock"],
    div[data-testid="stHorizontalBlock"]:has(.app-top-bar) > div:nth-child(2) > [data-testid="stVerticalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-end !important;
        height: 100% !important;
    }}
    div[data-testid="stColumn"]:has(#app_theme_dropdown) div[data-testid="element-container"],
    div[data-testid="stHorizontalBlock"]:has(.app-top-bar) > div:nth-child(2) div[data-testid="element-container"] {{
        margin: 0px !important;
        padding: 0px !important;
        display: flex !important;
        align-items: center !important;
    }}
    /* Inline label alongside dropdown box */
    .top-theme-container div[data-testid="stSelectbox"],
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        margin: 0px !important;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        padding: 0px !important;
    }}
    .top-theme-container label,
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) label {{
        display: inline-flex !important;
        align-items: center !important;
        margin: 0px !important;
        margin-right: 6px !important;
        padding: 0px !important;
        min-height: 0px !important;
        white-space: nowrap !important;
    }}
    .top-theme-container label p,
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) label p {{
        font-size: 0.72rem !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        margin: 0px !important;
        padding: 0px !important;
        line-height: normal !important;
        white-space: nowrap !important;
    }}
    /* Dropdown box width & styling */
    .top-theme-container div[data-baseweb="select"],
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) div[data-baseweb="select"] {{
        max-width: 170px !important;
        width: 170px !important;
        min-width: 150px !important;
    }}
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) > div {{
        margin: 0px !important;
        padding: 0px !important;
    }}
    .top-theme-container div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) div[data-baseweb="select"] > div {{
        min-height: 34px !important;
        height: 34px !important;
        padding: 3px 12px !important;
        font-size: 0.78rem !important;
        border-radius: 12px !important;
        border: 1px solid var(--border-color) !important;
        background: var(--surface-main) !important;
        box-sizing: border-box !important;
        display: flex !important;
        align-items: center !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
    }}
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) div[data-baseweb="select"] span,
    div[data-testid="stSelectbox"]:has(#app_theme_dropdown) div[data-baseweb="select"] div {{
        font-size: 0.78rem !important;
        line-height: normal !important;
    }}

    /* Google Gemini Hero Greeting — compact */
    .gemini-hero-greeting-container {{
        margin-bottom: 2px !important;
        padding-top: 0px !important;
    }}
    .gemini-greeting-gradient {{
        font-family: var(--font-heading);
        font-size: 1.25rem !important;
        font-weight: 600;
        line-height: 1.15 !important;
        margin-bottom: 1px !important;
        letter-spacing: -0.01em;
        background: linear-gradient(74deg, #4285F4 0%, #9B72CB 25%, #D96570 50%, var(--text-primary) 85%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .gemini-subgreeting {{
        font-size: 0.78rem !important;
        color: var(--text-secondary);
        line-height: 1.2 !important;
        font-weight: 400;
        margin-bottom: 2px !important;
    }}

    /* Gemini-Style Sidebar Background & Components */
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-color) !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background-color: var(--sidebar-bg) !important;
    }}
    [data-testid="stSidebar"] div.stButton:first-of-type > button {{
        background: var(--surface-main) !important;
        color: var(--text-primary) !important;
        border-radius: 9999px !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 10px 20px !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stSidebar"] div.stButton:first-of-type > button:hover {{
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        background: var(--surface-container) !important;
    }}

    .gemini-sidebar-section-title {{
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: var(--text-secondary);
        margin-bottom: 8px;
        padding-left: 4px;
    }}
    /* Plus Popover Attachment Button next to Chat Bar */
    div[data-testid="stPopover"] {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 100% !important;
        margin-top: 2px !important;
    }}
    div[data-testid="stPopover"] > button {{
        padding: 0px !important;
        height: 42px !important;
        width: 42px !important;
        min-width: 42px !important;
        border-radius: 12px !important;
        font-size: 1.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: var(--surface-main) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stPopover"] > button:hover {{
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        background: var(--surface-container-high) !important;
        transform: scale(1.05);
    }}
    .gemini-history-item {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        padding: 6px 10px;
        border-radius: 8px;
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        margin-bottom: 4px;
        transition: all 0.2s ease;
    }}
    .gemini-history-item:hover {{
        background: var(--surface-container-high);
        border-color: var(--primary-color);
    }}
    .gemini-history-title {{
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .gemini-history-meta {{
        font-size: 0.68rem;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .gemini-sidebar-stats-card {{
        display: flex;
        gap: 8px;
        margin-bottom: 14px;
    }}
    .gemini-stat-pill {{
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 9999px;
        padding: 4px 10px;
        font-size: 0.76rem;
        color: var(--text-primary);
    }}
    .gemini-sidebar-profile-dock {{
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }}
    .gemini-profile-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }}
    .gemini-avatar-img {{
        width: 36px;
        height: 36px;
        border-radius: 9999px;
        object-fit: cover;
        border: 1.5px solid var(--primary-color);
    }}
    .gemini-avatar-initials {{
        width: 36px;
        height: 36px;
        border-radius: 9999px;
        background: var(--surface-container-high);
        color: var(--primary-color);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 1rem;
    }}
    .gemini-profile-name {{
        font-weight: 600;
        font-size: 0.88rem;
        color: var(--text-primary);
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .gemini-profile-email {{
        font-size: 0.74rem;
        color: var(--text-secondary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .gemini-tenant-tag {{
        font-size: 0.68rem;
        background: var(--surface-container);
        color: var(--text-secondary);
        border-radius: 9999px;
        padding: 2px 8px;
        display: inline-block;
        font-family: monospace;
        border: 1px solid var(--border-color);
    }}

    /* WhatsApp / Chat-Style Alignment */
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
    .stChatMessage:has([data-testid="chatAvatarIcon-user"]) {{
        flex-direction: row-reverse !important;
        margin-left: auto !important;
        margin-right: 0px !important;
        max-width: 82% !important;
        background: var(--surface-container-high) !important;
        border: 1px solid var(--primary-color) !important;
        border-top-right-radius: 4px !important;
        border-top-left-radius: 18px !important;
        border-bottom-left-radius: 18px !important;
        border-bottom-right-radius: 18px !important;
        text-align: right !important;
    }}
    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
    .stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {{
        flex-direction: row !important;
        margin-right: auto !important;
        margin-left: 0px !important;
        max-width: 85% !important;
        background: var(--surface-main) !important;
        border: 1px solid var(--border-color) !important;
        border-top-left-radius: 4px !important;
        border-top-right-radius: 18px !important;
        border-bottom-left-radius: 18px !important;
        border-bottom-right-radius: 18px !important;
        text-align: left !important;
    }}

    /* Chronicle Feed Cards */
    .chronicle-header-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }}
    .chronicle-heading {{
        font-family: var(--font-heading);
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--text-primary);
    }}
    .chronicle-counter {{
        font-size: 0.78rem;
        color: var(--text-secondary);
        background: var(--surface-container);
        padding: 3px 10px;
        border-radius: 9999px;
    }}
    .entry-card {{
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease, background-color 0.2s ease;
    }}
    .entry-card:hover {{
        background: var(--surface-container);
        border-color: var(--card-hover-border);
    }}
    .entry-meta-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 8px;
    }}
    .date-pill {{
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-secondary);
        background: var(--surface-container-high);
        padding: 3px 9px;
        border-radius: 9999px;
    }}
    .entry-headline {{
        font-family: var(--font-heading);
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 6px;
        line-height: 1.35;
    }}
    .entry-summary {{
        font-size: 0.85rem;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-bottom: 12px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .chips-cluster {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
    }}
    .pill-chip {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 0.72rem;
        font-weight: 500;
    }}
    .chip-loc {{
        background: rgba(125, 172, 248, 0.12);
        color: var(--accent-blue);
    }}
    .chip-media {{
        background: rgba(125, 172, 248, 0.14);
        color: var(--accent-blue);
    }}
    .chip-tag {{
        background: var(--surface-container);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }}
    .reframe-card-box {{
        background: var(--emerald-container);
        border-left: 3px solid var(--emerald-accent);
        border-radius: 12px;
        padding: 10px 14px;
        margin-top: 12px;
        font-size: 0.83rem;
        color: var(--text-primary);
        line-height: 1.45;
    }}
    .reframe-title {{
        font-weight: 600;
        color: var(--emerald-accent);
        margin-bottom: 2px;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .block-container {{
        margin-top: 0 !important;
        padding-top: 0.25rem !important;
    }}

    /* -------------------------------------------------------
       Responsive Breakpoints - Narrower Viewport Fixes
    ------------------------------------------------------- */
    @media (max-width: 1100px) {{
        .app-top-bar {{
            flex-wrap: wrap;
            gap: 6px;
            padding: 6px 10px;
        }}
        .top-meta-chips {{
            flex-wrap: wrap;
            gap: 6px;
        }}
        .brand-title {{
            font-size: 1.05rem;
        }}
        .metric-grid-4 {{
            grid-template-columns: repeat(2, 1fr);
        }}
        .block-container {{
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }}
    }}
    @media (max-width: 820px) {{
        .metric-grid-4 {{
            grid-template-columns: 1fr 1fr;
        }}
        .app-top-bar {{
            flex-direction: column;
            align-items: flex-start;
        }}
        .streak-pill, .state-pill {{
            font-size: 0.7rem;
            padding: 2px 8px;
        }}
    }}

    @keyframes empty-pulse {{
        0%, 100% {{ box-shadow: 0 0 24px rgba(232, 178, 92, 0.18); }}
        50% {{ box-shadow: 0 0 40px rgba(232, 178, 92, 0.36); }}
    }}
    .journal-chat-scroll,
    .sidebar-history-scroll,
    .analytics-pane-scroll {{
        display: block !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none !important;
    }}
    div[data-testid="element-container"]:has(.journal-chat-scroll),
    div[data-testid="element-container"]:has(.sidebar-history-scroll),
    div[data-testid="element-container"]:has(.analytics-pane-scroll) {{
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }}

    /* Branded loading splash */
    .rp-splash {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
        gap: 16px;
    }}
    .rp-splash-orb {{
        width: 80px;
        height: 80px;
        border-radius: 9999px;
        background: var(--surface-container);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.5rem;
        animation: empty-pulse 1.8s ease-in-out infinite;
    }}
    .rp-splash-title {{
        font-family: var(--font-heading);
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(74deg, #4285F4 0%, #9B72CB 25%, #D96570 50%, var(--text-primary) 85%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .rp-splash-sub {{
        font-size: 0.85rem;
        color: var(--text-secondary);
    }}

    /* Perspective Shift - Discoverable subtitle */
    .ps-label-desc {{
        font-size: 0.74rem;
        color: var(--text-secondary);
        margin-top: -4px;
        margin-bottom: 4px;
        padding-left: 2px;
        line-height: 1.4;
    }}

    /* Metric Grid */
    .metric-grid-4 {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 22px;
    }}
    .metric-box {{
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 18px 14px;
        text-align: center;
        transition: background-color 0.2s ease;
    }}
    .metric-box:hover {{
        background: var(--surface-container);
    }}
    .metric-label {{
        font-size: 0.74rem;
        font-weight: 500;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }}
    .metric-number {{
        font-family: var(--font-heading);
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--text-primary);
    }}

    /* Weekly Digest Paper */
    .digest-paper-container {{
        background: var(--surface-main);
        border: 1px solid var(--border-color);
        border-radius: 22px;
        padding: 30px 26px;
        margin-top: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }}

    /* Clean Minimalist Tabs with Underline Indicator */
    div[data-testid="stTabs"] {{
        background: transparent !important;
        border: none !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"] {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        padding: 8px 16px !important;
        box-shadow: none !important;
        transition: color 0.2s ease !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"] p,
    div[data-testid="stTabs"] button[data-baseweb="tab"] span,
    div[data-testid="stTabs"] button[data-baseweb="tab"] div {{
        color: var(--tab-inactive-text) !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }}
    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{
        color: var(--tab-active-text) !important;
        background: transparent !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid var(--primary-color) !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] p,
    div[data-testid="stTabs"] button[aria-selected="true"] span,
    div[data-testid="stTabs"] button[aria-selected="true"] div {{
        color: var(--tab-active-text) !important;
        font-weight: 600 !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: var(--primary-color) !important;
    }}

    /* Text Inputs and TextAreas */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {{
        background: var(--input-bg) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        border-radius: 12px !important;
    }}
    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder {{
        color: var(--placeholder-color) !important;
    }}

    /* Widget Labels */
    label[data-testid="stWidgetLabel"] p,
    .stSelectbox label p,
    .stTextInput label p,
    .stTextArea label p {{
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
    }}

    /* Filled Tonal Submit Button */
    div[data-testid="stFormSubmitButton"] > button {{
        background: var(--primary-color) !important;
        color: var(--on-primary-color) !important;
        font-weight: 600 !important;
        border-radius: 9999px !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
        transition: opacity 0.2s ease, transform 0.2s ease !important;
    }}
    div[data-testid="stFormSubmitButton"] > button:hover {{
        opacity: 0.92 !important;
        transform: translateY(-1px) !important;
    }}

    /* Highest Priority Scoped Theme Rules */
    {theme_scoped_css}
    </style>
    <script>
    try {{
        localStorage.setItem("stSidebarCollapsed", "false");
        sessionStorage.setItem("stSidebarCollapsed", "false");
    }} catch(e) {{}}
    </script>
""", unsafe_allow_html=True)

render_custom_css(current_theme)

# --- Authentication Guard ---
if not firestore_service.db:
    render_custom_css(current_theme)
    st.markdown("""
        <div class='rp-splash'>
            <div class='rp-splash-orb'>🔮</div>
            <div class='rp-splash-title'>ReflectPulse</div>
            <div class='rp-splash-sub'>We're having trouble connecting right now — please refresh or try again in a moment.</div>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

# Process Google OAuth 2.0 callback if returning with ?code=...
# Show a branded loading splash while the OAuth exchange is in-flight.
if not st.session_state.authenticated:
    # Detect if we're mid-callback (URL has ?code= query param)
    query_params = st.query_params
    if "code" in query_params:
        # Show branded loading state while tokens are being exchanged
        st.markdown("""
            <div class='rp-splash'>
                <div class='rp-splash-orb'>🔮</div>
                <div class='rp-splash-title'>ReflectPulse</div>
                <div class='rp-splash-sub'>Signing you in — just a moment…</div>
            </div>
        """, unsafe_allow_html=True)
    auth.handle_oauth_callback()

if not st.session_state.authenticated:
    auth.show_auth_ui()
    st.stop()

# --- Authenticated User Metadata ---
user = st.session_state.user
user_id = user.get("id", "anonymous")
user_email = user.get("email", "unknown@example.com")
user_name = user.get("name", user_email.split("@")[0].capitalize())
user_picture = user.get("picture", "")

def extract_first_name(full_name: str, email: str = "") -> str:
    if not full_name:
        return email.split("@")[0].capitalize() if email else "friend"
    parts = full_name.strip().split()
    honorifics = {"dr", "dr.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "prof", "prof."}
    for part in parts:
        clean_part = part.strip()
        if clean_part.lower() not in honorifics and clean_part:
            return clean_part
    return parts[0] if parts else "friend"

first_name = extract_first_name(user_name, user_email)

# Fetch strictly isolated tenant journal entries
entries = firestore_service.get_journal_entries(user_id)
total_entries = len(entries)
curr_streak, max_streak = analytics.calculate_journal_streaks(entries)

# Determine recent mood for active state pill
recent_mood = entries[0].get("mood_category", "Reflective") if entries else "Reflective"

# --- Gemini-Style Sidebar Overhaul ---
with st.sidebar:
    # Top: Large Pill Button "+ New reflection"
    if st.button("＋ New reflection", key="gemini_new_entry_btn", use_container_width=True):
        st.session_state.chat_session = None
        st.session_state.chat_history = []
        st.session_state.active_entry_id = None
        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
        st.rerun()
    
    st.markdown(f"""
        <div class="gemini-sidebar-stats-card" style="margin-top: 8px; margin-bottom: 10px;">
            <div class="gemini-stat-pill">📝 <b>{total_entries}</b> reflections</div>
            <div class="gemini-stat-pill">🔥 <b>{curr_streak}d</b> streak</div>
        </div>
    """, unsafe_allow_html=True)

    # Middle: Chronicle Past Reflections List (Gemini Left-Rail History)
    st.markdown('<div class="gemini-sidebar-section-title">RECENT REFLECTIONS</div>', unsafe_allow_html=True)
    with st.container(height=300, border=False):
        st.markdown('<div class="sidebar-history-scroll"></div>', unsafe_allow_html=True)
        if not entries:
            st.markdown("""
                <div style="text-align:center; padding: 18px 8px; color: var(--text-secondary); font-size: 0.8rem; line-height: 1.5;">
                    ✨ Your first reflection will appear here.<br/>Use the journal area on the right to begin.
                </div>
            """, unsafe_allow_html=True)
        else:
            for entry in entries:
                date_val = entry.get("created_at")
                date_str = date_val.strftime("%b %d") if hasattr(date_val, "strftime") else str(date_val)[:10]
                title = entry.get("title", "Reflection")
                mood = entry.get("mood_category", "Calm")
                score = entry.get("mood_score", 5)
                summary = entry.get("summary", "")

                col_h1, col_h2 = st.columns([4.8, 1.2], gap="small", vertical_alignment="center")
                with col_h1:
                    if st.button(f"📝 {title}", key=f"open_chat_{entry['id']}", use_container_width=True, help=f"{date_str} • {mood} {score}/10\n{summary}"):
                        raw_transcript = entry.get("chat_transcript")
                        if raw_transcript and isinstance(raw_transcript, list) and len(raw_transcript) > 0:
                            st.session_state.chat_history = raw_transcript
                        else:
                            # Regex/delimiter parser for plain-text content
                            loaded_history = []
                            raw_text = entry.get("content", "")
                            # Split by 'User: ' or 'AI: ' tokens cleanly
                            parts = re.split(r'(?=(?:User|AI):\s)', raw_text)
                            for part in parts:
                                part = part.strip()
                                if part.startswith("User:"):
                                    loaded_history.append({"role": "user", "content": part.replace("User:", "", 1).strip()})
                                elif part.startswith("AI:"):
                                    loaded_history.append({"role": "model", "content": part.replace("AI:", "", 1).strip()})
                                elif part:
                                    loaded_history.append({"role": "model", "content": part})
                            st.session_state.chat_history = loaded_history if loaded_history else [
                                {"role": "model", "content": entry.get("summary", "Reflection entry loaded.")}
                            ]
                        st.session_state.active_entry_id = entry["id"]
                        st.rerun()
                with col_h2:
                    if st.button("🗑️", key=f"sb_del_{entry['id']}", help="Delete reflection"):
                        if firestore_service.delete_journal_entry(user_id, entry["id"]):
                            if st.session_state.get("active_entry_id") == entry["id"]:
                                st.session_state.chat_session = None
                                st.session_state.chat_history = []
                                st.session_state.active_entry_id = None
                            st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Tools: Perspective Shift Tool — subtitled for discoverability
    with st.expander("💡 Perspective Shift", expanded=False):
        st.markdown("<div class='ps-label-desc'>Get a fresh angle on a tough thought — write it below and Gemini will offer a calm, constructive reframe.</div>", unsafe_allow_html=True)
        sidebar_thought_input = st.text_area(
            "Notice a challenging thought:", 
            placeholder="e.g., I'm overwhelmed and falling behind...", 
            height=70, 
            key="sb_thought_in"
        )
        if st.button("Explore Perspective", key="sb_reframe_btn", use_container_width=True):
            if sidebar_thought_input.strip():
                with st.spinner("Exploring a fresh perspective..."):
                    try:
                        perspective_res = gemini_service.suggest_perspective(sidebar_thought_input)
                        st.markdown(f"""
                            <div class="reframe-card-box">
                                <div class="reframe-title">💡 Alternative Perspective</div>
                                {perspective_res}
                            </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.warning("Couldn't generate a perspective right now — please try again in a moment.")
            else:
                st.info("Write a thought above and then tap Explore to get a fresh angle.")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Bottom: User Profile Dock & Sign Out
    avatar_elem = (
        f'<img src="{user_picture}" class="gemini-avatar-img" />'
        if user_picture
        else f'<div class="gemini-avatar-initials">{user_name[0].upper()}</div>'
    )

    st.markdown(f"""
        <div class="gemini-sidebar-profile-dock">
            <div class="gemini-profile-row">
                {avatar_elem}
                <div style="overflow: hidden;">
                    <div class="gemini-profile-name">{user_name}</div>
                    <div class="gemini-profile-email">{user_email}</div>
                </div>
            </div>
            <div class="gemini-tenant-tag">TENANT: {user_id[:16]}...</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Sign Out", key="sidebar_logout_btn", use_container_width=True):
        auth.logout_user()

# --- Top App Bar with Embedded Theme Switcher ---
# Zero gap between the two columns to keep bar and selector on one tight row
is_authenticated = st.session_state.get("authenticated", False)

if is_authenticated:
    col_bar_left, col_bar_right = st.columns([3.8, 1.2], vertical_alignment="center", gap="small")

    with col_bar_left:
        st.markdown(f"""
            <div class="app-top-bar" style="margin-bottom: 0;">
                <div class="brand-cluster">
                    <div class="brand-orb">🔮</div>
                    <div class="brand-title">ReflectPulse</div>
                </div>
                <div class="top-meta-chips">
                    <div class="state-pill">
                        <span>✨ State:</span> {recent_mood}
                    </div>
                    <div class="streak-pill">
                        🔥 <b>{curr_streak}d</b> streak &nbsp;•&nbsp; 📝 <b>{total_entries}</b> reflections
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_bar_right:
        current_idx = THEME_OPTIONS.index(st.session_state.theme) if st.session_state.theme in THEME_OPTIONS else 0
        selected_app_theme = st.selectbox(
            "Theme:",
            options=THEME_OPTIONS,
            index=current_idx,
            label_visibility="visible",
            key="app_theme_dropdown"
        )
        if selected_app_theme != st.session_state.theme:
            st.session_state.theme = selected_app_theme
            st.rerun()
else:
    st.markdown(f"""
        <div class="app-top-bar" style="margin-bottom: 0;">
            <div class="brand-cluster">
                <div class="brand-orb">🔮</div>
                <div class="brand-title">ReflectPulse</div>
            </div>
            <div class="top-meta-chips">
                <div class="state-pill">
                    <span>✨ State:</span> {recent_mood}
                </div>
                <div class="streak-pill">
                    🔥 <b>{curr_streak}d</b> streak &nbsp;•&nbsp; 📝 <b>{total_entries}</b> reflections
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Main Navigation Tabs
tab_journal, tab_analytics = st.tabs([
    "✍️ Journal Studio", 
    "📊 Analytics & Synthesis"
])

# --- TAB 1: JOURNAL STUDIO ---
with tab_journal:
    # Full-Width Journal Studio Main Area (matching Gemini web interface)
    # Authentic Google Gemini Hero Greeting
    st.markdown(f"""
        <div class="gemini-hero-greeting-container">
            <div class="gemini-greeting-gradient">Hi {first_name}, let's reflect today</div>
            <div class="gemini-subgreeting">Capture a voice note, upload a photo moment, or converse with Gemini.</div>
        </div>
    """, unsafe_allow_html=True)

    # Conversational Companion Engine
    if "chat_session" not in st.session_state or st.session_state.chat_session is None:
        st.session_state.chat_session = gemini_service.create_chat_session()
        if not st.session_state.get("chat_history"):
            st.session_state.chat_history = []
            welcome_text = "What is on your mind today? Write, speak, or upload a photo to reflect with Gemini."
            st.session_state.chat_history.append({"role": "model", "content": welcome_text})

    # Chat Stream Area: Dedicated Scrollable Middle Zone (input + save dock stay pinned)
    chat_container = st.container(height=280, border=False)
    with chat_container:
        st.markdown('<div class="journal-chat-scroll"></div>', unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            role = "assistant" if msg["role"] == "model" else "user"
            with st.chat_message(role):
                st.write(msg["content"])
    
    # Multimodal Attach (+) Next to Chat Input Bar
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0)
    active_audio_capture = None
    photo_upload = None
    st.markdown("<div style='height: 70px;'></div>", unsafe_allow_html=True)
    input_col1, input_col2 = st.columns([0.08, 0.92], gap="small")
    with input_col1:
        with st.popover("➕", help="Add Photo or Voice Note"):
            st.markdown("##### 📎 Moment Attachments")
            photo_upload = st.file_uploader("Upload Moment Photo", type=["jpg", "jpeg", "png"], key=f"photo_upl_{st.session_state.uploader_key}")
            file_audio = st.file_uploader("Upload Voice Note", type=["wav", "mp3", "m4a"], key=f"voice_upl_{st.session_state.uploader_key}")
            active_audio_capture = file_audio
            if active_audio_capture:
                st.audio(active_audio_capture)
                st.markdown("<span class='pill-chip chip-media'>🎙️ Audio Attached</span>", unsafe_allow_html=True)
            if photo_upload:
                st.image(photo_upload, width=160)
                st.markdown("<span class='pill-chip chip-media'>📷 Image Attached</span>", unsafe_allow_html=True)
    with input_col2:
        user_prompt = st.chat_input("Write down your reflection, feelings, or questions...")

    if user_prompt and user_prompt.strip():
        with chat_container:
            with st.chat_message("user"):
                st.write(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        with chat_container:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown("*Thinking…*")
                if gemini_service.client and st.session_state.chat_session:
                    try:
                        reply = gemini_service.send_chat_message(st.session_state.chat_session, user_prompt)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"[Gemini chat error] {e}")
                        reply = "I'm having a little trouble connecting right now — please try again in a moment."
                elif not gemini_service.client:
                    reply = "The AI companion isn't available yet — please refresh or check your connection."
                elif not st.session_state.chat_session:
                    reply = "The reflection session needs a moment to start — please refresh the page."
                else:
                    reply = "Something unexpected happened. Please refresh and try again."
                placeholder.write(reply)
        st.session_state.chat_history.append({"role": "model", "content": reply})

    # Show visual badge if attachment is active
    if active_audio_capture or photo_upload:
        chips = []
        if active_audio_capture:
            chips.append("<span class='pill-chip chip-media'>🎙️ Audio Attached</span>")
        if photo_upload:
            chips.append("<span class='pill-chip chip-media'>📷 Photo Attached</span>")
        st.markdown(f"<div style='margin-bottom: 2px;'>{' '.join(chips)}</div>", unsafe_allow_html=True)

    # Integrated Save Reflection Docked Footer Bar
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    with st.form("save_reflection_form", clear_on_submit=False):
        hour = datetime.now().hour
        time_of_day = "Morning" if hour < 12 else ("Afternoon" if hour < 17 else "Evening")
        suggested_title = f"{time_of_day} Reflection • {datetime.now().strftime('%b %d')}"
        
        col_f1, col_f2, col_f3 = st.columns([1.8, 1.2, 1.4], gap="small")
        with col_f1:
            entry_title = st.text_input("Reflection Title", value=suggested_title, label_visibility="collapsed", placeholder="Reflection Title")
        with col_f2:
            location_choice = st.selectbox(
                "Context Setting",
                ["Auto-detect via AI", "Campus", "Workplace", "Home", "Travel", "Nature", "Social", "Custom"],
                index=0,
                label_visibility="collapsed"
            )
        with col_f3:
            save_action = st.form_submit_button("🔮 Synthesize & Save", use_container_width=True)
            
        custom_loc_val = ""
        if location_choice == "Custom":
            custom_loc_val = st.text_input("Specify Setting", placeholder="e.g., Studio, Library, Cafe", label_visibility="collapsed")
        
        if save_action:
            has_aud = bool(active_audio_capture)
            has_img = bool(photo_upload)
            # Only count actual user turns (model welcome doesn't count)
            user_turns = [m for m in st.session_state.chat_history if m.get("role") == "user"]
            has_txt = len(user_turns) >= 1
            
            if not (has_txt or has_aud or has_img):
                st.info("Share a thought, voice note, or photo before synthesizing your reflection.")
            else:
                with st.spinner("Synthesizing your reflection — analysing themes, mood, and perspective…"):
                    try:
                        transcript = st.session_state.chat_history.copy()
                        full_content = "\n".join([
                            f"{'User' if m['role']=='user' else 'AI'}: {m['content']}"
                            for m in transcript
                        ])
                        
                        aud_bytes = active_audio_capture.getvalue() if active_audio_capture else None
                        aud_mime = "audio/wav"
                        if active_audio_capture:
                            name_str = getattr(active_audio_capture, "name", "").lower()
                            if name_str.endswith(".mp3"):
                                aud_mime = "audio/mp3"
                            elif name_str.endswith(".m4a"):
                                aud_mime = "audio/m4a"

                        img_bytes = photo_upload.getvalue() if photo_upload else None
                        img_mime = getattr(photo_upload, "type", "image/jpeg") if photo_upload else "image/jpeg"
                        
                        hint = custom_loc_val.strip() if (location_choice == "Custom" and custom_loc_val.strip()) else location_choice

                        analysis = gemini_service.analyze_reflection(
                            chat_history=transcript,
                            audio_bytes=aud_bytes,
                            audio_mime_type=aud_mime,
                            image_bytes=img_bytes,
                            image_mime_type=img_mime,
                            context_hint=hint
                        )
                        
                        doc = {
                            "title": entry_title.strip() or suggested_title,
                            "content": full_content,
                            "chat_transcript": st.session_state.chat_history,  # Raw list of {'role': 'user'|'model', 'content': '...'}
                            "summary": analysis.summary,
                            "mood_category": analysis.mood_category,
                            "mood_score": analysis.mood_score,
                            "theme_tags": analysis.theme_tags,
                            "reflection_prompt": analysis.reflection_prompt,
                            "location_tag": analysis.location_tag,
                            "perspective_note": getattr(analysis, "perspective_note", None),
                            "has_audio": bool(aud_bytes),
                            "has_image": bool(img_bytes),
                            "created_at": datetime.now(timezone.utc)
                        }
                        
                        firestore_service.create_journal_entry(user_id, doc)
                        
                        st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
                        st.session_state.chat_session = None
                        st.session_state.chat_history = []
                        st.session_state.active_entry_id = None
                        st.toast("Reflection stored securely.", icon="🔮")
                        st.rerun()
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"[Save reflection error] {e}")
                        st.warning("We couldn't save your reflection right now — your conversation is still here. Please try again in a moment.")

# --- TAB 2: ANALYTICS & SYNTHESIS ---
with tab_analytics:
    # Sized to fill available tab space, matching chat_container behavior
    analytics_scroll = st.container(height=520, border=False)
    with analytics_scroll:
        st.markdown('<div class="analytics-pane-scroll"></div>', unsafe_allow_html=True)
        avg_mood = (sum(e.get("mood_score", 5) for e in entries) / total_entries) if total_entries else 0.0

        # Metric Grid
        st.markdown(f"""
            <div class="metric-grid-4">
                <div class="metric-box">
                    <div class="metric-label">Current Streak</div>
                    <div class="metric-number">{curr_streak} <span style="font-size:1rem;color:var(--text-secondary);font-weight:400;">days</span></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Best Streak</div>
                    <div class="metric-number">{max_streak} <span style="font-size:1rem;color:var(--text-secondary);font-weight:400;">days</span></div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Total Chronicle</div>
                    <div class="metric-number">{total_entries}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Average Mood</div>
                    <div class="metric-number">{avg_mood:.1f} <span style="font-size:1rem;color:var(--text-secondary);font-weight:400;">/ 10</span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Themed Plotly Charts Row
        col_c1, col_c2 = st.columns(2, gap="large")
        with col_c1:
            try:
                st.plotly_chart(analytics.generate_mood_trend_chart(entries, theme=st.session_state.theme), use_container_width=True)
            except Exception:
                st.caption("Mood trend chart couldn't load — please refresh.")
        with col_c2:
            try:
                st.plotly_chart(analytics.generate_theme_distribution_chart(entries, theme=st.session_state.theme), use_container_width=True)
            except Exception:
                st.caption("Theme distribution chart couldn't load — please refresh.")

        # Editorial Weekly Digest Section
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("### 🌌 Weekly Reflective Synthesis")
        st.markdown("<div style='color:var(--text-secondary);font-size:0.9rem;margin-bottom:16px;'>Synthesize recurring themes, mood patterns, and constructive takeaways from the past 7 days into an executive report.</div>", unsafe_allow_html=True)

        if st.button("✨ Generate Weekly Digest", use_container_width=True):
            with st.spinner("Synthesising your reflective trends — this may take a moment…"):
                try:
                    digest_content = gemini_service.generate_weekly_digest(entries[:10])
                    st.markdown(f"""
                        <div class="digest-paper-container">
                            {digest_content}
                        </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"[Weekly digest error] {e}")
                    st.warning("Couldn't generate the weekly digest right now — please try again in a moment.")

        # Subtle Safety & Medical Disclaimer Footer
        st.markdown("""
            <div style="text-align: center; margin-top: 24px; margin-bottom: 8px; padding: 10px 20px; border-top: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.82rem; line-height: 1.5;">
                ReflectPulse is an AI reflective journaling companion designed for personal insight, not medical or mental health advice.
            </div>
        """, unsafe_allow_html=True)

# Re-inject custom theme CSS at the bottom of DOM to win any cascade/timing order
render_custom_css(current_theme)
