# Projet DPE — Open Data University
## Séance 1 : Mise en place du Pipeline d'Ingestion

**Architecture visée :**
```
API ADEME → Kafka (topic: open-data) → MinIO (datalake/bronze/)
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
    │   ├── create_topic.py         ← Crée le topic "open-data"
    │   ├── producer.py             ← Télécharge l'API ADEME → envoie dans Kafka
    │   └── consumer.py             ← Lit Kafka → écrit dans MinIO/bronze
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

## Étape 4 — Créer le topic Kafka

```bash
docker-compose run --rm app python pipelines/kafka/create_topic.py
```

Résultat attendu :
```
✅ Topic 'open-data' créé avec succès !
   - Partitions        : 3
   - Replication factor: 1
```

Vérification : Kafka UI → onglet **Topics** → `open-data` doit apparaître.

---

## Étape 5 — Lancer le Producer

Le producer télécharge **directement depuis l'API ADEME** sans rien sauvegarder sur le disque.
Les données transitent en mémoire → Kafka.

**Test minimal — 100 lignes (commencer par ici) :**
```bash
docker-compose run --rm app python pipelines/kafka/producer_existant.py --limite 100
docker-compose run --rm app python pipelines/kafka/producer_neuf.py --limite 100
```

Résultat attendu :
```
=======================================================
  Producer DPE — API ADEME → Kafka
=======================================================
  Lignes disponibles : 6 245 301
  Lignes à envoyer   : 100
  Départ offset      : 0
  Topic Kafka        : open-data-existant, open-data-neuf
  Pages de           : 100 lignes
=======================================================

📥 Page 0 — offset=0 (100 lignes)...
   ✅ 100/100 envoyés (100.0%)

  Messages envoyés : 100
  Erreurs          : 0
```

Vérification : Kafka UI → **Topics** → **open-data** → onglet **Messages**
→ Les messages JSON avec les données DPE doivent apparaître.

---

## Étape 6 — Lancer le Consumer

Ouvrir un **nouveau terminal** et lancer :

**Test avec batch de 50 messages :**
```bash
docker-compose run --rm app python pipelines/kafka/consumer.py --batch-size 50
```
Résultat attendu :
```
✅ Connecté à MinIO (localhost:9000)
✅ Consumer connecté au topic 'open-data'
⚙️  Écriture dans MinIO tous les 50 messages
--------------------------------------------------
💾 50 messages écrits → MinIO : datalake/bronze/date=2025-03-05/dpe_1430.json
💾 50 messages écrits → MinIO : datalake/bronze/date=2025-03-05/dpe_1431.json
--------------------------------------------------
✅ Consommation terminée ! Total : 100 messages traités
```

> 💡 Tu peux lancer le consumer **avant** le producer : il attendra les messages patiemment.

---

## Étape 7 — Vérifier dans MinIO

1. Ouvrir http://localhost:9001
2. Login : `admin` / `admin123`
3. Naviguer : **datalake** → **bronze** → **date=2025-03-05**
4. Les fichiers `.json` doivent être présents

Structure attendue dans MinIO :
```
datalake/
└── bronze/
    └── date=2025-03-05/
        ├── dpe_1430.json    ← batch 1 (50 messages)
        ├── dpe_1431.json    ← batch 2 (50 messages)
        └── dpe_1432.json    ← dernier batch
```

---

## Résumé du flux de test

```
[Terminal 1]                              [Terminal 2]
──────────────────────────────────        ──────────────────────────────
docker-compose run --rm app \             docker-compose run --rm app \
  python pipelines/kafka/producer.py \      python pipelines/kafka/consumer.py
  --limite 100                              --batch-size 50
         │                                        │
         │   100 messages JSON                    │
         ▼                                        │
   [Kafka topic]  ────────────────────────▶  MinIO
    "open-data"                           datalake/
                                          └── bronze/
                                              └── date=2025-03-05/
                                                  └── dpe_1430.json ✅
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
| `Timeout` API ADEME | Connexion lente | Normal, le script réessaie automatiquement |
| `Exited (1)` sur kafka | Erreur de config | Lancer `docker-compose logs kafka` pour voir l'erreur |
| Topic déjà existant | Relance du script | Message `⚠️ Le topic existe déjà` → normal, continuer |