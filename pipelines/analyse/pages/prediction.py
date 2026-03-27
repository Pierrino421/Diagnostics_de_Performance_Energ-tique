"""
prediction.py — Modele ML — Apple-style, no icons
"""

import streamlit as st
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.model_loader import (
    charger_modele, predire_consommation, classe_dpe_from_conso,
    couleur_classe_dpe, MODALITES
)
from utils.data_loader import PRIX_KWH

PRED_CSS = """
<style>
.pred-intro {
    font-size: 15px;
    color: #86868b;
    margin-bottom: 24px;
    line-height: 1.5;
}
.form-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 2px 8px rgba(0,0,0,0.03);
    margin-bottom: 20px;
}
.form-section-label {
    font-size: 11px;
    font-weight: 700;
    color: #0071e3;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 16px;
}
.results-section {
    margin-top: 8px;
}
.res-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 28px 22px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 2px 8px rgba(0,0,0,0.03);
    transition: transform 0.28s cubic-bezier(0.4,0,0.2,1), box-shadow 0.28s ease;
}
.res-card:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.07);
    transform: translateY(-3px);
}
.res-val {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.8px;
    margin: 8px 0 4px;
}
.res-unit {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}
.res-eyebrow {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
    margin-bottom: 4px;
}
.dpe-badge {
    display: inline-block;
    padding: 10px 32px;
    border-radius: 12px;
    font-size: 1.8rem;
    font-weight: 800;
    color: white;
    letter-spacing: 3px;
    margin: 6px 0;
}
.chart-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 2px 8px rgba(0,0,0,0.03);
}
.chart-card-title {
    font-size: 14px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 2px;
    letter-spacing: -0.2px;
}
.chart-card-sub {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 500;
    margin-bottom: 12px;
}
</style>
"""

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font=dict(color="#6e6e73", family="Inter"),
    margin=dict(l=0, r=20, t=10, b=30),
)


