"""
producer.py
-----------
Télécharge le dataset DPE directement depuis l'API ADEME
et envoie chaque ligne dans le topic Kafka "open-data".

Aucun fichier n'est sauvegardé sur le disque.
Les données transitent directement en mémoire → Kafka.

Usage :
    python producer.py
    python producer.py --limite 1000    (test sur 1000 lignes)
    python producer.py --offset 5000    (reprend à partir de la ligne 5000)
"""

import os
import json
import time
import argparse
import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Configuration Kafka ────────────────────────────────────────
# os.getenv("KAFKA_BROKER", "localhost:9094") signifie :
#   → Si la variable KAFKA_BROKER existe (définie dans Docker) : on l'utilise
#   → Sinon on utilise "localhost:9094" (exécution locale)
# Le même script fonctionne ainsi dans les deux contextes
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9094")
TOPIC_NAME   = "open-data-existant"
DELAI_MS     = 5                # Délai entre messages (ms)

# ── Configuration API ADEME ────────────────────────────────────
# L'API ADEME (OpenDataSoft) permet de télécharger les données
# par pages via des paramètres :
#   - size   : nombre de lignes par page (max recommandé : 100)
#   - page   : numéro de page (commence à 0)
#   - format : json
API_URL   = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"
PAGE_SIZE = 100     # Lignes par requête — on pagine pour ne pas surcharger la mémoire
# ───────────────────────────────────────────────────────────────


def creer_producer() -> KafkaProducer:
    """Crée et retourne un producer Kafka."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda msg: json.dumps(msg, ensure_ascii=False).encode("utf-8"),
        acks="all",   # Attend confirmation de Kafka avant de continuer
        retries=3     # Réessaie 3 fois en cas d'erreur réseau
    )


def compter_total_lignes() -> int:
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

    Paramètres :
        numero_page : index de la page (0 = première page)
        taille      : nombre de lignes à récupérer

    Retourne :
        Liste de dicts — chaque dict = une ligne du dataset DPE
    """
    params = {
        "size"  : taille,
        "from"  : numero_page*taille,  # from = offset = page * taille
        "format": "json"
    }

    try:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get("results", [])

    except requests.exceptions.Timeout:
        # En cas de timeout, on attend 2 secondes et on réessaie une fois
        print(f"⚠️  Timeout page {numero_page}, nouvelle tentative...")
        time.sleep(2)
        return telecharger_page(numero_page, taille)

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API ADEME page {numero_page} : {e}")
        return []


def envoyer_page(lignes: list, producer: KafkaProducer) -> tuple:
    """
    Envoie une liste de lignes dans le topic Kafka.

    Retourne :
        (nb_envoyes, nb_erreurs) — tuple pour suivre la progression
    """
    envoyes = 0
    erreurs = 0

    for ligne in lignes:
        try:
            # send() est non-bloquant → get() attend la confirmation du broker
            futur = producer.send(TOPIC_NAME, value=ligne)
            futur.get(timeout=10)
            envoyes += 1
        except KafkaError as e:
            erreurs += 1
            print(f"❌ Erreur Kafka : {e}")

        time.sleep(DELAI_MS / 1000)   # Simule un flux progressif

    return envoyes, erreurs


def lancer_pipeline(limite: int = None, offset_depart: int = 0):
    """
    Pipeline principal : API ADEME → page par page → Kafka

    On pagine les requêtes pour deux raisons :
    1. L'API ADEME limite à 100 lignes par requête
    2. Charger 6 millions de lignes d'un coup ferait crasher la mémoire

    Paramètres :
        limite        : nombre max de lignes à envoyer (None = tout le dataset)
        offset_depart : reprendre à cette ligne si le script a été interrompu
    """
    total_dispo = compter_total_lignes()
    total_cible = min(limite, total_dispo) if limite else total_dispo

    print("=" * 55)
    print("  Producer DPE — API ADEME → Kafka")
    print("=" * 55)
    print(f"  Lignes disponibles : {total_dispo:,}")
    print(f"  Lignes à envoyer   : {total_cible:,}")
    print(f"  Départ offset      : {offset_depart:,}")
    print(f"  Topic Kafka        : {TOPIC_NAME}")
    print(f"  Pages de           : {PAGE_SIZE} lignes")
    print("=" * 55)

    producer      = creer_producer()
    total_envoye  = 0
    total_erreur  = 0
    offset        = offset_depart

    while total_envoye < total_cible:

        # Calcule la taille de la page courante
        # (la dernière page peut être plus petite que PAGE_SIZE)
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

    producer.flush()   # Vide le buffer interne avant de fermer
    producer.close()

    print("\n" + "=" * 55)
    print("  Pipeline terminé !")
    print(f"  Messages envoyés : {total_envoye:,}")
    print(f"  Erreurs          : {total_erreur:,}")
    print("=" * 55)


# ── Point d'entrée ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Producer — Télécharge l'API ADEME et envoie dans Kafka"
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