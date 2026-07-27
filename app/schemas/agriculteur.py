"""
=========================================================
TERRA — Schémas Agriculteurs (gestion par l'administrateur)

C'est l'ADMIN qui crée les comptes agriculteurs : il fournit
nom + email + mot de passe. Le backend crée alors :
  1. le compte dans Supabase Auth (auth.users)
  2. la ligne de profil dans la table `agriculteur`
=========================================================
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AgriculteurCreate(BaseModel):
    """Corps de POST /agriculteurs — les identifiants que l'admin
    communiquera ensuite à l'agriculteur."""

    nom: str = Field(..., min_length=2, description="Nom affiché dans l'interface")
    email: str = Field(..., description="Email de connexion (compte Supabase Auth)")
    mot_de_passe: str = Field(..., min_length=6, description="Mot de passe initial (min. 6 caractères)")

    @field_validator("email")
    @classmethod
    def email_valide(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Adresse email invalide.")
        return v.strip().lower()


class AgriculteurUpdate(BaseModel):
    """Corps de PATCH /agriculteurs/{id} — tous les champs sont
    optionnels : on ne modifie que ce qui est envoyé."""

    nom: str | None = None
    mot_de_passe: str | None = Field(None, min_length=6, description="Nouveau mot de passe (réinitialisation)")


class AgriculteurOut(BaseModel):
    """Un agriculteur tel qu'exposé à l'administrateur."""

    id: int
    id_uuid: str
    nom: str
    email: str | None = None       # colonne ajoutée par db/terra_tables.sql
    cree_le: datetime | None = None
