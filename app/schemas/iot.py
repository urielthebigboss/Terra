"""
=========================================================
TERRA — Schémas d'ingestion IoT (/api/v1/iot)

Contrat ENTRE la passerelle ESP32 (boîtier central) et le backend.
La passerelle agrège les mesures d'UN nœud (DHT22 + capacitif) et
les pousse en un seul POST toutes les 5 minutes.

Le payload est en anglais (côté firmware), le backend le NORMALISE
ensuite vers le modèle interne (JSONB sans unité, une ligne `mesure`
par capteur). Voir services/iot_service.py.

Toutes les grandeurs sont OPTIONNELLES : si un capteur est en panne
(lecture NaN), le firmware l'omet — on n'enregistre jamais de fausse
mesure, on stocke seulement ce qui est réellement mesuré.
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field


class IotIngestPayload(BaseModel):
    """Corps de POST /api/v1/iot/ingest (paquet d'un nœud)."""

    device_id: str = Field(..., description="Identifiant de la passerelle, ex. « CENTRAL_UNIT_001 »")
    sensor_node_id: str = Field(..., description="Identifiant du nœud émetteur, ex. « SENSOR_NODE_001 »")

    temperature_air: float | None = Field(None, description="Température de l'air (°C), DHT22")
    humidity_air: float | None = Field(None, description="Humidité relative de l'air (%), DHT22")
    soil_moisture: float | None = Field(None, description="Humidité du sol (%), capteur capacitif calibré")

    measured_at: datetime | None = Field(
        None, description="Horodatage de la mesure (UTC ISO-8601). Défaut : réception serveur."
    )
    sequence_number: int | None = Field(
        None, ge=0, description="Compteur incrémental du nœud — sert au diagnostic et à l'anti-doublon."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_id": "CENTRAL_UNIT_001",
                "sensor_node_id": "SENSOR_NODE_001",
                "temperature_air": 27.6,
                "humidity_air": 72.4,
                "soil_moisture": 45.8,
                "measured_at": "2026-07-23T12:00:00Z",
                "sequence_number": 15,
            }
        }
    }


class IotMesureCreee(BaseModel):
    """Une mesure effectivement écrite en base, renvoyée en accusé."""

    id: int
    id_capteur: int
    type: str
    donnees: dict
    date: datetime


class IotIngestResponse(BaseModel):
    """Accusé de réception structuré (le firmware peut le logger)."""

    status: str = Field(..., description="« ok » si au moins une mesure a été enregistrée")
    node_id: str
    id_parcelle: int
    mesures_creees: list[IotMesureCreee]
    ignorees: list[str] = Field(
        default_factory=list,
        description="Grandeurs écartées (hors bornes plausibles, doublon, ou capteur absent).",
    )
    moteur_declenche: bool = Field(
        False, description="True si le moteur expert a été relancé sur la parcelle après ingestion."
    )
