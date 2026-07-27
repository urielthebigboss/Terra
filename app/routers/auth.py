"""
=========================================================
TERRA — Routes d'authentification (/api/v1/auth)

  POST /api/v1/auth/login  → email + mot de passe → token + rôle
  GET  /api/v1/auth/me     → qui est connecté ? (token requis)

Ce fichier définit aussi deux DÉPENDANCES réutilisables :
  - utilisateur_courant : à mettre sur toute route protégée
  - admin_requis        : à mettre sur les routes réservées admin
Exemple d'usage dans un futur routeur :
    @router.get("/parcelles")
    def mes_parcelles(user: MeResponse = Depends(utilisateur_courant)): ...
=========================================================
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, RefreshRequest
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentification"])

# Extrait automatiquement l'en-tête « Authorization: Bearer <token> ».
# auto_error=False → c'est nous qui renvoyons une erreur claire en français.
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------
# Dépendances de sécurité (réutilisables par tous les routeurs)
# ---------------------------------------------------------
def utilisateur_courant(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> MeResponse:
    """Garde d'accès : la route ne s'exécute que si le token est valide.
    Retourne le rôle + profil de l'utilisateur connecté."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Connexion requise — envoyez le token dans l'en-tête Authorization: Bearer.",
        )
    return auth_service.verifier_token(credentials.credentials)


def admin_requis(user: MeResponse = Depends(utilisateur_courant)) -> MeResponse:
    """Garde renforcée : réservée à l'espace administrateur."""
    if user.role != "administrateur":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
    return user


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@router.post("/login", response_model=LoginResponse, summary="Se connecter (admin ou agriculteur)")
def login(corps: LoginRequest) -> LoginResponse:
    """Vérifie les identifiants auprès de Supabase Auth puis détermine
    le rôle via les tables `administrateur` / `agriculteur`.
    Le frontend redirige ensuite vers le bon espace selon `role`."""
    return auth_service.login(corps.email, corps.mot_de_passe)


@router.get("/me", response_model=MeResponse, summary="Profil de l'utilisateur connecté")
def me(user: MeResponse = Depends(utilisateur_courant)) -> MeResponse:
    """Permet au frontend de restaurer la session au chargement de la
    page : si le token stocké est encore valide, on récupère rôle + profil."""
    return user


@router.post("/refresh", response_model=LoginResponse, summary="Renouveler la session")
def refresh(corps: RefreshRequest) -> LoginResponse:
    """Échange le refresh_token contre une nouvelle paire de tokens.
    Le frontend l'appelle automatiquement quand l'access_token expire :
    l'utilisateur reste connecté en permanence, sans re-saisir son
    mot de passe."""
    return auth_service.rafraichir(corps.refresh_token)
