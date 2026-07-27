"""
=========================================================
TERRA — Route du MOTEUR EXPERT (/api/v1/moteur-expert)

Le moteur tourne automatiquement toutes les 10 h (planificateur
de main.py). Cette route permet de le DÉCLENCHER À LA DEMANDE
(bouton « Lancer l'analyse » côté admin / démo de soutenance)
et d'INSPECTER le calcul d'évapotranspiration d'une parcelle
sans rien écrire en base (transparence de l'algorithme).

Réservé à l'administrateur : c'est un traitement global qui
recalcule les prescriptions de toutes les parcelles.
=========================================================
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config.config import get_settings
from app.config.database import get_supabase
from app.routers.auth import admin_requis
from app.schemas.auth import MeResponse
from app.services import moteur_expert
from app.services.acces import get_parcelle_ou_404

router = APIRouter(prefix="/api/v1/moteur-expert", tags=["Moteur expert"])


class ExecutionResponse(BaseModel):
    """Bilan d'un passage du moteur."""

    parcelles_analysees: int
    prescriptions_creees: int
    details: list[dict]


class DiagnosticResponse(BaseModel):
    """Détail du calcul pour UNE parcelle, sans écriture en base :
    permet de montrer/vérifier le raisonnement du moteur."""

    parcelle: str
    jour_culture: int
    stade: str | None
    kc: float | None
    humidite_sol: float | None
    temperature_air: float | None
    humidite_air: float | None
    seuil_bas: float | None
    seuil_cible: float | None
    et0_mm_jour: float | None
    etc_mm_jour: float | None
    pluie_prevue_mm: float | None
    meteo_disponible: bool


@router.post("/executer", response_model=ExecutionResponse, summary="Lancer l'analyse (admin)")
async def executer(
    id_parcelle: int | None = Query(None, description="Limiter à une parcelle (défaut : toutes)"),
    admin: MeResponse = Depends(admin_requis),
) -> ExecutionResponse:
    """Exécute le moteur maintenant. Les prescriptions générées sont
    diffusées en WebSocket (les dashboards ouverts se mettent à jour)."""
    ids = [id_parcelle] if id_parcelle is not None else None
    bilan = await moteur_expert.executer(ids_parcelles=ids)
    return ExecutionResponse(**bilan)


@router.get("/diagnostic/{id_parcelle}", response_model=DiagnosticResponse,
            summary="Voir le calcul d'une parcelle (sans écrire)")
def diagnostic(id_parcelle: int, admin: MeResponse = Depends(admin_requis)) -> DiagnosticResponse:
    """Renvoie les grandeurs intermédiaires (ET0, ETc, humidité, seuils)
    pour cette parcelle — utile pour expliquer/déboguer le moteur."""
    sb = get_supabase()
    settings = get_settings()
    parcelle = get_parcelle_ou_404(id_parcelle)

    profils = sb.table("profil_culture").select("*").order("debut_jour").execute().data
    meteo = moteur_expert._meteo_24h(sb)

    date_plantation = datetime.fromisoformat(str(parcelle["date_plantation"])).date()
    jour_culture = (datetime.now(timezone.utc).date() - date_plantation).days + 1
    stade = moteur_expert._stade_courant(profils, jour_culture)
    capteurs = moteur_expert._mesures_capteurs(sb, id_parcelle)

    kc = (stade or {}).get("kc") or 1.0
    lat = parcelle.get("lat") or settings.default_lat
    jour_julien = datetime.now(timezone.utc).timetuple().tm_yday
    if meteo["disponible"]:
        tmoy, tmin, tmax = meteo["tmoy"], meteo["tmin"], meteo["tmax"]
    else:
        t = moteur_expert._temperature_actuelle(sb) or 28.0
        tmoy, tmin, tmax = t, t - 4, t + 4
    et0 = moteur_expert.et0_hargreaves(tmoy, tmin, tmax, lat, jour_julien) if stade else None
    etc = round(et0 * kc, 1) if et0 is not None else None

    return DiagnosticResponse(
        parcelle=parcelle["nom"],
        jour_culture=jour_culture,
        stade=(stade or {}).get("stade"),
        kc=kc if stade else None,
        humidite_sol=capteurs["humidite_sol"],
        temperature_air=capteurs["temperature"],
        humidite_air=capteurs["humidite_air"],
        seuil_bas=(stade or {}).get("seuil_bas"),
        seuil_cible=(stade or {}).get("seuil_cible"),
        et0_mm_jour=et0,
        etc_mm_jour=etc,
        pluie_prevue_mm=meteo["pluie_mm"],
        meteo_disponible=meteo["disponible"],
    )
