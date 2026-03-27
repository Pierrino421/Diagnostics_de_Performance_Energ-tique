"""
home.py — Apple-style home page with real photos, no icons
"""

import streamlit as st
import base64
import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _img_b64(filename):
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


HOME_CSS = """
<style>
/* ── Hero banner ──────────────────────────────────────────── */
.hero-banner {
    position: relative;
    border-radius: 24px;
    overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.hero-banner img {
    width: 100%;
    height: 420px;
    object-fit: cover;
    display: block;
}
.hero-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 3rem 3rem 2.5rem;
    background: linear-gradient(transparent 0%, rgba(0,0,0,0.65) 100%);
}
.hero-overlay h1 {
    font-size: 2.6rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.8px;
    line-height: 1.1;
    margin: 0 0 0.5rem 0;
}
.hero-overlay p {
    font-size: 1rem;
    color: rgba(255,255,255,0.85);
    max-width: 520px;
    line-height: 1.5;
    margin: 0;
}

/* ── Stat cards ───────────────────────────────────────────── */
.stat-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
}
.stat-card:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    transform: scale(1.02);
}
.stat-value {
    font-size: 2rem;
    font-weight: 800;
    color: #1d1d1f;
    letter-spacing: -0.5px;
}
.stat-value.accent { color: #0071e3; }
.stat-value.green { color: #34c759; }
.stat-value.orange { color: #ff9500; }
.stat-value.red { color: #ff3b30; }
.stat-label {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
    margin-top: 4px;
}

/* ── Photo cards ──────────────────────────────────────────── */
.photo-card {
    background: #ffffff;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.02);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
    height: 100%;
}
.photo-card:hover {
    box-shadow: 0 10px 40px rgba(0,0,0,0.08);
    transform: translateY(-4px);
}
.photo-card img {
    width: 100%;
    height: 220px;
    object-fit: cover;
    display: block;
}
.photo-card-body {
    padding: 24px;
}
.photo-card-title {
    font-size: 17px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 6px;
    letter-spacing: -0.2px;
}
.photo-card-text {
    font-size: 14px;
    color: #86868b;
    line-height: 1.55;
}

/* ── Feature row ──────────────────────────────────────────── */
.feature-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 28px 24px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    height: 100%;
}
.feature-card:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.06);
    transform: translateY(-3px);
}
.feature-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
    color: #0071e3;
    margin-bottom: 8px;
}
.feature-title {
    font-size: 17px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 6px;
    letter-spacing: -0.2px;
}
.feature-desc {
    font-size: 13px;
    color: #86868b;
    line-height: 1.55;
}

/* ── Pipeline section ─────────────────────────────────────── */
.pipeline-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.pipeline-title {
    font-size: 22px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 20px;
    letter-spacing: -0.3px;
}
.pipeline-step {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    margin: 2px 0;
    border-radius: 12px;
    transition: background 0.2s ease;
}
.pipeline-step:hover { background: #f5f5f7; }
.pipeline-num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f5f5f7;
    color: #86868b;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 14px;
    flex-shrink: 0;
}
.pipeline-text {
    font-size: 14px;
    color: #86868b;
}
.pipeline-text b {
    color: #1d1d1f;
    font-weight: 600;
}
</style>
"""