def render():
    st.markdown(PRED_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:24px;font-weight:800;color:#1d1d1f;letter-spacing:-0.5px;margin-bottom:4px;">
        Estimation de consommation energetique
    </div>
    <div class="pred-intro">
        Renseignez les caracteristiques de votre logement pour obtenir une estimation
        de sa consommation et de sa classe DPE.
    </div>
    """, unsafe_allow_html=True)

    model, scaler, feature_names, is_sim = charger_modele()
    if is_sim:
        st.caption("Mode demonstration — modele simule")

    # ── Form ──────────────────────────────────────────────────
    st.markdown('<div class="form-card"><div class="form-section-label">Caracteristiques du logement</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        surface  = st.number_input("Surface habitable (m²)", 10, 500, 75, 5, key="p_surf")
        type_bat = st.selectbox("Type de batiment", MODALITES["type_batiment"], key="p_type")
        zone     = st.selectbox("Zone climatique", MODALITES["zone_climatique"], key="p_zone")
        periode  = st.selectbox("Periode de construction", MODALITES["periode_construction"], key="p_per")
    with c2:
        chauff  = st.selectbox("Energie de chauffage", MODALITES["type_energie_principale_chauffage"], key="p_ch")
        ecs     = st.selectbox("Energie eau chaude", MODALITES["type_energie_principale_ecs"], key="p_ecs")
        ventil  = st.selectbox("Type de ventilation", MODALITES["type_ventilation"], key="p_vent")
        nb_niv  = st.number_input("Nombre de niveaux", 1, 10, 2, 1, key="p_niv")

    hauteur = st.slider("Hauteur sous plafond (m)", 2.0, 4.5, 2.50, 0.1, key="p_h")
    st.markdown('</div>', unsafe_allow_html=True)

    predict = st.button("Estimer la consommation", use_container_width=True, type="primary", key="btn_pred")

    if predict:
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

        conso_m2  = predire_consommation(inputs, model, scaler, feature_names)
        conso_tot = conso_m2 * surface
        cout      = conso_tot * PRIX_KWH
        classe    = classe_dpe_from_conso(conso_m2)
        couleur   = couleur_classe_dpe(classe)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:16px;font-weight:700;color:#1d1d1f;margin-bottom:16px;letter-spacing:-0.2px;">
            Resultats de l'estimation
        </div>
        """, unsafe_allow_html=True)

        # ── Result cards ──────────────────────────────────────
        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-eyebrow">Consommation</div>
                <div class="res-val" style="color:{couleur}">{conso_m2:.0f}</div>
                <div class="res-unit">kWh / m² / an</div>
            </div>
            """, unsafe_allow_html=True)

        with r2:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-eyebrow">Total annuel</div>
                <div class="res-val" style="color:#0071e3">{conso_tot:,.0f}</div>
                <div class="res-unit">kWh / an</div>
            </div>
            """, unsafe_allow_html=True)

        with r3:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-eyebrow">Cout estime</div>
                <div class="res-val" style="color:#ff9500">{cout:,.0f} €</div>
                <div class="res-unit">par an</div>
            </div>
            """, unsafe_allow_html=True)

        with r4:
            st.markdown(f"""
            <div class="res-card">
                <div class="res-eyebrow">Classe DPE</div>
                <div class="dpe-badge" style="background:{couleur}">{classe}</div>
                <div class="res-unit">predite</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── DPE gauge ─────────────────────────────────────────
        g1, g2 = st.columns(2)

        with g1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Position sur l\'echelle DPE</div><div class="chart-card-sub">kWh/m²/an</div>', unsafe_allow_html=True)
            classes_info = [
                ("A", 0,   70,  "#1a9e3f"), ("B", 70,  110, "#4cae4c"),
                ("C", 110, 180, "#8db33a"), ("D", 180, 250, "#e6c929"),
                ("E", 250, 330, "#e8872a"), ("F", 330, 420, "#d63b2f"),
                ("G", 420, 500, "#b91c1c"),
            ]
            fig = go.Figure()
            for nom, deb, fin, col in classes_info:
                op = 1.0 if nom == classe else 0.22
                fig.add_trace(go.Bar(
                    x=[fin - deb], y=["DPE"], orientation="h", base=deb,
                    marker=dict(color=col, opacity=op), name=nom,
                    text=[nom], textposition="inside",
                    textfont=dict(size=13, color="white", family="Arial Black"),
                    showlegend=False,
                ))
            pos = min(conso_m2, 500)
            fig.add_trace(go.Scatter(
                x=[pos], y=["DPE"], mode="markers+text",
                marker=dict(symbol="diamond", size=16, color="#1d1d1f",
                            line=dict(width=2, color="white")),
                text=[f"  {conso_m2:.0f}"], textposition="middle right",
                textfont=dict(size=12, color="#1d1d1f", family="Inter"), showlegend=False,
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT, barmode="stack", height=110,
                xaxis=dict(range=[0, 530], tickfont=dict(color="#aaa"), gridcolor="#f0f0f0"),
                yaxis=dict(visible=False),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with g2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Comparaison avec les moyennes</div><div class="chart-card-sub">kWh/m²/an par classe</div>', unsafe_allow_html=True)
            moy = {"B": 75, "C": 130, "D": 210, "E": 290, "F": 380}
            dpe_colors = {"B": "#4cae4c", "C": "#8db33a", "D": "#e6c929", "E": "#e8872a", "F": "#d63b2f"}
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=list(moy.keys()), y=list(moy.values()),
                marker_color=[dpe_colors[c] for c in moy],
                text=[str(v) for v in moy.values()],
                textposition="outside",
                opacity=0.4,
            ))
            fig.add_hline(
                y=conso_m2, line_dash="dot", line_color="#0071e3", line_width=2.5,
                annotation_text=f"  Votre logement : {conso_m2:.0f} kWh/m²",
                annotation_position="top right",
                annotation_font=dict(color="#0071e3", size=12, family="Inter")
            )
            fig.update_layout(
                **PLOTLY_LAYOUT, showlegend=False, height=240,
                xaxis_title="", yaxis_title=""
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
