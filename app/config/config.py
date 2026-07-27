
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contrat de configuration : chaque champ correspond à une
    variable du fichier .env (voir .env.example)."""

    # ---------- Supabase ----------
    supabase_url: str = ""          
    supabase_anon_key: str = ""     
    supabase_service_key: str = ""  

    # ---------- OpenWeather ----------
    openweather_api_key: str = ""   
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # ---------- Localisation par défaut ----------
    default_lat: float = 6.8276
    default_lon: float = -5.2893

    # ---------- Synchronisation météo automatique ----------
    # Toutes les N minutes, le backend interroge OpenWeather, stocke
    # le résultat et le DIFFUSE en WebSocket : les dashboards ouverts
    # se mettent à jour sans que personne ne recharge la page.
    meteo_sync_minutes: int = 15

    # ---------- Moteur expert (aide à la décision d'irrigation) ----------
    # Toutes les N minutes, le moteur recalcule l'évaporation et génère
    # les prescriptions. Cadence rapprochée (5 min) pour un rafraîchissement
    # quasi temps réel des recommandations sur le dashboard.
    moteur_expert_minutes: int = 5

    # ---------- Serveur ----------
    cors_origins: str = "http://localhost:5178,http://127.0.0.1:5178"

    # ---------- Ingestion IoT (passerelle ESP32 → backend) ----------
    # Clés d'API des passerelles autorisées à POSTer sur /api/v1/iot/ingest,
    # séparées par des virgules. Chaque boîtier central envoie sa clé dans
    # l'en-tête `X-Device-Key`. AUCUNE clé par défaut : tant que la variable
    # est vide, l'endpoint refuse toute ingestion (fail-safe). NE JAMAIS
    # committer les vraies clés — elles vivent dans Backend/.env.
    iot_device_keys: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        """Transforme la chaîne CORS_ORIGINS en liste exploitable par FastAPI."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def iot_device_keys_set(self) -> set[str]:
        """Ensemble des clés device autorisées (comparaison O(1))."""
        return {k.strip() for k in self.iot_device_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
