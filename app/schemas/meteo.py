"""
=========================================================
TERRA — Schémas météo (approche API-first)
Ces modèles Pydantic sont LE contrat entre le backend et le
frontend : ils définissent exactement la forme des données
échangées. La doc interactive (/docs) est générée à partir d'eux.
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MeteoMesure(BaseModel):
    """Une mesure météo « actuelle » telle que stockée puis exposée.
    C'est la ligne de la table Supabase `meteo_mesures`."""

    id: str | None = None                  # UUID généré par Supabase
    parcelle_id: str | None = None         # Parcelle concernée (optionnel)
    lat: float                             # Latitude du point de mesure
    lon: float                             # Longitude du point de mesure
    temperature: float                     # Température de l'air (°C)
    humidite: float                        # Humidité relative de l'air (%)
    pression: float | None = None          # Pression atmosphérique (hPa)
    vent_vitesse: float | None = None      # Vitesse du vent (m/s)
    vent_direction: float | None = None    # Direction du vent (degrés)
    pluie_1h: float = 0                    # Pluie tombée sur la dernière heure (mm)
    nuages: float | None = None            # Couverture nuageuse (%)
    description: str | None = None         # Ex. « ciel dégagé » (en français)
    mesure_le: datetime                    # Horodatage de la mesure (OpenWeather)


class MeteoPrevision(BaseModel):
    """Une prévision (pas de 3 h, jusqu'à 5 jours).
    C'est la ligne de la table Supabase `meteo_previsions`."""

    id: str | None = None                  # UUID généré par Supabase
    lat: float                             # Latitude du point prévu
    lon: float                             # Longitude du point prévu
    prevu_pour: datetime                   # Date/heure de validité de la prévision
    temperature: float                     # Température prévue (°C)
    humidite: float                        # Humidité prévue (%)
    pluie_3h: float = 0                    # Pluie prévue sur le créneau de 3 h (mm)
    vent_vitesse: float | None = None      # Vent prévu (m/s)
    description: str | None = None         # Résumé lisible
    recupere_le: datetime                  # Quand cette prévision a été récupérée


class MeteoSyncResponse(BaseModel):
    """Réponse du endpoint de synchronisation :
    ce qui vient d'être stocké en base."""

    mesure: MeteoMesure                              # Mesure actuelle stockée
    previsions: list[MeteoPrevision] = Field(default_factory=list)  # Prévisions stockées
    nb_previsions: int = 0                           # Compteur pratique pour le frontend
