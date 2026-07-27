"""
=========================================================
TERRA — Service d'authentification
Trois responsabilités :
  1. LOGIN : vérifier email + mot de passe auprès de
     Supabase Auth, puis déterminer le rôle en cherchant
     l'UUID dans nos tables `administrateur` / `agriculteur`.
  2. VÉRIFICATION : valider un token (Authorization: Bearer)
     sur les routes protégées et retrouver le profil associé.
     → mise en CACHE (TTL) : sans lui, CHAQUE requête API
     coûtait 3 allers-retours réseau vers Supabase (get_user
     + 2 lectures de profil) — c'était la première cause de
     lenteur du site.
  3. REFRESH : renouveler une session expirée à partir du
     refresh_token — l'utilisateur reste connecté en permanence,
     sans déconnexion intempestive.

Rappel du schéma DB (déjà conçu côté Supabase) :
  auth.users.id (uuid)  ←  administrateur.id_uuid
                        ←  agriculteur.id_uuid
=========================================================
"""

import time

import httpx
from fastapi import HTTPException
from supabase import create_client

from app.config.config import get_settings
from app.config.database import get_supabase
from app.schemas.auth import LoginResponse, MeResponse, ProfilUtilisateur

# Noms des tables de profil — un seul endroit à modifier si besoin
TABLE_ADMIN = "administrateur"
TABLE_AGRICULTEUR = "agriculteur"

# ---------------------------------------------------------
# Cache de vérification des tokens : token → (expiration, profil).
# TTL court (5 min) : un token révoqué/expiré côté Supabase reste
# accepté au plus 5 min — compromis sûr pour un gain majeur
# (0 appel réseau d'authentification pendant la durée du cache).
# ---------------------------------------------------------
_CACHE_TOKENS: dict[str, tuple[float, MeResponse]] = {}
_CACHE_TTL_S = 300
_CACHE_TAILLE_MAX = 500  # borne mémoire : purge complète au-delà


def invalider_cache_token(access_token: str | None = None) -> None:
    """Retire un token du cache (ou vide tout) — appelé quand un
    profil change (ex. suppression d'un agriculteur par l'admin)."""
    if access_token:
        _CACHE_TOKENS.pop(access_token, None)
    else:
        _CACHE_TOKENS.clear()


# ---------------------------------------------------------
# Recherche du profil métier à partir de l'UUID Supabase
# ---------------------------------------------------------
def _trouver_profil(id_uuid: str) -> tuple[str, ProfilUtilisateur]:
    """Cherche l'UUID d'abord chez les administrateurs, puis chez
    les agriculteurs. Le rôle découle de la table où on le trouve.
    Un compte Supabase sans profil TERRA est refusé (403)."""
    supabase = get_supabase()

    for role, table in ((("administrateur"), TABLE_ADMIN), (("agriculteur"), TABLE_AGRICULTEUR)):
        result = supabase.table(table).select("*").eq("id_uuid", id_uuid).limit(1).execute()
        if result.data:
            return role, ProfilUtilisateur(**result.data[0])

    # Le compte existe dans auth.users mais n'est relié à aucun rôle
    raise HTTPException(
        status_code=403,
        detail="Ce compte n'est associé à aucun profil TERRA (ni administrateur, ni agriculteur).",
    )


# ---------------------------------------------------------
# 1) LOGIN : email + mot de passe → tokens + rôle + profil
# ---------------------------------------------------------
def login(email: str, mot_de_passe: str) -> LoginResponse:
    """Vérifie les identifiants auprès de Supabase Auth.

    On crée un client Supabase JETABLE pour cet appel : la méthode
    sign_in_with_password mémorise la session dans le client, et le
    client partagé de l'application ne doit jamais porter la session
    d'un utilisateur (plusieurs personnes se connectent en parallèle).
    """
    settings = get_settings()
    client_jetable = create_client(
        settings.supabase_url,
        # La clé anon suffit pour l'authentification (c'est son rôle)
        settings.supabase_anon_key or settings.supabase_service_key,
    )

    try:
        resultat = client_jetable.auth.sign_in_with_password(
            {"email": email, "password": mot_de_passe}
        )
    except Exception:
        # Supabase renvoie une erreur pour tout échec (mauvais mot de
        # passe, email inconnu…). On ne précise pas lequel : dire
        # « cet email existe » à un inconnu serait une fuite d'information.
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    if resultat.session is None or resultat.user is None:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Authentifié ✔ — reste à savoir QUI il est pour TERRA
    role, profil = _trouver_profil(resultat.user.id)
    profil.email = resultat.user.email  # l'email vit dans auth.users

    return LoginResponse(
        access_token=resultat.session.access_token,
        refresh_token=resultat.session.refresh_token,
        role=role,
        profil=profil,
    )


