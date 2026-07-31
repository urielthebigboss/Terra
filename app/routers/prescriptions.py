"""
=========================================================
TERRA — Routes Prescriptions (/api/v1/prescriptions)
Produites par le moteur expert (toutes les 5 h) ou saisies à
la main. Valider une mission cumule l'eau utilisée sur la
parcelle et diffuse les changements en WebSocket.
=========================================================
"""

from fastapi import APIRouter, Depends, Query

from app.routers.auth import utilisateur_courant
from app.schemas.auth import MeResponse
from app.schemas.prescription import PrescriptionCreate, PrescriptionOut
from app.services import alerte_expert, prescription_service
from app.services.acces import get_parcelle_ou_404
from app.websocket.manager import manager

router = APIRouter(prefix="/api/v1/prescriptions", tags=["Prescriptions"])


@router.get("", response_model=list[PrescriptionOut], summary="Lister les prescriptions visibles")
def lister(
    id_parcelle: int | None = Query(None, description="Filtrer par parcelle"),
    etat: str | None = Query(None, description="a_faire | faite | ignoree"),
    limit: int = Query(100, ge=1, le=500),
    user: MeResponse = Depends(utilisateur_courant),
) -> list[PrescriptionOut]:
    return prescription_service.lister(user, id_parcelle=id_parcelle, etat=etat, limit=limit)


@router.post("", response_model=PrescriptionOut, status_code=201, summary="Créer une prescription (manuelle)")
async def creer(corps: PrescriptionCreate, user: MeResponse = Depends(utilisateur_courant)) -> PrescriptionOut:
    """Conseil saisi à la main (le moteur expert écrit, lui, en direct).
    Diffusée en WebSocket comme toute nouvelle prescription."""
    prescription = prescription_service.creer(user, corps)
    await manager.broadcast({"type": "prescription_update", "data": prescription.model_dump(mode="json")})
    return prescription


@router.post(
    "/{id_prescription}/faite",
    response_model=PrescriptionOut,
    summary="Valider une mission (irrigation effectuée)",
)
async def marquer_faite(id_prescription: int, user: MeResponse = Depends(utilisateur_courant)) -> PrescriptionOut:
    """etat=faite + date_faite, et le volume d'eau est CUMULÉ dans
    parcelle.eau_utilisee. La parcelle mise à jour est rediffusée en
    WebSocket : le compteur d'eau du dashboard bouge en direct."""
    prescription = prescription_service.marquer_faite(user, id_prescription)
    await manager.broadcast({"type": "prescription_update", "data": prescription.model_dump(mode="json")})
    # Le compteur d'eau de la parcelle a changé → on pousse la parcelle
    try:
        parcelle = get_parcelle_ou_404(prescription.id_parcelle)
        await manager.broadcast({"type": "parcelle_update", "data": parcelle})
        await alerte_expert.verifier_consommation(
            prescription.id_parcelle, prescription.volume_eau, parcelle.get("superficie")
        )
    except Exception:
        pass  # la diffusion est un confort, jamais bloquante
    return prescription
