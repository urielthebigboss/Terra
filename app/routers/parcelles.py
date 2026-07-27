"""
=========================================================
TERRA — Routes Parcelles (/api/v1/parcelles)
L'agriculteur gère SES parcelles ; l'admin voit tout.
Chaque parcelle est renvoyée avec `jour_actuel` (jours depuis
la plantation) — la clé du suivi du cycle de la plante.
=========================================================
"""

from fastapi import APIRouter, Depends, Query

from app.routers.auth import utilisateur_courant
from app.schemas.auth import MeResponse
from app.schemas.parcelle import ParcelleCreate, ParcelleOut, ParcelleUpdate
from app.services import parcelle_service
from app.websocket.manager import manager

router = APIRouter(prefix="/api/v1/parcelles", tags=["Parcelles"])


@router.get("", response_model=list[ParcelleOut], summary="Mes parcelles (ou toutes pour l'admin)")
def lister(
    id_agriculteur: int | None = Query(None, description="Filtre admin : parcelles d'un agriculteur"),
    user: MeResponse = Depends(utilisateur_courant),
) -> list[ParcelleOut]:
    return parcelle_service.lister(user, id_agriculteur=id_agriculteur)


@router.post("", response_model=ParcelleOut, status_code=201, summary="Créer une parcelle (admin)")
async def creer(corps: ParcelleCreate, user: MeResponse = Depends(utilisateur_courant)) -> ParcelleOut:
    """RÉSERVÉ à l'administrateur : il crée la parcelle et l'ATTRIBUE
    à un agriculteur (`id_agriculteur`). La date de plantation démarre
    le suivi du cycle. Diffusée en WebSocket (type parcelle_update)."""
    parcelle = parcelle_service.creer(user, corps)
    await manager.broadcast({"type": "parcelle_update", "data": parcelle.model_dump(mode="json")})
    return parcelle


@router.get("/{id_parcelle}", response_model=ParcelleOut, summary="Détail d'une parcelle")
def obtenir(id_parcelle: int, user: MeResponse = Depends(utilisateur_courant)) -> ParcelleOut:
    return parcelle_service.obtenir(user, id_parcelle)


@router.patch("/{id_parcelle}", response_model=ParcelleOut, summary="Modifier une parcelle")
async def modifier(
    id_parcelle: int, corps: ParcelleUpdate, user: MeResponse = Depends(utilisateur_courant)
) -> ParcelleOut:
    """L'agriculteur propriétaire ne modifie QUE la date de plantation ;
    l'admin modifie tout (y compris la réattribution id_agriculteur)."""
    parcelle = parcelle_service.modifier(user, id_parcelle, corps)
    await manager.broadcast({"type": "parcelle_update", "data": parcelle.model_dump(mode="json")})
    return parcelle


@router.delete("/{id_parcelle}", status_code=204, summary="Supprimer une parcelle (admin)")
async def supprimer(id_parcelle: int, user: MeResponse = Depends(utilisateur_courant)) -> None:
    """Administrateur uniquement — supprime aussi capteurs, mesures
    et prescriptions (cascade DB)."""
    parcelle_service.supprimer(user, id_parcelle)
    await manager.broadcast({"type": "parcelle_delete", "data": {"id": id_parcelle}})
