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
    5. modele_ml            (silver/ → gold/dpe_ridge_model.joblib)
           ↓
    6. aggregation_gold     (silver/ → gold/details_logements/)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner"           : "dpe-project",
    "depends_on_past" : False,
    "retries"         : 2,
    "retry_delay"     : timedelta(minutes=3),
    "email_on_failure": False,
}

APP   = "docker exec app"
SPARK = "docker exec spark-master /opt/spark/bin/spark-submit"

SCRIPTS_KAFKA = "/app/pipelines/kafka"
SCRIPTS_SPARK = "/app/pipelines/spark"
SCRIPTS_ML    = "/app/pipelines/ml"

with DAG(
    dag_id            = "dpe_pipeline_existant",
    description       = "Pipeline DPE : Kafka → Bronze → Silver → Gold → ML",
    default_args      = default_args,
    start_date        = datetime(2026, 1, 1),
    schedule_interval = "@daily",
    catchup           = False,
    max_active_runs   = 1,
    tags              = ["dpe", "bigdata", "existant"],
) as dag:

    debut = EmptyOperator(task_id="debut_pipeline")

    # ── Tâche 1 — Création topic Kafka ───────────────────────
    creer_topics = BashOperator(
        task_id      = "creer_topics_kafka",
        bash_command = f"{APP} python {SCRIPTS_KAFKA}/create_topic.py",
        doc_md       = """
        ## Création du topic Kafka
        - Crée le topic `open-data-existant` (3 partitions)
        - Idempotent : sans effet si le topic existe déjà
        - Vérification : Kafka UI → http://localhost:8090
        """,
    )

    # ── Tâche 2 — Producer : API ADEME → Kafka ───────────────
    producer_existant = BashOperator(
        task_id      = "producer_existant",
        bash_command = (
            f"{APP} python {SCRIPTS_KAFKA}/producer_existant.py "
            "--limite 60000 --offset 1000000"
        ),
        
        execution_timeout = timedelta(minutes=60),
        doc_md            = """
        ## Producer DPE Existants
        - Source  : API ADEME `dpe03existant`
        - Topic   : `open-data-existant`
        - Limite  : 80 000 lignes — offset départ : 1 000 000
        """,
    )

    # ── Tâche 3 — Consumer : Kafka → MinIO bronze/ ───────────
    consumer_kafka = BashOperator(
        task_id      = "consumer_kafka",
        bash_command = (
            f"{APP} python {SCRIPTS_KAFKA}/consumer.py "
            "--batch-size 500"
        ),
        execution_timeout = timedelta(minutes=20),
        doc_md            = """
        ## Consumer Kafka → Bronze
        - Écoute le topic `open-data-existant`
        - Écrit par batch de 500 messages dans MinIO :
          `bronze/existant/date=YYYY-MM-DD/dpe_HHMMSS.json`
        - S'arrête automatiquement après 10s sans message
        """,
    )

    # ── Tâche 4 — Nettoyage Spark : bronze/ → silver/ ────────
    nettoyage_spark = BashOperator(
        task_id      = "nettoyage_spark",
        bash_command = f"{SPARK} {SCRIPTS_SPARK}/nettoyage.py",
        execution_timeout = timedelta(minutes=45),
        doc_md            = """
        ## Nettoyage Spark — Bronze → Silver
        1. Lecture JSON depuis `bronze/existant/`
        2. Suppression colonnes inutiles
        3. Encodage étiquettes DPE/GES
        4. Encodage ordinal isolation
        5. Imputation valeurs nulles
        6. Traitement outliers IQR
        7. Transformation logarithmique
        8. Écriture Parquet dans `silver/existant/`
        """,
    )

    # ── Tâche 5 — Modèle ML : silver/ → gold/modele ──────────
    
    modele_ml = BashOperator(
        task_id      = "modele_ml",
        bash_command = f"{APP} python {SCRIPTS_ML}/modele.py",
        execution_timeout = timedelta(minutes=30),
        doc_md            = """
        ## Modèle ML — Ridge Regression
        - Chargement depuis `silver/existant/`
        - One-Hot Encoding + StandardScaler
        - Sélection alpha optimal (CV 5 folds)
        - Sauvegarde dans `gold/dpe_ridge_model.joblib`
        """,
    )

    # ── Tâche 6 — Agrégation Gold : silver/ → gold/ ──────────
    
    aggregation_gold = BashOperator(
        task_id      = "aggregation_gold",
        bash_command = f"{SPARK} {SCRIPTS_SPARK}/aggregation_analyse.py",
        execution_timeout = timedelta(minutes=30),
        doc_md            = """
        ## Agrégation Gold — Silver → Gold
        - Toutes les colonnes Silver conservées
        - Ajout `periode_construction`
        - Ajout `conso_calculee_par_m2`
        - Écriture Parquet dans `gold/details_logements/`
        """,
    )

    fin = EmptyOperator(
        task_id      = "fin_pipeline",
        trigger_rule = TriggerRule.ALL_SUCCESS,
    )

    # ── Dépendances ───────────────────────────────────────────
    (
        debut
        >> creer_topics
        >> producer_existant
        >> consumer_kafka
        >> nettoyage_spark
        >> modele_ml          # ✅ 5e — modele en premier
        >> aggregation_gold   # ✅ 6e — aggregation en dernier
        >> fin
    )