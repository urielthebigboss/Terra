"""
=========================================================
TERRA — Schémas Mesures (capteurs réels)

Une mesure est envoyée par UN capteur physique (ESP32 → HTTP,
toutes les 5 heures). Le champ `donnees` porte une ou plusieurs
GRANDEURS numériques — jamais d'unité (l'affichage des unités
est le rôle de l'interface) :

  Capteur capacitif du sol (type « humidite_sol ») :
      { "humidite": 27.6 }
  Capteur DHT22 (type « dht22 ») — DEUX valeurs par envoi :
      { "temperature": 27.6, "humidite": 30 }
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MesureCreate(BaseModel):
    """Corps de POST /mesures — le contrat des capteurs IoT
    (validé selon le type du capteur, cf. mesure_service)."""

    id_capteur: int = Field(..., description="Capteur émetteur")
    donnees: dict = Field(
        ...,
        description='Grandeurs numériques : {"humidite": 27.6} ou {"temperature": 27.6, "humidite": 30}',
    )
    date: datetime | None = Field(None, description="Horodatage (défaut : maintenant)")


class MesureOut(BaseModel):
    """Une mesure exposée au frontend (graphiques, dashboard)."""

    id: int
    id_capteur: int
    date: datetime
    donnees: dict
