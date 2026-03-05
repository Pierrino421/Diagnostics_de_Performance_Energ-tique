"""
create_topic.py
---------------
Crée le topic Kafka "open-data" avec ses paramètres.
À exécuter UNE SEULE FOIS avant de lancer le producer.

Usage :
    python create_topic.py
"""

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

# Connexion au broker Kafka
# Si tu exécutes ce script depuis ta machine locale → "localhost:9094"
# Si tu exécutes depuis un conteneur Docker         → "kafka:9092"
KAFKA_BROKER = "localhost:9094"
TOPIC_NAME   = "open-data"

def creer_topic():
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER)

    topic = NewTopic(
        name=TOPIC_NAME,
        num_partitions=3,       # 3 partitions = traitement parallèle possible
        replication_factor=1    # 1 seul broker en local donc 1 réplique max
    )

    try:
        admin.create_topics([topic])
        print(f"✅ Topic '{TOPIC_NAME}' créé avec succès !")
        print(f"   - Partitions        : 3")
        print(f"   - Replication factor: 1")

    except TopicAlreadyExistsError:
        print(f"⚠️  Le topic '{TOPIC_NAME}' existe déjà.")

    finally:
        admin.close()

if __name__ == "__main__":
    creer_topic()