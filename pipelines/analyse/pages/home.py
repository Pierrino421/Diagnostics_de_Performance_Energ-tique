"""
home.py — Apple-style home page — real photos, no icons, no pipeline section
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
    border-radius: 22px;
    overflow: hidden;
    margin-bottom: 2rem;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
}
.hero-banner img {
    width: 100%;
    height: 460px;
    object-fit: cover;
    display: block;
}
.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        rgba(0,0,0,0) 30%,
        rgba(0,0,0,0.72) 100%
    );
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 3rem 3.5rem;
}
.hero-tag {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.7);
    margin-bottom: 12px;
}
.hero-overlay h1 {
    font-size: 3rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -1.2px;
    line-height: 1.05;
    margin: 0 0 14px 0;
    max-width: 640px;
}
.hero-overlay p {
    font-size: 16px;
    color: rgba(255,255,255,0.82);
    max-width: 500px;
    line-height: 1.55;
    margin: 0;
    font-weight: 400;
}

/* ── Stat cards ───────────────────────────────────────────── */
.stat-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 28px 22px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.03);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), box-shadow 0.3s ease;
}
.stat-card:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.07);
    transform: translateY(-3px);
}
.stat-value {
    font-size: 2.1rem;
    font-weight: 800;
    color: #1d1d1f;
    letter-spacing: -0.8px;
    line-height: 1;
}
.stat-value.blue  { color: #0071e3; }
.stat-value.green { color: #1d8348; }
.stat-value.orange{ color: #c0392b; }
.stat-value.red   { color: #c0392b; }
.stat-sep {
    width: 28px;
    height: 2px;
    background: #e5e5ea;
    margin: 12px auto 10px;
    border-radius: 2px;
}
.stat-label {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}

/* ── Photo cards ──────────────────────────────────────────── */
.photo-card {
    background: #ffffff;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 3px 10px rgba(0,0,0,0.03);
    transition: transform 0.32s cubic-bezier(0.4,0,0.2,1), box-shadow 0.32s ease;
    height: 100%;
}
.photo-card:hover {
    box-shadow: 0 12px 40px rgba(0,0,0,0.09);
    transform: translateY(-5px);
}
.photo-card img {
    width: 100%;
    height: 240px;
    object-fit: cover;
    display: block;
}
.photo-card-body {
    padding: 26px 28px 28px;
}
.photo-card-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #0071e3;
    margin-bottom: 8px;
}
.photo-card-title {
    font-size: 18px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 10px;
    letter-spacing: -0.3px;
    line-height: 1.25;
}
.photo-card-text {
    font-size: 14px;
    color: #86868b;
    line-height: 1.6;
}



/* ── Wide photo card (solar) ──────────────────────────────── */
.wide-photo-card {
    background: #ffffff;
    border-radius: 22px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: transform 0.35s ease, box-shadow 0.35s ease;
    display: flex;
    gap: 0;
}
.wide-photo-card:hover {
    box-shadow: 0 14px 48px rgba(0,0,0,0.08);
    transform: translateY(-4px);
}
.wide-photo-card img {
    width: 52%;
    height: 320px;
    object-fit: cover;
    display: block;
    flex-shrink: 0;
}
.wide-photo-body {
    padding: 40px 36px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.wide-photo-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #0071e3;
    margin-bottom: 12px;
}
.wide-photo-title {
    font-size: 22px;
    font-weight: 800;
    color: #1d1d1f;
    margin-bottom: 14px;
    letter-spacing: -0.5px;
    line-height: 1.15;
}
.wide-photo-text {
    font-size: 14px;
    color: #86868b;
    line-height: 1.65;
}
</style>
"""


def render():
    st.markdown(HOME_CSS, unsafe_allow_html=True)

    hero_b64 = _img_b64("hero.png")
    dpe_b64  = _img_b64("dpe.png")
    reno_b64 = _img_b64("renovation.png")
    solar_b64 = _img_b64("solar.png")

    # ── Hero Banner ───────────────────────────────────────────
    if hero_b64:
        st.markdown(f"""
        <div class="hero-banner">
            <img src="data:image/png;base64,{hero_b64}" alt="Maison performante">
            <div class="hero-overlay">
                <div class="hero-tag">Diagnostic de Performance Energetique</div>
                <h1>La performance<br>energetique<br>de votre logement</h1>
                <p>Analysez, comparez et estimez les economies potentielles
                de millions de logements en France.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Stats ─────────────────────────────────────────────────
    cols = st.columns(4)
    stats = [
        ("14M+",    "Logements analyses",     "blue"),
        ("45%",     "Passoires thermiques",    "red"),
        ("1 630 €", "Economie annuelle moy.",  "green"),
        ("0.78",    "Score R² du modele ML",   "orange"),
    ]
    for col, (val, lbl, clr) in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value {clr}">{val}</div>
                <div class="stat-sep"></div>
                <div class="stat-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two photo cards ───────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        dpe_img = f'<img src="data:image/png;base64,{dpe_b64}" alt="Inspection thermique">' if dpe_b64 else ""
        st.markdown(f"""
        <div class="photo-card">
            {dpe_img}
            <div class="photo-card-body">
                <div class="photo-card-eyebrow">Comprendre le DPE</div>
                <div class="photo-card-title">Qu'est-ce que le Diagnostic de Performance Energetique ?</div>
                <div class="photo-card-text">
                    Le DPE classe chaque logement de A (tres performant) a G (passoire thermique).
                    Il mesure la consommation en kWh/m²/an et les emissions de CO2.
                    Obligatoire pour toute vente ou location depuis 2006.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        reno_img = f'<img src="data:image/png;base64,{reno_b64}" alt="Renovation energetique">' if reno_b64 else ""
        st.markdown(f"""
        <div class="photo-card">
            {reno_img}
            <div class="photo-card-body">
                <div class="photo-card-eyebrow">Agir pour l'environment</div>
                <div class="photo-card-title">Pourquoi renover son logement maintenant ?</div>
                <div class="photo-card-text">
                    Un logement classe F consomme 5 fois plus qu'un logement B.
                    L'isolation, le chauffage et la ventilation peuvent reduire votre
                    facture de 1 000 a 3 000 euros par an.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Wide photo card (solar) ───────────────────────────────
    if solar_b64:
        st.markdown(f"""
        <div class="wide-photo-card">
            <img src="data:image/png;base64,{solar_b64}" alt="Panneaux solaires">
            <div class="wide-photo-body">
                <div class="wide-photo-eyebrow">Energies renouvelables</div>
                <div class="wide-photo-title">Vers un parc immobilier<br>100% durable</div>
                <div class="wide-photo-text">
                    Les panneaux solaires, pompes a chaleur et systemes de ventilation
                    performants sont au coeur de la transition energetique du batiment.
                    La France vise la neutralite carbone d'ici 2050, ce qui implique
                    la renovation de plus de 5 millions de logements energivores.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
