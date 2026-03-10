"""
create_topic.py
---------------
Crée les topics Kafka nécessaires au projet DPE.
À exécuter UNE SEULE FOIS avant de lancer les producers.

Topics créés :
    - open-data      → DPE logements existants (dpe03existant)
    - open-data-neuf → DPE logements neufs     (dpe02neuf)

Usage :
    python create_topic.py
"""

import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9094")

# Liste de tous les topics à créer
# Pour en ajouter un nouveau : rajouter simplement une ligne ici
TOPICS = [
    "open-data-existant",        # DPE logements existants
    "open-data-neuf",   # DPE logements neufs
]

def creer_topics():
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER)

    print("=" * 45)
    print("  Création des topics Kafka — Projet DPE")
    print("=" * 45)

    for nom_topic in TOPICS:
        topic = NewTopic(
            name=nom_topic,
            num_partitions=3,       # 3 partitions = traitement parallèle possible
            replication_factor=1    # 1 seul broker en local donc 1 réplique max
        )
        try:
            admin.create_topics([topic])
            print(f"  ✅ '{nom_topic}' créé (3 partitions, replication: 1)")

        except TopicAlreadyExistsError:
            print(f"  ⚠️  '{nom_topic}' existe déjà → ignoré")

    admin.close()
    print("=" * 45)
    print("  Terminé ! Vérifier dans Kafka UI → Topics")
    print("=" * 45)

if __name__ == "__main__":
    creer_topics()