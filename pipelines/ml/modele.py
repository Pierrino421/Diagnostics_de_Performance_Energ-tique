"""
modele.py
---------
Entraine un Random Forest avec Scikit-learn pour predire
la consommation energetique (conso_5_usages_ef) d'un logement.

Corrections apportees :
- Suppression de conso_5_usages_par_m2_ep (data leakage)
- Suppression de toutes les colonnes de consommation/cout
  qui sont directement liees a la target
- Verification du R2 pour detecter le data leakage
- Affichage de la distribution des classes avant entrainement

Lecture  : MinIO/silver/existant/ (Parquet)
Ecriture : MinIO/gold/gains_par_classe.json
           MinIO/gold/metriques.json

Usage :
    python pipelines/ml/modele.py
"""

import os
import io
import json
import pandas as pd
import numpy as np

from minio import Minio
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# ── Configuration ──────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
CHEMIN_SILVER  = "silver/existant/"
CHEMIN_GOLD    = "gold/"
PRIX_KWH       = 0.25
# ───────────────────────────────────────────────────────────────

# TARGET normalisee par m² — evite que la surface biaise le modele
# Le modele apprend kWh/m²/an au lieu de kWh/an total
TARGET = "conso_5_usages_par_m2_ef"

# Features categorielles (texte -> LabelEncoder)
FEATURES_CAT = [
    "type_energie_principale_chauffage",
    "type_installation_chauffage",
    "type_batiment",
    "periode_construction",
]

# Features numeriques
# IMPORTANT : on exclut toutes les colonnes de consommation et de cout
# car elles sont directement calculees depuis la target (data leakage)
# On garde uniquement les caracteristiques physiques du logement
FEATURES_NUM = [
    # surface supprimee — inutile pour predire kWh/m²/an
    "annee_construction",            # age du batiment
    "ubat_w_par_m2_k",               # coefficient thermique (isolation globale)
    "hauteur_sous_plafond",          # volume du logement
    "etiquette_dpe_num",             # classe DPE (1->7) <- variable principale
    "qualite_isolation_murs_num",    # qualite isolation murs (1->4)
    "qualite_isolation_enveloppe_num", # qualite isolation globale (1->4)
    "qualite_isolation_menuiseries_num", # qualite fenetres (1->4)
    # nombre_niveau supprime — inutile pour predire kWh/m²/an
    "nombre_appartement",            # taille de l'immeuble
]

# Colonnes a exclure explicitement car liees a la target (data leakage)
# Ces colonnes sont calculees DEPUIS la consommation -> le modele trichemrait
COLONNES_LEAKAGE = [
    "conso_5_usages_par_m2_ep",    # = target / surface * coefficient
    "conso_5_usages_ep",           # = target * coefficient
    "conso_chauffage_ef",          # composante directe de la target
    "conso_ecs_ef",                # composante directe de la target
    "conso_eclairage_ef",          # composante directe de la target
    "conso_refroidissement_ef",    # composante directe de la target
    "conso_auxiliaires_ef",        # composante directe de la target
    "cout_total_5_usages",         # = target * prix_kwh
    "cout_chauffage",              # composante directe du cout
    "cout_ecs",
    "cout_eclairage",
    "cout_refroidissement",
    "cout_auxiliaires",
    "emission_ges_5_usages",       # calcule depuis la consommation
    "emission_ges_5_usages_par_m2",
]

MAPPING_DPE     = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
MAPPING_DPE_INV = {v: k for k, v in MAPPING_DPE.items()}


# ══════════════════════════════════════════════════════════════
#  ETAPE 1 — Lecture depuis MinIO/silver
# ══════════════════════════════════════════════════════════════

def lire_silver() -> pd.DataFrame:
    """
    Lit les fichiers Parquet depuis MinIO/silver/existant/
    et les fusionne en un seul DataFrame Pandas.
    """
    client   = Minio(MINIO_ENDPOINT, access_key=MINIO_USER,
                     secret_key=MINIO_PASSWORD, secure=False)
    objets   = list(client.list_objects(BUCKET, prefix=CHEMIN_SILVER, recursive=True))
    fichiers = [o.object_name for o in objets if o.object_name.endswith(".parquet")]

    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier Parquet dans {BUCKET}/{CHEMIN_SILVER}")

    print(f" {len(fichiers)} fichiers Parquet trouves dans silver/existant/")

    dfs = []
    for chemin in fichiers:
        response = client.get_object(BUCKET, chemin)
        contenu  = response.read()
        response.close()
        dfs.append(pd.read_parquet(io.BytesIO(contenu)))

    df = pd.concat(dfs, ignore_index=True)
    print(f"OK {len(df):,} lignes chargees — {len(df.columns)} colonnes")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 2 — Verification de la distribution des classes
