# Projet DPE — Open Data University
## Séance 1 : Mise en place du Pipeline d'Ingestion

**Architecture visée :**
```
API ADEME ──┬── Kafka (open-data)      ──┐
            │                            ├─→ MinIO (datalake/bronze/)
            └── Kafka (open-data-neuf) ──┘
```

---

## Prérequis

- Docker Desktop installé et lancé

> 💡 Pas besoin d'installer Python sur ta machine, tout tourne dans Docker.

---

## Structure du projet

```
PROJETBIGDATA/
├── docker-compose.yml              ← Infrastructure (Kafka + MinIO + App)
├── Dockerfile                      ← Environnement Python 3.11.9
├── requirements.txt                ← Dépendances Python
├── readme.md
├── datalake/                       ← Données locales (si besoin)
└── pipelines/
    ├── kafka/
    │   ├── create_topic.py         ← Crée les topics "open-data" et "open-data-neuf"
    │   ├── producer.py             ← Dataset existants (dpe03existant) → Kafka
    │   ├── producer_neuf.py        ← Dataset neufs (dpe02neuf) → Kafka
    │   └── consumer.py             ← Lit les deux topics → MinIO/bronze
    ├── airflow/                    ← Orchestration (séances suivantes)
    ├── spark/                      ← Traitement des données (séances suivantes)
    ├── analyse/                    ← Data analyse (séances suivantes)
    └── ml/                         ← Machine learning (séances suivantes)
```

---

## Étape 1 — Vérifier les prérequis

```bash
docker --version
docker-compose --version
```

---

## Étape 2 — Lancer l'infrastructure

```bash
docker-compose up -d
```

Attendre ~30 secondes, puis vérifier :

```bash
docker-compose ps
```

Résultat attendu :
```
NAME         STATUS
kafka        Up (healthy)    ← doit être "healthy", pas juste "Up"
kafka-ui     Up
minio        Up (healthy)
minio-init   Exited (0)      ← normal, il s'arrête après avoir créé le bucket
```

> ⚠️ Si kafka affiche Up sans (healthy), attendre encore 30s et relancer docker-compose ps.

**Interfaces web accessibles :**
| Service  | URL                   | Login          |
|----------|-----------------------|----------------|
| Kafka UI | http://localhost:8090 | aucun          |
| MinIO    | http://localhost:9001 | admin/admin123 |

---

## Étape 3 — Builder le conteneur Python

```bash
docker-compose build app
```

Résultat attendu :
```
 => [app] FROM python:3.11.9-slim
 => [app] pip install -r requirements.txt
 => [app] FINISHED
```

> 💡 À relancer uniquement si tu modifies `requirements.txt`. Sinon Docker utilise le cache.

---

## Étape 4 — Créer les topics Kafka

```bash
docker-compose run --rm app python pipelines/kafka/create_topic.py
```

Résultat attendu :
```
=============================================
  Création des topics Kafka — Projet DPE
=============================================
  ✅ 'open-data'      créé (3 partitions, replication: 1)
  ✅ 'open-data-neuf' créé (3 partitions, replication: 1)
=============================================
```

Vérification : Kafka UI → onglet **Topics** → les deux topics doivent apparaître.

---

## Étape 5 — Lancer les Producers

Les producers téléchargent **directement depuis l'API ADEME** sans rien sauvegarder sur le disque.

### Dataset logements existants (dpe03existant)

**Test minimal — 100 lignes :**
```bash
docker-compose run --rm app python pipelines/kafka/producer.py --limite 100
```

**Test intermédiaire — 1000 lignes :**
```bash
docker-compose run --rm app python pipelines/kafka/producer.py --limite 1000
```

**Reprendre si interrompu à la ligne 5000 :**
```bash
docker-compose run --rm app python pipelines/kafka/producer.py --offset 5000 --limite 1000
```

**Envoi complet (~14 millions de lignes) :**
```bash
docker-compose run --rm app python pipelines/kafka/producer.py
```

---

### Dataset logements neufs (dpe02neuf)

**Test minimal — 100 lignes :**
```bash
docker-compose run --rm app python pipelines/kafka/producer_neuf.py --limite 100
```

**Test intermédiaire — 1000 lignes :**
```bash
docker-compose run --rm app python pipelines/kafka/producer_neuf.py --limite 1000
```

**Reprendre si interrompu à la ligne 5000 :**
```bash
docker-compose run --rm app python pipelines/kafka/producer_neuf.py --offset 5000 --limite 1000
```

**Envoi complet :**
```bash
docker-compose run --rm app python pipelines/kafka/producer_neuf.py
```

Résultat attendu (même format pour les deux) :
```
=======================================================
  Producer DPE — API ADEME → Kafka
=======================================================
  Lignes disponibles : 14,220,911
  Lignes à envoyer   : 100
  Départ offset      : 0
  Topic Kafka        : open-data
  Pages de           : 100 lignes
=======================================================

📥 Page 0 — offset=0 (100 lignes)...
   ✅ 100/100 envoyés (100.0%)

  Messages envoyés : 100
  Erreurs          : 0
```

