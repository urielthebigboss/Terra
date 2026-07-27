"""
=========================================================
TERRA — Service Capteurs

Répartition des rôles (cahier des charges) :
  - l'AGRICULTEUR consulte ses capteurs et SIGNALE ceux qui
    ne fonctionnent pas (→ crée une Alerte pour l'admin) ;
  - l'ADMINISTRATEUR gère l'ÉTAT des capteurs (actif, panne,
    hors_ligne, maintenance) et le parc en général.
=========================================================
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.auth import MeResponse
from app.schemas.capteur import CapteurCreate, CapteurOut, CapteurUpdate, SignalementRequest
from app.schemas.alerte import AlerteOut
from app.services.acces import (
    est_admin,
    get_capteur_ou_404,
    get_parcelle_ou_404,
    ids_parcelles_de,
    verifier_acces_capteur,
    verifier_acces_parcelle,
)

TABLE = "capteur"


def lister(user: MeResponse, id_parcelle: int | None = None) -> list[CapteurOut]:
    """Capteurs visibles par l'utilisateur, filtrables par parcelle."""
    if id_parcelle is not None:
        parcelle = get_parcelle_ou_404(id_parcelle)
        verifier_acces_parcelle(user, parcelle)
        rows = get_supabase().table(TABLE).select("*").eq("id_parcelle", id_parcelle).order("id").execute().data
    else:
        visibles = ids_parcelles_de(user)
        if not visibles:
            return []
        rows = get_supabase().table(TABLE).select("*").in_("id_parcelle", visibles).order("id").execute().data
    return [CapteurOut(**row) for row in rows]


def obtenir(user: MeResponse, id_capteur: int) -> CapteurOut:
    capteur = get_capteur_ou_404(id_capteur)
    verifier_acces_capteur(user, capteur)
    return CapteurOut(**capteur)


def creer(user: MeResponse, corps: CapteurCreate) -> CapteurOut:
    """Déclare un capteur sur une parcelle (admin ou propriétaire)."""
    parcelle = get_parcelle_ou_404(corps.id_parcelle)
    verifier_acces_parcelle(user, parcelle)

    result = get_supabase().table(TABLE).insert(corps.model_dump()).execute()
    return CapteurOut(**result.data[0])


def modifier(user: MeResponse, id_capteur: int, corps: CapteurUpdate) -> CapteurOut:
    """Met à jour un capteur. Le changement d'ÉTAT est réservé à
    l'admin — l'agriculteur passe par /signaler."""
    capteur = get_capteur_ou_404(id_capteur)
    verifier_acces_capteur(user, capteur)

    if corps.etat is not None and not est_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur change l'état d'un capteur — utilisez /signaler pour remonter un problème.",
        )

    patch = corps.model_dump(exclude_none=True)
    if not patch:
        return CapteurOut(**capteur)

    result = get_supabase().table(TABLE).update(patch).eq("id", id_capteur).execute()
    return CapteurOut(**result.data[0])


def supprimer(user: MeResponse, id_capteur: int) -> None:
    """Retire un capteur du parc (admin uniquement)."""
    if not est_admin(user):
        raise HTTPException(status_code=403, detail="Seul l'administrateur retire un capteur du parc.")
    get_capteur_ou_404(id_capteur)
    get_supabase().table(TABLE).delete().eq("id", id_capteur).execute()


def signaler(user: MeResponse, id_capteur: int, corps: SignalementRequest) -> AlerteOut:
    """L'agriculteur signale un capteur défaillant :
      1. le capteur passe en « panne » (visible immédiatement)
      2. une Alerte « en_attente » est créée pour l'administrateur
    """
    capteur = get_capteur_ou_404(id_capteur)
    verifier_acces_capteur(user, capteur)
    supabase = get_supabase()

    supabase.table(TABLE).update({"etat": "panne"}).eq("id", id_capteur).execute()

    alerte = {
        "date": datetime.now(timezone.utc).isoformat(),
        "texte": f"[{capteur['nom']}] {corps.texte}",
        "etat": "en_attente",
        "id_capteur": id_capteur,
        "id_agriculteur": user.profil.id if user.role == "agriculteur" else None,
    }
    result = supabase.table("alerte").insert(alerte).execute()
    return AlerteOut(**result.data[0])
