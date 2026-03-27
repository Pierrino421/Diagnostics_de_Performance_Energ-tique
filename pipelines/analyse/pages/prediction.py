"""
prediction.py
-------------
Page Prédiction ML — Interface utilisateur pour estimer la consommation
énergétique d'un logement à partir de ses caractéristiques.
"""

import streamlit as st
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.model_loader import (
    charger_modele, predire_consommation, classe_dpe_from_conso,
    couleur_classe_dpe, MODALITES, SEUILS_DPE
)
from utils.data_loader import PRIX_KWH

PREDICTION_CSS = """
<style>
.prediction-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.5rem;
    color: white;
}
.prediction-header h2 {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
}
.prediction-header p {
    margin: 0.3rem 0 0 0;
    opacity: 0.85;
    font-size: 0.95rem;
}
.result-card {
    background: linear-gradient(135deg, rgba(46,204,113,0.08), rgba(46,204,113,0.02));
    border: 1px solid rgba(46,204,113,0.2);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin-top: 1rem;
}
.result-value {
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0.5rem 0;
}
.result-label {
    font-size: 0.9rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.dpe-badge {
    display: inline-block;
    padding: 0.8rem 2.5rem;
    border-radius: 12px;
    font-size: 2rem;
    font-weight: 800;
    color: white;
    margin: 0.5rem 0;
    letter-spacing: 2px;
}
.form-section {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.form-section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #2ecc71;
    margin-bottom: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ══════════════════════════════════════════════════════════════

def render():
    """Affiche la page de prédiction ML."""

    st.markdown(PREDICTION_CSS, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────
    st.markdown("""
    <div class="prediction-header">
        <h2>🤖 Prédiction de Consommation Énergétique</h2>
        <p>Saisissez les caractéristiques de votre logement pour obtenir une estimation de sa performance DPE</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Chargement du modèle ───────────────────────────────────
    model, scaler, feature_names, is_simulated = charger_modele()

    if is_simulated:
        st.info(
            "📎 **Mode démonstration** — Le modèle utilisé est simulé. "
            "Lancez `modele.py` pour entraîner le vrai modèle sur vos données."
        )

    # ── Formulaire ─────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">🏠 Caractéristiques du logement</div></div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        surface = st.number_input(
            "Surface habitable (m²)",
            min_value=10, max_value=500, value=75, step=5,
            help="Surface habitable du logement en m²",
            key="pred_surface"
        )
        type_batiment = st.selectbox(
            "Type de bâtiment",
            options=MODALITES["type_batiment"],
            key="pred_type"
        )
        zone_climatique = st.selectbox(
            "Zone climatique",
            options=MODALITES["zone_climatique"],
            key="pred_zone"
        )
        periode_construction = st.selectbox(
            "Période de construction",
            options=MODALITES["periode_construction"],
            key="pred_periode"
        )

    with col2:
        energie_chauffage = st.selectbox(
            "Énergie principale chauffage",
            options=MODALITES["type_energie_principale_chauffage"],
            key="pred_chauff"
        )
        energie_ecs = st.selectbox(
            "Énergie principale ECS (eau chaude)",
            options=MODALITES["type_energie_principale_ecs"],
            key="pred_ecs"
        )
        type_ventilation = st.selectbox(
            "Type de ventilation",
            options=MODALITES["type_ventilation"],
            key="pred_ventil"
        )

    st.markdown('<div class="form-section"><div class="form-section-title">📐 Dimensions</div></div>',
                unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        nb_niveaux = st.number_input(
            "Nombre de niveaux",
            min_value=1, max_value=10, value=2, step=1,
            key="pred_niveaux"
        )

    with col4:
        hauteur_plafond = st.number_input(
            "Hauteur sous plafond (m)",
            min_value=2.0, max_value=5.0, value=2.50, step=0.10,
            format="%.2f", key="pred_hauteur"
        )

    st.markdown("")

    # ── Bouton prédiction ──────────────────────────────────────
    predict_clicked = st.button(
        "🔮  Prédire la consommation",
        use_container_width=True,
        type="primary",
        key="btn_predict"
    )

    if predict_clicked:
        # Construire les inputs
        inputs = {
            "periode_construction": periode_construction,
            "type_batiment": type_batiment,
            "zone_climatique": zone_climatique,
            "type_energie_principale_chauffage": energie_chauffage,
            "type_ventilation": type_ventilation,
            "type_energie_principale_ecs": energie_ecs,
            "nombre_niveau_logement": nb_niveaux,
            "hauteur_sous_plafond": hauteur_plafond,
        }

        # Prédiction
        conso_m2 = predire_consommation(inputs, model, scaler, feature_names)
        conso_totale = conso_m2 * surface
        cout_annuel = conso_totale * PRIX_KWH
        classe = classe_dpe_from_conso(conso_m2)
        couleur = couleur_classe_dpe(classe)

        st.markdown("---")
        st.subheader("📋 Résultats de la prédiction")

        # ── Résultats principaux ───────────────────────────────
        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">Consommation</div>
                <div class="result-value" style="color: {couleur};">{conso_m2:.0f}</div>
                <div class="result-label">kWh/m²/an</div>
            </div>
            """, unsafe_allow_html=True)

        with r2:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">Conso. totale</div>
                <div class="result-value" style="color: #3498db;">{conso_totale:,.0f}</div>
                <div class="result-label">kWh/an</div>
            </div>
            """, unsafe_allow_html=True)

        with r3:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">Coût estimé</div>
                <div class="result-value" style="color: #f39c12;">{cout_annuel:,.0f} €</div>
                <div class="result-label">par an</div>
            </div>
            """, unsafe_allow_html=True)

        with r4:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-label">Classe DPE</div>
                <div class="dpe-badge" style="background-color: {couleur};">{classe}</div>
                <div class="result-label">prédite</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Jauge DPE visuelle ─────────────────────────────────
        _afficher_jauge_dpe(conso_m2, classe, couleur)

        # ── Comparaison avec les moyennes ──────────────────────
        _afficher_comparaison_classes(conso_m2)

        st.caption(
            "⚠️ Ces estimations sont basées sur un modèle statistique (Ridge Regression). "
            "La consommation réelle dépend de nombreux facteurs supplémentaires."
        )


# ══════════════════════════════════════════════════════════════
#  VISUALISATIONS
# ══════════════════════════════════════════════════════════════

def _afficher_jauge_dpe(conso_m2, classe, couleur):
    """Affiche une jauge visuelle de la position sur l'échelle DPE."""
    st.subheader("📏 Position sur l'échelle DPE")

    # Construire les segments DPE comme barres horizontales
    classes_info = [
        ("A", 0, 70, "#009900"),
        ("B", 70, 110, "#33CC00"),
        ("C", 110, 180, "#99CC00"),
        ("D", 180, 250, "#FFCC00"),
        ("E", 250, 330, "#FF9900"),
        ("F", 330, 420, "#FF3300"),
        ("G", 420, 500, "#CC0000"),
    ]

    fig = go.Figure()

    for nom, debut, fin, col in classes_info:
        opacity = 1.0 if nom == classe else 0.4
        fig.add_trace(go.Bar(
            x=[fin - debut],
            y=["DPE"],
            orientation="h",
            base=debut,
            marker=dict(color=col, opacity=opacity),
            name=nom,
            text=[nom],
            textposition="inside",
            textfont=dict(size=14, color="white", family="Arial Black"),
            hovertemplate=f"Classe {nom}: {debut}-{fin} kWh/m²/an<extra></extra>",
            showlegend=False
        ))

    # Marqueur de la position prédite
    conso_affichage = min(conso_m2, 500)
    fig.add_trace(go.Scatter(
        x=[conso_affichage],
        y=["DPE"],
        mode="markers+text",
        marker=dict(symbol="diamond", size=18, color="white",
                    line=dict(width=2, color="#333")),
        text=[f"{conso_m2:.0f}"],
        textposition="top center",
        textfont=dict(size=14, color="white", family="Arial Black"),
        showlegend=False,
        hovertemplate=f"Votre logement: {conso_m2:.0f} kWh/m²/an<extra></extra>"
    ))

    fig.update_layout(
        barmode="stack",
        height=140,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="kWh/m²/an", range=[0, 520],
            titlefont=dict(color="#888"), tickfont=dict(color="#888"),
            gridcolor="rgba(255,255,255,0.05)"
        ),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=20, t=20, b=40),
        font=dict(color="#e0e0e0"),
    )

    st.plotly_chart(fig, use_container_width=True)