Vérification : Kafka UI → **Topics** → **open-data** ou **open-data-neuf** → onglet **Messages**.

---

## Étape 6 — Lancer le Consumer

Le consumer écoute **les deux topics en même temps** et redirige chaque dataset
vers son propre dossier dans MinIO.

Ouvrir un **nouveau terminal** et lancer :

**Test avec batch de 50 messages :**
```bash
docker-compose run --rm app python pipelines/kafka/consumer.py --batch-size 50
```

**Lancement normal (batch de 200 messages par défaut) :**
```bash
docker-compose run --rm app python pipelines/kafka/consumer.py
```

Résultat attendu :
```
✅ Connecté à MinIO (minio:9000)
✅ Consumer abonné aux topics : ['open-data', 'open-data-neuf']
⚙️  Écriture dans MinIO tous les 50 messages
-------------------------------------------------------
💾 [existant] 50 messages → datalake/bronze/existant/date=2026-03-05/dpe_130100.json
💾 [neuf]     50 messages → datalake/bronze/neuf/date=2026-03-05/dpe_130101.json
-------------------------------------------------------
✅ Consommation terminée !
   [existant] : 100 messages traités
   [neuf]     : 100 messages traités
📁 Données dans MinIO : datalake/bronze/existant/ et bronze/neuf/
```

> 💡 Tu peux lancer le consumer **avant** les producers : il attendra les messages patiemment.

---

## Étape 7 — Vérifier dans MinIO

1. Ouvrir http://localhost:9001
2. Login : `admin` / `admin123`
3. Naviguer : **datalake** → **bronze**

Structure attendue dans MinIO :
```
datalake/
└── bronze/
    ├── existant/
    │   └── date=2026-03-05/
    │       ├── dpe_130100.json    ← batch 1 logements existants
    │       ├── dpe_130101.json    ← batch 2
    │       └── ...
    └── neuf/
        └── date=2026-03-05/
            ├── dpe_130100.json    ← batch 1 logements neufs
            ├── dpe_130101.json    ← batch 2
            └── ...
```

---

## Résumé du flux complet

```
[Terminal 1]                          [Terminal 2]
──────────────────────────────────    ─────────────────────────────────────
producer.py --limite 100         ───▶ [Kafka: open-data]      ──┐
                                                                  ├─▶ consumer.py
producer_neuf.py --limite 100    ───▶ [Kafka: open-data-neuf] ──┘       │
                                                                          ▼
                                                                    MinIO datalake/
                                                                    ├── bronze/existant/
                                                                    └── bronze/neuf/
```

---

## Arrêter l'infrastructure

```bash
docker-compose down       # Arrête les conteneurs (données MinIO conservées)
docker-compose down -v    # Arrête ET supprime les volumes (repart à zéro)
```

---

## Problèmes fréquents

| Problème | Cause | Solution |
|----------|-------|----------|
| `NoBrokersAvailable` | Kafka pas encore prêt | Attendre 30s, vérifier `docker-compose ps` |
| `Bucket not found` | `minio-init` a échoué | Créer le bucket manuellement dans la console MinIO |
| `400 Bad Request` API ADEME | Mauvais paramètre de pagination | Vérifier que `"from"` est utilisé à la place de `"page"` |
| `Timeout` API ADEME | Connexion lente | Normal, le script réessaie automatiquement |
| `Exited (1)` sur kafka | Erreur de config | Lancer `docker-compose logs kafka` pour voir l'erreur |
| Topic déjà existant | Relance du script | Message `⚠️ Le topic existe déjà` → normal, continuer |

---

## Historique des séances

| Séance | Objectif | Statut |
|--------|----------|--------|
| Séance 1 | Pipeline ingestion : API ADEME → Kafka → MinIO Bronze | ✅ Terminé |
| Séance 2 | Traitement Spark : Bronze → Silver | 🔜 À venir |
| Séance 3 | Orchestration Airflow | 🔜 À venir |
| Séance 4 | Analyse & ML | 🔜 À venir |

---

## Étape 8 — Nettoyage des données (Bronze → Silver)

Le nettoyage est effectué par **Apache Spark** qui lit les données brutes JSON depuis `bronze/existant/` et écrit les données nettoyées en Parquet dans `silver/existant/`.

### Prérequis — Builder l'image Spark

```bash
# À faire une seule fois (ou si Dockerfile.spark est modifié)
docker compose --progress plain build --no-cache spark-master spark-worker
```

### Lancer le nettoyage

```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit /app/pipelines/spark/nettoyage.py
```