# ══════════════════════════════════════════════════════════════

def verifier_classes(df: pd.DataFrame):
    """
    Affiche la distribution des classes DPE.
    Si une seule classe est presente, le modele ne peut pas
    apprendre les differences entre classes -> avertissement.
    """
    print("\n  Distribution des classes DPE dans silver :")
    print("-" * 40)

    if "etiquette_dpe" in df.columns:
        distribution = df["etiquette_dpe"].value_counts().sort_index()
        for classe, nb in distribution.items():
            pct = nb / len(df) * 100
            barre = "#" * int(pct / 2)
            print(f"  Classe {classe} : {nb:>6,} logements ({pct:>5.1f}%) {barre}")

    nb_classes = df["etiquette_dpe"].nunique() if "etiquette_dpe" in df.columns else 0
    print("-" * 40)

    if nb_classes < 4:
        print(f"  ATTENTION : seulement {nb_classes} classe(s) presente(s) !")
        print(f"  La simulation sera limitee aux transitions disponibles.")
        print(f"  Ingerer plus de donnees avec --offset pour avoir D, E, F, G.")
    else:
        print(f"  OK : {nb_classes} classes presentes — simulation complete possible")




# ══════════════════════════════════════════════════════════════
#  ETAPE 2b — Rééquilibrage des classes (undersampling)
# ══════════════════════════════════════════════════════════════

def reequilibrer_classes(df: pd.DataFrame, max_par_classe: int = 5000) -> pd.DataFrame:
    """
    Limite le nombre de logements par classe pour eviter
    que la classe dominante (ex: C avec 23 000 logements)
    ne biaise le modele.

    Technique : undersampling aleatoire
    On garde au maximum max_par_classe logements par classe.
    Les classes avec moins de lignes ne sont pas affectees.

    Avant : B:2846  C:23484  D:8806  E:5586  F:4219
    Apres : B:2846  C:5000   D:5000  E:5000  F:4219
    """
    if "etiquette_dpe" not in df.columns:
        return df

    print(f"\n Rééquilibrage des classes (max {max_par_classe:,} par classe) :")
    print("-" * 45)

    groupes = []
    for classe, groupe in df.groupby("etiquette_dpe"):
        nb_avant = len(groupe)
        if nb_avant > max_par_classe:
            groupe = groupe.sample(n=max_par_classe, random_state=42)
        print(f"  Classe {classe} : {nb_avant:>6,} -> {len(groupe):>6,} logements")
        groupes.append(groupe)

    df_balanced = pd.concat(groupes, ignore_index=True)
    print("-" * 45)
    print(f"  Total : {len(df):,} -> {len(df_balanced):,} logements")
    return df_balanced

# ══════════════════════════════════════════════════════════════
#  ETAPE 3 — Preparation des donnees
# ══════════════════════════════════════════════════════════════

