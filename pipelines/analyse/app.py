"""
app.py — DPE Analytics — Apple-style, no icons, real photos
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

section[data-testid="stSidebar"] {
    background: #fbfbfd;
    border-right: 1px solid #d2d2d7;
}

/* ── Tabs — Apple segmented control ────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #e8e8ed;
    border-radius: 9px;
    padding: 2px;
    justify-content: center;
    border: none;
    max-width: 420px;
    margin: 0 auto;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 6px 24px;
    font-size: 13px;
    font-weight: 500;
    color: #1d1d1f;
    border: none;
    background: transparent;
    transition: all 0.2s ease;
    white-space: nowrap;
}
.stTabs [data-baseweb="tab"]:hover { color: #1d1d1f; }
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #1d1d1f !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    font-weight: 600;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Metrics — clean Apple cards ───────────────────────────── */
div[data-testid="stMetric"] {
    background: #ffffff;
    border: none;
    border-radius: 18px;
    padding: 20px 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
}
div[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.04);
    transform: scale(1.01);
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
    font-size: 28px !important;
}

/* ── Buttons ───────────────────────────────────────────────── */
.stButton > button {
    border-radius: 980px;
    font-weight: 500;
    padding: 10px 20px;
    transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    border: none;
    background: #e8e8ed;
    color: #1d1d1f;
    font-size: 14px;
    letter-spacing: -0.01em;
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
    background: #0077ED;
    box-shadow: 0 4px 12px rgba(0,113,227,0.3);
}

/* ── DataFrame ─────────────────────────────────────────────── */
.stDataFrame {
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

div[data-testid="stAlert"] { border-radius: 14px; }

.streamlit-expanderHeader {
    background: #fff;
    border-radius: 14px;
    font-weight: 600;
    font-size: 14px;
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
