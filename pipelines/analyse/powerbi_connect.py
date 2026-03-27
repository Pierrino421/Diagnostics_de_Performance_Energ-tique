# ============================================================
#  Script Power BI — Lecture Gold depuis MinIO (toutes colonnes)
#  À coller dans : Accueil > Obtenir des données > Script Python
# ============================================================

import io
import pandas as pd
from minio import Minio

# ── Configuration MinIO ──────────────────────────────────────
MINIO_ENDPOINT = "localhost:9000"
MINIO_USER     = "admin"
MINIO_PASSWORD = "admin123"
BUCKET         = "datalake"
CHEMIN_GOLD    = "gold/details_logements/"
# ─────────────────────────────────────────────────────────────

# ── Connexion MinIO ──────────────────────────────────────────
client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_USER,
    secret_key=MINIO_PASSWORD,
    secure=False
)

# ── Lecture de tous les fichiers Parquet ─────────────────────
objets   = list(client.list_objects(BUCKET, prefix=CHEMIN_GOLD, recursive=True))
fichiers = [o.object_name for o in objets if o.object_name.endswith(".parquet")]

if not fichiers:
    raise FileNotFoundError(f"Aucun fichier Parquet trouvé dans {CHEMIN_GOLD}")

dfs = []
for fichier in fichiers:
    data = client.get_object(BUCKET, fichier).read()
    dfs.append(pd.read_parquet(io.BytesIO(data)))

df = pd.concat(dfs, ignore_index=True)

# ── Correction automatique des types ─────────────────────────
# Power BI ne supporte pas certains types numpy/pandas exotiques
# On normalise sans toucher aux valeurs ni supprimer de colonnes

for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].astype(str).replace("nan", "")
    elif str(df[col].dtype).startswith("float"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    elif str(df[col].dtype).startswith("int"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

# df est maintenant disponible dans Power BI avec toutes ses colonnes