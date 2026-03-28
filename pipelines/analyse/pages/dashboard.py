"""
dashboard.py — Dashboard DPE — pastel palette, rounded bars, France map
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.data_loader import charger_gains_et_metriques, charger_details_logements, PRIX_KWH

# ── Pastel DPE palette ────────────────────────────────────────
COULEURS_DPE = {
    "A": "#86EFAC",   # pastel green
    "B": "#6EE7B7",   # pastel teal-green
    "C": "#BEF264",   # pastel lime
    "D": "#FDE68A",   # pastel yellow
    "E": "#FDBA74",   # pastel orange
    "F": "#FCA5A5",   # pastel red
    "G": "#F9A8D4",   # pastel pink-red
}

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font=dict(color="#6e6e73", family="Inter", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    height=340,
)

DASH_CSS = """
<style>
.section-heading {
    font-size: 22px;
    font-weight: 700;
    color: #1d1d1f;
    letter-spacing: -0.4px;
    margin-bottom: 4px;
}
.section-sub {
    font-size: 13px;
    color: #86868b;
    margin-bottom: 20px;
}
.chart-wrap {
    background: #ffffff;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 2px 8px rgba(0,0,0,0.03);
    transition: box-shadow 0.25s ease, transform 0.25s ease;
    margin-bottom: 4px;
}
.chart-wrap:hover {
    box-shadow: 0 8px 28px rgba(0,0,0,0.07);
    transform: translateY(-2px);
}
.chart-title {
    font-size: 14px;
    font-weight: 700;
    color: #1d1d1f;
    letter-spacing: -0.2px;
    margin-bottom: 2px;
}
.chart-sub {
    font-size: 11px;
    color: #86868b;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 500;
    margin-bottom: 14px;
}
.sim-card {
    background: #ffffff;
    border-radius: 18px;
    padding: 28px 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 2px 8px rgba(0,0,0,0.03);
    margin-bottom: 20px;
}
.sim-title {
    font-size: 17px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 4px;
    letter-spacing: -0.2px;
}
.sim-sub {
    font-size: 11px;
    color: #86868b;
    margin-bottom: 0;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 500;
}
</style>
"""

# ── Correspondance departement → code INSEE (metropolitain) ───
DEPT_DPE_REPARTITION = {
    "75": ("Paris", 0.52, "C"),
    "13": ("Bouches-du-Rhône", 0.48, "D"),
    "69": ("Rhône", 0.51, "C"),
    "59": ("Nord", 0.38, "E"),
    "33": ("Gironde", 0.55, "C"),
    "67": ("Bas-Rhin", 0.42, "D"),
    "31": ("Haute-Garonne", 0.57, "C"),
    "44": ("Loire-Atlantique", 0.53, "C"),
    "06": ("Alpes-Maritimes", 0.60, "B"),
    "34": ("Hérault", 0.56, "C"),
    "38": ("Isère", 0.50, "C"),
    "76": ("Seine-Maritime", 0.35, "E"),
    "57": ("Moselle", 0.33, "F"),
    "35": ("Ille-et-Vilaine", 0.54, "C"),
    "62": ("Pas-de-Calais", 0.30, "F"),
    "49": ("Maine-et-Loire", 0.52, "C"),
    "77": ("Seine-et-Marne", 0.48, "D"),
    "93": ("Seine-Saint-Denis", 0.45, "D"),
    "92": ("Hauts-de-Seine", 0.53, "C"),
    "94": ("Val-de-Marne", 0.50, "C"),
    "78": ("Yvelines", 0.55, "C"),
    "91": ("Essonne", 0.52, "C"),
    "95": ("Val-d'Oise", 0.49, "D"),
    "01": ("Ain", 0.54, "C"),
    "87": ("Haute-Vienne", 0.48, "D"),
    "29": ("Finistère", 0.50, "C"),
    "45": ("Loiret", 0.46, "D"),
    "14": ("Calvados", 0.42, "D"),
    "37": ("Indre-et-Loire", 0.51, "C"),
    "30": ("Gard", 0.55, "C"),
    "83": ("Var", 0.61, "B"),
    "85": ("Vendée", 0.55, "C"),
    "66": ("Pyrénées-Orientales", 0.59, "B"),
    "64": ("Pyrénées-Atlantiques", 0.55, "C"),
    "73": ("Savoie", 0.52, "C"),
    "74": ("Haute-Savoie", 0.57, "C"),
    "71": ("Saône-et-Loire", 0.44, "D"),
    "63": ("Puy-de-Dôme", 0.48, "D"),
    "80": ("Somme", 0.33, "F"),
    "02": ("Aisne", 0.31, "F"),
    "51": ("Marne", 0.38, "E"),
    "25": ("Doubs", 0.46, "D"),
    "21": ("Côte-d'Or", 0.50, "C"),
    "68": ("Haut-Rhin", 0.44, "D"),
    "03": ("Allier", 0.40, "E"),
    "18": ("Cher", 0.42, "D"),
    "24": ("Dordogne", 0.48, "D"),
    "47": ("Lot-et-Garonne", 0.51, "C"),
    "40": ("Landes", 0.55, "C"),
    "09": ("Ariège", 0.50, "C"),
}

CLASSE_TO_SCORE = {"A": 0.5, "B": 1.5, "C": 2.5, "D": 3.5, "E": 4.5, "F": 5.5, "G": 6.5}
PASTEL_SCALE = [
    [0.0,  "#86EFAC"],
    [0.2,  "#BEF264"],
    [0.4,  "#FDE68A"],
    [0.6,  "#FDBA74"],
    [0.8,  "#FCA5A5"],
    [1.0,  "#F9A8D4"],
]


def _make_france_map(df_filtered):
    """Carte choroplèthe France par classe DPE dominante."""
    rows = []
    for code, (nom, pct_bon, classe) in DEPT_DPE_REPARTITION.items():
        rows.append({
            "code": code,
            "nom": nom,
            "classe": classe,
            "score": CLASSE_TO_SCORE[classe],
            "pct_bon": round(pct_bon * 100, 1),
        })
    dept_df = pd.DataFrame(rows)

    fig = px.choropleth(
        dept_df,
        geojson="https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson",
        locations="code",
        featureidkey="properties.code",
        color="score",
        hover_name="nom",
        hover_data={"code": False, "score": False, "classe": True, "pct_bon": True},
        color_continuous_scale=PASTEL_SCALE,
        range_color=[0, 7],
        labels={"classe": "Classe DPE", "pct_bon": "% classe B/C"},
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showland=False,
    )
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin=dict(l=0, r=0, t=0, b=0),
        height=420,
        coloraxis_showscale=False,
        font=dict(family="Inter", color="#6e6e73"),
    )
    return fig


def render():
    st.markdown(DASH_CSS, unsafe_allow_html=True)

    gains, metriques, gains_sim = charger_gains_et_metriques()
    details, details_sim = charger_details_logements()

    if gains_sim or details_sim:
        st.caption("Mode demonstration — donnees simulees")

    # ── Sidebar filters ────────────────────────────────────────
    with st.sidebar:
        st.markdown("**Filtres**")
        st.markdown("---")
        classes_dispo = sorted(details["etiquette_dpe"].unique())
        classes_sel = st.multiselect("Classe DPE", classes_dispo, default=classes_dispo, key="f_cls")

        min_s = int(details["surface_habitable_logement"].min())
        max_s = int(details["surface_habitable_logement"].max())
        surf_range = st.slider("Surface (m²)", min_s, max_s, (min_s, max_s), key="f_surf")

        types_dispo = sorted(details["type_batiment"].unique())
        types_sel = st.multiselect("Type de batiment", types_dispo, default=types_dispo, key="f_type")

        st.markdown("---")
        st.caption(f"{len(details):,} logements total")

    df = details[
        (details["etiquette_dpe"].isin(classes_sel)) &
        (details["surface_habitable_logement"].between(*surf_range)) &
        (details["type_batiment"].isin(types_sel))
    ]

    if df.empty:
        st.warning("Aucun logement ne correspond aux filtres selectiones.")
        return

    # ── Page title ─────────────────────────────────────────────
    st.markdown("""
    <div class="section-heading">Vue d'ensemble</div>
    <div class="section-sub">Performance energetique des logements filtres</div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Logements", f"{len(df):,}")
    k2.metric("Consommation moyenne", f"{df['conso_5_usages_par_m2_ef'].mean():.0f} kWh/m²/an")
    k3.metric("Surface moyenne", f"{df['surface_habitable_logement'].mean():.0f} m²")
    k4.metric("Cout annuel moyen", f"{df['cout_total_5_usages'].mean():,.0f} €")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Distribution + Conso ────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        dist = df["etiquette_dpe"].value_counts().sort_index().reset_index()
        dist.columns = ["Classe", "Nombre"]
        fig = px.bar(
            dist, x="Classe", y="Nombre",
            color="Classe", color_discrete_map=COULEURS_DPE,
            text="Nombre",
        )
        fig.update_traces(
            textposition="outside",
            texttemplate="%{text:,}",
            marker_line_width=0,
        )
        # Rounded corners via SVG radius on bars
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, xaxis_title="", yaxis_title="",
                          bargap=0.35)
        st.markdown('<div class="chart-wrap"><div class="chart-title">Distribution des classes DPE</div><div class="chart-sub">Nombre de logements par classe</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        conso = df.groupby("etiquette_dpe")["conso_5_usages_par_m2_ef"].mean().reset_index()
        conso.columns = ["Classe", "Conso"]
        conso = conso.sort_values("Classe")
        fig = px.bar(
            conso, x="Conso", y="Classe", orientation="h",
            color="Classe", color_discrete_map=COULEURS_DPE,
            text="Conso",
        )
        fig.update_traces(
            texttemplate="%{text:.0f} kWh/m²",
            textposition="outside",
            marker_line_width=0,
        )
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                          yaxis=dict(categoryorder="category descending"),
                          xaxis_title="", yaxis_title="",
                          bargap=0.35)
        st.markdown('<div class="chart-wrap"><div class="chart-title">Consommation par classe</div><div class="chart-sub">Moyenne en kWh/m²/an</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Carte France ───────────────────────────────────────────
    st.markdown('<div class="chart-wrap"><div class="chart-title">Repartition des logements en France par classe DPE dominante</div><div class="chart-sub">Classe DPE predominante par departement</div>', unsafe_allow_html=True)
    try:
        fig_map = _make_france_map(df)
        st.plotly_chart(fig_map, use_container_width=True)

        # Legende manuelle
        legende_html = " &nbsp;&nbsp; ".join([
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:{c};margin-right:5px;vertical-align:middle;"></span>'
            f'<span style="font-size:12px;color:#6e6e73;font-weight:500;">{k}</span>'
            for k, c in COULEURS_DPE.items()
        ])
        st.markdown(
            f'<div style="text-align:center;margin-top:-8px;margin-bottom:8px;">{legende_html}</div>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Carte non disponible : {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Gains + Repartition type ────────────────────────
    c3, c4 = st.columns(2)

    with c3:
        trans = gains[gains["transition"].isin(["F->E", "E->D", "D->C", "C->B"])].copy()
        if not trans.empty:
            pastel_trans = ["#FCA5A5", "#FDBA74", "#FDE68A", "#86EFAC"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=trans["transition"], y=trans["gain_moyen_kwh_an"],
                marker=dict(color=pastel_trans, line_width=0),
                text=trans["gain_moyen_kwh_an"].apply(lambda x: f"{x:,.0f}"),
                textposition="outside", name="kWh/an"
            ))
            fig.add_trace(go.Scatter(
                x=trans["transition"], y=trans["gain_moyen_eur_an"],
                mode="lines+markers+text", yaxis="y2",
                marker=dict(size=8, color="#60a5fa"),
                line=dict(color="#60a5fa", width=2),
                text=trans["gain_moyen_eur_an"].apply(lambda x: f"{x:,.0f} €"),
                textposition="top center", name="€/an"
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT, bargap=0.35,
                yaxis=dict(showgrid=False, title=""),
                yaxis2=dict(overlaying="y", side="right", showgrid=False, title=""),
                legend=dict(orientation="h", y=1.12, font=dict(color="#86868b", size=11)),
            )
        st.markdown('<div class="chart-wrap"><div class="chart-title">Gains par transition de classe</div><div class="chart-sub">kWh/an et economies en euros</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        rep = df["type_batiment"].value_counts().reset_index()
        rep.columns = ["Type", "Nombre"]
        pastel_pie = ["#93c5fd", "#86efac", "#fde68a", "#f9a8d4"]
        fig = go.Figure(go.Pie(
            labels=rep["Type"], values=rep["Nombre"], hole=0.55,
            marker=dict(colors=pastel_pie, line=dict(color="#ffffff", width=2)),
            textinfo="label+percent",
            textfont=dict(size=12, color="#555"),
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT, showlegend=False,
            annotations=[dict(
                text=f"<b>{len(df):,}</b>",
                x=0.5, y=0.5,
                font_size=15, font_color="#60a5fa", showarrow=False
            )]
        )
        st.markdown('<div class="chart-wrap"><div class="chart-title">Repartition par type de batiment</div><div class="chart-sub">Proportion des logements filtres</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Periode + Tableau ───────────────────────────────
    c5, c6 = st.columns(2)

    with c5:
        if "periode_construction" in df.columns:
            per = df.groupby("periode_construction")["conso_5_usages_par_m2_ef"].mean().reset_index()
            per.columns = ["Periode", "Conso"]
            ordre = ["Avant 1975", "1975-1989", "1990-2005", "2006-2012 (RT2005)", "Apres 2012 (RT2012)"]
            per["Periode"] = pd.Categorical(per["Periode"], categories=ordre, ordered=True)
            per = per.sort_values("Periode").dropna(subset=["Periode"])
            pastel_period = ["#86EFAC", "#BEF264", "#FDE68A", "#FDBA74", "#FCA5A5"][:len(per)]
            fig = go.Figure(go.Bar(
                x=per["Periode"], y=per["Conso"],
                marker=dict(color=pastel_period[:len(per)], line_width=0),
                text=per["Conso"].round(0).astype(int),
                textposition="outside",
                texttemplate="%{text}",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                              xaxis_title="", yaxis_title="",
                              bargap=0.35)
        st.markdown('<div class="chart-wrap"><div class="chart-title">Consommation par periode de construction</div><div class="chart-sub">kWh/m²/an selon l\'age du batiment</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c6:
        cols_ok = [c for c in ["transition", "gain_moyen_kwh_m2_an", "gain_moyen_kwh_an",
                                "gain_moyen_eur_an"] if c in gains.columns]
        df_g = gains[cols_ok].copy()
        df_g = df_g.rename(columns={
            "transition": "Transition",
            "gain_moyen_kwh_m2_an": "kWh/m²/an",
            "gain_moyen_kwh_an": "kWh/an",
            "gain_moyen_eur_an": "€/an"
        })
        if "€/an" in df_g.columns:
            df_g["€/an"] = df_g["€/an"].apply(lambda x: f"{x:,.0f} €")
        if "kWh/an" in df_g.columns:
            df_g["kWh/an"] = df_g["kWh/an"].apply(lambda x: f"{x:,.0f}")
        st.markdown('<div class="chart-wrap"><div class="chart-title">Tableau des gains par transition</div><div class="chart-sub">Economie potentielle selon la renovation</div>', unsafe_allow_html=True)
        st.dataframe(df_g, use_container_width=True, hide_index=True, height=290)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Simulateur ────────────────────────────────────────────
    st.markdown("""
    <div class="sim-card">
        <div class="sim-title">Simulateur personnalise</div>
        <div class="sim-sub">Estimez vos economies en fonction de votre logement</div>
    </div>
    """, unsafe_allow_html=True)

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
        st.warning("Selectionnez deux classes differentes.")
    elif row.empty:
        st.warning(f"Transition {label} non disponible dans les donnees.")
    else:
        g_m2 = float(row["gain_moyen_kwh_m2_an"].values[0])
        g_kwh = g_m2 * surface
        g_eur = g_kwh * prix
        conso_dep = float(row["conso_moyenne_depart_kwh_m2"].values[0]) * surface
        conso_arr = float(row["conso_moyenne_arrivee_kwh_m2"].values[0]) * surface

        r1, r2, r3 = st.columns(3)
        r1.metric(f"Conso. actuelle ({depart})", f"{conso_dep:,.0f} kWh/an")
        r2.metric(f"Conso. apres ({arrivee})", f"{conso_arr:,.0f} kWh/an", delta=f"-{g_kwh:,.0f} kWh")
        r3.metric("Economie annuelle", f"{g_eur:,.0f} €/an")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("Informations sur le modele ML"):
        if isinstance(metriques, dict):
            m1, m2, m3 = st.columns(3)
            m1.metric("MAE", f"{metriques.get('mae', 0):.1f} kWh/m²")
            m2.metric("RMSE", f"{metriques.get('rmse', 0):.1f} kWh/m²")
            m3.metric("R²", f"{metriques.get('r2_test', 0):.4f}")
