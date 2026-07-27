"""
=========================================================
TERRA — Schémas d'authentification (API-first)
Contrats d'entrée/sortie des routes /api/v1/auth.

Principe : l'authentification est déléguée à Supabase Auth
(table auth.users). Le RÔLE, lui, vient de nos tables métier :
  - administrateur (id, id_uuid → auth.users.id, nom)
  - agriculteur    (id, id_uuid → auth.users.id, nom)
Un compte Supabase sans ligne dans l'une de ces tables
n'a pas accès à TERRA.
=========================================================
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Corps attendu par POST /auth/login : les identifiants
    que l'administrateur a communiqués à l'utilisateur."""

    email: str = Field(..., description="Email du compte Supabase")
    mot_de_passe: str = Field(..., min_length=1, description="Mot de passe")


class RefreshRequest(BaseModel):
    """Corps de POST /auth/refresh — renouvelle la session expirée
    sans redemander le mot de passe (connexion permanente)."""

    refresh_token: str = Field(..., min_length=1, description="Refresh token de la session")


class ProfilUtilisateur(BaseModel):
    """Le profil métier TERRA (ligne de `administrateur` ou `agriculteur`)."""

    id: int                # Clé primaire de la table métier (int4)
    id_uuid: str           # UUID du compte Supabase Auth (auth.users.id)
    nom: str               # Nom affiché dans l'interface
    email: str | None = None  # Email de connexion — vit dans auth.users
                              # (pas dans nos tables métier) ; injecté par
                              # auth_service depuis la session Supabase.


class LoginResponse(BaseModel):
    """Réponse d'une connexion réussie.
    Le frontend stocke le token et l'envoie ensuite dans
    l'en-tête :  Authorization: Bearer <access_token>"""

    access_token: str      # JWT signé par Supabase (prouve l'identité)
    refresh_token: str     # Permet de renouveler l'access_token expiré
    token_type: str = "bearer"
    role: str              # "administrateur" ou "agriculteur"
    profil: ProfilUtilisateur


class MeResponse(BaseModel):
    """Réponse de GET /auth/me : qui est connecté ?
    (utile au frontend pour restaurer une session au chargement)"""

    role: str
    profil: ProfilUtilisateur
