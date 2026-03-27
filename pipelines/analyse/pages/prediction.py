"""
prediction.py — Page Prédiction ML — Apple-style
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

PRED_CSS = """
<style>
.res-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 1.5rem;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    transition: all 0.25s ease;
}
.res-card:hover {
    box-shadow: 0 6px 24px rgba(0,0,0,0.07);
    transform: translateY(-2px);
}
.res-val {
    font-size: 2.2rem;
    font-weight: 800;
    margin: 0.3rem 0;
}
.res-lbl {
    font-size: 0.7rem;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}
.dpe-badge {
    display: inline-block;
    padding: 0.6rem 2rem;
    border-radius: 12px;
    font-size: 1.6rem;
    font-weight: 800;
    color: white;
    letter-spacing: 2px;
}
</style>
"""

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font=dict(color="#6e6e73", family="Inter"),
    margin=dict(l=0, r=20, t=20, b=40),
)


def render():
    st.markdown(PRED_CSS, unsafe_allow_html=True)

    st.markdown("Saisissez les caractéristiques de votre logement pour obtenir une estimation.")

    model, scaler, feature_names, is_sim = charger_modele()

    if is_sim:
        st.caption("📎 Mode démo — modèle simulé")

    # ── Form ──────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        surface = st.number_input("Surface (m²)", 10, 500, 75, 5, key="p_surf")
        type_bat = st.selectbox("Type de bâtiment", MODALITES["type_batiment"], key="p_type")
        zone = st.selectbox("Zone climatique", MODALITES["zone_climatique"], key="p_zone")
        periode = st.selectbox("Période de construction", MODALITES["periode_construction"], key="p_per")

    with c2:
        chauff = st.selectbox("Énergie chauffage", MODALITES["type_energie_principale_chauffage"], key="p_ch")
        ecs = st.selectbox("Énergie eau chaude", MODALITES["type_energie_principale_ecs"], key="p_ecs")
        ventil = st.selectbox("Ventilation", MODALITES["type_ventilation"], key="p_vent")
        nb_niv = st.number_input("Nombre de niveaux", 1, 10, 2, 1, key="p_niv")

    hauteur = st.slider("Hauteur sous plafond (m)", 2.0, 4.5, 2.50, 0.1, key="p_h")

    st.markdown("")

    if st.button("🔮  Estimer la consommation", use_container_width=True, type="primary", key="btn_pred"):
        inputs = {
            "periode_construction": periode,
            "type_batiment": type_bat,
            "zone_climatique": zone,
            "type_energie_principale_chauffage": chauff,
            "type_ventilation": ventil,
            "type_energie_principale_ecs": ecs,
            "nombre_niveau_logement": nb_niv,
            "hauteur_sous_plafond": hauteur,
        }

        conso_m2 = predire_consommation(inputs, model, scaler, feature_names)
        conso_tot = conso_m2 * surface
        cout = conso_tot * PRIX_KWH
        classe = classe_dpe_from_conso(conso_m2)
        couleur = couleur_classe_dpe(classe)

        st.markdown("---")
        st.markdown("##### Résultats")

        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-lbl">Consommation</div>
                <div class="res-val" style="color:{couleur}">{conso_m2:.0f}</div>
                <div class="res-lbl">kWh/m²/an</div>
            </div>
            """, unsafe_allow_html=True)

        with r2:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-lbl">Total annuel</div>
                <div class="res-val" style="color:#0071e3">{conso_tot:,.0f}</div>
                <div class="res-lbl">kWh/an</div>
            </div>
            """, unsafe_allow_html=True)

        with r3:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-lbl">Coût estimé</div>
                <div class="res-val" style="color:#ff9500">{cout:,.0f}€</div>
                <div class="res-lbl">par an</div>
            </div>
            """, unsafe_allow_html=True)

        with r4:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-lbl">Classe DPE</div>
                <div class="dpe-badge" style="background:{couleur}">{classe}</div>
                <div class="res-lbl" style="margin-top:0.5rem">prédite</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── DPE gauge ─────────────────────────────────────────
        st.markdown("##### Échelle DPE")
        classes_info = [
            ("A", 0, 70, "#34c759"), ("B", 70, 110, "#30d158"),
            ("C", 110, 180, "#a2c039"), ("D", 180, 250, "#ffd60a"),
            ("E", 250, 330, "#ff9f0a"), ("F", 330, 420, "#ff453a"),
            ("G", 420, 500, "#d70015"),
        ]
        fig = go.Figure()
        for nom, deb, fin, col in classes_info:
            op = 1.0 if nom == classe else 0.25
            fig.add_trace(go.Bar(
                x=[fin - deb], y=["DPE"], orientation="h", base=deb,
                marker=dict(color=col, opacity=op), name=nom,
                text=[nom], textposition="inside",
                textfont=dict(size=14, color="white", family="Arial Black"),
                showlegend=False,
            ))
        pos = min(conso_m2, 500)
        fig.add_trace(go.Scatter(
            x=[pos], y=["DPE"], mode="markers+text",
            marker=dict(symbol="diamond", size=16, color="#1d1d1f",
                        line=dict(width=2, color="white")),
            text=[f"{conso_m2:.0f}"], textposition="top center",
            textfont=dict(size=13, color="#1d1d1f"), showlegend=False,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=110,
                          xaxis=dict(range=[0, 520], tickfont=dict(color="#aaa"),
                                     gridcolor="#f0f0f0"),
                          yaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Comparison ────────────────────────────────────────
        st.markdown("##### Comparaison avec les moyennes")
        moy = {"B": 75, "C": 130, "D": 210, "E": 290, "F": 380}
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(moy.keys()), y=list(moy.values()),
            marker_color=[couleur_classe_dpe(c) for c in moy],
            text=[f"{v}" for v in moy.values()],
            textposition="outside", opacity=0.45,
        ))
        fig.add_hline(y=conso_m2, line_dash="dash", line_color="#0071e3", line_width=2.5,
                      annotation_text=f"  Vous : {conso_m2:.0f} kWh/m²",
                      annotation_position="top right",
                      annotation_font=dict(color="#0071e3", size=12))
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, height=300,
                          xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
