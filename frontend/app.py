"""Personalized Networking Assistant -- Streamlit frontend.

Run with:  streamlit run frontend/app.py
Requires the FastAPI backend on http://localhost:8000 (configurable below).
"""
import os
import random
import uuid
from datetime import datetime, timezone

import requests
import streamlit as st

API_BASE = os.environ.get("PNA_API_BASE", "http://localhost:8000")

# ===================================================================== #
# Page config & Custom CSS
# ===================================================================== #
st.set_page_config(
    page_title="Personalized Networking Assistant😁",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Premium dark glassmorphic theme --
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ---- Global ---- */
html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%);
    color: #e0e0e0;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d1a 0%, #141428 100%) !important;
    border-right: 1px solid rgba(139, 92, 246, 0.15);
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #c4b5fd !important;
}

/* ---- Headers ---- */
h1, h2, h3 {
    color: #f0e6ff !important;
    font-weight: 700 !important;
}

/* ---- Glassmorphic cards ---- */
div[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.03) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(139, 92, 246, 0.15) !important;
    border-radius: 14px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

div[data-testid="stExpander"]:hover {
    border-color: rgba(139, 92, 246, 0.35) !important;
    box-shadow: 0 4px 30px rgba(139, 92, 246, 0.08) !important;
    transform: translateY(-1px);
}

/* ---- Container/cards with border ---- */
div[data-testid="stVerticalBlockBorderWrapper"] > div:has(> div[data-testid="stVerticalBlock"]) {
    background: rgba(255, 255, 255, 0.02) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(139, 92, 246, 0.12) !important;
    border-radius: 14px !important;
    transition: all 0.3s ease !important;
}

/* ---- Tabs ---- */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #9ca3af !important;
    padding: 12px 24px !important;
    border-radius: 10px 10px 0 0 !important;
    transition: all 0.3s ease !important;
}

button[data-baseweb="tab"]:hover {
    color: #c4b5fd !important;
    background: rgba(139, 92, 246, 0.08) !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #a78bfa !important;
    background: rgba(139, 92, 246, 0.1) !important;
}

div[data-baseweb="tab-highlight"] {
    background-color: #8b5cf6 !important;
    height: 3px !important;
    border-radius: 3px !important;
}

/* ---- Buttons ---- */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: 1px solid rgba(139, 92, 246, 0.2) !important;
    background: rgba(139, 92, 246, 0.08) !important;
    color: #c4b5fd !important;
}

.stButton > button:hover {
    background: rgba(139, 92, 246, 0.2) !important;
    border-color: rgba(139, 92, 246, 0.5) !important;
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #6d28d9, #5b21b6) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed, #6d28d9) !important;
    box-shadow: 0 6px 25px rgba(124, 58, 237, 0.4) !important;
    transform: translateY(-2px) !important;
}

/* ---- Inputs ---- */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(139, 92, 246, 0.15) !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(139, 92, 246, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
}

/* ---- Metrics ---- */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(139, 92, 246, 0.12) !important;
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stMetric"]:hover {
    border-color: rgba(139, 92, 246, 0.3) !important;
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.08) !important;
}

div[data-testid="stMetric"] label {
    color: #9ca3af !important;
    font-weight: 500 !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #c4b5fd !important;
    font-weight: 700 !important;
}

/* ---- Progress bar ---- */
div[data-testid="stProgress"] > div > div {
    background: rgba(139, 92, 246, 0.1) !important;
    border-radius: 10px !important;
}

div[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #a78bfa, #c084fc) !important;
    border-radius: 10px !important;
}

/* ---- Divider ---- */
hr {
    border-color: rgba(139, 92, 246, 0.12) !important;
}

/* ---- Slider ---- */
div[data-testid="stSlider"] > div > div > div {
    color: #a78bfa !important;
}

/* ---- Toggle ---- */
div[data-testid="stToggle"] label span {
    color: #c4b5fd !important;
}

/* ---- Animated header ---- */
.hero-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
}

.hero-header h1 {
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #c084fc, #a78bfa, #818cf8, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 4s ease infinite;
    background-size: 200% 200%;
}

@keyframes gradient-shift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.hero-subtitle {
    color: #9ca3af;
    font-size: 0.95rem;
    margin-top: -0.5rem;
    font-weight: 400;
}

