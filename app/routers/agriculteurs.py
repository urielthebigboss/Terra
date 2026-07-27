"""
=========================================================
TERRA — Routes Agriculteurs (/api/v1/agriculteurs)
Réservées à l'ADMINISTRATEUR : c'est lui qui crée les comptes
(nom + email + mot de passe) et les communique aux agriculteurs.
=========================================================
"""

from fastapi import APIRouter, Depends

from app.routers.auth import admin_requis
from app.schemas.agriculteur import AgriculteurCreate, AgriculteurOut, AgriculteurUpdate
from app.schemas.auth import MeResponse
from app.services import agriculteur_service

router = APIRouter(prefix="/api/v1/agriculteurs", tags=["Agriculteurs (admin)"])


@router.get("", response_model=list[AgriculteurOut], summary="Lister les agriculteurs")
def lister(admin: MeResponse = Depends(admin_requis)) -> list[AgriculteurOut]:
    return agriculteur_service.lister()


@router.post("", response_model=AgriculteurOut, status_code=201, summary="Créer un agriculteur")
def creer(corps: AgriculteurCreate, admin: MeResponse = Depends(admin_requis)) -> AgriculteurOut:
    """Crée le compte Supabase Auth + le profil `agriculteur`.
    L'admin communique ensuite email + mot de passe à l'intéressé."""
    return agriculteur_service.creer(corps)


@router.get("/{id_agriculteur}", response_model=AgriculteurOut, summary="Détail d'un agriculteur")
def obtenir(id_agriculteur: int, admin: MeResponse = Depends(admin_requis)) -> AgriculteurOut:
    return agriculteur_service.obtenir(id_agriculteur)


@router.patch("/{id_agriculteur}", response_model=AgriculteurOut, summary="Modifier (nom / mot de passe)")
def modifier(
    id_agriculteur: int, corps: AgriculteurUpdate, admin: MeResponse = Depends(admin_requis)
) -> AgriculteurOut:
    return agriculteur_service.modifier(id_agriculteur, corps)


@router.delete("/{id_agriculteur}", status_code=204, summary="Supprimer un agriculteur")
def supprimer(id_agriculteur: int, admin: MeResponse = Depends(admin_requis)) -> None:
    """Supprime profil + compte Auth. Ses parcelles, capteurs, mesures
    et prescriptions partent en cascade (contrainte DB)."""
    agriculteur_service.supprimer(id_agriculteur)
