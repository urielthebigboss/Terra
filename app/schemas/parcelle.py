"""
=========================================================
TERRA — Schémas Parcelles

Une parcelle appartient à UN agriculteur (id_agriculteur).
`jour_actuel` n'est jamais stocké : le backend le CALCULE à
partir de date_plantation — c'est lui qui permet de suivre
l'évolution de la plante (stades du profil de culture).
=========================================================
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ParcelleCreate(BaseModel):
    """Corps de POST /parcelles — RÉSERVÉ à l'administrateur : c'est
    lui qui crée les parcelles et les attribue à un agriculteur."""

    nom: str = Field(..., min_length=1, description="Nom de la parcelle (ex. « Parcelle A »)")
    culture: str = Field("Tomate", description="Culture pratiquée")
    date_plantation: date = Field(..., description="Jour de plantation (suivi du cycle)")
    superficie: float | None = Field(None, gt=0, description="Superficie en hectares")
    nombre_plant: int | None = Field(None, ge=0, description="Nombre de plants sur la parcelle")
    lat: float | None = Field(None, description="Latitude (météo localisée)")
    lon: float | None = Field(None, description="Longitude")
    id_agriculteur: int = Field(..., description="Agriculteur propriétaire (attribution par l'admin)")


class ParcelleUpdate(BaseModel):
    """Corps de PATCH /parcelles/{id}.
    Un AGRICULTEUR ne peut modifier QUE date_plantation (il saisit le
    jour de plantation) ; l'ADMIN peut tout modifier, y compris
    réattribuer la parcelle (id_agriculteur)."""

    nom: str | None = None
    culture: str | None = None
    date_plantation: date | None = None
    superficie: float | None = Field(None, gt=0)
    nombre_plant: int | None = Field(None, ge=0)
    lat: float | None = None
    lon: float | None = None
    etat: str | None = Field(None, description="active | archivee")
    id_agriculteur: int | None = Field(None, description="Réattribution (admin uniquement)")


class ParcelleOut(BaseModel):
    """Une parcelle exposée au frontend, enrichie de jour_actuel
    (nombre de jours écoulés depuis la plantation)."""

    id: int
    id_agriculteur: int
    nom: str
    culture: str
    date_plantation: date
    superficie: float | None = None
    nombre_plant: int | None = None
    lat: float | None = None
    lon: float | None = None
    etat: str = "active"
    cree_le: datetime | None = None
    jour_actuel: int = Field(0, description="Jours écoulés depuis la plantation (calculé)")
    eau_utilisee: float | None = Field(
        None, description="Consommation d'eau totale (L/m²) — cumulée à chaque mission validée"
    )
    evaporation_mm: float | None = Field(
        None, description="Dernière évapotranspiration ETc calculée par le moteur expert (mm/jour)"
    )
