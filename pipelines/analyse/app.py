"""
app.py
------
Point d'entrée principal — Application Streamlit Multi-pages DPE
Navigation : Accueil | Dashboard | Prédiction
"""

import streamlit as st

# ── Configuration de la page (DOIT être le premier appel Streamlit) ──
st.set_page_config(
    page_title="DPE — Analyse & Prédiction",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports des pages ──────────────────────────────────────────
from pages import home, dashboard, prediction

# ══════════════════════════════════════════════════════════════
#  CSS GLOBAL
# ══════════════════════════════════════════════════════════════

GLOBAL_CSS = """
<style>
/* ── Import Google Font ────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Base ──────────────────────────────────────────────────── */
html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Dark theme override ───────────────────────────────────── */
.stApp {
    background-color: #0e1117;
}

/* ── Sidebar ───────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #111922 100%);
    border-right: 1px solid rgba(46,204,113,0.1);
}
section[data-testid="stSidebar"] .stRadio > label {
    font-size: 0.95rem;
    font-weight: 500;
}

/* ── Navigation radio buttons ──────────────────────────────── */
div[data-testid="stSidebar"] .stRadio > div {
    gap: 0.1rem;
}
div[data-testid="stSidebar"] .stRadio > div > label {
    padding: 0.7rem 1rem;
    border-radius: 10px;
    transition: all 0.25s ease;
    cursor: pointer;
}
div[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(46,204,113,0.08);
}

/* ── Metrics ───────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1rem;
    transition: all 0.25s ease;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(46,204,113,0.3);
    box-shadow: 0 4px 12px rgba(46,204,113,0.08);
}
div[data-testid="stMetric"] label {
    color: #888 !important;
}

/* ── Buttons ───────────────────────────────────────────────── */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.3s ease;
    border: 1px solid rgba(46,204,113,0.3);
}
.stButton > button:hover {
    border-color: #2ecc71;
    box-shadow: 0 4px 15px rgba(46,204,113,0.2);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1a7a4a, #2ecc71);
    color: white;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(46,204,113,0.3);
    transform: translateY(-1px);
}

/* ── Expander ──────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
}

/* ── DataFrame ─────────────────────────────────────────────── */
.stDataFrame {
    border-radius: 10px;
    overflow: hidden;
}

/* ── Info/Warning/Success boxes ─────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 10px;
}

/* ── Sidebar logo & title ──────────────────────────────────── */
.sidebar-title {
    font-size: 1.3rem;
    font-weight: 800;
    color: #2ecc71;
    margin-bottom: 0.2rem;
    letter-spacing: -0.3px;
}
.sidebar-subtitle {
    font-size: 0.78rem;
    color: #666;
    margin-bottom: 1.5rem;
    line-height: 1.4;
}

/* ── Hide Streamlit branding ───────────────────────────────── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""


# ══════════════════════════════════════════════════════════════
#  APPLICATION PRINCIPALE
# ══════════════════════════════════════════════════════════════

def main():
    # Injecter le CSS global
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Sidebar Navigation ─────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-title">⚡ DPE Analytics</div>
        <div class="sidebar-subtitle">Analyse & Prédiction des Diagnostics de Performance Énergétique</div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Initialiser la page par défaut
        if "page" not in st.session_state:
            st.session_state["page"] = "🏠 Accueil"

        # Navigation radio
        page = st.radio(
            "Navigation",
            options=["🏠 Accueil", "📊 Dashboard", "🤖 Prédiction"],
            index=["🏠 Accueil", "📊 Dashboard", "🤖 Prédiction"].index(
                st.session_state["page"]
            ),
            label_visibility="collapsed",
            key="nav_radio"
        )

        # Sync session state
        st.session_state["page"] = page

        st.markdown("---")

        # Infos sidebar
        st.markdown("""
        **📡 Stack technique**
        - Apache Kafka (ingestion)
        - MinIO (data lake S3)
        - Apache Spark (nettoyage)
        - Scikit-learn (ML)
        - Streamlit (visualisation)
        """)

        st.markdown("---")
        st.caption("Projet Open Data University · 2026")

    # ── Routage des pages ──────────────────────────────────────
    if page == "🏠 Accueil":
        home.render()
    elif page == "📊 Dashboard":
        dashboard.render()
    elif page == "🤖 Prédiction":
        prediction.render()


# ── Point d'entrée ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
