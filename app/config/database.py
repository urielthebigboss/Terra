"""
=========================================================
TERRA — Connexion Supabase
Fournit UN client Supabase partagé par toute l'application.
La base de données est déjà conçue côté Supabase : ce module
ne crée aucune table, il ne fait que s'y connecter.
=========================================================
"""

from functools import lru_cache

from supabase import Client, create_client

from app.config.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Retourne le client Supabase (créé une seule fois).

    On utilise la clé `service_role` côté serveur : elle contourne
    les règles RLS, ce qui est voulu puisque c'est le backend qui
    contrôle les accès. Si elle est absente, on retombe sur la clé
    anon (lecture selon les policies définies dans Supabase).
    """
    settings = get_settings()

    # Garde-fou : message clair si le .env n'est pas rempli
    if not settings.supabase_url:
        raise RuntimeError(
            "SUPABASE_URL manquant — copiez .env.example vers .env et remplissez vos clés."
        )

    key = settings.supabase_service_key or settings.supabase_anon_key
    if not key:
        raise RuntimeError(
            "Aucune clé Supabase trouvée — renseignez SUPABASE_SERVICE_KEY (ou SUPABASE_ANON_KEY) dans .env."
        )

    return create_client(settings.supabase_url, key)
