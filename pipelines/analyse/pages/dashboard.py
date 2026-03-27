"""
dashboard.py
------------
Page Dashboard — Analyse interactive des données DPE
Graphiques Plotly + filtres sidebar + simulateur
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.data_loader import charger_gains_et_metriques, charger_details_logements, PRIX_KWH

# ── Couleurs DPE officielles ──────────────────────────────────
COULEURS_DPE = {
    "A": "#009900", "B": "#33CC00", "C": "#99CC00",
    "D": "#FFCC00", "E": "#FF9900", "F": "#FF3300", "G": "#CC0000",
}

DASHBOARD_CSS = """
<style>
.dashboard-header {
    background: linear-gradient(135deg, #0a3d1f 0%, #145a32 60%, #1e8449 100%);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.5rem;
    color: white;
}
.dashboard-header h2 {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
}
.dashboard-header p {
    margin: 0.3rem 0 0 0;
    opacity: 0.85;
    font-size: 0.95rem;
}
.section-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(46,204,113,0.3), transparent);
    margin: 1.5rem 0;
    border: none;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ══════════════════════════════════════════════════════════════

def render():
    """Affiche la page Dashboard."""

    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────
    st.markdown("""
    <div class="dashboard-header">
        <h2>📊 Dashboard d'Analyse DPE</h2>
        <p>Explorez les données de performance énergétique — Consommation, classes DPE, gains potentiels</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Chargement des données ─────────────────────────────────
    gains, metriques, gains_simule = charger_gains_et_metriques()
    details, details_simule = charger_details_logements()

    if gains_simule or details_simule:
        st.info(
            "📎 **Mode démonstration** — Les données affichées sont simulées. "
            "Lancez le pipeline complet (Bronze → Silver → Gold) pour utiliser vos données réelles."
        )

    # ── Filtres sidebar ────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Filtres")

        # Filtre classe DPE
        classes_disponibles = sorted(details["etiquette_dpe"].unique())
        classes_selectionnees = st.multiselect(
            "Classe DPE",
            options=classes_disponibles,
            default=classes_disponibles,
            key="filtre_classe"
        )

        # Filtre surface
        min_surf = int(details["surface_habitable_logement"].min())
        max_surf = int(details["surface_habitable_logement"].max())
        surface_range = st.slider(
            "Surface (m²)",
            min_value=min_surf,
            max_value=max_surf,
            value=(min_surf, max_surf),
            key="filtre_surface"
        )

        # Filtre type bâtiment
        types_disponibles = sorted(details["type_batiment"].unique())
        types_selectionnes = st.multiselect(
            "Type de bâtiment",
            options=types_disponibles,
            default=types_disponibles,
            key="filtre_type"
        )

        st.markdown("---")
        st.caption(f"📊 {len(details):,} logements au total")

    # ── Appliquer les filtres ──────────────────────────────────
    df_filtre = details[
        (details["etiquette_dpe"].isin(classes_selectionnees)) &
        (details["surface_habitable_logement"] >= surface_range[0]) &
        (details["surface_habitable_logement"] <= surface_range[1]) &
        (details["type_batiment"].isin(types_selectionnes))
    ]

    if df_filtre.empty:
        st.warning("Aucun logement ne correspond aux filtres sélectionnés.")
        return

    # ── KPIs ───────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Logements filtrés", f"{len(df_filtre):,}")
    with col2:
        conso_moy = df_filtre["conso_5_usages_par_m2_ef"].mean()
        st.metric("Conso. moyenne", f"{conso_moy:.0f} kWh/m²/an")
    with col3:
        surface_moy = df_filtre["surface_habitable_logement"].mean()
        st.metric("Surface moyenne", f"{surface_moy:.0f} m²")
    with col4:
        cout_moy = df_filtre["cout_total_5_usages"].mean()
        st.metric("Coût moyen 5 usages", f"{cout_moy:,.0f} €/an")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Ligne 1 : Distribution DPE + Conso par classe ─────────
    col_g, col_d = st.columns(2)

    with col_g:
        _afficher_distribution_dpe(df_filtre)

    with col_d:
        _afficher_conso_par_classe(df_filtre)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Ligne 2 : Gains + Répartition par type ────────────────
    col_g2, col_d2 = st.columns(2)

    with col_g2:
        transitions_simples = gains[gains["transition"].isin(
            ["F->E", "E->D", "D->C", "C->B"]
        )].copy()
        _afficher_gains_barres(transitions_simples)

    with col_d2:
        _afficher_repartition_type(df_filtre)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Ligne 3 : Conso par période + Tableau gains ──────────
    col_g3, col_d3 = st.columns(2)

    with col_g3:
        _afficher_conso_par_periode(df_filtre)

    with col_d3:
        _afficher_tableau_gains(gains)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Simulateur ─────────────────────────────────────────────
    _afficher_simulateur(gains)

    # ── Métriques modèle ───────────────────────────────────────
    _afficher_metriques_modele(metriques)


# ══════════════════════════════════════════════════════════════
#  GRAPHIQUES
# ══════════════════════════════════════════════════════════════

def _afficher_distribution_dpe(df):
    """Distribution des classes DPE (barres verticales colorées)."""
    st.subheader("🏷️ Distribution des classes DPE")

    dist = df["etiquette_dpe"].value_counts().sort_index().reset_index()
    dist.columns = ["Classe", "Nombre"]

    fig = px.bar(
        dist, x="Classe", y="Nombre",
        color="Classe",
        color_discrete_map=COULEURS_DPE,
        text="Nombre"
    )
    fig.update_traces(textposition="outside", texttemplate="%{text:,}")
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        xaxis_title="Classe DPE",
        yaxis_title="Nombre de logements",
        font=dict(color="#e0e0e0"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _afficher_conso_par_classe(df):
    """Consommation moyenne par classe DPE (barres horizontales)."""
    st.subheader("🔥 Consommation par classe DPE")

    conso = df.groupby("etiquette_dpe")["conso_5_usages_par_m2_ef"].mean().reset_index()
    conso.columns = ["Classe", "Conso (kWh/m²/an)"]
    conso = conso.sort_values("Classe")

    fig = px.bar(
        conso, x="Conso (kWh/m²/an)", y="Classe",
        orientation="h",
        color="Classe",
        color_discrete_map=COULEURS_DPE,
        text="Conso (kWh/m²/an)"
    )
    fig.update_traces(texttemplate="%{text:.0f} kWh/m²", textposition="outside")
    fig.update_layout(
        showlegend=False,
        yaxis=dict(categoryorder="category descending"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        font=dict(color="#e0e0e0"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _afficher_gains_barres(transitions):
    """Gains kWh/an par transition avec ligne €/an."""
    st.subheader("📈 Gains par transition DPE")

    if transitions.empty:
        st.info("Pas de transitions disponibles.")
        return

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Gain kWh/an",
        x=transitions["transition"],
        y=transitions["gain_moyen_kwh_an"],
        marker_color=["#FF3300", "#FF9900", "#FFCC00", "#99CC00"],
        text=transitions["gain_moyen_kwh_an"].apply(lambda x: f"{x:,.0f} kWh"),
        textposition="outside",
        yaxis="y"
    ))

    fig.add_trace(go.Scatter(
        name="Gain €/an",
        x=transitions["transition"],
        y=transitions["gain_moyen_eur_an"],
        mode="lines+markers+text",
        marker=dict(size=10, color="#2ecc71"),
        line=dict(color="#2ecc71", width=2.5),
        text=transitions["gain_moyen_eur_an"].apply(lambda x: f"{x:,.0f} €"),
        textposition="top center",
        yaxis="y2"
    ))

    fig.update_layout(
        yaxis=dict(title="kWh/an", titlefont=dict(color="#e0e0e0")),
        yaxis2=dict(title="€/an", overlaying="y", side="right", titlefont=dict(color="#2ecc71")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color="#e0e0e0")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        font=dict(color="#e0e0e0"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Hypothèse : {PRIX_KWH} €/kWh — surface moyenne ~72 m²")


def _afficher_repartition_type(df):
    """Répartition par type de bâtiment (donut chart)."""
    st.subheader("🏠 Répartition par type de bâtiment")

    repartition = df["type_batiment"].value_counts().reset_index()
    repartition.columns = ["Type", "Nombre"]

    couleurs_type = ["#2ecc71", "#3498db", "#e67e22", "#9b59b6", "#e74c3c"]

    fig = go.Figure(data=[go.Pie(
        labels=repartition["Type"],
        values=repartition["Nombre"],
        hole=0.45,
        marker=dict(colors=couleurs_type[:len(repartition)]),
        textinfo="label+percent",
        textfont=dict(size=13, color="#e0e0e0"),
    )])
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        font=dict(color="#e0e0e0"),
        annotations=[dict(
            text=f"<b>{len(df):,}</b><br>logements",
            x=0.5, y=0.5,
            font_size=14, font_color="#2ecc71",
            showarrow=False
        )]
    )
    st.plotly_chart(fig, use_container_width=True)


def _afficher_conso_par_periode(df):
    """Consommation moyenne par période de construction."""
    st.subheader("📅 Consommation par période de construction")

    if "periode_construction" not in df.columns:
        st.info("Colonne 'periode_construction' non disponible.")
        return

    periode = df.groupby("periode_construction")["conso_5_usages_par_m2_ef"].mean().reset_index()
    periode.columns = ["Période", "Conso (kWh/m²/an)"]

    # Tri chronologique
    ordre = ["Avant 1975", "1975-1989", "1990-2005", "2006-2012 (RT2005)", "Après 2012 (RT2012)"]
    periode["Période"] = pd.Categorical(periode["Période"], categories=ordre, ordered=True)
    periode = periode.sort_values("Période").dropna(subset=["Période"])

    fig = px.bar(
        periode, x="Période", y="Conso (kWh/m²/an)",
        text="Conso (kWh/m²/an)",
        color="Conso (kWh/m²/an)",
        color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
    )
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        xaxis_title="",
        yaxis_title="kWh/m²/an",
        font=dict(color="#e0e0e0"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _afficher_tableau_gains(gains):
    """Tableau complet des gains par transition."""
    st.subheader("📋 Tableau des gains par transition")

    cols_affichage = [
        "transition", "conso_moyenne_depart_kwh_m2",
        "conso_moyenne_arrivee_kwh_m2", "gain_moyen_kwh_m2_an",
        "gain_moyen_kwh_an", "gain_moyen_eur_an", "nb_logements"
    ]

    # Vérifier que toutes les colonnes existent
    cols_ok = [c for c in cols_affichage if c in gains.columns]
    df_aff = gains[cols_ok].copy()

    noms = {
        "transition": "Transition",
        "conso_moyenne_depart_kwh_m2": "Conso départ (kWh/m²/an)",
        "conso_moyenne_arrivee_kwh_m2": "Conso arrivée (kWh/m²/an)",
        "gain_moyen_kwh_m2_an": "Gain (kWh/m²/an)",
        "gain_moyen_kwh_an": "Gain (kWh/an)",
        "gain_moyen_eur_an": "Gain (€/an)",
        "nb_logements": "Nb logements"
    }
    df_aff = df_aff.rename(columns=noms)

    if "Gain (€/an)" in df_aff.columns:
        df_aff["Gain (€/an)"] = df_aff["Gain (€/an)"].apply(lambda x: f"{x:,.0f} €")
    if "Gain (kWh/an)" in df_aff.columns:
        df_aff["Gain (kWh/an)"] = df_aff["Gain (kWh/an)"].apply(lambda x: f"{x:,.0f}")
    if "Nb logements" in df_aff.columns:
        df_aff["Nb logements"] = df_aff["Nb logements"].apply(lambda x: f"{x:,}")

    st.dataframe(df_aff, use_container_width=True, hide_index=True, height=250)


# ══════════════════════════════════════════════════════════════
#  SIMULATEUR
# ══════════════════════════════════════════════════════════════

def _afficher_simulateur(gains):
    """Simulateur de gains personnalisé."""
    st.subheader("🧮 Simulateur de gains personnalisé")
    st.markdown("Estimez vos économies en renseignant votre logement :")

    col1, col2 = st.columns(2)

    with col1:
        surface = st.number_input(
            "Surface du logement (m²)",
            min_value=10, max_value=500, value=75, step=5,
            key="simu_surface"
        )
        prix_kwh = st.number_input(
            "Prix du kWh (€)",
            min_value=0.10, max_value=0.50, value=PRIX_KWH,
            step=0.01, format="%.2f", key="simu_prix"
        )

    with col2:
        classes_dispo = sorted(
            set(gains["classe_depart"].tolist() + gains["classe_arrivee"].tolist())
        )
        classe_depart = st.selectbox(
            "Classe DPE actuelle",
            options=classes_dispo,
            index=classes_dispo.index("F") if "F" in classes_dispo else 0,
            key="simu_depart"
        )
        classe_arrivee = st.selectbox(
            "Classe DPE cible (après rénovation)",
            options=classes_dispo,
            index=classes_dispo.index("C") if "C" in classes_dispo else 0,
            key="simu_arrivee"
        )

    transition_label = f"{classe_depart}->{classe_arrivee}"
    row = gains[gains["transition"] == transition_label]

    st.markdown("---")

    if classe_depart == classe_arrivee:
        st.warning("⚠️ La classe de départ et la classe cible sont identiques.")
    elif row.empty:
        st.warning(f"La transition {transition_label} n'est pas disponible. Essayez F→E, E→D, D→C ou C→B.")
    else:
        gain_m2 = float(row["gain_moyen_kwh_m2_an"].values[0])
        gain_kwh = gain_m2 * surface
        gain_eur = gain_kwh * prix_kwh
        conso_dep = float(row["conso_moyenne_depart_kwh_m2"].values[0]) * surface
        conso_arr = float(row["conso_moyenne_arrivee_kwh_m2"].values[0]) * surface

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(f"Conso actuelle ({classe_depart})", f"{conso_dep:,.0f} kWh/an")
        with c2:
            st.metric(f"Après rénovation ({classe_arrivee})", f"{conso_arr:,.0f} kWh/an",
                      delta=f"-{gain_kwh:,.0f} kWh/an")
        with c3:
            st.metric("💰 Économie estimée", f"{gain_eur:,.0f} €/an",
                      delta=f"{gain_m2:.1f} kWh/m²/an économisés")

        cout_renov = surface * 200
        if gain_eur > 0:
            retour = cout_renov / gain_eur
            st.info(
                f"💡 **Retour sur investissement** : pour des travaux estimés à "
                f"{cout_renov:,.0f} € (200 €/m²), retour en **{retour:.0f} ans** "
                f"à {prix_kwh} €/kWh."
            )

        st.caption("⚠️ Estimations basées sur des moyennes statistiques.")


# ══════════════════════════════════════════════════════════════
#  MÉTRIQUES MODÈLE
# ══════════════════════════════════════════════════════════════

def _afficher_metriques_modele(metriques):
    """Affiche les métriques du modèle ML."""
    with st.expander("🤖 Informations sur le modèle ML"):
        st.markdown("""
        **Modèle :** Ridge Regression (Scikit-learn)

        **Features :** type d'énergie chauffage/ECS, ventilation, type de bâtiment,
        période de construction, zone climatique, nombre de niveaux, hauteur sous plafond.

        **Target :** `conso_5_usages_par_m2_ef` (kWh/m²/an)

        **Données :** Dataset ADEME dpe03existant — logements existants
        """)

        if isinstance(metriques, dict):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("MAE", f"{metriques.get('mae', 0):.2f} kWh/m²/an")
            with c2:
                st.metric("RMSE", f"{metriques.get('rmse', 0):.2f} kWh/m²/an")
            with c3:
                st.metric("R² Test", f"{metriques.get('r2_test', 0):.4f}")
        elif isinstance(metriques, list):
            st.dataframe(pd.DataFrame(metriques), use_container_width=True, hide_index=True)