def preparer_donnees(df: pd.DataFrame):
    """
    Prepare le DataFrame pour Scikit-learn :
    - Supprime les colonnes de data leakage
    - Encode les colonnes categorielles
    - Retourne X (features) et y (target)
    """
    # Supprime les colonnes leakage si elles sont presentes
    cols_a_supprimer = [c for c in COLONNES_LEAKAGE if c in df.columns]
    if cols_a_supprimer:
        print(f"\n Colonnes leakage supprimees : {cols_a_supprimer}")
        df = df.drop(columns=cols_a_supprimer)

    # Garde uniquement les colonnes utiles
    toutes = FEATURES_CAT + FEATURES_NUM + [TARGET]
    dispo  = [c for c in toutes if c in df.columns]
    df     = df[dispo].copy()

    # Supprime les lignes ou la target est null
    nb_avant = len(df)
    df       = df.dropna(subset=[TARGET])
    print(f"OK Lignes supprimees (target null) : {nb_avant - len(df):,}")

    # Nulls features cat -> "Inconnu"
    for col in FEATURES_CAT:
        if col in df.columns:
            df[col] = df[col].fillna("Inconnu")

    # Nulls features num -> 0
    for col in FEATURES_NUM:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # LabelEncoder sur les colonnes categorielles
    encoders = {}
    for col in FEATURES_CAT:
        if col in df.columns:
            le            = LabelEncoder()
            df[col]       = le.fit_transform(df[col].astype(str))
            encoders[col] = le

    features_dispo = [c for c in FEATURES_CAT + FEATURES_NUM if c in df.columns]
    X = df[features_dispo]
    y = df[TARGET].astype(float)

    # Calcul de la target normalisee par m² (kWh/m²/an)
    # Permet de comparer des logements de tailles differentes
    # independamment de la surface
    if "surface_habitable_logement" in df.columns:
        surface = df["surface_habitable_logement"].replace(0, np.nan).fillna(df["surface_habitable_logement"].median())
        y_par_m2 = (y / surface).round(2)
    else:
        y_par_m2 = y.copy()

    print(f"OK Donnees preparees : {len(X):,} lignes — {len(X.columns)} features")
    print(f"   Features utilisees : {list(X.columns)}")
    return X, y, y_par_m2, encoders


# ══════════════════════════════════════════════════════════════
#  ETAPE 4 — Entrainement et evaluation
# ══════════════════════════════════════════════════════════════

def entrainer_evaluer(X: pd.DataFrame, y: pd.Series):
    """
    Entraine le Random Forest et evalue les performances.
    Detecte automatiquement le data leakage si R2 > 0.99.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\n Split : {len(X_train):,} train / {len(X_test):,} test")

    print(" Entrainement en cours...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    print("OK Modele entraine")

    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    rmse   = np.sqrt(mean_squared_error(y_test, y_pred))
    r2     = r2_score(y_test, y_pred)

    print("\n" + "=" * 50)
    print("  METRIQUES DU MODELE")
    print("=" * 50)
    print(f"  MAE  (erreur moyenne)     : {mae:,.0f} kWh/an")
    print(f"  RMSE (erreur quadratique) : {rmse:,.0f} kWh/an")
    print(f"  R2   (variance expliquee) : {r2:.4f}")

    # Detection automatique du data leakage
    if r2 > 0.99:
        print(f"\n  ATTENTION : R2 = {r2:.4f} — trop proche de 1.0 !")
        print(f"  Signe possible de data leakage.")
        print(f"  Verifier les features les plus importantes.")
    elif r2 > 0.85:
        print(f"\n  Bon modele — R2 satisfaisant")
    else:
        print(f"\n  R2 faible — le modele peut etre ameliore")
    print("=" * 50)

    # Importance des features
    print("\n  Top 10 features importantes :")
    importances = pd.DataFrame({
        "feature":    X.columns,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False).head(10)
    print(importances.to_string(index=False))

    return model, {"mae": float(mae), "rmse": float(rmse), "r2": float(r2)}


# ══════════════════════════════════════════════════════════════
#  ETAPE 5 — Simulation contrefactuelle
# ══════════════════════════════════════════════════════════════

def simuler_gains(model: RandomForestRegressor, X: pd.DataFrame, df_original: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque transition (ex: F->E) :
    1. Filtre les logements de classe F
    2. Predit leur conso en classe F
    3. Change etiquette_dpe_num : F(6) -> E(5)
    4. Predit leur conso en classe E
    5. Gain = conso_F - conso_E en kWh/an et euros/an
    """
    print("\n Simulation contrefactuelle en cours...")

    if "etiquette_dpe_num" not in X.columns:
        print("ERREUR : etiquette_dpe_num absent des features")
        return pd.DataFrame()

    # Transitions disponibles avec les classes B, C, D, E, F
    # (classes A et G absentes du dataset dpe03existant)
    transitions = [
        (6, 5, "F->E"),   # 1 niveau d amelioration
        (5, 4, "E->D"),
        (4, 3, "D->C"),
        (3, 2, "C->B"),
        (6, 4, "F->D"),   # 2 niveaux d amelioration
        (5, 3, "E->C"),
        (4, 2, "D->B"),
        (6, 2, "F->B"),   # renovation complete (F vers B)
    ]

    resultats = []

    for num_depart, num_arrivee, label in transitions:

        lettre_depart  = MAPPING_DPE_INV[num_depart]
        lettre_arrivee = MAPPING_DPE_INV[num_arrivee]

        masque   = X["etiquette_dpe_num"] == num_depart
        X_depart = X[masque].copy()
        nb       = len(X_depart)

        if nb == 0:
            print(f"  {label} : aucun logement de classe {lettre_depart}")
            continue

        # Prediction conso classe depart
        conso_depart  = model.predict(X_depart)

        # Change la classe et predit la conso arrivee
        X_arrivee     = X_depart.copy()
        X_arrivee["etiquette_dpe_num"] = float(num_arrivee)
        conso_arrivee = model.predict(X_arrivee)

        # Le modele predit maintenant en kWh/m²/an
        # gain_m2 = difference de conso par m² entre les deux classes
        gain_moy_m2  = float(np.mean(conso_depart - conso_arrivee))

        # On reconvertit en kWh/an total avec la surface moyenne
        # pour donner un resultat concret au proprietaire
        surface_moy  = float(df_original[df_original["etiquette_dpe_num"] == num_depart]["surface_habitable_logement"].mean()) if "surface_habitable_logement" in df_original.columns else 75.0
        gain_moy_kwh = gain_moy_m2 * surface_moy
        gain_moy_eur = gain_moy_kwh * PRIX_KWH

        # Avertissement si gain negatif
        if gain_moy_m2 < 0:
            print(f"  {label} : ATTENTION gain negatif ({gain_moy_m2:.1f} kWh/m²) — modele insuffisant")
        else:
            print(f"  {label} : {gain_moy_m2:.1f} kWh/m²/an → {gain_moy_kwh:,.0f} kWh/an = {gain_moy_eur:,.0f} euros/an  ({nb} logements, surface moy: {surface_moy:.0f}m²)")

        resultats.append({
            "transition":                  label,
            "classe_depart":               lettre_depart,
            "classe_arrivee":              lettre_arrivee,
            "conso_moyenne_depart_kwh_m2": round(float(np.mean(conso_depart)),  1),
            "conso_moyenne_arrivee_kwh_m2":round(float(np.mean(conso_arrivee)), 1),
            "gain_moyen_kwh_m2_an":        round(gain_moy_m2,  2),
            "surface_moyenne_m2":          round(surface_moy,  1),
            "gain_moyen_kwh_an":           round(gain_moy_kwh, 1),
            "gain_moyen_eur_an":           round(gain_moy_eur, 2),
            "nb_logements":                nb,
        })

    return pd.DataFrame(resultats)


