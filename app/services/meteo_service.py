"""
=========================================================
TERRA — Service météo (logique « on stocke, puis on expose »)
Orchestration :
  1. SYNC   : OpenWeather → Supabase (+ diffusion WebSocket)
  2. EXPOSE : Supabase → API (le frontend ne parle JAMAIS
              directement à OpenWeather)

Tables Supabase attendues (déjà conçues côté DB) :
  - meteo_mesures     : conditions actuelles horodatées
  - meteo_previsions  : prévisions 5 jours / pas de 3 h
(le SQL de référence est fourni dans db/meteo_tables.sql —
 adaptez les noms ci-dessous si votre schéma diffère)
=========================================================
"""

from app.config.database import get_supabase
from app.schemas.meteo import MeteoMesure, MeteoPrevision, MeteoSyncResponse
from app.services import openweather
from app.websocket.manager import manager

# Noms des tables — un seul endroit à modifier si le schéma DB diffère
TABLE_MESURES = "meteo_mesures"
TABLE_PREVISIONS = "meteo_previsions"


# ---------------------------------------------------------
# 1) SYNCHRONISATION : OpenWeather → Supabase → WebSocket
# ---------------------------------------------------------
async def sync_meteo(lat: float, lon: float, parcelle_id: str | None = None) -> MeteoSyncResponse:
    """Récupère la météo actuelle + les prévisions chez OpenWeather,
    les STOCKE dans Supabase, puis diffuse la mesure aux clients
    WebSocket connectés. Retourne ce qui a été stocké."""
    supabase = get_supabase()

    # --- Récupération chez OpenWeather (2 appels) ---
    mesure = await openweather.fetch_meteo_actuelle(lat, lon)
    mesure.parcelle_id = parcelle_id
    previsions = await openweather.fetch_previsions(lat, lon)

    # --- Stockage de la mesure actuelle ---
    # mode="json" convertit les datetime en chaînes ISO (format attendu par Supabase)
    # exclude={"id"} : l'UUID est généré par la base, pas par nous
    row = mesure.model_dump(mode="json", exclude={"id"})
    inserted = supabase.table(TABLE_MESURES).insert(row).execute()
    if inserted.data:
        mesure.id = inserted.data[0].get("id")

    # --- Stockage des prévisions ---
    # On remplace les anciennes prévisions du même point : elles sont
    # périmées dès qu'un nouveau lot arrive (pas d'intérêt historique).
    supabase.table(TABLE_PREVISIONS).delete().eq("lat", lat).eq("lon", lon).execute()
    rows = [p.model_dump(mode="json", exclude={"id"}) for p in previsions]
    if rows:
        supabase.table(TABLE_PREVISIONS).insert(rows).execute()

    # --- Diffusion temps réel : les dashboards se mettent à jour seuls ---
    await manager.broadcast({"type": "meteo_update", "data": mesure.model_dump(mode="json")})

    return MeteoSyncResponse(mesure=mesure, previsions=previsions, nb_previsions=len(previsions))


# ---------------------------------------------------------
# 2) EXPOSITION : Supabase → API (lecture seule)
# ---------------------------------------------------------
def get_derniere_mesure() -> MeteoMesure | None:
    """Dernière mesure stockée (celle qu'affiche le dashboard)."""
    result = (
        get_supabase()
        .table(TABLE_MESURES)
        .select("*")
        .order("mesure_le", desc=True)  # la plus récente d'abord
        .limit(1)
        .execute()
    )
    return MeteoMesure(**result.data[0]) if result.data else None


def get_historique_mesures(limit: int = 50) -> list[MeteoMesure]:
    """Historique des mesures (pour les graphiques d'évolution)."""
    result = (
        get_supabase()
        .table(TABLE_MESURES)
        .select("*")
        .order("mesure_le", desc=True)
        .limit(limit)
        .execute()
    )
    return [MeteoMesure(**row) for row in result.data]


def get_previsions() -> list[MeteoPrevision]:
    """Prévisions stockées, triées par échéance croissante
    (le frontend affiche les prochains créneaux)."""
    result = (
        get_supabase()
        .table(TABLE_PREVISIONS)
        .select("*")
        .order("prevu_pour", desc=False)
        .execute()
    )
    return [MeteoPrevision(**row) for row in result.data]
