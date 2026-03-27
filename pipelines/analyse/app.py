"""
app.py — DPE Analytics — Apple-style, zero icons
"""

import streamlit as st

st.set_page_config(
    page_title="DPE Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from pages import home, dashboard, prediction

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
    -webkit-font-smoothing: antialiased;
}

.stApp { background: #f5f5f7; }

#MainMenu, footer, header { visibility: hidden; }

/* Sidebar — filters only */
section[data-testid="stSidebar"] {
    background: #fbfbfd;
    border-right: 1px solid #d2d2d7;
}

/* ── Navigation tabs — Apple segmented pill ─────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #e8e8ed;
    border-radius: 10px;
    padding: 3px;
    justify-content: center;
    border: none;
    max-width: 380px;
    margin: 0 auto;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 7px 26px;
    font-size: 13px;
    font-weight: 500;
    color: #6e6e73;
    border: none;
    background: transparent;
    transition: all 0.18s ease;
    white-space: nowrap;
    letter-spacing: -0.1px;
}
.stTabs [data-baseweb="tab"]:hover { color: #1d1d1f; }
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #1d1d1f !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Metric cards ─────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: none;
    border-radius: 18px;
    padding: 22px 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 2px 6px rgba(0,0,0,0.03);
    transition: transform 0.25s cubic-bezier(0.4,0,0.2,1), box-shadow 0.25s ease;
}
div[data-testid="stMetric"]:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.07);
    transform: translateY(-2px);
}
div[data-testid="stMetric"] label {
    color: #86868b !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 600 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: #1d1d1f !important;
    font-size: 26px !important;
    letter-spacing: -0.5px;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    border-radius: 980px;
    font-weight: 500;
    padding: 9px 20px;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1);
    border: none;
    background: #e8e8ed;
    color: #1d1d1f;
    font-size: 14px;
    letter-spacing: -0.1px;
}
.stButton > button:hover {
    background: #dddde1;
    transform: scale(1.02);
}
.stButton > button[kind="primary"] {
    background: #0071e3;
    color: white;
}
.stButton > button[kind="primary"]:hover {
    background: #0077ed;
    box-shadow: 0 4px 14px rgba(0,113,227,0.28);
}

/* ── Alert ───────────────────────────────────────────────── */
div[data-testid="stAlert"] { border-radius: 14px; }

/* ── Expander ────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #fff;
    border-radius: 14px;
    font-weight: 600;
    font-size: 14px;
}

/* ── DataFrame ───────────────────────────────────────────── */
.stDataFrame {
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
</style>
"""


def main():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    tab_home, tab_dash, tab_pred = st.tabs(["Accueil", "Dashboard", "Modele ML"])

    with tab_home:
        home.render()
    with tab_dash:
        dashboard.render()
    with tab_pred:
        prediction.render()


if __name__ == "__main__":
    main()
