"""
model_loader.py
---------------
Chargement du modèle Ridge depuis MinIO (gold/dpe_ridge_model.joblib).
Fallback avec un modèle simulé si MinIO est indisponible.
"""

import os
import io
import numpy as np
import pandas as pd
import streamlit as st
import joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from minio import Minio

# ── Configuration ──────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
CHEMIN_MODELE  = "gold/dpe_ridge_model.joblib"

# ── Features du modèle (identiques à modele.py) ───────────────
FEATURES_CATEGORIELLES = [
    "periode_construction",
    "type_batiment",
    "zone_climatique",
    "type_energie_principale_chauffage",
    "type_ventilation",
    "type_energie_principale_ecs",
]

FEATURES_NUMERIQUES = [
    "nombre_niveau_logement",
    "hauteur_sous_plafond",
]

# ── Seuils officiels DPE (kWh/m²/an) ──────────────────────────
SEUILS_DPE = {
    "A": (0, 70),
    "B": (70, 110),
    "C": (110, 180),
    "D": (180, 250),
    "E": (250, 330),
    "F": (330, 420),
    "G": (420, float("inf")),
}

# ── Modalités connues pour chaque feature catégorielle ─────────
MODALITES = {
    "periode_construction": [
        "Avant 1975", "1975-1989", "1990-2005",
        "2006-2012 (RT2005)", "Après 2012 (RT2012)"
    ],
    "type_batiment": ["Maison", "Appartement", "Immeuble"],
    "zone_climatique": ["H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3"],
    "type_energie_principale_chauffage": [
        "Gaz naturel", "Électricité", "Fioul domestique",
        "Bois", "GPL", "Réseau de chaleur"
    ],
    "type_ventilation": [
        "Ventilation naturelle", "VMC simple flux",
        "VMC double flux", "VMC Hygroréglable"
    ],
    "type_energie_principale_ecs": [
        "Gaz naturel", "Électricité", "Fioul domestique",
        "Solaire", "Réseau de chaleur"
    ],
}


# ══════════════════════════════════════════════════════════════
#  CHARGEMENT DU MODÈLE
# ══════════════════════════════════════════════════════════════

@st.cache_resource
def charger_modele():
    """
    Charge le modèle Ridge + scaler + features depuis MinIO.
    Si indisponible, crée un modèle simulé.

    Returns:
        tuple: (model, scaler, feature_names, is_simulated)
    """
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_USER,
            secret_key=MINIO_PASSWORD,
            secure=False
        )
        data = client.get_object(BUCKET, CHEMIN_MODELE).read()
        model_data = joblib.load(io.BytesIO(data))

        return (
            model_data["model"],
            model_data["scaler"],
            model_data["features_names"],
            False
        )

    except Exception:
        return _creer_modele_simule()


def _creer_modele_simule():
    """
    Crée un modèle Ridge simulé avec les mêmes features
    que le vrai modèle pour garantir le fonctionnement de l'interface.
    """
    np.random.seed(42)
    n_samples = 2000

    # Générer des données synthétiques
    data = {}
    for feat in FEATURES_CATEGORIELLES:
        data[feat] = np.random.choice(MODALITES[feat], size=n_samples)

    data["nombre_niveau_logement"] = np.random.choice([1, 2, 3, 4, 5], size=n_samples)
    data["hauteur_sous_plafond"] = np.clip(np.random.normal(2.5, 0.3, n_samples), 2.2, 4.0)

    df = pd.DataFrame(data)

    # Target simulée (consommation kWh/m²/an)
    y = 150 + np.random.normal(0, 60, n_samples)

    # Facteurs réalistes
    for i, row in df.iterrows():
        if row["type_energie_principale_chauffage"] == "Fioul domestique":
            y[i] += 80
        elif row["type_energie_principale_chauffage"] == "Gaz naturel":
            y[i] += 30
        elif row["type_energie_principale_chauffage"] == "Bois":
            y[i] += 40
        elif row["type_energie_principale_chauffage"] == "Électricité":
            y[i] -= 10

        if row["type_ventilation"] == "VMC double flux":
            y[i] -= 40
        elif row["type_ventilation"] == "Ventilation naturelle":
            y[i] += 30

        if row["periode_construction"] == "Avant 1975":
            y[i] += 60
        elif row["periode_construction"] == "Après 2012 (RT2012)":
            y[i] -= 50

    y = np.clip(y, 30, 600)

    # One-hot encoding
    X_cat = pd.get_dummies(df[FEATURES_CATEGORIELLES], drop_first=True, dtype=float)
    X_num = df[FEATURES_NUMERIQUES].astype(float)
    X = pd.concat([X_num, X_cat], axis=1)

    # Scaler + entraînement
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

    model = Ridge(alpha=10.0)
    model.fit(X_scaled, y)

    return model, scaler, X.columns.tolist(), True


# ══════════════════════════════════════════════════════════════
#  PRÉDICTION
# ══════════════════════════════════════════════════════════════

def predire_consommation(inputs: dict, model, scaler, feature_names):
    """
    Prédit la consommation kWh/m²/an à partir des inputs utilisateur.

    Args:
        inputs: dict avec les valeurs saisies par l'utilisateur
        model: modèle Ridge entraîné
        scaler: StandardScaler fitted
        feature_names: liste des noms de features attendus

    Returns:
        float: consommation prédite en kWh/m²/an
    """
    # Construire le DataFrame d'entrée
    df_input = pd.DataFrame([inputs])

    # One-hot encoding
    X_cat = pd.get_dummies(
        df_input[FEATURES_CATEGORIELLES],
        drop_first=True, dtype=float
    )
    X_num = df_input[FEATURES_NUMERIQUES].astype(float)
    X = pd.concat([X_num, X_cat], axis=1)

    # Aligner les colonnes avec celles du modèle
    for col in feature_names:
        if col not in X.columns:
            X[col] = 0.0
    X = X[feature_names]

    # Scaler + prédiction
    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]

    return max(prediction, 0)


def classe_dpe_from_conso(conso_kwh_m2):
    """Détermine la classe DPE à partir de la consommation."""
    for classe, (low, high) in SEUILS_DPE.items():
        if low <= conso_kwh_m2 < high:
            return classe
    return "G"


def couleur_classe_dpe(classe):
    """Retourne la couleur officielle pour une classe DPE."""
    couleurs = {
        "A": "#009900", "B": "#33CC00", "C": "#99CC00",
        "D": "#FFCC00", "E": "#FF9900", "F": "#FF3300", "G": "#CC0000"
    }
    return couleurs.get(classe, "#999999")