def render():
    st.markdown(HOME_CSS, unsafe_allow_html=True)

    hero_b64 = _img_b64("hero.png")
    dpe_b64 = _img_b64("dpe.png")
    reno_b64 = _img_b64("renovation.png")
    solar_b64 = _img_b64("solar.png")

    # ── Hero Banner ───────────────────────────────────────────
    if hero_b64:
        st.markdown(f"""
        <div class="hero-banner">
            <img src="data:image/png;base64,{hero_b64}" alt="Modern house">
            <div class="hero-overlay">
                <h1>Performance Energetique<br>des Logements</h1>
                <p>Analysez les diagnostics DPE et decouvrez combien vous pourriez economiser grace a la renovation energetique.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        ("14M+", "Logements analyses", "accent"),
        ("45%", "Passoires thermiques", "red"),
        ("1 630 euros", "Economie moy. / an", "green"),
        ("0.78", "Score R2 du modele", "orange"),
    ]
    for col, (val, lbl, clr) in zip([c1, c2, c3, c4], stats):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value {clr}">{val}</div>
                <div class="stat-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Photo cards ───────────────────────────────────────────
    col_l, col_r = st.columns(2)

    dpe_img = f'<img src="data:image/png;base64,{dpe_b64}" alt="Diagnostic DPE">' if dpe_b64 else ""
    reno_img = f'<img src="data:image/png;base64,{reno_b64}" alt="Renovation">' if reno_b64 else ""

    with col_l:
        st.markdown(f"""
        <div class="photo-card">
            {dpe_img}
            <div class="photo-card-body">
                <div class="photo-card-title">Le Diagnostic de Performance Energetique</div>
                <div class="photo-card-text">
                    Le DPE classe chaque logement de A (tres performant) a G (passoire thermique).
                    Il mesure la consommation d'energie en kWh/m2/an et les emissions de gaz a effet de serre.
                    Obligatoire pour toute vente ou location depuis 2006.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown(f"""
        <div class="photo-card">
            {reno_img}
            <div class="photo-card-body">
                <div class="photo-card-title">Pourquoi renover son logement ?</div>
                <div class="photo-card-text">
                    Un logement classe F consomme 5 fois plus qu'un logement B.
                    L'isolation, le chauffage et la ventilation peuvent reduire votre facture
                    de 1 000 a 3 000 euros par an tout en ameliorant votre confort.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feature row ───────────────────────────────────────────
    f1, f2, f3 = st.columns(3)

    features = [
        ("INGESTION", "Apache Kafka", "Collecte en temps reel depuis l'API ADEME via streaming Kafka."),
        ("TRAITEMENT", "Apache Spark", "Nettoyage et transformation distribuee des donnees brutes."),
        ("PREDICTION", "Modele Ridge", "Estimation de la consommation energetique par machine learning."),
    ]
    for col, (label, title, desc) in zip([f1, f2, f3], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-label">{label}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Solar image + Pipeline side-by-side ───────────────────
    col_img, col_pipe = st.columns([1, 1])

    with col_img:
        if solar_b64:
            st.markdown(f"""
            <div class="photo-card">
                <img src="data:image/png;base64,{solar_b64}" alt="Solar panels" style="height:320px;">
                <div class="photo-card-body">
                    <div class="photo-card-title">Les energies renouvelables</div>
                    <div class="photo-card-text">
                        Les panneaux solaires et pompes a chaleur permettent de reduire
                        considerablement l'empreinte carbone des batiments residentiels.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_pipe:
        st.markdown("""
        <div class="pipeline-card" style="height:100%;">
            <div class="pipeline-title">Architecture du Pipeline</div>
            <div class="pipeline-step"><div class="pipeline-num">1</div><div class="pipeline-text"><b>API ADEME</b> — Source officielle des donnees DPE</div></div>
            <div class="pipeline-step"><div class="pipeline-num">2</div><div class="pipeline-text"><b>Apache Kafka</b> — Ingestion streaming</div></div>
            <div class="pipeline-step"><div class="pipeline-num">3</div><div class="pipeline-text"><b>MinIO</b> — Data Lake S3 (Bronze)</div></div>
            <div class="pipeline-step"><div class="pipeline-num">4</div><div class="pipeline-text"><b>Apache Spark</b> — Nettoyage (Silver)</div></div>
            <div class="pipeline-step"><div class="pipeline-num">5</div><div class="pipeline-text"><b>Scikit-learn</b> — Modele Ridge (Gold)</div></div>
            <div class="pipeline-step"><div class="pipeline-num">6</div><div class="pipeline-text"><b>Streamlit</b> — Dashboard interactif</div></div>
        </div>
        """, unsafe_allow_html=True)
