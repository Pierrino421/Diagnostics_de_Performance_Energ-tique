"""
home.py
-------
Page d'accueil — Analyse et Prédiction des DPE
Design moderne avec CSS custom (thème vert/énergie)
"""

import streamlit as st


# ══════════════════════════════════════════════════════════════
#  CSS CUSTOM
# ══════════════════════════════════════════════════════════════

HOME_CSS = """
<style>
/* ── Hero Section ──────────────────────────────────────────── */
.hero-section {
    background: linear-gradient(135deg, #0d4f2b 0%, #1a7a4a 40%, #2ecc71 100%);
    border-radius: 20px;
    padding: 3rem 2.5rem;
    margin-bottom: 2rem;
    color: white;
    position: relative;
    overflow: hidden;
}
.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.hero-section::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -10%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.03);
    border-radius: 50%;
}
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 1;
}
.hero-subtitle {
    font-size: 1.15rem;
    opacity: 0.92;
    margin-bottom: 0;
    line-height: 1.6;
    position: relative;
    z-index: 1;
    max-width: 700px;
}

/* ── Cards Navigation ──────────────────────────────────────── */
.nav-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(46,204,113,0.20);
    border-radius: 16px;
    padding: 2rem 1.8rem;
    text-align: center;
    transition: all 0.35s cubic-bezier(0.4,0,0.2,1);
    cursor: pointer;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.nav-card:hover {
    transform: translateY(-6px);
    border-color: #2ecc71;
    box-shadow: 0 12px 40px rgba(46,204,113,0.15);
    background: rgba(46,204,113,0.08);
}
.nav-card-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}
.nav-card-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #e8e8e8;
    margin-bottom: 0.6rem;
}
.nav-card-desc {
    font-size: 0.92rem;
    color: #a0a0a0;
    line-height: 1.5;
}

/* ── Stats Row ─────────────────────────────────────────────── */
.stat-box {
    background: linear-gradient(135deg, rgba(46,204,113,0.08), rgba(46,204,113,0.02));
    border: 1px solid rgba(46,204,113,0.15);
    border-radius: 14px;
    padding: 1.4rem 1.2rem;
    text-align: center;
    transition: all 0.3s ease;
}
.stat-box:hover {
    border-color: rgba(46,204,113,0.4);
    box-shadow: 0 4px 20px rgba(46,204,113,0.1);
}
.stat-value {
    font-size: 2rem;
    font-weight: 800;
    color: #2ecc71;
    margin-bottom: 0.2rem;
}
.stat-label {
    font-size: 0.85rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Pipeline Section ──────────────────────────────────────── */
.pipeline-section {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 2rem;
    margin: 1.5rem 0;
}
.pipeline-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #e0e0e0;
    margin-bottom: 1.2rem;
}
.pipeline-step {
    display: flex;
    align-items: center;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    border-radius: 10px;
    background: rgba(46,204,113,0.04);
    border-left: 3px solid #2ecc71;
    transition: all 0.2s ease;
}
.pipeline-step:hover {
    background: rgba(46,204,113,0.08);
}
.pipeline-step-icon {
    font-size: 1.3rem;
    margin-right: 0.8rem;
    min-width: 30px;
    text-align: center;
}
.pipeline-step-text {
    font-size: 0.95rem;
    color: #c0c0c0;
}
.pipeline-step-text strong {
    color: #e0e0e0;
}

/* ── Footer ────────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 1.5rem;
    margin-top: 2rem;
    border-top: 1px solid rgba(255,255,255,0.06);
    color: #666;
    font-size: 0.85rem;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
#  PAGE D'ACCUEIL
# ══════════════════════════════════════════════════════════════

def render():
    """Affiche la page d'accueil."""

    st.markdown(HOME_CSS, unsafe_allow_html=True)

    # ── Hero Section ───────────────────────────────────────────
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">⚡ Analyse et Prédiction des Diagnostics Énergétiques</div>
        <div class="hero-subtitle">
            Plateforme Big Data pour l'analyse des performances énergétiques des logements français.
            Explorez les données DPE issues de l'ADEME et estimez les gains de rénovation grâce au Machine Learning.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Stats en haut ──────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-value">14M+</div>
            <div class="stat-label">Logements analysés</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-value">5</div>
            <div class="stat-label">Classes DPE</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-value">Ridge</div>
            <div class="stat-label">Modèle ML</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="stat-box">
            <div class="stat-value">0.25€</div>
            <div class="stat-label">Prix kWh référence</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cartes de navigation ───────────────────────────────────
    col_dash, col_pred = st.columns(2)

    with col_dash:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-card-icon">📊</div>
            <div class="nav-card-title">Dashboard d'Analyse</div>
            <div class="nav-card-desc">
                Explorez les données DPE : distribution des classes, consommation
                moyenne, gains par transition, simulateur personnalisé.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📊  Accéder au Dashboard", use_container_width=True, key="btn_dash"):
            st.session_state["page"] = "📊 Dashboard"
            st.rerun()

    with col_pred:
        st.markdown("""
        <div class="nav-card">
            <div class="nav-card-icon">🤖</div>
            <div class="nav-card-title">Prédiction ML</div>
            <div class="nav-card-desc">
                Saisissez les caractéristiques de votre logement et obtenez
                une estimation de consommation, coût et classe DPE.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🤖  Tester le Modèle", use_container_width=True, key="btn_pred"):
            st.session_state["page"] = "🤖 Prédiction"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Architecture Pipeline ──────────────────────────────────
    st.markdown("""
    <div class="pipeline-section">
        <div class="pipeline-title">🏗️ Architecture du Pipeline de Données</div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">🌐</div>
            <div class="pipeline-step-text"><strong>API ADEME</strong> — Source des données DPE (14M+ logements)</div>
        </div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">📡</div>
            <div class="pipeline-step-text"><strong>Apache Kafka</strong> — Ingestion en temps réel (topics open-data)</div>
        </div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">🪣</div>
            <div class="pipeline-step-text"><strong>MinIO Bronze</strong> — Stockage brut des données JSON</div>
        </div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">⚙️</div>
            <div class="pipeline-step-text"><strong>Apache Spark</strong> — Nettoyage et transformation (Silver, Parquet)</div>
        </div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">🤖</div>
            <div class="pipeline-step-text"><strong>Scikit-learn</strong> — Modèle Ridge pour la prédiction (Gold)</div>
        </div>
        <div class="pipeline-step">
            <div class="pipeline-step-icon">📊</div>
            <div class="pipeline-step-text"><strong>Streamlit</strong> — Visualisation et interface utilisateur</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Footer ─────────────────────────────────────────────────
    st.markdown("""
    <div class="footer">
        Projet Open Data University · Partenariat Enedis · Données ADEME · 2026
    </div>
    """, unsafe_allow_html=True)
