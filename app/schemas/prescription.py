"""
=========================================================
TERRA — Schémas Prescriptions (recommandations d'irrigation)

Une prescription concerne UNE parcelle. Elles sont produites
par le MOTEUR EXPERT (toutes les 5 h, à partir des capteurs,
de la météo et du profil de culture) ou saisies à la main.
États : a_faire | faite | ignoree
=========================================================
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class PrescriptionCreate(BaseModel):
    """Corps de POST /prescriptions (création manuelle par un humain
    — le moteur expert écrit, lui, directement en base)."""

    id_parcelle: int = Field(..., description="Parcelle concernée")
    action: str = Field(..., min_length=3, description="Ce qu'il faut faire")
    justification: str | None = Field(None, description="Pourquoi cette action")
    volume_eau: float = Field(0, ge=0, description="Volume d'eau en L/m²")
    priorite: str = Field("moyenne", description="haute | moyenne | basse")


class PrescriptionOut(BaseModel):
    """Une prescription exposée au frontend."""

    id: int
    id_parcelle: int
    date: date
    action: str
    justification: str | None = None
    volume_eau: float = 0
    priorite: str = "moyenne"
    etat: str = "a_faire"
    date_faite: date | None = None
    cree_le: datetime | None = None
    duree_irrigation_minutes: int | None = Field(
        None, description="Durée d'arrosage recommandée (minutes) — calculée par le moteur"
    )


