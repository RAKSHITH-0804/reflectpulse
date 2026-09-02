import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import firestore_service
import gemini_service
import auth
import analytics

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="ReflectPulse - Immersive Reflective Studio",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Obsidian & Flame Immersive Design System CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,600;1,700&display=swap');

    /* Design System Color Tokens */
    :root {
        --obsidian-base: #050404;
        --obsidian-surface: #0A0A0C;
        --obsidian-card: #0E0E11;
        --obsidian-elevated: #141418;
        
        --flame-vivid: #FF4C00;
        --flame-bright: #FF7A33;
        --flame-glow: #FF9E66;
        --flame-subtle: rgba(255, 76, 0, 0.12);
        
        --linen-head: #F5F5F7;
        --linen-subtext: #A1A1AA;
        --linen-muted: #71717A;
        --hairline-border: rgba(255, 255, 255, 0.08);
    }

    /* Core Canvas Styling */
    .stApp {
        background-color: var(--obsidian-base) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--linen-head);
        letter-spacing: -0.01em;
    }

    h1, h2, h3, h4, .serif-font {
        font-family: 'Playfair Display', Georgia, serif !important;
        color: var(--linen-head);
        letter-spacing: -0.02em;
    }

    /* Layout Spacing Normalization */
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        max-width: 1440px !important;
    }

    /* Minimalist Flame Top Bar */
    .flame-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(12, 12, 14, 0.75);
        backdrop-filter: blur(20px);
        border: 1px solid var(--hairline-border);
        border-radius: 16px;
        padding: 12px 24px;
        margin-bottom: 22px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.6);
        position: relative;
    }
    .flame-top-bar::after {
        content: '';
        position: absolute;
        bottom: -1px;
        left: 20%;
        right: 20%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 76, 0, 0.4), transparent);
    }
    .brand-group {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-orb {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: linear-gradient(135deg, rgba(255, 76, 0, 0.25), rgba(255, 122, 51, 0.1));
        border: 1px solid rgba(255, 76, 0, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        box-shadow: 0 0 16px rgba(255, 76, 0, 0.2);
    }
    .brand-name {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--linen-head);
        letter-spacing: -0.01em;
    }
    .brand-flame-tag {
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        background: var(--flame-subtle);
        color: var(--flame-bright);
        border: 1px solid rgba(255, 76, 0, 0.25);
        border-radius: 6px;
        padding: 2px 7px;
        letter-spacing: 0.08em;
    }
    .top-meta-group {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .flame-state-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 76, 0, 0.08);
        border: 1px solid rgba(255, 76, 0, 0.25);
        color: var(--flame-glow);
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 9999px;
        padding: 4px 12px;
    }
    .streak-chip {
        font-size: 0.84rem;
        color: var(--linen-subtext);
        font-weight: 500;
    }

    /* Executive Sidebar Profile */
    .sidebar-executive-card {
        background: var(--obsidian-surface);
        border: 1px solid var(--hairline-border);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 18px;
    }
    .profile-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    }
    .profile-avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 2px solid rgba(255, 76, 0, 0.6);
        object-fit: cover;
    }
    .profile-initials {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: linear-gradient(135deg, #FF4C00, #B43403);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        border: 2px solid rgba(255, 255, 255, 0.15);
    }
    .profile-name {
        font-weight: 700;
        font-size: 0.95rem;
        color: var(--linen-head);
        line-height: 1.2;
    }
    .profile-email {
        font-size: 0.78rem;
        color: var(--linen-subtext);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 170px;
    }
    .tenant-pill {
        font-size: 0.72rem;
        background: rgba(0, 0, 0, 0.4);
        color: var(--linen-muted);
        border-radius: 6px;
        padding: 3px 8px;
        font-family: monospace;
        border: 1px solid var(--hairline-border);
        word-break: break-all;
    }

    /* Ambient Thought Reframer */
    .ambient-reframer {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 4, 4, 0.6) 100%);
        border: 1px solid rgba(16, 185, 129, 0.22);
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 16px;
    }

    /* Chronicle Feed Cards */
    .chronicle-header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .chronicle-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--linen-head);
    }
    .chronicle-badge {
        font-size: 0.78rem;
        color: var(--linen-subtext);
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 8px;
        border-radius: 12px;
    }
    .chronicle-entry-card {
        background: var(--obsidian-surface);
        border: 1px solid var(--hairline-border);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.22s ease;
    }
    .chronicle-entry-card:hover {
        border-color: rgba(255, 76, 0, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px -6px rgba(255, 76, 0, 0.12);
    }
    .entry-meta-line {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 8px;
    }
    .entry-date-chip {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--linen-subtext);
        background: rgba(255, 255, 255, 0.04);
        padding: 2px 7px;
        border-radius: 5px;
    }
    .entry-headline {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--linen-head);
        margin-bottom: 6px;
        line-height: 1.35;
    }
    .entry-excerpt {
        font-size: 0.85rem;
        color: #D4D4D8;
        line-height: 1.45;
        margin-bottom: 10px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .entry-chips-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
    }
    .badge-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border-radius: 9999px;
        padding: 2px 8px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .badge-loc {
        background: rgba(255, 76, 0, 0.08);
        color: #FF7A33;
        border: 1px solid rgba(255, 76, 0, 0.25);
    }
    .badge-tag {
        background: rgba(255, 255, 255, 0.04);
        color: var(--linen-head);
        border: 1px solid var(--hairline-border);
    }
    .badge-media {
        background: rgba(255, 122, 51, 0.1);
        color: #FF9E66;
        border: 1px solid rgba(255, 122, 51, 0.25);
    }
    .reframe-callout {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(6, 78, 59, 0.12) 100%);
        border-left: 3px solid #10B981;
        border-radius: 8px;
        padding: 10px 12px;
        margin-top: 10px;
        font-size: 0.82rem;
        color: #A7F3D0;
        line-height: 1.45;
    }
    .reframe-header {
        font-weight: 700;
        color: #6EE7B7;
        margin-bottom: 3px;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* Reflection Studio Panel */
    .studio-shell {
        background: var(--obsidian-surface);
        border: 1px solid var(--hairline-border);
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .studio-header {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--linen-head);
        margin-bottom: 12px;
    }

    /* Executive Metric Tiles */
    .obsidian-metric-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    .obsidian-metric-card {
        background: var(--obsidian-surface);
        border: 1px solid var(--hairline-border);
        border-radius: 14px;
        padding: 18px 14px;
        text-align: center;
        transition: border-color 0.2s ease;
    }
    .obsidian-metric-card:hover {
        border-color: rgba(255, 76, 0, 0.3);
    }
    .metric-caption {
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--linen-subtext);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .metric-number {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--linen-head);
    }

    /* Weekly Digest Editorial Paper */
    .editorial-digest-card {
        background: linear-gradient(180deg, #0A0A0D 0%, #050404 100%);
        border: 1px solid rgba(255, 76, 0, 0.2);
        border-radius: 18px;
        padding: 32px 28px;
        margin-top: 20px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 30px rgba(255, 76, 0, 0.05);
    }

    /* Custom Streamlit Tab Overhaul */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        margin-bottom: 18px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: var(--linen-subtext);
        font-weight: 600;
        font-size: 0.9rem;
        padding: 8px 18px;
        border: 1px solid transparent;
        background: rgba(255, 255, 255, 0.02);
    }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        background: rgba(255, 76, 0, 0.14) !important;
        border-color: rgba(255, 76, 0, 0.35) !important;
    }

    /* Normalize Form Submit Buttons */
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #FF4C00 0%, #FF7A33 100%) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(255, 76, 0, 0.3) !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(135deg, #FF5B14 0%, #FF8A47 100%) !important;
        box-shadow: 0 6px 22px rgba(255, 76, 0, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Authentication Guard ---
if not firestore_service.db:
    st.error("⚠️ Firestore database client is not initialized.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None

if not st.session_state.authenticated:
    auth.show_auth_ui()
    st.stop()

# --- Authenticated User Metadata ---
user = st.session_state.user
user_id = user.get("id", "anonymous")
user_email = user.get("email", "unknown@example.com")
user_name = user.get("name", user_email.split("@")[0].capitalize())
user_picture = user.get("picture", "")

# --- Executive Sidebar Profile & Actions ---
with st.sidebar:
    avatar_elem = (
        f'<img src="{user_picture}" class="profile-avatar" />'
        if user_picture
        else f'<div class="profile-initials">{user_name[0].upper()}</div>'
    )
    
    st.markdown(f"""
        <div class="sidebar-executive-card">
            <div class="profile-row">
                {avatar_elem}
                <div>
                    <div class="profile-name">{user_name}</div>
                    <div class="profile-email">{user_email}</div>
                </div>
            </div>
            <div class="tenant-pill">TENANT: {user_id[:16]}...</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Ambient Sidebar Thought Reframer
    with st.expander("🌱 Thought Reframer", expanded=False):
        st.caption("Transform self-criticism into clarity.")
        sidebar_thought_input = st.text_area(
            "Catch a thought:", 
            placeholder="e.g., I'm overwhelmed and falling behind...", 
            height=70, 
            key="sb_thought_in"
        )
        if st.button("Reframe Thought", key="sb_reframe_btn", use_container_width=True):
            if sidebar_thought_input.strip():
                with st.spinner("Reframing..."):
                    reframed_res = gemini_service.reframe_thought(sidebar_thought_input)
                    st.markdown(f"""
                        <div class="reframe-callout">
                            <div class="reframe-header">🌱 Constructive Reframe</div>
                            {reframed_res}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Enter a thought to reframe.")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        if st.button("✍️ New Entry", use_container_width=True):
            st.session_state.chat_session = None
            st.session_state.chat_history = []
            st.rerun()
    with col_sb2:
        if st.button("🚪 Sign Out", use_container_width=True):
            auth.logout_user()

# Fetch strictly isolated tenant journal entries
entries = firestore_service.get_journal_entries(user_id)
total_entries = len(entries)
curr_streak, max_streak = analytics.calculate_journal_streaks(entries)

# Determine recent mood for active state chip
recent_mood = entries[0].get("mood_category", "Reflective") if entries else "Reflective"

# --- Minimalist Flame Top Bar ---
st.markdown(f"""
    <div class="flame-top-bar">
        <div class="brand-group">
            <div class="brand-orb">🔮</div>
            <div class="brand-name">ReflectPulse</div>
            <span class="brand-flame-tag">Studio</span>
        </div>
        <div class="top-meta-group">
            <div class="flame-state-pill">
                <span>🔥 State:</span> {recent_mood}
            </div>
            <div class="streak-chip">
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
    col_chronicle, col_workspace = st.columns([1, 1.55], gap="large")
    
    # --- Left Pane: Chronicle Feed ---
    with col_chronicle:
        st.markdown(f"""
            <div class="chronicle-header-bar">
                <div class="chronicle-title">Chronicle</div>
                <div class="chronicle-badge">{total_entries} reflections</div>
            </div>
        """, unsafe_allow_html=True)
        
        if not entries:
            st.markdown("""
                <div class="chronicle-entry-card" style="text-align: center; padding: 36px 16px;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">📖</div>
                    <div style="font-weight: 600; margin-bottom: 4px; color: #F5F5F7;">Your chronicle is waiting</div>
                    <div style="font-size: 0.85rem; color: #A1A1AA;">Begin with a thought, voice note, or photo on the right.</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="max-height: 690px; overflow-y: auto; padding-right: 6px;">', unsafe_allow_html=True)
            for entry in entries:
                date_val = entry.get("created_at")
                date_str = date_val.strftime("%b %d, %H:%M") if hasattr(date_val, "strftime") else str(date_val)[:16]
                
                title = entry.get("title", "Reflection")
                summary = entry.get("summary", "")
                mood = entry.get("mood_category", "Neutral")
                score = entry.get("mood_score", 5)
                tags = entry.get("theme_tags", [])
                loc = entry.get("location_tag", "")
                has_aud = entry.get("has_audio", False)
                has_img = entry.get("has_image", False)
                reframe = entry.get("cognitive_reframe")
                
                # Structured mood badges matching obsidian palette
                mood_palette = {
                    "Joy": ("rgba(16, 185, 129, 0.15)", "#34D399"),
                    "Calm": ("rgba(255, 122, 51, 0.15)", "#FF9E66"),
                    "Gratitude": ("rgba(236, 72, 153, 0.15)", "#F472B6"),
                    "Hope": ("rgba(20, 184, 166, 0.15)", "#2DD4BF"),
                    "Sadness": ("rgba(59, 130, 246, 0.15)", "#60A5FA"),
                    "Anxiety": ("rgba(245, 158, 11, 0.15)", "#FBBF24"),
                    "Anger": ("rgba(239, 68, 68, 0.15)", "#F87171"),
                    "Frustration": ("rgba(220, 38, 38, 0.15)", "#F87171")
                }
                bg_col, text_col = mood_palette.get(mood, ("rgba(255,255,255,0.06)", "#F5F5F7"))
                
                loc_chip = f'<span class="badge-chip badge-loc">📍 {loc}</span>' if loc else ''
                aud_chip = '<span class="badge-chip badge-media">🎙️ Voice</span>' if has_aud else ''
                img_chip = '<span class="badge-chip badge-media">📷 Photo</span>' if has_img else ''
                
                reframe_block = f"""
                    <div class="reframe-callout">
                        <div class="reframe-header">🌱 Constructive Reframe</div>
                        {reframe}
                    </div>
                """ if reframe else ""
                
                st.markdown(f"""
                    <div class="chronicle-entry-card">
                        <div class="entry-meta-line">
                            <span class="entry-date-chip">{date_str}</span>
                            <span class="badge-chip" style="background:{bg_col}; color:{text_col};">{mood} {score}/10</span>
                        </div>
                        <div class="entry-headline">{title}</div>
                        <div class="entry-excerpt">{summary}</div>
                        <div class="entry-chips-row">
                            {loc_chip}
                            {aud_chip}
                            {img_chip}
                            {" ".join(f'<span class="badge-chip badge-tag">{t}</span>' for t in tags[:3])}
                        </div>
                        {reframe_block}
                    </div>
                """, unsafe_allow_html=True)
                
                col_sp, col_d = st.columns([5, 1])
                with col_d:
                    if st.button("🗑️", key=f"del_{entry['id']}", help="Delete reflection"):
                        if firestore_service.delete_journal_entry(user_id, entry["id"]):
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # --- Right Pane: Reflection Studio Workspace ---
    with col_workspace:
        st.markdown("""
            <div class="studio-header">Reflection Studio</div>
        """, unsafe_allow_html=True)
        
        # Inline Multimodal Capture Tray
        with st.expander("🎙️ Voice & 📷 Photo Moment Capture", expanded=False):
            col_m1, col_m2 = st.columns(2, gap="medium")
            
            with col_m1:
                st.markdown("##### 🎙️ Spoken Reflection")
                mic_audio = None
                if hasattr(st, "audio_input"):
                    mic_audio = st.audio_input("Record Voice Note", key="studio_mic")
                file_audio = st.file_uploader("Or upload audio note", type=["wav", "mp3", "m4a"], key="studio_file_audio")
                active_audio_capture = mic_audio or file_audio
                if active_audio_capture:
                    st.audio(active_audio_capture)
                    st.markdown("<span class='badge-chip badge-media'>🎙️ Audio Attached</span>", unsafe_allow_html=True)
                    
            with col_m2:
                st.markdown("##### 📷 Photo Moment")
                photo_upload = st.file_uploader("Upload moment photo", type=["jpg", "jpeg", "png"], key="studio_photo")
                if photo_upload:
                    st.image(photo_upload, width=180)
                    st.markdown("<span class='badge-chip badge-media'>📷 Image Attached</span>", unsafe_allow_html=True)

        # Conversational Companion Engine
        if "chat_session" not in st.session_state or st.session_state.chat_session is None:
            st.session_state.chat_session = gemini_service.create_chat_session()
            st.session_state.chat_history = []
            welcome_text = "What is on your mind today? Write, speak, or upload a photo to reflect with Gemini."
            st.session_state.chat_history.append({"role": "model", "content": welcome_text})
        
        # Chat Stream Area
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                role = "assistant" if msg["role"] == "model" else "user"
                with st.chat_message(role):
                    st.write(msg["content"])
        
        # Chat Prompt Input
        if user_prompt := st.chat_input("Write down your reflection, feelings, or questions..."):
            with st.chat_message("user"):
                st.write(user_prompt)
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                if gemini_service.client and st.session_state.chat_session:
                    try:
                        reply = st.session_state.chat_session.send_message(user_prompt).text
                    except Exception as e:
                        reply = f"Could not connect to assistant: {e}"
                else:
                    reply = "I hear you. When things feel demanding, what is one grounded perspective you can lean on today?"
                placeholder.write(reply)
            st.session_state.chat_history.append({"role": "model", "content": reply})

        # Integrated Save Reflection Footer Bar
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        with st.form("save_reflection_form", clear_on_submit=False):
            # Smart default title suggestion based on time
            hour = datetime.now().hour
            time_of_day = "Morning" if hour < 12 else ("Afternoon" if hour < 17 else "Evening")
            suggested_title = f"{time_of_day} Reflection • {datetime.now().strftime('%b %d')}"
            
            col_f1, col_f2 = st.columns([1.4, 1])
            with col_f1:
                entry_title = st.text_input("Reflection Title", value=suggested_title)
            with col_f2:
                location_choice = st.selectbox(
                    "Context Setting",
                    ["Auto-detect via AI", "Campus", "Workplace", "Home", "Travel", "Nature", "Social", "Custom"],
                    index=0
                )
                
            custom_loc_val = ""
            if location_choice == "Custom":
                custom_loc_val = st.text_input("Specify Setting", placeholder="e.g., Studio, Library, Cafe")
                
            save_action = st.form_submit_button("🔮 Synthesize & Save Reflection", use_container_width=True)
            
            if save_action:
                has_aud = bool(active_audio_capture)
                has_img = bool(photo_upload)
                has_txt = len(st.session_state.chat_history) >= 2
                
                if not (has_txt or has_aud or has_img):
                    st.warning("Please share a thought, voice note, or photo before saving.")
                else:
                    with st.spinner("Analyzing themes, audio, and synthesizing perspective..."):
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
                            "summary": analysis.summary,
                            "mood_category": analysis.mood_category,
                            "mood_score": analysis.mood_score,
                            "theme_tags": analysis.theme_tags,
                            "reflection_prompt": analysis.reflection_prompt,
                            "location_tag": analysis.location_tag,
                            "cognitive_reframe": analysis.cognitive_reframe,
                            "has_audio": bool(aud_bytes),
                            "has_image": bool(img_bytes),
                            "created_at": datetime.now(timezone.utc)
                        }
                        
                        firestore_service.create_journal_entry(user_id, doc)
                        
                        st.session_state.chat_session = None
                        st.session_state.chat_history = []
                        st.toast("Reflection stored securely.", icon="🔥")
                        st.rerun()

# --- TAB 2: ANALYTICS & SYNTHESIS ---
with tab_analytics:
    if not entries:
        st.info("Record reflections to unlock trajectory trends and weekly digest synthesis.")
    else:
        avg_mood = sum(e.get("mood_score", 5) for e in entries) / total_entries
        
        # Executive Metric Row
        st.markdown(f"""
            <div class="obsidian-metric-row">
                <div class="obsidian-metric-card">
                    <div class="metric-caption">Current Streak</div>
                    <div class="metric-number">{curr_streak} <span style="font-size:1rem;color:#A1A1AA;font-family:'Inter';">days</span></div>
                </div>
                <div class="obsidian-metric-card">
                    <div class="metric-caption">Best Streak</div>
                    <div class="metric-number">{max_streak} <span style="font-size:1rem;color:#A1A1AA;font-family:'Inter';">days</span></div>
                </div>
                <div class="obsidian-metric-card">
                    <div class="metric-caption">Total Chronicle</div>
                    <div class="metric-number">{total_entries}</div>
                </div>
                <div class="obsidian-metric-card">
                    <div class="metric-caption">Average Mood</div>
                    <div class="metric-number">{avg_mood:.1f} <span style="font-size:1rem;color:#A1A1AA;font-family:'Inter';">/ 10</span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Charts Row
        col_c1, col_c2 = st.columns(2, gap="large")
        with col_c1:
            st.plotly_chart(analytics.generate_mood_trend_chart(entries), use_container_width=True)
        with col_c2:
            st.plotly_chart(analytics.generate_theme_distribution_chart(entries), use_container_width=True)
            
        # Editorial Weekly Digest Section
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("### 🌌 Weekly Reflective Synthesis")
        st.markdown("<div style='color:#A1A1AA;font-size:0.9rem;margin-bottom:16px;'>Synthesize recurring themes, mood patterns, and constructive takeaways from the past 7 days into an executive report.</div>", unsafe_allow_html=True)
        
        if st.button("🔥 Generate Weekly Digest", use_container_width=True):
            with st.spinner("Synthesizing reflective trends..."):
                digest_content = gemini_service.generate_weekly_digest(entries[:10])
                st.markdown(f"""
                    <div class="editorial-digest-card">
                        {digest_content}
                    </div>
                """, unsafe_allow_html=True)
