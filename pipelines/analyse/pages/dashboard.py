"""
dashboard.py — Dashboard DPE — Apple-style, filters in sidebar
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.data_loader import charger_gains_et_metriques, charger_details_logements, PRIX_KWH

COULEURS_DPE = {
    "A": "#34c759", "B": "#30d158", "C": "#a2c039",
    "D": "#ffd60a", "E": "#ff9f0a", "F": "#ff453a", "G": "#d70015",
}

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font=dict(color="#6e6e73", family="Inter", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    height=340,
)


def render():
    gains, metriques, gains_sim = charger_gains_et_metriques()
    details, details_sim = charger_details_logements()

    if gains_sim or details_sim:
        st.caption("📎 Mode démo — données simulées")

    # ── Sidebar filters ───────────────────────────────────────
    with st.sidebar:
        st.markdown("#### 🔍 Filtres")

        classes_dispo = sorted(details["etiquette_dpe"].unique())
        classes_sel = st.multiselect("Classe DPE", classes_dispo, default=classes_dispo, key="f_cls")

        min_s = int(details["surface_habitable_logement"].min())
        max_s = int(details["surface_habitable_logement"].max())
        surf_range = st.slider("Surface (m²)", min_s, max_s, (min_s, max_s), key="f_surf")

        types_dispo = sorted(details["type_batiment"].unique())
        types_sel = st.multiselect("Type bâtiment", types_dispo, default=types_dispo, key="f_type")

        st.markdown("---")
        st.caption(f"📊 {len(details):,} logements au total")

    df = details[
        (details["etiquette_dpe"].isin(classes_sel)) &
        (details["surface_habitable_logement"].between(*surf_range)) &
        (details["type_batiment"].isin(types_sel))
    ]

    if df.empty:
        st.warning("Aucun logement ne correspond aux filtres.")
        return

    # ── KPIs ──────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Logements", f"{len(df):,}")
    k2.metric("Conso. moy.", f"{df['conso_5_usages_par_m2_ef'].mean():.0f} kWh/m²/an")
    k3.metric("Surface moy.", f"{df['surface_habitable_logement'].mean():.0f} m²")
    k4.metric("Coût moy.", f"{df['cout_total_5_usages'].mean():,.0f} €/an")

    st.markdown("")

    # ── Row 1 ─────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### 🏷️ Distribution des classes DPE")
        dist = df["etiquette_dpe"].value_counts().sort_index().reset_index()
        dist.columns = ["Classe", "Nombre"]
        fig = px.bar(dist, x="Classe", y="Nombre", color="Classe",
                     color_discrete_map=COULEURS_DPE, text="Nombre")
        fig.update_traces(textposition="outside", texttemplate="%{text:,}")
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### 🔥 Consommation par classe")
        conso = df.groupby("etiquette_dpe")["conso_5_usages_par_m2_ef"].mean().reset_index()
        conso.columns = ["Classe", "Conso"]
        conso = conso.sort_values("Classe")
        fig = px.bar(conso, x="Conso", y="Classe", orientation="h",
                     color="Classe", color_discrete_map=COULEURS_DPE, text="Conso")
        fig.update_traces(texttemplate="%{text:.0f} kWh/m²", textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                          yaxis=dict(categoryorder="category descending"),
                          xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2 ─────────────────────────────────────────────────
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("##### 📈 Gains par transition")
        trans = gains[gains["transition"].isin(["F->E", "E->D", "D->C", "C->B"])].copy()
        if not trans.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=trans["transition"], y=trans["gain_moyen_kwh_an"],
                marker_color=["#ff453a", "#ff9f0a", "#ffd60a", "#30d158"],
                text=trans["gain_moyen_kwh_an"].apply(lambda x: f"{x:,.0f}"),
                textposition="outside", name="kWh/an"
            ))
            fig.add_trace(go.Scatter(
                x=trans["transition"], y=trans["gain_moyen_eur_an"],
                mode="lines+markers+text", yaxis="y2",
                marker=dict(size=9, color="#0071e3"),
                line=dict(color="#0071e3", width=2),
                text=trans["gain_moyen_eur_an"].apply(lambda x: f"{x:,.0f}€"),
                textposition="top center", name="€/an"
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                yaxis=dict(showgrid=False, title=""),
                yaxis2=dict(overlaying="y", side="right", showgrid=False, title=""),
                legend=dict(orientation="h", y=1.12, font=dict(color="#86868b")),
            )
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown("##### 🏠 Répartition par type")
        rep = df["type_batiment"].value_counts().reset_index()
        rep.columns = ["Type", "Nombre"]
        fig = go.Figure(go.Pie(
            labels=rep["Type"], values=rep["Nombre"], hole=0.5,
            marker=dict(colors=["#0071e3", "#34c759", "#ff9500", "#af52de"]),
            textinfo="label+percent",
            textfont=dict(size=12, color="#6e6e73"),
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT, showlegend=False,
            annotations=[dict(text=f"<b>{len(df):,}</b>", x=0.5, y=0.5,
                              font_size=15, font_color="#0071e3", showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3 ─────────────────────────────────────────────────
    c5, c6 = st.columns(2)

    with c5:
        st.markdown("##### 📅 Consommation par période")
        if "periode_construction" in df.columns:
            per = df.groupby("periode_construction")["conso_5_usages_par_m2_ef"].mean().reset_index()
            per.columns = ["Période", "Conso"]
            ordre = ["Avant 1975", "1975-1989", "1990-2005", "2006-2012 (RT2005)", "Après 2012 (RT2012)"]
            per["Période"] = pd.Categorical(per["Période"], categories=ordre, ordered=True)
            per = per.sort_values("Période").dropna(subset=["Période"])
            fig = px.bar(per, x="Période", y="Conso", text="Conso",
                         color="Conso", color_continuous_scale=["#34c759", "#ffd60a", "#ff453a"])
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    with c6:
        st.markdown("##### 📋 Tableau des gains")
        cols_ok = [c for c in ["transition", "gain_moyen_kwh_m2_an", "gain_moyen_kwh_an",
                                "gain_moyen_eur_an"] if c in gains.columns]
        df_g = gains[cols_ok].copy()
        noms = {"transition": "Transition", "gain_moyen_kwh_m2_an": "kWh/m²/an",
                "gain_moyen_kwh_an": "kWh/an", "gain_moyen_eur_an": "€/an"}
        df_g = df_g.rename(columns=noms)
        if "€/an" in df_g.columns:
            df_g["€/an"] = df_g["€/an"].apply(lambda x: f"{x:,.0f} €")
        if "kWh/an" in df_g.columns:
            df_g["kWh/an"] = df_g["kWh/an"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_g, use_container_width=True, hide_index=True, height=280)

    st.markdown("")

    # ── Simulateur ────────────────────────────────────────────
    st.markdown("##### 🧮 Simulateur personnalisé")

    s1, s2 = st.columns(2)
    with s1:
        surface = st.number_input("Surface (m²)", 10, 500, 75, 5, key="sim_s")
        prix = st.number_input("Prix kWh (€)", 0.10, 0.50, PRIX_KWH, 0.01, format="%.2f", key="sim_p")
    with s2:
        cls_list = sorted(set(gains["classe_depart"].tolist() + gains["classe_arrivee"].tolist()))
        depart = st.selectbox("Classe actuelle", cls_list,
                              index=cls_list.index("F") if "F" in cls_list else 0, key="sim_d")
        arrivee = st.selectbox("Classe cible", cls_list,
                               index=cls_list.index("C") if "C" in cls_list else 0, key="sim_a")

    label = f"{depart}->{arrivee}"
    row = gains[gains["transition"] == label]

    if depart == arrivee:
        st.warning("Les deux classes sont identiques.")
    elif row.empty:
        st.warning(f"Transition {label} non disponible.")
    else:
        g_m2 = float(row["gain_moyen_kwh_m2_an"].values[0])
        g_kwh = g_m2 * surface
        g_eur = g_kwh * prix
        conso_dep = float(row["conso_moyenne_depart_kwh_m2"].values[0]) * surface
        conso_arr = float(row["conso_moyenne_arrivee_kwh_m2"].values[0]) * surface

        r1, r2, r3 = st.columns(3)
        r1.metric(f"Conso ({depart})", f"{conso_dep:,.0f} kWh/an")
        r2.metric(f"Après ({arrivee})", f"{conso_arr:,.0f} kWh/an", delta=f"-{g_kwh:,.0f} kWh")
        r3.metric("Économie", f"{g_eur:,.0f} €/an")

    st.markdown("")

    with st.expander("🤖 Infos modèle ML"):
        if isinstance(metriques, dict):
            m1, m2, m3 = st.columns(3)
            m1.metric("MAE", f"{metriques.get('mae', 0):.1f} kWh/m²")
            m2.metric("RMSE", f"{metriques.get('rmse', 0):.1f} kWh/m²")
            m3.metric("R²", f"{metriques.get('r2_test', 0):.4f}")