/* ---- Demo mode banner ---- */
.demo-banner {
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.12), rgba(245, 158, 11, 0.06));
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-radius: 10px;
    padding: 0.6rem 1rem;
    text-align: center;
    color: #fbbf24;
    font-weight: 500;
    font-size: 0.85rem;
    margin-bottom: 1rem;
    animation: pulse-border 3s ease-in-out infinite;
}

@keyframes pulse-border {
    0%, 100% { border-color: rgba(245, 158, 11, 0.25); }
    50% { border-color: rgba(245, 158, 11, 0.5); }
}

/* ---- Starter card ---- */
.starter-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(139, 92, 246, 0.12);
    border-left: 3px solid;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.5rem 0;
    transition: all 0.3s ease;
}

.starter-card:hover {
    border-color: rgba(139, 92, 246, 0.3);
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.08);
    transform: translateX(3px);
}

/* ---- Theme badges ---- */
.theme-badge {
    display: inline-block;
    background: rgba(139, 92, 246, 0.12);
    border: 1px solid rgba(139, 92, 246, 0.25);
    color: #c4b5fd;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    margin: 0.15rem;
    transition: all 0.2s ease;
}

.theme-badge:hover {
    background: rgba(139, 92, 246, 0.2);
    border-color: rgba(139, 92, 246, 0.4);
}

/* ---- Empty state ---- */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #6b7280;
}

.empty-state .emoji {
    font-size: 3rem;
    margin-bottom: 0.5rem;
}

