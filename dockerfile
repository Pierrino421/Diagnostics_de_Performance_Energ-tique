# ─────────────────────────────────────────────────────────────
#  Dockerfile — Conteneur Python pour le projet DPE
#  Tout le monde utilise Python 3.11.9, peu importe la machine
# ─────────────────────────────────────────────────────────────

FROM python:3.11.9-slim

WORKDIR /app

# Copie uniquement le requirements.txt d'abord
# Astuce Docker : si requirements.txt ne change pas, cette couche
# est mise en cache → pip install ne se relance pas à chaque build
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le dossier pipelines/ (kafka/, airflow/, spark/, analyse/, ml/)
COPY pipelines/ ./pipelines/

CMD ["python"]