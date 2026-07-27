"""
=========================================================
TERRA — Test de bout en bout du backend métier

À lancer APRÈS avoir :
  1. exécuté db/terra_tables.sql dans Supabase (SQL Editor)
  2. démarré l'API :  uvicorn app.main:app --reload

Usage (depuis Backend/, venv activé) :
  python scripts/test_flux_complet.py --email admin@... --mot-de-passe ...

Le script rejoue TOUT le scénario métier :
  admin crée un agriculteur → l'agriculteur se connecte, crée une
  parcelle (avec date de plantation) + capteurs → simulation de
  mesures et de prescriptions → il marque une prescription faite,
  signale un capteur en panne → l'admin traite l'alerte (le capteur
  redevient actif) → nettoyage complet.
=========================================================
"""

import argparse
import sys
import uuid

import httpx

API = "http://localhost:8000/api/v1"


def bandeau(titre: str) -> None:
    print(f"\n{'=' * 60}\n  {titre}\n{'=' * 60}")


def verifier(condition: bool, message: str) -> None:
    statut = "OK " if condition else "ECHEC"
    print(f"  [{statut}] {message}")
    if not condition:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test de bout en bout TERRA")
    parser.add_argument("--email", required=True, help="Email d'un compte ADMINISTRATEUR")
    parser.add_argument("--mot-de-passe", required=True, help="Mot de passe admin")
    args = parser.parse_args()

    client = httpx.Client(timeout=30)

    # ---------- 1) Connexion admin ----------
    bandeau("1. Connexion administrateur")
    r = client.post(f"{API}/auth/login", json={"email": args.email, "mot_de_passe": args.mot_de_passe})
    verifier(r.status_code == 200, f"login admin ({r.status_code})")
    verifier(r.json()["role"] == "administrateur", "rôle = administrateur")
    admin = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # ---------- 2) Admin crée un agriculteur ----------
    bandeau("2. Création d'un agriculteur (par l'admin)")
    email_agri = f"test-{uuid.uuid4().hex[:8]}@terra-test.local"
    r = client.post(
        f"{API}/agriculteurs",
        headers=admin,
        json={"nom": "Agriculteur Test", "email": email_agri, "mot_de_passe": "tomate2026"},
    )
    verifier(r.status_code == 201, f"POST /agriculteurs ({r.status_code}) {r.text[:120]}")
    id_agri = r.json()["id"]

    # ---------- 3) L'agriculteur se connecte ----------
    bandeau("3. Connexion de l'agriculteur créé")
    r = client.post(f"{API}/auth/login", json={"email": email_agri, "mot_de_passe": "tomate2026"})
    verifier(r.status_code == 200, f"login agriculteur ({r.status_code})")
    verifier(r.json()["role"] == "agriculteur", "rôle = agriculteur")
    agri = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # ---------- 4) Parcelle : créée par l'ADMIN et attribuée ----------
    bandeau("4. Création d'une parcelle par l'admin (attribution + jour_actuel)")
    r = client.post(
        f"{API}/parcelles",
        headers=admin,
        json={"nom": "Parcelle Test", "culture": "Tomate", "date_plantation": "2026-06-01",
              "superficie": 0.8, "id_agriculteur": id_agri},
    )
    verifier(r.status_code == 201, f"POST /parcelles admin ({r.status_code}) {r.text[:120]}")
    parcelle = r.json()
    verifier(parcelle["jour_actuel"] > 0, f"jour_actuel calculé = {parcelle['jour_actuel']} jours")
    id_parcelle = parcelle["id"]
    r = client.post(f"{API}/parcelles", headers=agri,
                    json={"nom": "Interdit", "date_plantation": "2026-06-01", "id_agriculteur": id_agri})
    verifier(r.status_code == 403, f"un agriculteur NE crée PAS de parcelle (403, reçu {r.status_code})")

    # ---------- 5) Capteurs réels (capacitif sol + DHT22) ----------
    bandeau("5. Déclaration des 2 capteurs réels")
    id_capteurs = []
    for nom, type_ in [
        ("Sonde capacitive du sol", "humidite_sol"),
        ("Capteur DHT22", "dht22"),
    ]:
        r = client.post(
            f"{API}/capteurs",
            headers=agri,
            json={"id_parcelle": id_parcelle, "nom": nom, "type": type_, "batterie": 90},
        )
        verifier(r.status_code == 201, f"capteur « {nom} » ({r.status_code})")
        id_capteurs.append(r.json()["id"])

    # ---------- 6) Mesures réelles (format multi-grandeurs) ----------
    bandeau("6. Envoi de mesures au format capteurs (ESP32)")
    r = client.post(f"{API}/mesures", headers=agri,
                    json={"id_capteur": id_capteurs[0], "donnees": {"humidite": 27.6}})
    verifier(r.status_code == 201, f"mesure capacitif {{humidite}} ({r.status_code})")
    r = client.post(f"{API}/mesures", headers=agri,
                    json={"id_capteur": id_capteurs[1], "donnees": {"temperature": 27.6, "humidite": 30}})
    verifier(r.status_code == 201, f"mesure DHT22 {{temperature, humidite}} ({r.status_code})")
    r = client.post(f"{API}/mesures", headers=agri,
                    json={"id_capteur": id_capteurs[0], "donnees": {"oops": True}})
    verifier(r.status_code == 422, f"payload invalide refusé (422, reçu {r.status_code})")

    # ---------- 7) Moteur expert + validation d'une mission ----------
    bandeau("7. Moteur expert (analyse réelle) puis mission validée")
    r = client.post(f"{API}/moteur-expert/executer?id_parcelle={id_parcelle}", headers=admin)
    verifier(r.status_code == 200, f"exécution du moteur ({r.status_code})")
    r = client.get(f"{API}/prescriptions?id_parcelle={id_parcelle}&etat=a_faire", headers=agri)
    verifier(r.status_code == 200, f"lecture prescriptions ({len(r.json())} à faire)")
    if r.json():
        id_prescription = r.json()[0]["id"]
        r = client.post(f"{API}/prescriptions/{id_prescription}/faite", headers=agri)
        verifier(r.status_code == 200 and r.json()["etat"] == "faite", "mission validée (eau cumulée)")

    # ---------- 8) Signalement d'un capteur ----------
    bandeau("8. Signalement d'un capteur défaillant (agriculteur)")
    r = client.post(
        f"{API}/capteurs/{id_capteurs[0]}/signaler",
        headers=agri,
        json={"texte": "Ne remonte plus de données depuis ce matin."},
    )
    verifier(r.status_code == 201, f"signalement ({r.status_code}) {r.text[:120]}")
    id_alerte = r.json()["id"]
    r = client.get(f"{API}/capteurs/{id_capteurs[0]}", headers=agri)
    verifier(r.json()["etat"] == "panne", "le capteur est passé en « panne »")

    # ---------- 9) L'admin traite l'alerte ----------
    bandeau("9. Traitement de l'alerte (admin)")
    r = client.get(f"{API}/alertes?etat=en_attente", headers=admin)
    verifier(any(a["id"] == id_alerte for a in r.json()), "l'alerte apparaît chez l'admin")
    for etat in ("en_intervention", "repare"):
        r = client.patch(f"{API}/alertes/{id_alerte}", headers=admin, json={"etat": etat})
        verifier(r.status_code == 200 and r.json()["etat"] == etat, f"alerte → {etat}")
    r = client.get(f"{API}/capteurs/{id_capteurs[0]}", headers=admin)
    verifier(r.json()["etat"] == "actif", "capteur réparé → redevenu « actif »")

    # ---------- 10) Cloisonnement des rôles ----------
    bandeau("10. Sécurité : cloisonnement des rôles")
    r = client.get(f"{API}/agriculteurs", headers=agri)
    verifier(r.status_code == 403, "un agriculteur ne liste PAS les agriculteurs (403)")
    r = client.patch(f"{API}/capteurs/{id_capteurs[1]}", headers=agri, json={"etat": "panne"})
    verifier(r.status_code == 403, "un agriculteur ne change PAS l'état d'un capteur (403)")

    # ---------- 11) Nettoyage ----------
    bandeau("11. Nettoyage (suppression de l'agriculteur de test)")
    r = client.delete(f"{API}/agriculteurs/{id_agri}", headers=admin)
    verifier(r.status_code == 204, "agriculteur supprimé (cascade : parcelle, capteurs, mesures…)")

    print("\n🎉 TOUS LES TESTS SONT PASSÉS — le backend métier est fonctionnel.\n")


if __name__ == "__main__":
    main()
