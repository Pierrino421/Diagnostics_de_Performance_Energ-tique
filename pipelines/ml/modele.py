import os
import io
import pandas as pd
import numpy as np

from minio import Minio
from sklearn.linear_model import Ridge
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib

# ── 1. CONFIGURATION ───────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
CHEMIN_SILVER  = "silver/existant/"

# ── 2. FEATURES MACRO UNIQUEMENT ───────────────────────────────
#
#  On garde seulement les 6 grandes dimensions qui influencent
#  la conso, sans entrer dans le détail des sous-types qui
#  permettent de reconstruire la formule DPE exacte.
#
FEATURES_CATEGORIELLES = [
    "periode_construction",       # avant1948 / 1948-1974 / ... / 2013-2021
    "type_batiment",              # Maison / Appartement / Immeuble
    "zone_climatique",            # H1a / H1b / H2a / H2b / H3 ...
    "type_energie_principale_chauffage",  # Gaz / Électricité / Fioul / Bois ...
    "type_ventilation",           # Naturelle / VMC SF / VMC DF ...
    "type_energie_principale_ecs",# Gaz / Électricité / ...
]

FEATURES_NUMERIQUES = [
    "nombre_niveau_logement",     # Nombre d'étages du logement
    "hauteur_sous_plafond",       # Hauteur (m)
]


# ── 3. CHARGEMENT ──────────────────────────────────────────────
def lire_silver():
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False
    )
    objets   = list(client.list_objects(BUCKET, prefix=CHEMIN_SILVER, recursive=True))
    fichiers = [o.object_name for o in objets if o.object_name.endswith(".parquet")]

    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier Parquet dans {CHEMIN_SILVER}")

    print(f" Chargement de {len(fichiers)} partitions Parquet...")
    dfs = [
        pd.read_parquet(io.BytesIO(client.get_object(BUCKET, f).read()))
        for f in fichiers
    ]
    df = pd.concat(dfs, ignore_index=True)
    print(f"   → {len(df):,} lignes | {len(df.columns)} colonnes brutes")
    return df


# ── 4. PRÉPARATION ─────────────────────────────────────────────
def preparer_donnees(df):
    # --- Target ---
    surface = df['surface_habitable_logement'].replace(0, np.nan)
    df['target_conso_m2'] = df['conso_5_usages_ef'] / surface
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=['target_conso_m2'])
    df = df[(df['target_conso_m2'] > 10) & (df['target_conso_m2'] < 2000)]

    print(f"\n Target : {len(df):,} lignes valides")
    print(f"   médiane={df['target_conso_m2'].median():.1f} | "
          f"min={df['target_conso_m2'].min():.1f} | "
          f"max={df['target_conso_m2'].max():.1f} kWh/m²/an")

    # --- Tri ---
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    y = df['target_conso_m2'].copy()

    # --- Features catégorielles ---
    cats_ok = [f for f in FEATURES_CATEGORIELLES if f in df.columns]
    nums_ok  = [f for f in FEATURES_NUMERIQUES    if f in df.columns]

    print(f"\n Features retenues :")
    print(f"   Catégorielles ({len(cats_ok)}) : {cats_ok}")
    print(f"   Numériques    ({len(nums_ok)}) : {nums_ok}")

    X_cat = df[cats_ok].copy().fillna("Inconnu")
    X_num = df[nums_ok].copy()
    for col in X_num.columns:
        X_num[col] = pd.to_numeric(X_num[col], errors='coerce')
        X_num[col] = X_num[col].fillna(X_num[col].median())

    # --- One-Hot Encoding ---
    X_ohe = pd.get_dummies(X_cat, drop_first=True, dtype=float)

    # --- Assemblage & normalisation ---
    X = pd.concat([X_num, X_ohe], axis=1)

    scaler  = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X),
        columns=X.columns,
        index=X.index
    )

    print(f"\n🔢 {len(cats_ok)} features catégorielles → {X_ohe.shape[1]} colonnes OHE")
    print(f"   Total : {X_scaled.shape[1]} colonnes en entrée du modèle")

    # --- Aperçu des modalités ---
    print(f"\n Modalités par feature :")
    for col in cats_ok:
        n = df[col].nunique()
        vals = df[col].value_counts().head(3).index.tolist()
        print(f"   {col:<45} {n:>3} modalités  ex: {vals}")

    return X_scaled, y, scaler


# ── 5. SPLIT ───────────────────────────────────────────────────
def split_aleatoire(X, y, ratio_test=0.2):
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=ratio_test, random_state=42
    )
    print(f"\n Split aléatoire 80/20 :")
    print(f"   Train : {len(X_train):,} | Test : {len(X_test):,}")
    return X_train, X_test, y_train, y_test


