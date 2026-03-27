"""
dashboard.py
------------
Dashboard Streamlit — Projet DPE Open Data University

Visualisations :
    1. Consommation moyenne par classe DPE
    2. Graphique en barres des gains kWh/an
    3. Tableau des gains par transition
    4. Simulateur personnalise (surface + classe -> gain estime)

Source des donnees : MinIO/gold/gains_par_classe.json

Usage :
    streamlit run /app/pipelines/visualisation/dashboard.py
"""

import os
import io
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from minio import Minio

# ── Configuration ──────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
PRIX_KWH       = 0.25
# ───────────────────────────────────────────────────────────────

# ── Configuration de la page ───────────────────────────────────
st.set_page_config(
    page_title="Dashboard DPE — Gains Energetiques",
    page_icon="⚡",
    layout="wide"
)

# ── Couleurs par classe DPE (standard officiel) ────────────────
COULEURS_DPE = {
    "A": "#009900",
    "B": "#33CC00",
    "C": "#99CC00",
    "D": "#FFCC00",
    "E": "#FF9900",
    "F": "#FF3300",
    "G": "#CC0000",
}


# ══════════════════════════════════════════════════════════════
#  CHARGEMENT DES DONNEES
# ══════════════════════════════════════════════════════════════

@st.cache_data
def charger_donnees():
    """
    Charge les donnees depuis MinIO/gold/
    @st.cache_data evite de recharger a chaque interaction
    """
    try:
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER,
                       secret_key=MINIO_PASSWORD, secure=False)

        # Gains par classe
        response = client.get_object(BUCKET, "gold/gains_par_classe.json")
        gains    = pd.DataFrame(json.loads(response.read().decode("utf-8")))

        # Metriques du modele
        response  = client.get_object(BUCKET, "gold/metriques.json")
        metriques = json.loads(response.read().decode("utf-8"))

        return gains, metriques

    except Exception as e:
        st.error(f"Erreur de connexion a MinIO : {e}")
        st.info("Verifier que MinIO tourne et que les donnees gold/ sont presentes.")
        return None, None


# ══════════════════════════════════════════════════════════════
#  PAGE PRINCIPALE
# ══════════════════════════════════════════════════════════════

def main():

    # ── En-tete ────────────────────────────────────────────────
    st.title("⚡ Dashboard DPE — Gains Energetiques")
    st.markdown("""
    **Projet Open Data University — Partenariat Enedis**

    > *Combien gagne-t-on sur ses factures d'électricité en passant d'une classe DPE à une autre ?*

    Les résultats présentés sont issus d'un modèle **Random Forest** entraîné sur les données
    open data ADEME (dataset dpe03existant — logements existants).
    """)
    st.divider()

    # Chargement
    gains, metriques = charger_donnees()
    if gains is None:
        return

    # Garde uniquement les transitions simples (1 niveau)
    transitions_simples = gains[gains["transition"].isin(
        ["F->E", "E->D", "D->C", "C->B"]
    )].copy()

    # ── KPIs en haut ───────────────────────────────────────────
    st.subheader("📊 Chiffres clés")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        gain_max = gains["gain_moyen_eur_an"].max()
        st.metric(
            label="Gain max (F→B)",
            value=f"{gain_max:,.0f} €/an",
            delta="rénovation complète"
        )
    with col2:
        gain_fe = gains[gains["transition"] == "F->E"]["gain_moyen_eur_an"].values[0]
        st.metric(
            label="Gain F→E",
            value=f"{gain_fe:,.0f} €/an",
            delta="1 niveau d'amélioration"
        )
    with col3:
        gain_kwh = gains[gains["transition"] == "F->B"]["gain_moyen_kwh_an"].values[0]
        st.metric(
            label="Économie énergie (F→B)",
            value=f"{gain_kwh:,.0f} kWh/an",
            delta="soit ~16 000 kWh économisés"
        )
    with col4:
        surface_moy = gains["surface_moyenne_m2"].mean()
        st.metric(
            label="Surface moyenne analysée",
            value=f"{surface_moy:.0f} m²",
            delta=f"{len(gains)} transitions calculées"
        )

    st.divider()

    # ── Ligne 1 : Conso par classe + Gains en barres ───────────
    col_gauche, col_droite = st.columns(2)

    with col_gauche:
        afficher_conso_par_classe(gains)

    with col_droite:
        afficher_gains_barres(transitions_simples)

    st.divider()

    # ── Ligne 2 : Tableau + Simulateur ─────────────────────────
    col_tableau, col_simu = st.columns(2)

    with col_tableau:
        afficher_tableau_gains(gains)

    with col_simu:
        afficher_simulateur(gains)

    st.divider()

    # ── Metriques du modele ────────────────────────────────────
    afficher_metriques_modele(metriques)


