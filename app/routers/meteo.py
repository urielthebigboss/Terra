"""
  POST /api/v1/meteo/sync        → OpenWeather → DB (+ WebSocket)
  GET  /api/v1/meteo/actuelle    → dernière mesure stockée
  GET  /api/v1/meteo/historique  → mesures passées (graphiques)
  GET  /api/v1/meteo/previsions  → prévisions stockées
"""

from fastapi import APIRouter, HTTPException, Query

from app.config.config import get_settings
from app.schemas.meteo import MeteoMesure, MeteoPrevision, MeteoSyncResponse
from app.services import meteo_service

router = APIRouter(prefix="/api/v1/meteo", tags=["Météo"])


@router.post("/sync", response_model=MeteoSyncResponse, summary="Synchroniser depuis OpenWeather")
async def sync_meteo(
    # Coordonnées optionnelles : sans elles, on utilise la localisation
    # par défaut du .env (DEFAULT_LAT / DEFAULT_LON)
    lat: float | None = Query(None, description="Latitude (défaut : .env)"),
    lon: float | None = Query(None, description="Longitude (défaut : .env)"),
    parcelle_id: str | None = Query(None, description="Parcelle à associer à la mesure"),
) -> MeteoSyncResponse:
    """Récupère la météo actuelle + prévisions 5 jours chez OpenWeather,
    les **stocke** dans Supabase, puis **diffuse** la mesure en WebSocket.
    À appeler périodiquement (cron / bouton « Actualiser » du frontend)."""
    settings = get_settings()
    return await meteo_service.sync_meteo(
        lat=lat if lat is not None else settings.default_lat,
        lon=lon if lon is not None else settings.default_lon,
        parcelle_id=parcelle_id,
    )


@router.get("/actuelle", response_model=MeteoMesure, summary="Dernière mesure stockée")
def meteo_actuelle() -> MeteoMesure:
    """Expose la dernière mesure **depuis la base** (jamais en direct
    d'OpenWeather) — c'est le principe « on stocke, puis on expose »."""
    mesure = meteo_service.get_derniere_mesure()
    if mesure is None:
        # Base vide → il faut lancer une première synchronisation
        raise HTTPException(
            status_code=404,
            detail="Aucune mesure en base. Lancez d'abord POST /api/v1/meteo/sync.",
        )
    return mesure


@router.get("/historique", response_model=list[MeteoMesure], summary="Historique des mesures")
def meteo_historique(
    # ge/le = garde-fous : entre 1 et 500 lignes par appel
    limit: int = Query(50, ge=1, le=500, description="Nombre de mesures à retourner"),
) -> list[MeteoMesure]:
    """Mesures passées, de la plus récente à la plus ancienne
    (alimente les graphiques d'évolution du frontend)."""
    return meteo_service.get_historique_mesures(limit=limit)


@router.get("/previsions", response_model=list[MeteoPrevision], summary="Prévisions stockées")
def meteo_previsions() -> list[MeteoPrevision]:
    """Prévisions 5 jours (pas de 3 h) stockées lors du dernier sync,
    triées par échéance croissante."""
    return meteo_service.get_previsions()
