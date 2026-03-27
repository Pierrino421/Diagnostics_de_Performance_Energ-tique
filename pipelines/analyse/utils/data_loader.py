"""
data_loader.py
--------------
Chargement des données depuis MinIO (couche Gold).
Fallback avec données simulées si MinIO est indisponible.
"""

import os
import io
import json
import numpy as np
import pandas as pd
import streamlit as st
from minio import Minio

# ── Configuration MinIO ────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
PRIX_KWH       = 0.2516


# ══════════════════════════════════════════════════════════════
#  CONNEXION MINIO
# ══════════════════════════════════════════════════════════════

def _get_minio_client():
    """Retourne un client MinIO connecté."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False
    )


# ══════════════════════════════════════════════════════════════
#  CHARGEMENT GAINS + MÉTRIQUES (Gold)
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=600)
def charger_gains_et_metriques():
    """
    Charge gains_par_classe.json et metriques.json depuis MinIO/gold/.
    Fallback avec données simulées si indisponible.
    """
    try:
        client = _get_minio_client()

        # Gains par classe
        resp = client.get_object(BUCKET, "gold/gains_par_classe.json")
        gains = pd.DataFrame(json.loads(resp.read().decode("utf-8")))

        # Métriques du modèle
        resp = client.get_object(BUCKET, "gold/metriques.json")
        metriques = json.loads(resp.read().decode("utf-8"))

        return gains, metriques, False  # False = pas simulé

    except Exception:
        return _simuler_gains(), _simuler_metriques(), True


# ══════════════════════════════════════════════════════════════
#  CHARGEMENT DÉTAILS LOGEMENTS (Gold Parquet)
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=600)
def charger_details_logements():
    """
    Charge les fichiers Parquet depuis gold/details_logements/.
    Fallback avec données simulées si indisponible.
    """
    try:
        client = _get_minio_client()
        prefix = "gold/details_logements/"
        objets = list(client.list_objects(BUCKET, prefix=prefix, recursive=True))
        fichiers = [o.object_name for o in objets if o.object_name.endswith(".parquet")]

        if not fichiers:
            raise FileNotFoundError("Aucun fichier Parquet dans gold/details_logements/")

        dfs = []
        for f in fichiers:
            data = client.get_object(BUCKET, f).read()
            dfs.append(pd.read_parquet(io.BytesIO(data)))

        df = pd.concat(dfs, ignore_index=True)
        return df, False

    except Exception:
        return _simuler_details_logements(), True


# ══════════════════════════════════════════════════════════════
#  DONNÉES SIMULÉES (FALLBACK)
# ══════════════════════════════════════════════════════════════

def _simuler_gains():
    """Génère des données de gains réalistes pour le fallback."""
    np.random.seed(42)
    transitions = [
        {"transition": "F->E", "classe_depart": "F", "classe_arrivee": "E",
         "conso_moyenne_depart_kwh_m2": 380, "conso_moyenne_arrivee_kwh_m2": 290,
         "gain_moyen_kwh_m2_an": 90, "gain_moyen_kwh_an": 6480,
         "gain_moyen_eur_an": 1620, "surface_moyenne_m2": 72, "nb_logements": 4219},
        {"transition": "E->D", "classe_depart": "E", "classe_arrivee": "D",
         "conso_moyenne_depart_kwh_m2": 290, "conso_moyenne_arrivee_kwh_m2": 210,
         "gain_moyen_kwh_m2_an": 80, "gain_moyen_kwh_an": 5760,
         "gain_moyen_eur_an": 1440, "surface_moyenne_m2": 72, "nb_logements": 5586},
        {"transition": "D->C", "classe_depart": "D", "classe_arrivee": "C",
         "conso_moyenne_depart_kwh_m2": 210, "conso_moyenne_arrivee_kwh_m2": 130,
         "gain_moyen_kwh_m2_an": 80, "gain_moyen_kwh_an": 5760,
         "gain_moyen_eur_an": 1440, "surface_moyenne_m2": 72, "nb_logements": 8806},
        {"transition": "C->B", "classe_depart": "C", "classe_arrivee": "B",
         "conso_moyenne_depart_kwh_m2": 130, "conso_moyenne_arrivee_kwh_m2": 75,
         "gain_moyen_kwh_m2_an": 55, "gain_moyen_kwh_an": 3960,
         "gain_moyen_eur_an": 990, "surface_moyenne_m2": 72, "nb_logements": 2846},
        {"transition": "F->B", "classe_depart": "F", "classe_arrivee": "B",
         "conso_moyenne_depart_kwh_m2": 380, "conso_moyenne_arrivee_kwh_m2": 75,
         "gain_moyen_kwh_m2_an": 305, "gain_moyen_kwh_an": 21960,
         "gain_moyen_eur_an": 5490, "surface_moyenne_m2": 72, "nb_logements": 1200},
    ]
    return pd.DataFrame(transitions)


def _simuler_metriques():
    """Génère des métriques modèle pour le fallback."""
    return {
        "alpha": 10.0,
        "mae": 42.5,
        "rmse": 58.3,
        "r2_train": 0.4812,
        "r2_test": 0.4650,
    }


def _simuler_details_logements():
    """Génère un DataFrame simulé de logements pour le dashboard."""
    np.random.seed(42)
    n = 5000

    classes_dpe = np.random.choice(
        ["B", "C", "D", "E", "F"],
        size=n,
        p=[0.06, 0.52, 0.20, 0.12, 0.10]
    )

    conso_par_classe = {"B": 75, "C": 130, "D": 210, "E": 290, "F": 380}
    conso = np.array([
        conso_par_classe[c] + np.random.normal(0, 20) for c in classes_dpe
    ])

    types_bat = np.random.choice(
        ["Maison", "Appartement", "Immeuble"],
        size=n, p=[0.40, 0.50, 0.10]
    )

    zones = np.random.choice(
        ["H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3"],
        size=n, p=[0.15, 0.15, 0.10, 0.15, 0.10, 0.10, 0.10, 0.15]
    )

    periodes = np.random.choice(
        ["Avant 1975", "1975-1989", "1990-2005", "2006-2012 (RT2005)", "Après 2012 (RT2012)"],
        size=n, p=[0.25, 0.20, 0.25, 0.15, 0.15]
    )

    surfaces = np.clip(np.random.normal(72, 30, n), 15, 300).astype(int)

    energies_chauff = np.random.choice(
        ["Gaz naturel", "Électricité", "Fioul domestique", "Bois", "GPL"],
        size=n, p=[0.35, 0.35, 0.15, 0.10, 0.05]
    )

    energies_ecs = np.random.choice(
        ["Gaz naturel", "Électricité", "Fioul domestique", "Solaire"],
        size=n, p=[0.35, 0.40, 0.15, 0.10]
    )

    ventilations = np.random.choice(
        ["Ventilation naturelle", "VMC simple flux", "VMC double flux"],
        size=n, p=[0.30, 0.50, 0.20]
    )

    annees = np.clip(np.random.normal(1985, 20, n), 1900, 2024).astype(int)
    niveaux = np.random.choice([1, 2, 3, 4, 5], size=n, p=[0.35, 0.30, 0.20, 0.10, 0.05])
    hauteurs = np.clip(np.random.normal(2.5, 0.3, n), 2.2, 4.0).round(2)

    emissions = conso * 0.2 + np.random.normal(0, 5, n)
    cout_total = conso * surfaces / 1000 * PRIX_KWH * 10

    df = pd.DataFrame({
        "etiquette_dpe": classes_dpe,
        "conso_5_usages_par_m2_ef": conso.round(1),
        "conso_5_usages_ef": (conso * surfaces).round(0),
        "surface_habitable_logement": surfaces,
        "type_batiment": types_bat,
        "zone_climatique": zones,
        "periode_construction": periodes,
        "annee_construction": annees,
        "type_energie_principale_chauffage": energies_chauff,
        "type_energie_principale_ecs": energies_ecs,
        "type_ventilation": ventilations,
        "nombre_niveau_logement": niveaux,
        "hauteur_sous_plafond": hauteurs,
        "emission_ges_5_usages_par_m2": emissions.round(1),
        "cout_total_5_usages": cout_total.round(0),
        "conso_calculee_par_m2": conso.round(1),
    })

    return df
