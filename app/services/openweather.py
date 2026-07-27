"""
=========================================================
TERRA — Client OpenWeather
Rôle unique : appeler l'API OpenWeather et TRADUIRE sa réponse
brute vers nos schémas internes (MeteoMesure / MeteoPrevision).
Aucun accès base de données ici — c'est le service météo
(meteo_service.py) qui orchestre « on stocke, puis on expose ».

Endpoints OpenWeather utilisés (plan gratuit) :
  - /weather   → conditions actuelles
  - /forecast  → prévisions par pas de 3 h sur 5 jours
=========================================================
"""

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config.config import get_settings
from app.schemas.meteo import MeteoMesure, MeteoPrevision


def _check_api_key() -> str:
    """Garde-fou : erreur claire si la clé OpenWeather n'est pas dans .env."""
    key = get_settings().openweather_api_key
    if not key:
        raise HTTPException(
            status_code=503,
            detail="OPENWEATHER_API_KEY manquante — ajoutez votre clé dans Backend/.env",
        )
    return key


async def _get_json(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    """Appel GET générique avec gestion d'erreurs propre :
    une panne OpenWeather devient une erreur HTTP lisible côté API."""
    try:
        response = await client.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        # Clé invalide (401), quota dépassé (429), etc.
        raise HTTPException(
            status_code=502,
            detail=f"OpenWeather a répondu {exc.response.status_code} : {exc.response.text[:200]}",
        )
    except httpx.RequestError as exc:
        # Réseau injoignable, timeout…
        raise HTTPException(status_code=504, detail=f"OpenWeather injoignable : {exc}")


async def fetch_meteo_actuelle(lat: float, lon: float) -> MeteoMesure:
    """Récupère les conditions actuelles et les mappe vers MeteoMesure."""
    settings = get_settings()
    key = _check_api_key()

    async with httpx.AsyncClient() as client:
        data = await _get_json(
            client,
            f"{settings.openweather_base_url}/weather",
            # units=metric → °C et m/s ; lang=fr → descriptions en français
            {"lat": lat, "lon": lon, "appid": key, "units": "metric", "lang": "fr"},
        )

    # --- Traduction réponse brute OpenWeather → notre contrat interne ---
    weather = (data.get("weather") or [{}])[0]
    return MeteoMesure(
        lat=lat,
        lon=lon,
        temperature=data["main"]["temp"],
        humidite=data["main"]["humidity"],
        pression=data["main"].get("pressure"),
        vent_vitesse=data.get("wind", {}).get("speed"),
        vent_direction=data.get("wind", {}).get("deg"),
        pluie_1h=data.get("rain", {}).get("1h", 0),  # absent s'il ne pleut pas
        nuages=data.get("clouds", {}).get("all"),
        description=weather.get("description"),
        icone=weather.get("icon"),
        # "dt" = horodatage Unix de la mesure côté OpenWeather
        mesure_le=datetime.fromtimestamp(data["dt"], tz=timezone.utc),
    )


async def fetch_previsions(lat: float, lon: float) -> list[MeteoPrevision]:
    """Récupère les prévisions 5 jours (pas de 3 h) et les mappe
    vers une liste de MeteoPrevision."""
    settings = get_settings()
    key = _check_api_key()

    async with httpx.AsyncClient() as client:
        data = await _get_json(
            client,
            f"{settings.openweather_base_url}/forecast",
            {"lat": lat, "lon": lon, "appid": key, "units": "metric", "lang": "fr"},
        )

    maintenant = datetime.now(tz=timezone.utc)
    previsions: list[MeteoPrevision] = []

    # Chaque élément de "list" est un créneau de 3 heures
    for item in data.get("list", []):
        weather = (item.get("weather") or [{}])[0]
        previsions.append(
            MeteoPrevision(
                lat=lat,
                lon=lon,
                prevu_pour=datetime.fromtimestamp(item["dt"], tz=timezone.utc),
                temperature=item["main"]["temp"],
                humidite=item["main"]["humidity"],
                pluie_3h=item.get("rain", {}).get("3h", 0),
                vent_vitesse=item.get("wind", {}).get("speed"),
                description=weather.get("description"),
                icone=weather.get("icon"),
                recupere_le=maintenant,
            )
        )
    return previsions