/* ---- Info cards ---- */
.info-card {
    background: rgba(139, 92, 246, 0.05);
    border: 1px solid rgba(139, 92, 246, 0.15);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.3rem 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(139, 92, 246, 0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(139, 92, 246, 0.5); }
</style>
""", unsafe_allow_html=True)


# ===================================================================== #
# Hero Header
# ===================================================================== #
st.markdown("""
<div class="hero-header">
    <h1>🤝 Networking Assistant</h1>
    <p class="hero-subtitle">
        Smart, tailored conversation starters powered by AI theme analysis & Wikipedia fact-checking
    </p>
</div>
""", unsafe_allow_html=True)


# ===================================================================== #
# Sidebar
# ===================================================================== #
with st.sidebar:
    st.markdown("## ⚡ Quick Start")
    st.markdown("""
    <div class="info-card">
        <strong>1.</strong> Enter an event description<br>
        <strong>2.</strong> Add your bio & interests<br>
        <strong>3.</strong> Click <em>Generate Starters</em><br>
        <strong>4.</strong> Rate with 👍/👎 to personalize
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Demo mode toggle
    demo_mode = st.toggle("🧪 **Demo Mode**", value=st.session_state.get("demo_mode", False),
                          help="Try the app without the backend running")
    st.session_state["demo_mode"] = demo_mode

    if demo_mode:
        st.caption("✨ Using realistic mock data — no backend needed!")
    else:
        st.caption(f"🔗 Backend: `{API_BASE}`")

    st.markdown("---")
    st.markdown("### 🛠️ About")
    st.markdown("""
    <div class="info-card" style="font-size: 0.82rem;">
        <strong>Theme Analysis:</strong> DistilBERT zero-shot<br>
        <strong>Generation:</strong> GPT-2 + smart templates<br>
        <strong>Fact Check:</strong> Wikipedia API<br>
        <strong>History:</strong> Local JSON with feedback
    </div>
    """, unsafe_allow_html=True)


# Demo mode banner
if demo_mode:
    st.markdown("""
    <div class="demo-banner">
        🧪 Demo Mode Active — showing sample data. Disable in the sidebar to connect to the live backend.
    </div>
    """, unsafe_allow_html=True)


# ===================================================================== #
# Demo mode mock data
# ===================================================================== #
_DEMO_THEMES = [
    {"label": "artificial intelligence", "score": 0.92},
    {"label": "sustainability", "score": 0.78},
    {"label": "urban planning", "score": 0.65},
    {"label": "climate change", "score": 0.54},
]

_DEMO_STARTERS_POOL = [
    "What's a bold prediction you have about AI-driven urban design that most people would disagree with?",
    "If you could fast-forward five years, how do you think sustainable city infrastructure will have changed?",
    "What emerging trend in climate tech do you think is being seriously underestimated right now?",
    "What's the most counterintuitive lesson you've learned working at the intersection of AI and sustainability?",
    "Can you share a time when urban planning completely changed your perspective on how cities should evolve?",
    "What's a popular opinion about AI in public policy that you actually disagree with?",
    "If you had unlimited resources, what's the first thing you'd change about how we approach climate change?",
    "What question about sustainable AI keeps you up at night?",
    "Who in the smart cities space has influenced your thinking the most, and why?",
    "What's one technology in green AI that could be a complete game-changer for urban life?",
]

_DEMO_HISTORY = [
    {
        "id": "demo_001", "timestamp": "2026-07-14T10:30:00+00:00",
        "event_description": "AI for Sustainable Cities — a summit on smart urban infrastructure and green tech",
        "interests": ["climate change", "urban planning"],
        "themes": ["artificial intelligence", "sustainability"],
        "starter_text": "What emerging trend in AI-driven city planning do you think is being underestimated right now?",
        "useful": True,
    },
    {
        "id": "demo_002", "timestamp": "2026-07-14T10:30:00+00:00",
        "event_description": "AI for Sustainable Cities — a summit on smart urban infrastructure and green tech",
        "interests": ["climate change", "urban planning"],
        "themes": ["artificial intelligence", "sustainability"],
        "starter_text": "If you had unlimited resources, what's the first thing you'd change about urban sustainability?",
        "useful": None,
    },
    {
        "id": "demo_003", "timestamp": "2026-07-13T15:00:00+00:00",
        "event_description": "FinTech Innovation Summit 2026 — the future of digital banking and decentralized finance",
        "interests": ["blockchain", "finance"],
        "themes": ["finance", "blockchain"],
        "starter_text": "What's a popular opinion about blockchain in banking that you actually disagree with?",
        "useful": False,
    },
]

_DEMO_VERIFY = {
    "query": "", "found": True, "verdict": "valid",
    "explanation": "The key elements of the claim are supported by the reference source.",
    "correct_info": "", "confidence": 0.72,
    "title": "GPT-2", "summary": "Generative Pre-trained Transformer 2 (GPT-2) is a large language model by OpenAI, released in February 2019. It was trained on 40 GB of text from the internet. GPT-2 was notable for its ability to generate coherent paragraphs of text.",
    "url": "https://en.wikipedia.org/wiki/GPT-2",
}


def _demo_generate(event, bio, interests, n):
    """Generate mock starters for demo mode."""
    selected = random.sample(_DEMO_STARTERS_POOL, min(n, len(_DEMO_STARTERS_POOL)))
    starters = [{"id": uuid.uuid4().hex[:12], "text": t, "themes": ["artificial intelligence", "sustainability"]} for t in selected]
    return {"themes": _DEMO_THEMES[:3], "starters": starters, "engine": "demo-mode", "rejected": 0}, None


def _demo_verify(query):
    """Generate mock fact-check for demo mode."""
    result = dict(_DEMO_VERIFY)
    result["query"] = query
    return result, None


def _demo_history(only_useful):
    """Return mock history for demo mode."""
    entries = list(_DEMO_HISTORY)
    if only_useful:
        entries = [e for e in entries if e.get("useful") is True]
    total = len(_DEMO_HISTORY)
    useful_count = sum(1 for e in _DEMO_HISTORY if e.get("useful") is True)
    return {"entries": entries, "total": total, "useful_count": useful_count}, None


def _demo_feedback_stats():
    """Return mock feedback stats for demo mode."""
    return {"total_feedback": 5, "useful": 3, "not_useful": 2, "useful_rate": 0.6}, None


# ===================================================================== #
# API helper
# ===================================================================== #
def api(method: str, path: str, **kwargs):
    try:
        resp = requests.request(method, f"{API_BASE}{path}", timeout=120, **kwargs)
        resp.raise_for_status()
        return resp.json(), None
    except requests.ConnectionError:
        return None, f"Cannot reach backend at {API_BASE}. Start it with: `uvicorn backend.main:app --port 8000` — or enable **Demo Mode** in the sidebar!"
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            pass
        return None, f"API error {exc.response.status_code}: {detail}"
    except requests.RequestException as exc:
        return None, str(exc)


# ===================================================================== #
# Accent colors for starter cards
# ===================================================================== #
_ACCENT_COLORS = [
    "#8b5cf6", "#6366f1", "#a78bfa", "#818cf8", "#c084fc",
    "#7c3aed", "#6d28d9", "#5b21b6", "#4f46e5", "#4338ca",
]


# ===================================================================== #
# Tabs
# ===================================================================== #
tab_generate, tab_verify, tab_history, tab_feedback = st.tabs(
    ["✨ Generate Starters", "🔎 Fact Check", "📚 History", "📊 Feedback"]
)


# --------------------------------------------------------------------- #
# Tab 1 — Generate Smart Starters
# --------------------------------------------------------------------- #
with tab_generate:
    col_input, col_output = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("### 📝 Your Details")
        bio = st.text_area(
            "Profile bio",
            placeholder="e.g., Data scientist interested in climate tech and public policy...",
            height=90,
        )
        event = st.text_area(
            "Event description",
            placeholder='e.g., "AI for Sustainable Cities" — a summit on smart urban infrastructure...',
            height=110,
        )
        interests_raw = st.text_input(
            "Your interests (comma-separated)",
            placeholder="climate change, urban planning, AI",
        )
        n = st.slider("Number of starters", 1, 5, 3)
        go = st.button("⚡ Generate Starters", type="primary", use_container_width=True)

    with col_output:
        st.markdown("### 💡 Generated Starters")
        if go:
            if not event.strip():
                st.warning("⚠️ Please enter an event description first.")
            else:
                interests = [i.strip() for i in interests_raw.split(",") if i.strip()]
                with st.spinner("🔮 Analyzing themes and generating starters..."):
                    if demo_mode:
                        data, err = _demo_generate(event, bio, interests, n)
                    else:
                        data, err = api(
                            "POST",
                            "/api/v1/generate",
                            json={
                                "event_description": event,
                                "user_bio": bio,
                                "interests": interests,
                                "num_starters": n,
                            },
                        )
                if err:
                    st.error(err)
                else:
                    st.session_state["last_result"] = data

        result = st.session_state.get("last_result")
        if result:
            # Theme badges
            theme_html = " ".join(
                f'<span class="theme-badge">{t["label"]} ({t["score"]:.0%})</span>'
                for t in result["themes"]
            )
            st.markdown(f"**Extracted Themes:** {theme_html}" if theme_html else "_No strong themes detected._", unsafe_allow_html=True)
            st.caption(f"🔧 Engine: `{result['engine']}`")
            st.divider()

            # Starter cards
            for i, starter in enumerate(result["starters"]):
                accent = _ACCENT_COLORS[i % len(_ACCENT_COLORS)]
                with st.container(border=True):
                    st.markdown(f"**{i+1}.** {starter['text']}")
                    if not demo_mode:
                        c1, c2, _ = st.columns([1, 1, 6])
                        if c1.button("👍", key=f"up_{starter['id']}"):
                            _, err = api("POST", "/api/v1/feedback", json={"starter_id": starter["id"], "useful": True})
                            st.toast("✅ Marked useful — thanks!" if not err else err)
                        if c2.button("👎", key=f"down_{starter['id']}"):
                            _, err = api("POST", "/api/v1/feedback", json={"starter_id": starter["id"], "useful": False})
                            st.toast("📝 Feedback recorded." if not err else err)
                    else:
                        st.caption("_Feedback disabled in demo mode_")
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="emoji">✨</div>
                <p>Enter your event details and click <strong>Generate Starters</strong><br>to get personalized conversation openers!</p>
            </div>
            """, unsafe_allow_html=True)


# --------------------------------------------------------------------- #
# Tab 2 — Quick Fact Verification
# --------------------------------------------------------------------- #
with tab_verify:
    st.markdown("### 🔎 Quick Fact Verification")
    st.caption("Verify claims or explore topics using Wikipedia as a reference source.")

    query = st.text_input(
        "Claim or topic to verify",
        placeholder="e.g., GPT-2 was released by OpenAI in 2019",
    )
    if st.button("🔎 Verify", type="primary"):
        if not query.strip():
            st.warning("⚠️ Enter a topic first.")
        else:
            with st.spinner("📡 Checking Wikipedia..."):
                if demo_mode:
                    data, err = _demo_verify(query)
                else:
                    data, err = api("GET", "/api/v1/verify", params={"q": query})
            if err:
                st.error(err)
            elif not data["found"]:
                st.info(data.get("explanation") or "No reliable reference found for that topic. Try rephrasing.")
            else:
                verdict = data.get("verdict", "uncertain")
                verdict_display = {
                    "valid": ("✅ Supported", "success"),
                    "invalid": ("❌ Not Supported", "error"),
                    "uncertain": ("❓ Uncertain", "warning"),
                }
                label, kind = verdict_display.get(verdict, ("❓ Uncertain", "warning"))
                confidence = data.get("confidence")
                conf_suffix = f" ({confidence:.0%} term overlap)" if confidence is not None else ""
                getattr(st, kind)(f"**{label}** — {data.get('explanation', '')}{conf_suffix}")

                if data.get("correct_info"):
                    st.markdown(f"**📖 What the source says:** {data['correct_info']}")

                with st.expander(f"📄 Reference: {data['title']}", expanded=False):
                    st.write(data["summary"])
                    if data.get("url"):
                        st.markdown(f"[🔗 Read the full article →]({data['url']})")


# --------------------------------------------------------------------- #
# Tab 3 — History with Per-Item Delete
# --------------------------------------------------------------------- #
with tab_history:
    st.markdown("### 📚 Conversation History")

    col_controls, col_delete_all = st.columns([4, 1])
    with col_delete_all:
        if not demo_mode:
            if st.session_state.get("confirm_delete_history"):
                st.warning("⚠️ Delete ALL history?")
                c1, c2 = st.columns(2)
                if c1.button("Yes", type="primary", key="confirm_delete_yes"):
                    _, del_err = api("DELETE", "/api/v1/history")
                    st.session_state["confirm_delete_history"] = False
                    if del_err:
                        st.error(del_err)
                    else:
                        st.toast("🗑️ History cleared.")
                    st.rerun()
                if c2.button("Cancel", key="confirm_delete_cancel"):
                    st.session_state["confirm_delete_history"] = False
                    st.rerun()
            else:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state["confirm_delete_history"] = True
                    st.rerun()

    only_useful = st.toggle("Show only starters marked useful 👍")

    # Fetch history
    if demo_mode:
        data, err = _demo_history(only_useful)
    else:
        data, err = api("GET", "/api/v1/history", params={"only_useful": only_useful})

    if err:
        st.error(err)
    elif not data["entries"]:
        st.markdown("""
        <div class="empty-state">
            <div class="emoji">📭</div>
            <p>No history yet — generate some starters first!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        m1, m2 = st.columns(2)
        m1.metric("📊 Total Generated", data["total"])
        m2.metric("👍 Marked Useful", data["useful_count"])
        st.divider()

        for e in data["entries"]:
            badge = "👍" if e["useful"] is True else ("👎" if e["useful"] is False else "⬜")
            preview = e["starter_text"][:80]

            with st.expander(f"{badge}  {preview}"):
                st.markdown(f"**{e['starter_text']}**")
                st.caption(
                    f"📅 **Event:** {e['event_description'][:120]}\n\n"
                    f"🏷️ **Themes:** {', '.join(e['themes']) or '—'}\n\n"
                    f"🕐 **When:** {e['timestamp']}"
                )
                # Per-item delete button
                if not demo_mode:
                    if st.button(f"🗑️ Delete this entry", key=f"del_{e['id']}"):
                        _, del_err = api("DELETE", f"/api/v1/history/{e['id']}")
                        if del_err:
                            st.error(del_err)
                        else:
                            st.toast(f"🗑️ Entry deleted.")
                        st.rerun()


# --------------------------------------------------------------------- #
# Tab 4 — Feedback Stats
# --------------------------------------------------------------------- #
with tab_feedback:
    st.markdown("### 📊 Feedback Dashboard")
    st.caption("Track how useful your generated starters have been over time.")

    if demo_mode:
        data, err = _demo_feedback_stats()
    else:
        data, err = api("GET", "/api/v1/feedback/stats")

    if err:
        st.error(err)
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("💬 Total Feedback", data["total_feedback"])
        c2.metric("👍 Useful", data["useful"])
        c3.metric("👎 Not Useful", data["not_useful"])

        st.markdown("")  # spacing
        rate = data["useful_rate"]
        st.progress(rate, text=f"✨ Usefulness Rate: **{rate:.0%}**")

        if data["total_feedback"] == 0:
            st.markdown("""
            <div class="empty-state">
                <div class="emoji">📊</div>
                <p>No feedback logged yet — rate some starters with 👍/👎 to build this view.</p>
            </div>
            """, unsafe_allow_html=True)
