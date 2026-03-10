"""
consumer.py
-----------
Consomme les messages des topics Kafka "open-data" et "open-data-neuf"
et les écrit dans MinIO dans la couche Bronze avec dossiers séparés :

    datalake / bronze / existant / date=YYYY-MM-DD / dpe_HHMM.json
    datalake / bronze / neuf     / date=YYYY-MM-DD / dpe_HHMM.json

Usage :
    python consumer.py                         (écoute les deux topics)
    python consumer.py --batch-size 100
"""

import os
import json
import argparse
from datetime import datetime
from io import BytesIO

from kafka import KafkaConsumer
from minio import Minio
from minio.error import S3Error

# ── Configuration ──────────────────────────────────────────────
KAFKA_BROKER   = os.getenv("KAFKA_BROKER",   "localhost:9094")
CONSUMER_GROUP = "dpe-consumer-group"

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET_NAME    = "datalake"

# Mapping topic Kafka → dossier MinIO
# Clé   : nom du topic Kafka
# Valeur : sous-dossier dans bronze/
TOPICS = {
    "open-data-existant"     : "existant",   
    "open-data-neuf": "neuf",       
}

BATCH_SIZE_DEFAULT = 200
# ───────────────────────────────────────────────────────────────


def construire_chemin_minio(sous_dossier: str) -> str:
    """
    Construit le chemin de stockage dans MinIO selon le topic source.

    Paramètres :
        sous_dossier : "existant" ou "neuf" selon le topic d'origine

    Exemples :
        → bronze/existant/date=2026-03-05/dpe_1430.json
        → bronze/neuf/date=2026-03-05/dpe_1430.json
    """
    maintenant = datetime.now()
    date_str   = maintenant.strftime("%Y-%m-%d")
    heure_str  = maintenant.strftime("%H%M%S")    # secondes incluses pour éviter les doublons

    return f"bronze/{sous_dossier}/date={date_str}/dpe_{heure_str}.json"


def ecrire_dans_minio(client_minio: Minio, messages: list, sous_dossier: str):
    """
    Écrit un batch de messages JSON dans MinIO.

    Paramètres :
        client_minio : client MinIO connecté
        messages     : liste de dict Python à sauvegarder
        sous_dossier : "existant" ou "neuf" — détermine le dossier de destination
    """
    chemin = construire_chemin_minio(sous_dossier)

    contenu_jsonl = "\n".join(json.dumps(msg, ensure_ascii=False) for msg in messages)
    contenu_bytes = contenu_jsonl.encode("utf-8")
    fichier       = BytesIO(contenu_bytes)

    try:
        client_minio.put_object(
            bucket_name=BUCKET_NAME,
            object_name=chemin,
            data=fichier,
            length=len(contenu_bytes),
            content_type="application/json"
        )
        print(f"💾 [{sous_dossier}] {len(messages)} messages → {BUCKET_NAME}/{chemin}")

    except S3Error as e:
        print(f"❌ Erreur MinIO : {e}")


def consommer(batch_size: int):
    """
    Écoute les deux topics Kafka en même temps et écrit dans MinIO.
    Chaque topic est redirigé vers son propre dossier dans bronze/.
    """

    # ── Connexion MinIO ────────────────────────────────────────
    client_minio = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False
    )
    print(f"✅ Connecté à MinIO ({MINIO_ENDPOINT})")

    # ── Connexion Kafka — abonnement aux DEUX topics ───────────
    # On passe une liste de topics à KafkaConsumer
    # Il écoute les deux en parallèle dans la même boucle
    consumer = KafkaConsumer(
        *TOPICS.keys(),                  # dépaquète le dict → "open-data", "open-data-neuf"
        bootstrap_servers=KAFKA_BROKER,
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda msg: json.loads(msg.decode("utf-8")),
        consumer_timeout_ms=10000
    )
    print(f"✅ Consumer abonné aux topics : {list(TOPICS.keys())}")
    print(f"⚙️  Écriture dans MinIO tous les {batch_size} messages")
    print("-" * 55)

    # ── Buffers séparés par topic ──────────────────────────────
    # Un buffer par topic pour ne pas mélanger les données
    # Exemple : batches = {"open-data": [...], "open-data-neuf": [...]}
    batches = {topic: [] for topic in TOPICS}
    totaux  = {topic: 0  for topic in TOPICS}

    for message in consumer:

        topic       = message.topic           # "open-data" ou "open-data-neuf"
        sous_dossier = TOPICS.get(topic, "inconnu")

        batches[topic].append(message.value)
        totaux[topic] += 1

        # Quand le batch du topic est plein → écriture dans MinIO
        if len(batches[topic]) >= batch_size:
            ecrire_dans_minio(client_minio, batches[topic], sous_dossier)
            batches[topic] = []   # Vide le buffer après écriture

    # ── Écrit les derniers batches incomplets ──────────────────
    for topic, batch in batches.items():
        if batch:
            sous_dossier = TOPICS[topic]
            print(f"📦 Dernier batch [{sous_dossier}] : {len(batch)} messages...")
            ecrire_dans_minio(client_minio, batch, sous_dossier)

    consumer.close()

    print("-" * 55)
    print(f"✅ Consommation terminée !")
    for topic, total in totaux.items():
        sous_dossier = TOPICS[topic]
        print(f"   [{sous_dossier}] : {total:,} messages traités")
    print(f"📁 Données dans MinIO : {BUCKET_NAME}/bronze/existant/ et bronze/neuf/")


# ── Point d'entrée ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consumer Kafka → MinIO Bronze")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE_DEFAULT,
        help=f"Messages par fichier MinIO (défaut: {BATCH_SIZE_DEFAULT})"
    )
    args = parser.parse_args()
    consommer(args.batch_size)