# ══════════════════════════════════════════════════════════════
#  ETAPE 6 — Ecriture dans MinIO/gold
# ══════════════════════════════════════════════════════════════

def ecrire_gold(df_gains: pd.DataFrame, metriques: dict):
    """Ecrit les resultats JSON dans MinIO/gold/"""
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER,
                   secret_key=MINIO_PASSWORD, secure=False)

    def upload_json(data, chemin):
        contenu = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        client.put_object(BUCKET, chemin, data=io.BytesIO(contenu),
                          length=len(contenu), content_type="application/json")
        print(f"OK Ecrit dans : {BUCKET}/{chemin}")

    upload_json(df_gains.to_dict(orient="records"), CHEMIN_GOLD + "gains_par_classe.json")
    upload_json(metriques, CHEMIN_GOLD + "metriques.json")


# ══════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("=" * 55)
    print("  MODELE DPE — Scikit-learn Random Forest")
    print("=" * 55)

    df                         = lire_silver()
    verifier_classes(df)
    df                         = reequilibrer_classes(df, max_par_classe=5000)
    X, y, y_par_m2, encoders   = preparer_donnees(df)
    model, metriques           = entrainer_evaluer(X, y)
    df_gains                   = simuler_gains(model, X, df)

    if not df_gains.empty:
        print("\n" + "=" * 65)
        print("  GAINS PAR TRANSITION DE CLASSE DPE")
        print("=" * 65)
        print(df_gains.to_string(index=False))

    ecrire_gold(df_gains, metriques)
    print("\nOK Pipeline ML termine !")