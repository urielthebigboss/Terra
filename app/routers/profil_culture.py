"""
=========================================================
TERRA — Route Profil de culture (/api/v1/profil-culture)

LECTURE SEULE : le contenu de la table est maintenu à la main
par l'administrateur (stades agronomiques de la tomate, Kc FAO,
seuils d'humidité volumétrique du sol). Le frontend s'en sert
pour afficher le cycle réel ; le futur Moteur Expert s'en
servira pour calculer les prescriptions.
=========================================================
"""

from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.config.database import get_supabase
from app.routers.auth import utilisateur_courant
from app.schemas.auth import MeResponse

router = APIRouter(prefix="/api/v1/profil-culture", tags=["Profil de culture"])


class ProfilCultureOut(BaseModel):
    """Un stade du cycle de culture (ligne de la table profil_culture)."""

    id: int
    culture: str
    stade: str
    debut_jour: int
    fin_jour: int
    kc: float | None = None
    seuil_bas: float | None = None
    seuil_cible: float | None = None
    humidite_min: float | None = None
    humidite_max: float | None = None


@router.get("", response_model=list[ProfilCultureOut], summary="Stades du cycle de culture")
def lister(
    culture: str | None = None,
    user: MeResponse = Depends(utilisateur_courant),
) -> list[ProfilCultureOut]:
    """Le référentiel agronomique, trié par jour de début de stade.
    Filtrable par culture (défaut : toutes)."""
    query = get_supabase().table("profil_culture").select("*").order("debut_jour")
    if culture:
        query = query.eq("culture", culture)
    return [ProfilCultureOut(**row) for row in query.execute().data]