# ---------------------------------------------------------
# 2) VÉRIFICATION : token Bearer → rôle + profil (avec cache)
# ---------------------------------------------------------
def verifier_token(access_token: str) -> MeResponse:
    """Valide un access_token et retrouve le profil TERRA.

    Chemin rapide : le token est dans le cache et non périmé →
    ZÉRO appel réseau (c'est le cas de ~99 % des requêtes d'une
    session de navigation normale).
    Chemin lent : vérification complète auprès de Supabase, puis
    mise en cache du résultat pour les prochaines requêtes."""
    # --- Chemin rapide : cache ---
    entree = _CACHE_TOKENS.get(access_token)
    if entree and entree[0] > time.monotonic():
        return entree[1]

    # --- Chemin lent : vérification Supabase ---
    try:
        # get_user(jwt) interroge Supabase sans modifier la session
        # du client partagé — pas besoin de client jetable ici.
        utilisateur = get_supabase().auth.get_user(access_token)
    except httpx.HTTPError:
        # Erreur RÉSEAU vers Supabase (timeout, coupure…) : la session
        # n'est pas en cause → 503 « réessayez », surtout pas 401 qui
        # déconnecterait l'utilisateur à tort.
        raise HTTPException(status_code=503, detail="Service d'authentification momentanément indisponible — réessayez.")
    except Exception as exc:
        # Les erreurs réseau enveloppées par gotrue (AuthRetryableError)
        # doivent aussi rester des 503, pas des 401.
        if "retryable" in exc.__class__.__name__.lower():
            raise HTTPException(status_code=503, detail="Service d'authentification momentanément indisponible — réessayez.")
        raise HTTPException(status_code=401, detail="Session invalide ou expirée — reconnectez-vous.")

    if utilisateur is None or utilisateur.user is None:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée — reconnectez-vous.")

    role, profil = _trouver_profil(utilisateur.user.id)
    profil.email = utilisateur.user.email  # l'email vit dans auth.users
    reponse = MeResponse(role=role, profil=profil)

    # --- Mise en cache (avec borne mémoire) ---
    if len(_CACHE_TOKENS) >= _CACHE_TAILLE_MAX:
        _CACHE_TOKENS.clear()
    _CACHE_TOKENS[access_token] = (time.monotonic() + _CACHE_TTL_S, reponse)
    return reponse


# ---------------------------------------------------------
# 3) REFRESH : renouveler la session sans re-saisir le mot de passe
# ---------------------------------------------------------
def rafraichir(refresh_token: str) -> LoginResponse:
    """Échange un refresh_token contre une nouvelle paire de tokens.

    Le frontend appelle cette route quand l'access_token expire
    (réponse 401) : l'utilisateur reste connecté en permanence tant
    que son refresh_token est valide. Client JETABLE, comme pour le
    login : la session ne doit jamais coller au client partagé."""
    settings = get_settings()
    client_jetable = create_client(
        settings.supabase_url,
        settings.supabase_anon_key or settings.supabase_service_key,
    )
    try:
        resultat = client_jetable.auth.refresh_session(refresh_token)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Service d'authentification momentanément indisponible — réessayez.")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expirée — reconnectez-vous.")

    if resultat.session is None or resultat.user is None:
        raise HTTPException(status_code=401, detail="Session expirée — reconnectez-vous.")

    role, profil = _trouver_profil(resultat.user.id)
    profil.email = resultat.user.email  # l'email vit dans auth.users
    return LoginResponse(
        access_token=resultat.session.access_token,
        refresh_token=resultat.session.refresh_token,
        role=role,
        profil=profil,
    )