def _afficher_comparaison_classes(conso_m2):
    """Compare la prédiction avec les moyennes de chaque classe."""
    st.subheader("📊 Comparaison avec les moyennes par classe")

    moyennes = {
        "B": 75, "C": 130, "D": 210, "E": 290, "F": 380
    }

    classes = list(moyennes.keys())
    valeurs = list(moyennes.values())
    couleurs = [couleur_classe_dpe(c) for c in classes]

    fig = go.Figure()

    # Barres des moyennes
    fig.add_trace(go.Bar(
        x=classes,
        y=valeurs,
        marker_color=couleurs,
        name="Moyenne classe",
        text=[f"{v} kWh/m²" for v in valeurs],
        textposition="outside",
        opacity=0.6
    ))

    # Ligne horizontale de la prédiction
    fig.add_hline(
        y=conso_m2,
        line_dash="dash",
        line_color="#2ecc71",
        line_width=2.5,
        annotation_text=f"  Votre logement : {conso_m2:.0f} kWh/m²/an",
        annotation_position="top right",
        annotation_font=dict(color="#2ecc71", size=13)
    )

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=350,
        xaxis_title="Classe DPE",
        yaxis_title="kWh/m²/an",
        font=dict(color="#e0e0e0"),
    )

    st.plotly_chart(fig, use_container_width=True)
