"""
nettoyage.py
------------
Version Spark du notebook de nettoyage DPE existants.
Lit depuis MinIO/bronze/existant/ → nettoie → écrit dans MinIO/silver/existant/

Chaque étape est une fonction indépendante (modulaire).

Usage :
    /opt/spark/bin/spark-submit /app/pipelines/spark/nettoyage.py
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType

# ── Configuration ──────────────────────────────────────────────
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS   = "admin"
MINIO_SECRET   = "admin123"
CHEMIN_BRONZE  = "s3a://datalake/bronze/existant/"
CHEMIN_SILVER  = "s3a://datalake/silver/existant/"
# ───────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════
#  ETAPE 0 — Session Spark
# ══════════════════════════════════════════════════════════════

def creer_session_spark() -> SparkSession:
    """Cree une session Spark connectee a MinIO via S3A."""
    spark = SparkSession.builder \
        .appName("DPE-Nettoyage-Existant") \
        .config("spark.hadoop.fs.s3a.endpoint",          MINIO_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.access.key",        MINIO_ACCESS) \
        .config("spark.hadoop.fs.s3a.secret.key",        MINIO_SECRET) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


# ══════════════════════════════════════════════════════════════
#  ETAPE 1 — Chargement depuis MinIO/bronze
# ══════════════════════════════════════════════════════════════

def lire_bronze(spark: SparkSession) -> DataFrame:
    """Lit tous les fichiers JSON depuis MinIO/bronze/existant/"""
    print(f"\n Lecture depuis : {CHEMIN_BRONZE}")
    df = spark.read.json(CHEMIN_BRONZE)
    print(f"OK {df.count():,} lignes — {len(df.columns)} colonnes")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 2 — Suppression des colonnes inutiles
# ══════════════════════════════════════════════════════════════

def supprimer_colonnes_inutiles(df: DataFrame) -> DataFrame:
    """
    Supprime les colonnes qui n'apportent rien au projet :
    - Metadonnees internes ADEME (_id, _i, _rand...)
    - Dates (pas utiles pour le ML)
    - Colonnes texte libres (adresses, noms...)
    """

    cols_meta = [
        "_id", "_i", "_rand", "_score",
        "numero_dpe", "statut_geocodage",
        "adresse_complete_brut", "version_dpe",
        "methode_application_dpe", "modele_dpe",
        "code_postal_brut"
    ]

    cols_dates = [
        "date_etablissement_dpe", "date_reception_dpe",
        "date_fin_validite_dpe", "date_derniere_modification_dpe",
        "date_visite_diagnostiqueur"
    ]

    cols_texte = [
        "numero_voie_ban", "provenance_id_rnb", "adresse_ban",
        "id_rnb", "adresse_brut", "nom_rue_ban", "nom_residence",
        "complement_adresse_batiment", "complement_adresse_logement",
        "numero_dpe_immeuble_associe", "nom_commune_ban", "nom_commune_brut"
    ]

    toutes = cols_meta + cols_dates + cols_texte
    a_supprimer = [c for c in toutes if c in df.columns]
    df = df.drop(*a_supprimer)

    print(f"OK Colonnes supprimees : {len(a_supprimer)} — Restantes : {len(df.columns)}")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 3 — Encodage des etiquettes DPE/GES en numerique
# ══════════════════════════════════════════════════════════════

def encoder_etiquettes(df: DataFrame) -> DataFrame:
    """
    Transforme les etiquettes DPE/GES (A->G) en valeurs numeriques (1->7).
    A=1 (meilleure classe) -> G=7 (moins bonne classe)
    """
    mapping = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}

    expr_dpe = F.lit(None).cast(IntegerType())
    expr_ges = F.lit(None).cast(IntegerType())

    for lettre, chiffre in mapping.items():
        expr_dpe = F.when(F.col("etiquette_dpe") == lettre, chiffre).otherwise(expr_dpe)
        expr_ges = F.when(F.col("etiquette_ges") == lettre, chiffre).otherwise(expr_ges)

    df = df.withColumn("etiquette_dpe_num", expr_dpe)
    df = df.withColumn("etiquette_ges_num", expr_ges)

    print("OK Etiquettes DPE/GES encodees en numerique")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 4 — Encodage ordinal de l'isolation
# ══════════════════════════════════════════════════════════════

def encoder_isolation(df: DataFrame) -> DataFrame:
    """
    Transforme les qualites d'isolation en valeurs ordinales.
    insuffisante=1, moyenne=2, bonne=3, tres bonne=4
    """
    mapping_iso = {
        "insuffisante": 1,
        "moyenne":      2,
        "bonne":        3,
        "tres bonne":   4,
        "très bonne":   4,
    }

    cols_iso = [
        "qualite_isolation_menuiseries",
        "qualite_isolation_enveloppe",
        "qualite_isolation_murs",
        "qualite_isolation_plancher_bas",
    ]

    for col_iso in cols_iso:
        if col_iso not in df.columns:
            continue
        new_col = col_iso + "_num"
        expr = F.lit(0).cast(IntegerType())
        for texte, valeur in mapping_iso.items():
            expr = F.when(F.lower(F.col(col_iso)) == texte, valeur).otherwise(expr)
        df = df.withColumn(new_col, expr)

    print("OK Isolation encodee en ordinal")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 5 — Imputation des valeurs nulles
# ══════════════════════════════════════════════════════════════

def imputer_nulls(df: DataFrame) -> DataFrame:
    """
    Remplace les valeurs nulles :
    - Colonnes critiques nulles   -> suppression de la ligne
    - Usages absents              -> 0
    - Booleens                    -> 0
    - Colonnes numeriques         -> mediane
    """

    # Suppression des lignes critiques
    nb_avant = df.count()
    df = df.dropna(subset=["etiquette_dpe", "conso_5_usages_ef",
                            "surface_habitable_logement", "cout_total_5_usages"])
    print(f"OK Lignes critiques supprimees : {nb_avant - df.count():,}")

    # Usages potentiellement absents -> 0
    cols_zero = [
        "conso_refroidissement_ef", "conso_refroidissement_ep",
        "cout_refroidissement", "emission_ges_refroidissement",
        "production_electricite_pv_kwhep_par_an",
        "conso_5_usages_ef_energie_n2", "conso_ecs_ef_energie_n2",
        "conso_chauffage_ef_energie_n2", "cout_total_5_usages_energie_n2",
        "emission_ges_5_usages_energie_n2",
    ]
    for col in cols_zero:
        if col in df.columns:
            df = df.withColumn(col, F.coalesce(F.col(col).cast(FloatType()), F.lit(0.0)))

    # Booleens -> 0/1
    cols_bool = [
        "presence_brasseur_air", "logement_traversant",
        "inertie_lourde", "presence_production_pv",
        "appartement_non_visite"
    ]
    for col in cols_bool:
        if col in df.columns:
            df = df.withColumn(
                col,
                F.when(F.col(col) == True, 1)
                .when(F.col(col) == False, 0)
                .otherwise(0).cast(IntegerType())
            )

    # Colonnes numeriques -> mediane via approxQuantile
    cols_numeriques = [
        "score_ban", "surface_habitable_immeuble", "annee_construction",
        "nombre_niveau_logement", "nombre_niveau_immeuble",
        "nombre_appartement", "hauteur_sous_plafond", "ubat_w_par_m2_k",
        "numero_etage_appartement", "conso_auxiliaires_ep", "conso_auxiliaires_ef",
        "cout_eclairage", "cout_chauffage", "cout_ecs",
        "conso_5_usages_par_m2_ep", "conso_5_usages_par_m2_ef",
        "conso_ecs_ef_energie_n1", "conso_chauffage_ef_energie_n1",
        "emission_ges_chauffage", "emission_ges_eclairage",
        "emission_ges_ecs", "emission_ges_5_usages_par_m2",
        "besoin_chauffage", "besoin_ecs", "deperditions_totales_logement",
        "deperditions_murs", "deperditions_enveloppe",
    ]
    for col in cols_numeriques:
        if col not in df.columns:
            continue
        try:
            mediane = df.approxQuantile(col, [0.5], 0.01)[0]
            df = df.withColumn(
                col,
                F.coalesce(F.col(col).cast(FloatType()), F.lit(float(mediane)))
            )
        except Exception:
            pass

    print("OK Valeurs nulles imputees")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 6 — Traitement des outliers par IQR (clipping)
# ══════════════════════════════════════════════════════════════

def traiter_outliers(df: DataFrame) -> DataFrame:
    """
    Plafonne les valeurs extremes par les bornes IQR.
    Borne basse = Q1 - 1.5 * IQR
    Borne haute = Q3 + 1.5 * IQR
    """
    cols_outliers = [
        "surface_habitable_immeuble", "surface_habitable_logement",
        "hauteur_sous_plafond", "nombre_appartement", "nombre_niveau_immeuble",
    ]

    for col in cols_outliers:
        if col not in df.columns:
            continue
        q1, q3 = df.approxQuantile(col, [0.25, 0.75], 0.01)
        iqr     = q3 - q1
        lower   = q1 - 1.5 * iqr
        upper   = q3 + 1.5 * iqr
        df = df.withColumn(
            col,
            F.when(F.col(col) < lower, lower)
            .when(F.col(col) > upper, upper)
            .otherwise(F.col(col)).cast(FloatType())
        )

    print("OK Outliers traites par clipping IQR")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 7 — Transformation logarithmique
# ══════════════════════════════════════════════════════════════

def transformer_log(df: DataFrame) -> DataFrame:
    """
    Applique log1p sur les colonnes tres asymetriques.
    log1p(x) = log(1+x), fonctionne meme pour x=0.
    Reduit l'ecart entre les petites et grandes valeurs.
    """
    cols_log = [
        "conso_chauffage_ef_energie_n2",
        "conso_ecs_ef_energie_n2",
        "cout_total_5_usages_energie_n2",
        "conso_5_usages_ef_energie_n2",
    ]
    for col in cols_log:
        if col in df.columns:
            df = df.withColumn(col, F.log1p(F.col(col).cast(FloatType())))

    print("OK Transformation logarithmique appliquee")
    return df


# ══════════════════════════════════════════════════════════════
#  ETAPE 8 — Rapport final
# ══════════════════════════════════════════════════════════════

def afficher_rapport(df: DataFrame):
    """Affiche un resume des donnees apres nettoyage."""
    print("\n" + "=" * 55)
    print("  RAPPORT APRES NETTOYAGE")
    print("=" * 55)
    print(f"  Lignes finales    : {df.count():,}")
    print(f"  Colonnes finales  : {len(df.columns)}")
    print("\n  Distribution par classe DPE :")
    df.groupBy("etiquette_dpe").count().orderBy("etiquette_dpe").show()
    print("=" * 55)


# ══════════════════════════════════════════════════════════════
#  ETAPE 9 — Ecriture dans MinIO/silver
# ══════════════════════════════════════════════════════════════

def ecrire_silver(df: DataFrame):
    """Ecrit les donnees nettoyees en Parquet dans MinIO/silver/existant/"""
    print(f"\n Ecriture dans : {CHEMIN_SILVER}")
    df.write.mode("overwrite").parquet(CHEMIN_SILVER)
    print("OK Donnees ecrites en Parquet dans MinIO/silver/existant/")


# ══════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("=" * 55)
    print("  NETTOYAGE DPE EXISTANTS — Bronze -> Silver")
    print("=" * 55)

    spark = creer_session_spark()

    df = lire_bronze(spark)
    df = supprimer_colonnes_inutiles(df)
    df = encoder_etiquettes(df)
    df = encoder_isolation(df)
    df = imputer_nulls(df)
    df = traiter_outliers(df)
    df = transformer_log(df)
    afficher_rapport(df)
    ecrire_silver(df)

    spark.stop()
    print("\nOK Pipeline termine !")