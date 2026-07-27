"""
=========================================================
TERRA — Contrôle d'accès aux ressources métier

Règle unique du projet :
  - l'ADMINISTRATEUR voit et gère tout ;
  - l'AGRICULTEUR ne voit que SES parcelles (et donc ses
    capteurs, mesures, prescriptions, alertes).

Ces helpers sont appelés par tous les services : ils chargent
la ressource et vérifient que l'utilisateur connecté a le
droit d'y toucher (sinon 404 / 403).
=========================================================
"""

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.auth import MeResponse


def est_admin(user: MeResponse) -> bool:
    return user.role == "administrateur"


def get_parcelle_ou_404(id_parcelle: int) -> dict:
    """Charge une parcelle ; 404 si elle n'existe pas."""
    result = get_supabase().table("parcelle").select("*").eq("id", id_parcelle).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Parcelle {id_parcelle} introuvable.")
    return result.data[0]


def verifier_acces_parcelle(user: MeResponse, parcelle: dict) -> None:
    """403 si un agriculteur tente d'accéder à la parcelle d'un autre."""
    if est_admin(user):
        return
    if parcelle["id_agriculteur"] != user.profil.id:
        raise HTTPException(status_code=403, detail="Cette parcelle ne vous appartient pas.")


def get_capteur_ou_404(id_capteur: int) -> dict:
    """Charge un capteur ; 404 s'il n'existe pas."""
    result = get_supabase().table("capteur").select("*").eq("id", id_capteur).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Capteur {id_capteur} introuvable.")
    return result.data[0]


def verifier_acces_capteur(user: MeResponse, capteur: dict) -> dict:
    """Vérifie l'accès au capteur VIA sa parcelle.
    Retourne la parcelle (souvent utile à l'appelant)."""
    parcelle = get_parcelle_ou_404(capteur["id_parcelle"])
    verifier_acces_parcelle(user, parcelle)
    return parcelle


def ids_parcelles_de(user: MeResponse) -> list[int]:
    """Liste des ids de parcelles visibles par l'utilisateur.
    Admin → toutes ; agriculteur → les siennes."""
    query = get_supabase().table("parcelle").select("id")
    if not est_admin(user):
        query = query.eq("id_agriculteur", user.profil.id)
    return [row["id"] for row in query.execute().data]