Résultat attendu :
```
  NETTOYAGE DPE EXISTANTS — Bronze -> Silver
=======================================================
 Lecture depuis : s3a://datalake/bronze/existant/
OK 44,941 lignes chargées — 188 colonnes
OK Colonnes supprimées : 23 — Restantes : 165
OK Etiquettes DPE/GES encodées en numérique
OK Isolation encodée en ordinal
OK Lignes critiques supprimées : 0
OK Valeurs nulles imputées
OK Outliers traités par clipping IQR
OK Transformation logarithmique appliquée

  RAPPORT APRES NETTOYAGE
=======================================================
  Lignes finales    : 44,941
  Colonnes finales  : 168

  Distribution par classe DPE :
  +-------------+-------+
  |etiquette_dpe| count |
  +-------------+-------+
  |           B |  2846 |
  |           C | 23484 |
  |           D |  8806 |
  |           E |  5586 |
  |           F |  4219 |
  +-------------+-------+

 Ecriture dans : s3a://datalake/silver/existant/
OK Donnees ecrites en Parquet dans MinIO/silver/existant/
OK Pipeline terminé !
```

Vérification dans MinIO : **http://localhost:9001** → `datalake` → `silver` → `existant`

Structure attendue :
```
datalake/
└── silver/
    └── existant/
        ├── part-00000.parquet
        ├── part-00001.parquet
        └── ...
```

> ⚠️ Si `S3AFileSystem not found` → vérifier que les jars sont bien présents :
> ```bash
> docker-compose exec spark-master ls /opt/spark/jars/ | grep -E "hadoop-aws|aws-java"
> ```

---

## Étape 9 — Entraînement du modèle ML (Silver → Gold)

Le modèle Random Forest est entraîné par **Scikit-learn** sur les données nettoyées de `silver/existant/` pour répondre à la question :

> *"Combien gagne-t-on sur ses factures d'électricité en passant d'une classe DPE à une autre ?"*

### Lancer l'entraînement

```bash
docker-compose run --rm app python pipelines/ml/modele.py
```

Résultat attendu :
```
=======================================================
  MODELE DPE — Scikit-learn Random Forest
=======================================================
 8 fichiers Parquet trouvés dans silver/existant/
OK 44,941 lignes chargées — 188 colonnes

  Distribution des classes DPE :
  Classe B :  2,846 (  6.3%) ###
  Classe C : 23,484 ( 52.3%) ##########################
  Classe D :  8,806 ( 19.6%) #########
  Classe E :  5,586 ( 12.4%) ######
  Classe F :  4,219 (  9.4%) ####

 Reequilibrage (max 5,000 par classe) :
  Total : 44,941 -> 22,065 logements

 1er entrainement (toutes les features)...
 2eme entrainement (features importantes seulement)...

  METRIQUES DU MODELE FINAL
==================================================
  MAE  : X kWh/m²/an
  RMSE : X kWh/m²/an
  R2   : X.XXXX
==================================================

  GAINS PAR TRANSITION DE CLASSE DPE
=================================================================
  F->E : XX kWh/m²/an → X,XXX kWh/an = X,XXX euros/an
  E->D : XX kWh/m²/an → X,XXX kWh/an = X,XXX euros/an
  D->C : XX kWh/m²/an → X,XXX kWh/an = X,XXX euros/an
  C->B : XX kWh/m²/an → X,XXX kWh/an = X,XXX euros/an
  F->B : XX kWh/m²/an → X,XXX kWh/an = X,XXX euros/an

OK Ecrit dans : datalake/gold/gains_par_classe.json
OK Ecrit dans : datalake/gold/metriques.json
OK Pipeline ML terminé !
```

Vérification dans MinIO : **http://localhost:9001** → `datalake` → `gold`

Structure attendue :
```
datalake/
└── gold/
    ├── gains_par_classe.json   ← gains kWh/an et €/an par transition
    └── metriques.json          ← MAE, RMSE, R² du modèle
```

---

## Flux complet du pipeline (toutes étapes)

```
API ADEME (dpe03existant)
        ↓
[Étape 4] create_topic.py     → crée les topics Kafka
        ↓
[Étape 5] producer.py         → télécharge l'API → Kafka (open-data)
        ↓
[Étape 6] consumer.py         → Kafka → MinIO/bronze/existant/
        ↓
[Étape 8] nettoyage.py        → Spark : bronze/ → silver/ (Parquet)
        ↓
[Étape 9] modele.py           → Scikit-learn : silver/ → gold/ (résultats)
```

---

## Interfaces web

| Service    | URL                    | Login           | Utilité                        |
|------------|------------------------|-----------------|-------------------------------|
| Kafka UI   | http://localhost:8090  | aucun           | Visualiser les topics/messages |
| MinIO      | http://localhost:9001  | admin/admin123  | Visualiser bronze/silver/gold  |
| Spark UI   | http://localhost:8081  | aucun           | Surveiller les jobs Spark      |

---