# ── 6. PIPELINE RIDGE ──────────────────────────────────────────
def executer_pipeline_ml(X_train, X_test, y_train, y_test):

    alphas = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
    print("\n Sélection du meilleur alpha (Ridge, CV 5 folds) :")
    print("─" * 42)
    print(f"  {'Alpha':>8}  {'R² CV moyen':>12}  {'± std':>8}")
    print("─" * 42)

    meilleur_alpha, meilleur_score = 1.0, -np.inf
    for alpha in alphas:
        scores = cross_val_score(
            Ridge(alpha=alpha), X_train, y_train,
            cv=5, scoring='r2', n_jobs=-1
        )
        flag = " ←" if scores.mean() > meilleur_score else ""
        print(f"  {alpha:>8.2f}  {scores.mean():>12.4f}  {scores.std():>8.4f}{flag}")
        if scores.mean() > meilleur_score:
            meilleur_score = scores.mean()
            meilleur_alpha = alpha

    print("─" * 42)
    print(f"  Alpha retenu : {meilleur_alpha}")

    # Entraînement final
    print(f"\n Entraînement final Ridge(α={meilleur_alpha})...")
    model = Ridge(alpha=meilleur_alpha)
    model.fit(X_train, y_train)

    y_pred_train = model.predict(X_train)
    y_pred_test  = model.predict(X_test)

    coefficients = pd.Series(
        model.coef_, index=X_train.columns
    ).sort_values(key=abs, ascending=False)

    stats = {
        "alpha"    : meilleur_alpha,
        "mae"      : float(mean_absolute_error(y_test, y_pred_test)),
        "rmse"     : float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
        "r2_train" : float(r2_score(y_train, y_pred_train)),
        "r2_test"  : float(r2_score(y_test, y_pred_test)),
    }
    return model, stats, coefficients


# ── 7. RAPPORT ─────────────────────────────────────────────────
def afficher_rapport(stats, coefficients):
    print("\n" + "=" * 62)
    print("  RAPPORT FINAL — RIDGE + ONE-HOT (features macro)")
    print("=" * 62)
    print(f"  Alpha            : {stats['alpha']}")
    print(f"  MAE              : {stats['mae']:.2f} kWh/m²/an")
    print(f"  RMSE             : {stats['rmse']:.2f} kWh/m²/an")
    print(f"  R² Train         : {stats['r2_train']:.4f}")
    print(f"  R² Test          : {stats['r2_test']:.4f}")
    gap = stats['r2_train'] - stats['r2_test']
    print(f"  Gap train/test   : {gap:.4f}")

    max_abs = coefficients.abs().max()

    print(f"\n Top 5 — AUGMENTENT la conso :")
    print("─" * 58)
    for feat, coef in coefficients[coefficients > 0].head(5).items():
        barre = "█" * int(coef / max_abs * 20)
        print(f"  {feat:<48} +{coef:5.1f}  {barre}")

    print(f"\n Top 5 — DIMINUENT la conso :")
    print("─" * 58)
    for feat, coef in coefficients[coefficients < 0].head(5).items():
        barre = "█" * int(abs(coef) / max_abs * 20)
        print(f"  {feat:<48}  {coef:5.1f}  {barre}")

    print("\n🩺 Diagnostic :")
    if stats['r2_test'] > 0.95:
        print("  🔴 R² trop élevé → réduire encore les features")
    elif gap > 0.15:
        print(f"  🟠 Overfitting (gap={gap:.3f})")
    elif stats['r2_test'] < 0.50:
        print(f"  🟡 R²={stats['r2_test']:.4f} — correct, relations non-linéaires dans les données")
    else:
        print(f"  🟢 R²={stats['r2_test']:.4f} — résultat sain et défendable")
    print("=" * 62)


# ── 8. MAIN ───────────────────────────────────────────────────
if __name__ == "__main__":
    df_raw                     = lire_silver()
    X, y, scaler               = preparer_donnees(df_raw)
    X_train, X_test, y_train, y_test = split_aleatoire(X, y)
    model, stats, coefficients = executer_pipeline_ml(
        X_train, X_test, y_train, y_test
    )
    afficher_rapport(stats, coefficients)

    # ... (après ton entraînement et tes calculs de stats)

    # ── 9. SAUVEGARDE LOCALE ET EXPORT VERS MINIO ────────────────
    print("\n Préparation du modèle pour l'export...")

    model_data = {
        "model": model,
        "scaler": scaler,
        "features_names": X.columns.tolist(),
    }

    # 1. Sauvegarde dans un buffer mémoire (BytesIO)
    buffer = io.BytesIO()
    joblib.dump(model_data, buffer)
    buffer.seek(0) # Revenir au début du fichier en mémoire

    # 2. Envoi vers le dossier GOLD de MinIO
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, 
                secret_key=MINIO_PASSWORD, secure=False)

    CHEMIN_MODELE_GOLD = "gold/dpe_ridge_model.joblib"

    client.put_object(
        BUCKET, 
        CHEMIN_MODELE_GOLD, 
        data=buffer, 
        length=len(buffer.getvalue()), 
        content_type="application/octet-stream"
    )

    print(f" Modèle sauvegardé avec succès dans : {BUCKET}/{CHEMIN_MODELE_GOLD}")