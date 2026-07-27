"""
=========================================================
TERRA — Service Alertes

L'alerte est le lien agriculteur → administrateur pour la
maintenance du parc de capteurs. Workflow :
  en_attente → en_intervention → repare → cloture
Effet de bord volontaire : quand l'admin passe une alerte à
« repare », le capteur associé redevient « actif ».
=========================================================
"""

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.alerte import AlerteOut, AlerteUpdate
from app.schemas.auth import MeResponse
from app.services.acces import est_admin

TABLE = "alerte"


def lister(user: MeResponse, etat: str | None = None) -> list[AlerteOut]:
    """Admin → toutes les alertes ; agriculteur → celles qu'il a émises."""
    query = get_supabase().table(TABLE).select("*").order("date", desc=True)
    if not est_admin(user):
        query = query.eq("id_agriculteur", user.profil.id)
    if etat:
        query = query.eq("etat", etat)
    return [AlerteOut(**row) for row in query.execute().data]


def changer_etat(user: MeResponse, id_alerte: int, corps: AlerteUpdate) -> AlerteOut:
    """Fait avancer l'alerte dans le workflow (admin uniquement)."""
    supabase = get_supabase()

    result = supabase.table(TABLE).select("*").eq("id", id_alerte).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Alerte {id_alerte} introuvable.")
    alerte = result.data[0]

    # L'admin qui traite l'alerte est tracé dans id_administrateur
    patch = {"etat": corps.etat, "id_administrateur": user.profil.id}
    maj = supabase.table(TABLE).update(patch).eq("id", id_alerte).execute()

    # Réparé → le capteur repart en service
    if corps.etat == "repare" and alerte.get("id_capteur"):
        supabase.table("capteur").update({"etat": "actif"}).eq("id", alerte["id_capteur"]).execute()

    return AlerteOut(**maj.data[0])
