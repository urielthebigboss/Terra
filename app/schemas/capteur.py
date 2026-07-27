"""
=========================================================
TERRA — Schémas Capteurs

Un capteur est installé sur UNE parcelle. Cycle de vie :
  - l'agriculteur SIGNALE un capteur défaillant (→ crée une Alerte)
  - l'administrateur GÈRE l'état du capteur (actif, panne, …)
États possibles : actif | hors_ligne | panne | maintenance
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

ETATS_CAPTEUR = ("actif", "hors_ligne", "panne", "maintenance")


class CapteurCreate(BaseModel):
    """Corps de POST /capteurs."""

    id_parcelle: int = Field(..., description="Parcelle sur laquelle le capteur est installé")
    nom: str = Field(..., min_length=1, description="Ex. « Sonde humidité du sol »")
    type: str = Field(..., description="humidite_sol | temperature_air | humidite_air | pluie")
    unite: str | None = Field(None, description="% | °C | mm")
    emplacement: str | None = Field(None, description="Ex. « Zone racinaire — rang 3 »")
    batterie: int | None = Field(None, ge=0, le=100, description="Charge restante en %")


class CapteurUpdate(BaseModel):
    """Corps de PATCH /capteurs/{id}. Le champ `etat` est réservé
    à l'administrateur (gestion du parc de capteurs)."""

    nom: str | None = None
    type: str | None = None
    unite: str | None = None
    emplacement: str | None = None
    batterie: int | None = Field(None, ge=0, le=100)
    etat: str | None = None

    @field_validator("etat")
    @classmethod
    def etat_valide(cls, v: str | None) -> str | None:
        if v is not None and v not in ETATS_CAPTEUR:
            raise ValueError(f"État invalide — attendu : {', '.join(ETATS_CAPTEUR)}")
        return v


class CapteurOut(BaseModel):
    """Un capteur exposé au frontend."""

    id: int
    id_parcelle: int
    nom: str
    type: str
    unite: str | None = None
    etat: str = "actif"
    batterie: int | None = None
    emplacement: str | None = None
    derniere_comm: datetime | None = None
    cree_le: datetime | None = None


class SignalementRequest(BaseModel):
    """Corps de POST /capteurs/{id}/signaler — l'agriculteur décrit
    le problème constaté ; une Alerte est créée pour l'admin."""

    texte: str = Field(..., min_length=3, description="Description du problème constaté")
