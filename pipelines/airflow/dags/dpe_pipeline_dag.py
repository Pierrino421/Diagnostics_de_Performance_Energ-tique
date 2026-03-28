"""
dpe_pipeline_dag.py
-------------------
DAG Airflow — Orchestration complète du pipeline DPE existants

Chaîne d'exécution :
    1. creer_topics_kafka
           ↓
    2. producer_existant    (API ADEME → Kafka)
           ↓
    3. consumer_kafka       (Kafka → MinIO bronze/)
           ↓
    4. nettoyage_spark      (bronze/ → silver/)
           ↓
    5. aggregation_gold     (silver/ → gold/details_logements/)
           ↓
    6. modele_ml            (silver/ → gold/dpe_ridge_model.joblib)

Conteneurs utilisés :
    - app          → scripts Python (kafka, ml)
    - spark-master → spark-submit (nettoyage, aggregation)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

# ── Configuration par défaut ────────────────────────────────────
default_args = {
    "owner"           : "dpe-project",
    "depends_on_past" : False,
    "retries"         : 2,
    "retry_delay"     : timedelta(minutes=3),
    "email_on_failure": False,
}

# ── Commandes vers les conteneurs Docker ────────────────────────
#
#  Airflow tourne dans Docker avec accès au socket Docker.
#  → docker exec  : exécute une commande dans un conteneur qui tourne
#
#  Conteneur "app"          → scripts Python (kafka, ml)
#  Conteneur "spark-master" → spark-submit   (nettoyage, aggregation)
#
APP    = "docker exec app"
SPARK  = "docker exec spark-master /opt/spark/bin/spark-submit"

# Chemin des scripts dans les conteneurs
# (volume monté : ./pipelines → /app/pipelines)
SCRIPTS_KAFKA = "/app/pipelines/kafka"
SCRIPTS_SPARK = "/app/pipelines/spark"
SCRIPTS_ML    = "/app/pipelines/ml"

# ── DAG ─────────────────────────────────────────────────────────
with DAG(
    dag_id            = "dpe_pipeline_existant",
    description       = "Pipeline DPE : Kafka → Bronze → Silver → Gold → ML",
    default_args      = default_args,
    start_date        = datetime(2026, 1, 1),
    schedule_interval = "@daily",   # Exécution quotidienne
    catchup           = False,      # Ne pas rejouer les runs passés
    max_active_runs   = 1,          # Un seul run simultané
    tags              = ["dpe", "bigdata", "existant"],
) as dag:

    # ════════════════════════════════════════════════════════════
    #  DÉBUT
    # ════════════════════════════════════════════════════════════
    debut = EmptyOperator(
        task_id = "debut_pipeline",
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 1 — Création du topic Kafka "open-data-existant"
    # ════════════════════════════════════════════════════════════
    creer_topics = BashOperator(
        task_id      = "creer_topics_kafka",
        bash_command = f"{APP} python {SCRIPTS_KAFKA}/create_topic.py",
        doc_md       = """
        ## Création du topic Kafka
        Exécute `create_topic.py` dans le conteneur **app**.

        - Crée le topic `open-data-existant` (3 partitions)
        - Idempotent : sans effet si le topic existe déjà
        - Vérification : Kafka UI → http://localhost:8090
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 2 — Producer : API ADEME → Kafka
    # ════════════════════════════════════════════════════════════
    producer_existant = BashOperator(
        task_id      = "producer_existant",
        bash_command = (
            f"{APP} python {SCRIPTS_KAFKA}/producer_existant.py "
            "--limite 5000"
        ),
        execution_timeout = timedelta(minutes=30),
        doc_md            = """
        ## Producer DPE Existants
        Exécute `producer_existant.py` dans le conteneur **app**.

        - Source  : API ADEME `dpe03existant`
        - Topic   : `open-data-existant`
        - Limite  : 5 000 lignes par run quotidien
        - Reprise : possible via `--offset` si interrompu
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 3 — Consumer : Kafka → MinIO bronze/
    # ════════════════════════════════════════════════════════════
    consumer_kafka = BashOperator(
        task_id      = "consumer_kafka",
        bash_command = (
            f"{APP} python {SCRIPTS_KAFKA}/consumer.py "
            "--batch-size 200"
        ),
        execution_timeout = timedelta(minutes=20),
        doc_md            = """
        ## Consumer Kafka → Bronze
        Exécute `consumer.py` dans le conteneur **app**.

        - Écoute le topic `open-data-existant`
        - Écrit par batch de 200 messages dans MinIO :
          `bronze/existant/date=YYYY-MM-DD/dpe_HHMMSS.json`
        - S'arrête automatiquement après 10s sans message
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 4 — Nettoyage Spark : bronze/ → silver/
    # ════════════════════════════════════════════════════════════
    nettoyage_spark = BashOperator(
        task_id      = "nettoyage_spark",
        bash_command = f"{SPARK} {SCRIPTS_SPARK}/nettoyage.py",
        execution_timeout = timedelta(minutes=45),
        doc_md            = """
        ## Nettoyage Spark — Bronze → Silver
        Exécute `nettoyage.py` via **spark-submit** sur spark-master.

        Étapes :
        1. Lecture JSON depuis `bronze/existant/`
        2. Suppression colonnes inutiles (métadonnées, dates, textes)
        3. Encodage étiquettes DPE/GES (A→1 ... G→7)
        4. Encodage ordinal isolation (insuffisante→1 ... très bonne→4)
        5. Imputation valeurs nulles (médiane / zéro / suppression)
        6. Traitement outliers par clipping IQR
        7. Transformation logarithmique (colonnes asymétriques)
        8. Écriture Parquet dans `silver/existant/`

        Vérification : MinIO → silver/existant/part-*.parquet
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 5 — Agrégation Gold : silver/ → gold/
    # ════════════════════════════════════════════════════════════
    aggregation_gold = BashOperator(
        task_id      = "aggregation_gold",
        bash_command = f"{SPARK} {SCRIPTS_SPARK}/aggregation_analyse.py",
        execution_timeout = timedelta(minutes=30),
        doc_md            = """
        ## Agrégation Gold — Silver → Gold
        Exécute `aggregation_analyse.py` via **spark-submit** sur spark-master.

        - Toutes les colonnes Silver conservées (~168 colonnes)
        - Ajout `periode_construction` (Avant 1975 / 1975-1989 / ...)
        - Ajout `conso_calculee_par_m2` (conso_5_usages_ef / surface)
        - Écriture Parquet dans `gold/details_logements/`

        Utilisé par Power BI via `powerbi_connect.py`
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  TÂCHE 6 — Modèle ML : silver/ → gold/modele
    # ════════════════════════════════════════════════════════════
    modele_ml = BashOperator(
        task_id      = "modele_ml",
        bash_command = f"{APP} python {SCRIPTS_ML}/modele.py",
        execution_timeout = timedelta(minutes=30),
        doc_md            = """
        ## Modèle ML — Ridge Regression
        Exécute `modele.py` dans le conteneur **app**.

        - Chargement données depuis `silver/existant/`
        - Features macro : periode_construction, type_batiment,
          zone_climatique, type_energie_principale_chauffage,
          type_ventilation, type_energie_principale_ecs,
          nombre_niveau_logement, hauteur_sous_plafond
        - One-Hot Encoding + StandardScaler
        - Sélection alpha optimal (CV 5 folds)
        - Sauvegarde dans `gold/dpe_ridge_model.joblib`
        """,
    )

    # ════════════════════════════════════════════════════════════
    #  FIN
    # ════════════════════════════════════════════════════════════
    fin = EmptyOperator(
        task_id      = "fin_pipeline",
        trigger_rule = TriggerRule.ALL_SUCCESS,
    )

    # ════════════════════════════════════════════════════════════
    #  DÉPENDANCES — Chaîne linéaire
    # ════════════════════════════════════════════════════════════
    (
        debut
        >> creer_topics
        >> producer_existant
        >> consumer_kafka
        >> nettoyage_spark
        >> aggregation_gold
        >> modele_ml
        >> fin
    )