import os
import io
import joblib
import pandas as pd
from minio import Minio

# ── 1. CONFIGURATION ───────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_USER     = os.getenv("MINIO_USER",     "admin")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD", "admin123")
BUCKET         = "datalake"
CHEMIN_MODELE  = "gold/dpe_ridge_model.joblib"

# ── 2. CHARGEMENT DU MODÈLE DEPUIS MINIO ───────────────────────
def charger_modele():
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASSWORD, secure=False)
    print(f"📥 Téléchargement du modèle depuis {BUCKET}/{CHEMIN_MODELE}...")
    
    response = client.get_object(BUCKET, CHEMIN_MODELE)
    model_data = joblib.load(io.BytesIO(response.read()))
    response.close()
    response.release_conn()
    return model_data

# ── 3. CLASSIFICATION DPE ──────────────────────────────────────
def get_classe_dpe(conso):
    if conso <= 70: return "A"
    if conso <= 110: return "B"
    if conso <= 180: return "C"
    if conso <= 250: return "D"
    if conso <= 330: return "E"
    if conso <= 420: return "F"
    return "G"

# ── 4. SCRIPT DE TEST ──────────────────────────────────────────
if __name__ == "__main__":
    # Charger les composants
    data = charger_modele()
    model = data["model"]
    scaler = data["scaler"]
    features_train = data["features_names"]

    print("\n--- Test du modèle DPE (Entrée manuelle) ---")
    
    # Saisie utilisateur (Valeurs numériques)
    hsp = float(input("Hauteur sous plafond (m) [ex: 2.5] : "))
    niveaux = float(input("Nombre de niveaux du logement [ex: 1] : "))

    # Saisie utilisateur (Valeurs catégorielles)
    # Note : Doit correspondre aux valeurs vues durant l'entraînement
    periode = input("Période construction [ex: 1975-1977, avant1948] : ")
    batiment = input("Type bâtiment [Maison, Appartement] : ")
    zone = input("Zone climatique [ex: H1a, H1b] : ")
    energie = input("Énergie principale chauffage [Électricité, Gaz naturel] : ")
    ventilation = input("Type ventilation [ex: VMC SF] : ")
    ecs = input("Énergie principale ECS [Électricité, Gaz naturel] : ")

    # Créer un dictionnaire avec les entrées
    input_dict = {
        "hauteur_sous_plafond": hsp,
        "nombre_niveau_logement": niveaux,
        "periode_construction": periode,
        "type_batiment": batiment,
        "zone_climatique": zone,
        "type_energie_principale_chauffage": energie,
        "type_ventilation": ventilation,
        "type_energie_principale_ecs": ecs
    }

    # Transformer en DataFrame
    df_input = pd.DataFrame([input_dict])

    # 1. One-Hot Encoding manuel pour correspondre au format d'entraînement
    df_ohe = pd.get_dummies(df_input)

    # 2. Aligner les colonnes : Créer un DF vide avec les colonnes d'entraînement
    X_final = pd.DataFrame(0, index=[0], columns=features_train)

    # 3. Remplir avec nos valeurs saisies
    for col in df_ohe.columns:
        if col in X_final.columns:
            X_final[col] = df_ohe[col]
    
    # 4. Scaling
    X_scaled = scaler.transform(X_final)

    # 5. Prédiction
    pred = model.predict(X_scaled)[0]
    classe = get_classe_dpe(pred)

    print("\n" + "="*40)
    print(f"📊 RÉSULTAT DE LA PRÉDICTION")
    print(f"Consommation estimée : {pred:.2f} kWh/m²/an")
    print(f"Classe DPE prédite   : {classe}")
    print("="*40)