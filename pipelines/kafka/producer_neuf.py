"""
producer_neuf.py
----------------
Télécharge le dataset DPE logements NEUFS depuis l'API ADEME
et envoie chaque ligne dans le topic Kafka "open-data-neuf".

Aucun fichier n'est sauvegardé sur le disque.
Les données transitent directement en mémoire → Kafka.

Usage :
    python producer_neuf.py
    python producer_neuf.py --limite 1000    (test sur 1000 lignes)
    python producer_neuf.py --offset 5000    (reprend à partir de la ligne 5000)
"""

import os
import json
import time
import argparse
import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Configuration Kafka ────────────────────────────────────────
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9094")
TOPIC_NAME   = "open-data-neuf"         

# ── Configuration API ADEME ────────────────────────────────────
API_URL   = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe02neuf/lines"
PAGE_SIZE = 100
# ───────────────────────────────────────────────────────────────


def creer_producer() -> KafkaProducer:
    """Crée et retourne un producer Kafka."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda msg: json.dumps(msg, ensure_ascii=False).encode("utf-8"),
        acks="all",
        retries=3
    )


def compter_total_lignes() -> int:
    """Récupère le nombre total de lignes disponibles dans le dataset."""
    try:
        response = requests.get(API_URL, params={"size": 1}, timeout=10)
        response.raise_for_status()
        return response.json().get("total", 0)
    except Exception as e:
        print(f"⚠️  Impossible de compter les lignes : {e}")
        return 0


def telecharger_page(numero_page: int, taille: int) -> list:
    """
    Télécharge une page de données depuis l'API ADEME.
    Utilise le paramètre "from" (offset direct) propre à l'API Data Fair.
    """
    params = {
        "size"  : taille,
        "from"  : numero_page * taille,   # offset direct : 0, 100, 200...
        "format": "json"
    }

    try:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("results", [])

    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout page {numero_page}, nouvelle tentative...")
        time.sleep(2)
        return telecharger_page(numero_page, taille)

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API ADEME page {numero_page} : {e}")
        return []


def envoyer_page(lignes: list, producer: KafkaProducer) -> tuple:
    """Envoie une liste de lignes dans le topic Kafka."""
    envoyes = 0
    erreurs = 0

    for ligne in lignes:
        try:
            futur = producer.send(TOPIC_NAME, value=ligne)
            futur.get(timeout=10)
            envoyes += 1
        except KafkaError as e:
            erreurs += 1
            print(f"❌ Erreur Kafka : {e}")

        time.sleep(5 / 1000)

    return envoyes, erreurs


def lancer_pipeline(limite: int = None, offset_depart: int = 0):
    """Pipeline principal : API ADEME (neufs) → Kafka → topic open-data-neuf"""

    total_dispo = compter_total_lignes()
    total_cible = min(limite, total_dispo) if limite else total_dispo

    print("=" * 55)
    print("  Producer DPE NEUFS — API ADEME → Kafka")
    print("=" * 55)
    print(f"  Dataset            : DPE Logements Neufs")
    print(f"  Lignes disponibles : {total_dispo:,}")
    print(f"  Lignes à envoyer   : {total_cible:,}")
    print(f"  Départ offset      : {offset_depart:,}")
    print(f"  Topic Kafka        : {TOPIC_NAME}")
    print(f"  Pages de           : {PAGE_SIZE} lignes")
    print("=" * 55)

    producer     = creer_producer()
    total_envoye = 0
    total_erreur = 0
    offset       = offset_depart

    while total_envoye < total_cible:

        restant     = total_cible - total_envoye
        taille_page = min(PAGE_SIZE, restant)
        numero_page = offset // PAGE_SIZE

        print(f"\n📥 Page {numero_page} — offset={offset} ({taille_page} lignes)...")
        lignes = telecharger_page(numero_page, taille_page)

        if not lignes:
            print("⚠️  Page vide — fin du dataset atteinte.")
            break

        envoyes, erreurs = envoyer_page(lignes, producer)
        total_envoye    += envoyes
        total_erreur    += erreurs
        offset          += taille_page

        pct = (total_envoye / total_cible) * 100
        print(f"   ✅ {total_envoye:,}/{total_cible:,} envoyés ({pct:.1f}%)")

    producer.flush()
    producer.close()

    print("\n" + "=" * 55)
    print("  Pipeline terminé !")
    print(f"  Messages envoyés : {total_envoye:,}")
    print(f"  Erreurs          : {total_erreur:,}")
    print("=" * 55)


# ── Point d'entrée ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Producer — DPE Neufs → Kafka"
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Nombre max de lignes (défaut: tout le dataset)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Reprendre à partir de cette ligne (défaut: 0)"
    )
    args = parser.parse_args()
    lancer_pipeline(limite=args.limite, offset_depart=args.offset)