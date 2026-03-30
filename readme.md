```markdown
# Projet DPE — BigData Pipeline

Pipeline complet d'ingestion, transformation et analyse des données
de Diagnostic de Performance Énergétique (ADEME).

---

## Architecture

```
API ADEME
    ↓
[Kafka]          → Ingestion streaming
    ↓
[Bronze]         → JSON bruts dans MinIO
    ↓  Spark
[Silver]         → Parquet nettoyés dans MinIO
    ↓
[Gold]           → Parquet enrichis + modèle ML
```

---

## Structure du projet

```
PROJETBIGDATA/
├── docker-compose.yml           ← Infrastructure principale
├── docker-compose.airflow.yml   ← Services Airflow
├── Dockerfile                   ← Image Python
├── Dockerfile.spark             ← Image Spark
├── Dockerfile.airflow           ← Image Airflow + Docker CLI
├── requirements.txt
└── pipelines/
    ├── kafka/
    │   ├── create_topic.py          ← Crée les topics Kafka
    │   ├── producer_existant.py     ← API ADEME → Kafka
    │   └── consumer.py              ← Kafka → MinIO bronze/
    ├── spark/
    │   ├── nettoyage.py             ← Bronze → Silver
    │   └── aggregation_analyse.py   ← Silver → Gold
    ├── ml/
    │   └── modele.py                ← Entraînement Ridge Regression
    ├── airflow/
    │   └── dags/
    │       └── dpe_pipeline_dag.py  ← DAG orchestration
    └── analyse/
        └── dashboard.py             ← Dashboard Streamlit
```

---

## Prérequis

- Docker Desktop installé et lancé

---

## Démarrage

### 1 — Builder les images

```bash
# Image Python (app)
docker-compose build app

# Images Spark
docker compose --progress plain build --no-cache spark-master spark-worker
```

### 2 — Initialiser Airflow (une seule fois)

```bash
docker-compose -f docker-compose.yml \
               -f docker-compose.airflow.yml \
               run --rm airflow-init
```

### 3 — Lancer toute l'infrastructure

```bash
docker-compose -f docker-compose.yml \
               -f docker-compose.airflow.yml \
               up -d
```

Vérification :
```bash
docker-compose ps
```

---

## Interfaces web

| Service   | URL                    | Login           |
|-----------|------------------------|-----------------|
| Kafka UI  | http://localhost:8090  | —               |
| MinIO     | http://localhost:9001  | admin/admin123  |
| Spark UI  | http://localhost:8081  | —               |
| Airflow   | http://localhost:8082  | admin/admin     |
| Streamlit | http://localhost:8501  | —               |

---

## Pipeline manuel (étape par étape)

### Étape 1 — Créer les topics Kafka

```bash
docker-compose run --rm app python pipelines/kafka/create_topic.py
```

### Étape 2 — Télécharger les données (API ADEME → Kafka)

```bash
docker-compose run --rm app python pipelines/kafka/producer_existant.py \
  --limite 80000 --offset 1000000
```

### Étape 3 — Consommer les données (Kafka → MinIO bronze/)

```bash
docker-compose run --rm app python pipelines/kafka/consumer.py \
  --batch-size 500
```

### Étape 4 — Nettoyage Spark (bronze/ → silver/)

```bash
docker-compose exec spark-master \
  /opt/spark/bin/spark-submit /app/pipelines/spark/nettoyage.py
```

### Étape 5 — Entraîner le modèle ML (silver/ → gold/)

```bash
docker-compose run --rm app python pipelines/ml/modele.py
```

### Étape 6 — Agrégation Gold (silver/ → gold/details_logements/)

```bash
docker-compose exec spark-master \
  /opt/spark/bin/spark-submit /app/pipelines/spark/aggregation_analyse.py
```

---

## Pipeline automatique avec Airflow

Le DAG `dpe_pipeline_existant` orchestre toutes les étapes ci-dessus
automatiquement dans l'ordre.

```
Airflow UI → http://localhost:8082
  → DAGs → dpe_pipeline_existant → ▶ Trigger DAG
```

Ordre d'exécution :
```
creer_topics_kafka
      ↓
producer_existant
      ↓
consumer_kafka
      ↓
nettoyage_spark
      ↓
modele_ml
      ↓
aggregation_gold
```

---

## Résultat dans MinIO

```
datalake/
├── bronze/existant/date=YYYY-MM-DD/   ← JSON bruts
├── silver/existant/                   ← Parquet nettoyés
└── gold/
    ├── details_logements/             ← Parquet enrichis (Power BI)
    └── dpe_ridge_model.joblib         ← Modèle ML
```

---

## Arrêter l'infrastructure

```bash
# Arrêt simple (données conservées)
docker-compose -f docker-compose.yml \
               -f docker-compose.airflow.yml \
               down

# Arrêt + suppression des volumes (repart à zéro)
docker-compose -f docker-compose.yml \
               -f docker-compose.airflow.yml \
               down -v
```

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| `NoBrokersAvailable` | Attendre 30s que Kafka soit healthy |
| `container app is not running` | Démarrer avec les deux fichiers compose |
| `DAG not found` | Attendre 30s le scan du scheduler |
| `S3AFileSystem not found` | Vérifier les jars Spark : `docker-compose exec spark-master ls /opt/spark/jars/ \| grep hadoop-aws` |
| `network dpe-network not found` | Lancer `docker-compose up -d` avant airflow-init |
```