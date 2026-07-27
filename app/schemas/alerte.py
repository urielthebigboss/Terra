"""
=========================================================
TERRA — Schémas Alertes

Une alerte naît quand un agriculteur SIGNALE un capteur
défaillant. L'administrateur la fait ensuite avancer :
  en_attente → en_intervention → repare → cloture
Quand l'admin passe l'alerte à « repare », le capteur associé
redevient automatiquement « actif ».
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

ETATS_ALERTE = ("en_attente", "en_intervention", "repare", "cloture")


class AlerteOut(BaseModel):
    """Une alerte exposée au frontend (admin ou agriculteur)."""

    id: int
    date: datetime | None = None
    texte: str | None = None
    etat: str = "en_attente"
    id_capteur: int | None = None
    id_agriculteur: int | None = None
    id_administrateur: int | None = None   # admin qui a pris en charge


class AlerteUpdate(BaseModel):
    """Corps de PATCH /alertes/{id} — réservé à l'administrateur."""

    etat: str = Field(..., description=" | ".join(ETATS_ALERTE))

    @field_validator("etat")
    @classmethod
    def etat_valide(cls, v: str) -> str:
        if v not in ETATS_ALERTE:
            raise ValueError(f"État invalide — attendu : {', '.join(ETATS_ALERTE)}")
        return v
