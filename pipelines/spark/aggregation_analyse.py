"""
aggrégation_analyse.py
----------------------
Version "Détail" : Transfère les logements ligne par ligne vers le dossier Gold.
Garde TOUTES les colonnes du Silver + ajoute des colonnes calculées.
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

# ── Configuration ──────────────────────────────────────────────
MINIO_ENDPOINT     = "http://minio:9000"
MINIO_ACCESS       = "admin"
MINIO_SECRET       = "admin123"
CHEMIN_SILVER      = "s3a://datalake/silver/existant/"
CHEMIN_GOLD_DETAIL = "s3a://datalake/gold/details_logements/"
# ───────────────────────────────────────────────────────────────

def creer_session_spark() -> SparkSession:
    return SparkSession.builder \
        .appName("DPE-Detail-Gold") \
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

def preparer_details_gold(df: DataFrame) -> DataFrame:
    """
    Garde TOUTES les colonnes du Silver.
    Ajoute uniquement des colonnes calculées supplémentaires.
    """

    # Ajout de la colonne 'periode_construction'
    df_final = df.withColumn(
        "periode_construction",
        F.when(F.col("annee_construction") < 1975, "Avant 1975")
         .when(F.col("annee_construction").between(1975, 1989), "1975-1989")
         .when(F.col("annee_construction").between(1990, 2005), "1990-2005")
         .when(F.col("annee_construction").between(2006, 2012), "2006-2012 (RT2005)")
         .otherwise("Après 2012 (RT2012)")
    )

    # Ajout de la consommation par m² (utile pour Power BI)
    df_final = df_final.withColumn(
        "conso_calculee_par_m2",
        F.when(
            F.col("surface_habitable_logement") > 0,
            F.col("conso_5_usages_ef") / F.col("surface_habitable_logement")
        ).otherwise(None)
    )

    # ✅ On retourne TOUT le DataFrame avec les colonnes ajoutées
    # ❌ Pas de .select() → toutes les colonnes Silver sont conservées
    return df_final


if __name__ == "__main__":
    spark = creer_session_spark()
    spark.sparkContext.setLogLevel("ERROR")

    print("Chargement des données Silver...")
    df_silver = spark.read.parquet(CHEMIN_SILVER)

    print(f"Colonnes Silver : {len(df_silver.columns)}")

    print("Préparation de la table Gold (toutes colonnes)...")
    df_gold_detail = preparer_details_gold(df_silver)

    print(f"Colonnes Gold   : {len(df_gold_detail.columns)}")
    print(f"Lignes à exporter : {df_gold_detail.count():,}")

    print(f"Écriture vers {CHEMIN_GOLD_DETAIL}...")
    df_gold_detail.write.mode("overwrite").parquet(CHEMIN_GOLD_DETAIL)

    spark.stop()
    print("✅ Dossier Gold 'Détail' généré avec toutes les colonnes.")