# ══════════════════════════════════════════════════════════════
#  VISUALISATION 1 — Consommation moyenne par classe
# ══════════════════════════════════════════════════════════════

def afficher_conso_par_classe(gains: pd.DataFrame):
    """
    Graphique horizontal montrant la consommation moyenne
    de chaque classe DPE en kWh/m²/an.
    """
    st.subheader("🏠 Consommation moyenne par classe DPE")

    # Reconstruit les consos moyennes depuis les gains
    # conso_depart de chaque transition = conso de la classe depart
    classes_data = {}
    for _, row in gains.iterrows():
        classes_data[row["classe_depart"]] = row["conso_moyenne_depart_kwh_m2"]
        classes_data[row["classe_arrivee"]] = row["conso_moyenne_arrivee_kwh_m2"]

    df_conso = pd.DataFrame([
        {"classe": k, "conso_kwh_m2": v}
        for k, v in sorted(classes_data.items())
    ])

    fig = px.bar(
        df_conso,
        x="conso_kwh_m2",
        y="classe",
        orientation="h",
        color="classe",
        color_discrete_map=COULEURS_DPE,
        labels={
            "conso_kwh_m2": "Consommation (kWh/m²/an)",
            "classe": "Classe DPE"
        },
        text="conso_kwh_m2"
    )
    fig.update_traces(texttemplate="%{text:.0f} kWh/m²", textposition="outside")
    fig.update_layout(
        showlegend=False,
        yaxis=dict(categoryorder="category descending"),
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Source : modèle Random Forest — dataset ADEME dpe03existant")


# ══════════════════════════════════════════════════════════════
#  VISUALISATION 2 — Gains en barres
# ══════════════════════════════════════════════════════════════

def afficher_gains_barres(transitions_simples: pd.DataFrame):
    """
    Graphique en barres des gains kWh/an par transition simple.
    """
    st.subheader("📈 Gains énergétiques par transition")

    fig = go.Figure()

    # Barres kWh/an
    fig.add_trace(go.Bar(
        name="Gain kWh/an",
        x=transitions_simples["transition"],
        y=transitions_simples["gain_moyen_kwh_an"],
        marker_color=["#FF3300", "#FF9900", "#FFCC00", "#99CC00"],
        text=transitions_simples["gain_moyen_kwh_an"].apply(lambda x: f"{x:,.0f} kWh"),
        textposition="outside",
        yaxis="y"
    ))

    # Ligne €/an (axe secondaire)
    fig.add_trace(go.Scatter(
        name="Gain €/an",
        x=transitions_simples["transition"],
        y=transitions_simples["gain_moyen_eur_an"],
        mode="lines+markers+text",
        marker=dict(size=10, color="#003366"),
        line=dict(color="#003366", width=2),
        text=transitions_simples["gain_moyen_eur_an"].apply(lambda x: f"{x:,.0f} €"),
        textposition="top center",
        yaxis="y2"
    ))

    fig.update_layout(
        yaxis=dict(title="kWh/an"),
        yaxis2=dict(title="€/an", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Hypothèse tarifaire : {PRIX_KWH} €/kWh — surface moyenne ~72 m²")


# ══════════════════════════════════════════════════════════════
#  VISUALISATION 3 — Tableau des gains
# ══════════════════════════════════════════════════════════════

def afficher_tableau_gains(gains: pd.DataFrame):
    """
    Tableau complet des gains par transition avec mise en forme.
    """
    st.subheader("📋 Tableau complet des gains")

    df_affiche = gains[[
        "transition", "conso_moyenne_depart_kwh_m2",
        "conso_moyenne_arrivee_kwh_m2", "gain_moyen_kwh_m2_an",
        "gain_moyen_kwh_an", "gain_moyen_eur_an", "nb_logements"
    ]].copy()

    df_affiche.columns = [
        "Transition", "Conso départ\n(kWh/m²/an)", "Conso arrivée\n(kWh/m²/an)",
        "Gain\n(kWh/m²/an)", "Gain\n(kWh/an)", "Gain\n(€/an)", "Nb logements"
    ]

    # Formate les colonnes numeriques
    df_affiche["Gain\n(€/an)"]     = df_affiche["Gain\n(€/an)"].apply(lambda x: f"{x:,.0f} €")
    df_affiche["Gain\n(kWh/an)"]   = df_affiche["Gain\n(kWh/an)"].apply(lambda x: f"{x:,.0f}")
    df_affiche["Nb logements"]      = df_affiche["Nb logements"].apply(lambda x: f"{x:,}")

    st.dataframe(df_affiche, use_container_width=True, hide_index=True)
    st.caption("Gains moyens calculés sur les logements de chaque classe")


# ══════════════════════════════════════════════════════════════
#  VISUALISATION 4 — Simulateur personnalise
# ══════════════════════════════════════════════════════════════

def afficher_simulateur(gains: pd.DataFrame):
    """
    Simulateur interactif — l'utilisateur entre sa surface
    et ses classes DPE de depart et arrivee.
    Le gain est calcule en temps reel.
    """
    st.subheader("🧮 Simulateur personnalisé")
    st.markdown("Estimez vos économies selon votre logement :")

    col1, col2 = st.columns(2)

    with col1:
        surface = st.number_input(
            "Surface du logement (m²)",
            min_value=10,
            max_value=500,
            value=75,
            step=5
        )
        prix_kwh = st.number_input(
            "Prix du kWh (€)",
            min_value=0.10,
            max_value=0.50,
            value=PRIX_KWH,
            step=0.01,
            format="%.2f"
        )

    with col2:
        classes_dispo = sorted(
            set(gains["classe_depart"].tolist() + gains["classe_arrivee"].tolist())
        )
        classe_depart = st.selectbox(
            "Classe DPE actuelle",
            options=classes_dispo,
            index=classes_dispo.index("F") if "F" in classes_dispo else 0
        )
        classe_arrivee = st.selectbox(
            "Classe DPE cible (après rénovation)",
            options=classes_dispo,
            index=classes_dispo.index("C") if "C" in classes_dispo else 0
        )

    # Recherche la transition dans les donnees
    transition_label = f"{classe_depart}->{classe_arrivee}"
    row = gains[gains["transition"] == transition_label]

    st.markdown("---")

    if classe_depart == classe_arrivee:
        st.warning("La classe de départ et la classe cible sont identiques.")

    elif row.empty:
        st.warning(
            f"La transition {transition_label} n'est pas disponible dans les données. "
            f"Essayez une transition directe (ex: F→E, E→D...)."
        )

    else:
        gain_m2    = float(row["gain_moyen_kwh_m2_an"].values[0])
        gain_kwh   = gain_m2 * surface
        gain_eur   = gain_kwh * prix_kwh
        conso_dep  = float(row["conso_moyenne_depart_kwh_m2"].values[0]) * surface
        conso_arr  = float(row["conso_moyenne_arrivee_kwh_m2"].values[0]) * surface

        col_r1, col_r2, col_r3 = st.columns(3)

        with col_r1:
            st.metric(
                label=f"Conso actuelle (classe {classe_depart})",
                value=f"{conso_dep:,.0f} kWh/an"
            )
        with col_r2:
            st.metric(
                label=f"Conso après rénovation (classe {classe_arrivee})",
                value=f"{conso_arr:,.0f} kWh/an",
                delta=f"-{gain_kwh:,.0f} kWh/an"
            )
        with col_r3:
            st.metric(
                label="Économie estimée",
                value=f"{gain_eur:,.0f} €/an",
                delta=f"{gain_m2:.1f} kWh/m²/an économisés"
            )

        # Retour sur investissement estimatif
        st.markdown("---")
        cout_renov_estime = surface * 200   # hypothèse 200€/m² de travaux
        if gain_eur > 0:
            retour = cout_renov_estime / gain_eur
            st.info(
                f"💡 **Estimation retour sur investissement** : "
                f"pour des travaux estimés à {cout_renov_estime:,.0f} € "
                f"(hypothèse 200 €/m²), le retour sur investissement est "
                f"d'environ **{retour:.0f} ans** à {prix_kwh} €/kWh."
            )

        st.caption(
            "⚠️ Ces estimations sont basées sur des moyennes statistiques. "
            "Les gains réels dépendent des caractéristiques spécifiques de votre logement."
        )


# ══════════════════════════════════════════════════════════════
#  METRIQUES DU MODELE
# ══════════════════════════════════════════════════════════════

def afficher_metriques_modele(metriques):
    """Affiche les metriques du modele ML en bas de page."""
    with st.expander("🤖 Informations sur le modèle ML"):
        st.markdown("""
        **Modèle utilisé :** Random Forest Regressor (Scikit-learn)

        **Approche :** Un modèle par classe DPE (B, C, D, E, F)
        — chaque modèle apprend les patterns physiques de sa classe
        sans utiliser l'étiquette DPE comme feature.

        **Target :** `conso_5_usages_par_m2_ef` (kWh/m²/an)

        **Features :** type d'énergie, type d'installation, type de bâtiment,
        période de construction, année de construction, coefficient thermique (Ubat),
        qualité isolation, hauteur sous plafond, nombre d'appartements.

        **Données :** Dataset ADEME dpe03existant — logements existants
        """)

        if isinstance(metriques, list):
            df_m = pd.DataFrame(metriques)
            st.dataframe(df_m, use_container_width=True, hide_index=True)
        else:
            st.json(metriques)


# ── Point d'entree ─────────────────────────────────────────────
if __name__ == "__main__":
    main()