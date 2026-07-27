"""
=========================================================
TERRA — Routes Capteurs (/api/v1/capteurs)
  - l'agriculteur consulte ses capteurs et SIGNALE les défaillants
  - l'administrateur gère l'état du parc (PATCH etat, DELETE)
=========================================================
"""

from fastapi import APIRouter, Depends, Query

from app.routers.auth import utilisateur_courant
from app.schemas.alerte import AlerteOut
from app.schemas.auth import MeResponse
from app.schemas.capteur import CapteurCreate, CapteurOut, CapteurUpdate, SignalementRequest
from app.services import capteur_service
from app.websocket.manager import manager

router = APIRouter(prefix="/api/v1/capteurs", tags=["Capteurs"])


@router.get("", response_model=list[CapteurOut], summary="Lister les capteurs visibles")
def lister(
    id_parcelle: int | None = Query(None, description="Filtrer par parcelle"),
    user: MeResponse = Depends(utilisateur_courant),
) -> list[CapteurOut]:
    return capteur_service.lister(user, id_parcelle=id_parcelle)


@router.post("", response_model=CapteurOut, status_code=201, summary="Déclarer un capteur")
async def creer(corps: CapteurCreate, user: MeResponse = Depends(utilisateur_courant)) -> CapteurOut:
    """Déclare un capteur installé sur une parcelle (admin ou
    propriétaire de la parcelle). Diffusé en WebSocket."""
    capteur = capteur_service.creer(user, corps)
    await manager.broadcast({"type": "capteur_update", "data": capteur.model_dump(mode="json")})
    return capteur


@router.get("/{id_capteur}", response_model=CapteurOut, summary="Détail d'un capteur")
def obtenir(id_capteur: int, user: MeResponse = Depends(utilisateur_courant)) -> CapteurOut:
    return capteur_service.obtenir(user, id_capteur)


@router.patch("/{id_capteur}", response_model=CapteurOut, summary="Modifier un capteur (état : admin)")
async def modifier(
    id_capteur: int, corps: CapteurUpdate, user: MeResponse = Depends(utilisateur_courant)
) -> CapteurOut:
    """Le changement d'ÉTAT (actif, panne, hors_ligne, maintenance)
    est réservé à l'administrateur. Diffusé en WebSocket : le tableau
    de bord de l'agriculteur voit l'état changer sans recharger."""
    capteur = capteur_service.modifier(user, id_capteur, corps)
    await manager.broadcast({"type": "capteur_update", "data": capteur.model_dump(mode="json")})
    return capteur


@router.delete("/{id_capteur}", status_code=204, summary="Retirer un capteur (admin)")
async def supprimer(id_capteur: int, user: MeResponse = Depends(utilisateur_courant)) -> None:
    capteur_service.supprimer(user, id_capteur)
    await manager.broadcast({"type": "capteur_delete", "data": {"id": id_capteur}})


@router.post(
    "/{id_capteur}/signaler",
    response_model=AlerteOut,
    status_code=201,
    summary="Signaler un capteur défaillant",
)
async def signaler(
    id_capteur: int, corps: SignalementRequest, user: MeResponse = Depends(utilisateur_courant)
) -> AlerteOut:
    """Cas d'usage clé de l'agriculteur : le capteur passe en « panne »
    et une ALERTE est créée pour l'administrateur (diffusée aussi en
    WebSocket pour l'affichage temps réel)."""
    alerte = capteur_service.signaler(user, id_capteur, corps)
    await manager.broadcast({"type": "alerte_update", "data": alerte.model_dump(mode="json")})
    # Le capteur vient de passer en « panne » : les dashboards doivent le voir
    capteur = capteur_service.obtenir(user, id_capteur)
    await manager.broadcast({"type": "capteur_update", "data": capteur.model_dump(mode="json")})
    return alerte
