"""
consumer.py
-----------
Consomme les messages du topic Kafka "open-data"
et les écrit dans MinIO dans la couche Bronze :
    datalake / bronze / date=YYYY-MM-DD / dpe_HHMM.json

Usage :
    python consumer.py
    python consumer.py --batch-size 100   (écrit dans MinIO tous les 100 messages)
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
# os.getenv("VAR", "valeur_par_defaut") :
#   → Dans Docker  : utilise la variable d'environnement définie dans docker-compose
#   → En local     : utilise la valeur par défaut (localhost)
# Le même script fonctionne dans les deux contextes sans modification
KAFKA_BROKER   = os.getenv("KAFKA_BROKER",   "localhost:9094")
TOPIC_NAME     = "open-data"
CONSUMER_GROUP = "dpe-consumer-group"   # Groupe de consommateurs Kafka
                                        # Permet à plusieurs consumers de se
                                        # coordonner sur les partitions

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET_NAME    = "datalake"

BATCH_SIZE_DEFAULT = 200    # Nombre de messages avant écriture dans MinIO
# ───────────────────────────────────────────────────────────────


def construire_chemin_minio() -> str:
    """
    Construit le chemin de stockage dans MinIO.
    Format : bronze/date=2025-03-05/dpe_1430.json
                                         ↑ heure et minute courantes
    """
    maintenant = datetime.now()
    date_str   = maintenant.strftime("%Y-%m-%d")      # ex: 2025-03-05
    heure_str  = maintenant.strftime("%H%M")          # ex: 1430

    return f"bronze/date={date_str}/dpe_{heure_str}.json"


def ecrire_dans_minio(client_minio: Minio, messages: list):
    """
    Écrit un batch de messages JSON dans MinIO.

    Paramètres :
        client_minio : client MinIO connecté
        messages     : liste de dict Python à sauvegarder
    """
    chemin = construire_chemin_minio()

    # Convertit la liste de messages en JSON (1 objet par ligne = JSONL)
    # Le format JSONL (JSON Lines) est standard en Data Engineering :
    # chaque ligne est un JSON valide, facile à lire ligne par ligne
    contenu_jsonl = "\n".join(json.dumps(msg, ensure_ascii=False) for msg in messages)
    contenu_bytes = contenu_jsonl.encode("utf-8")

    # BytesIO transforme les bytes en un "faux fichier" lisible par MinIO
    fichier = BytesIO(contenu_bytes)
    taille  = len(contenu_bytes)

    try:
        client_minio.put_object(
            bucket_name=BUCKET_NAME,
            object_name=chemin,
            data=fichier,
            length=taille,
            content_type="application/json"
        )
        print(f"💾 {len(messages)} messages écrits → MinIO : {BUCKET_NAME}/{chemin}")

    except S3Error as e:
        print(f"❌ Erreur MinIO : {e}")


def consommer(batch_size: int):
    """
    Écoute le topic Kafka et écrit dans MinIO par batch.

    Paramètres :
        batch_size : nombre de messages accumulés avant écriture dans MinIO
    """

    # ── Connexion MinIO ────────────────────────────────────────
    client_minio = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False            # False car on est en local (pas de HTTPS)
    )
    print(f"✅ Connecté à MinIO ({MINIO_ENDPOINT})")

    # ── Connexion Kafka Consumer ───────────────────────────────
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BROKER,
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",   # Relit depuis le début si nouveau groupe
        enable_auto_commit=True,        # Valide automatiquement la position de lecture
        value_deserializer=lambda msg: json.loads(msg.decode("utf-8")),
        consumer_timeout_ms=10000       # S'arrête si aucun message pendant 10s
    )
    print(f"✅ Consumer connecté au topic '{TOPIC_NAME}'")
    print(f"⚙️  Écriture dans MinIO tous les {batch_size} messages")
    print("-" * 50)

    # ── Lecture des messages ───────────────────────────────────
    batch    = []    # Buffer qui accumule les messages avant écriture
    total    = 0

    for message in consumer:
        batch.append(message.value)   # message.value = le dict Python désérialisé
        total += 1

        # Quand le batch est plein → on écrit dans MinIO et on vide le buffer
        if len(batch) >= batch_size:
            ecrire_dans_minio(client_minio, batch)
            batch = []

    # ── Écrit le dernier batch (souvent incomplet) ─────────────
    if batch:
        print(f"📦 Écriture du dernier batch ({len(batch)} messages)...")
        ecrire_dans_minio(client_minio, batch)

    consumer.close()

    print("-" * 50)
    print(f"✅ Consommation terminée ! Total : {total} messages traités")
    print(f"📁 Données disponibles dans MinIO : {BUCKET_NAME}/bronze/")


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