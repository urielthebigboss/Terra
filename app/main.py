"""
TERRA — Point d'entrée du backend FastAPI
Assemble l'application : middleware CORS, routeurs REST,
endpoint WebSocket.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config.config import get_settings
from app.routers import (
    agriculteurs,
    alertes,
    auth,
    capteurs,
    iot,
    mesures,
    meteo,
    moteur_expert as moteur_expert_router,
    parcelles,
    prescriptions,
    profil_culture,
)
from app.services import meteo_service, moteur_expert
from app.websocket.manager import manager

logger = logging.getLogger("terra")


# ---------- Synchronisation météo automatique ----------
async def _sync_meteo_periodique() -> None:
    """Tâche de fond : OpenWeather → Supabase → WebSocket, en boucle.

    C'est elle qui rend la météo « temps réel » côté frontend : chaque
    synchronisation diffuse un message `meteo_update`, et tous les
    dashboards ouverts se rafraîchissent sans rechargement de page.
    Une erreur (réseau, clé API…) n'arrête jamais la boucle : on
    réessaie simplement au cycle suivant.
    """
    settings = get_settings()
    while True:
        try:
            await meteo_service.sync_meteo(lat=settings.default_lat, lon=settings.default_lon)
            logger.info("Météo synchronisée automatiquement (OpenWeather → Supabase → WebSocket)")
        except Exception as exc:
            logger.warning("Sync météo automatique échouée (%s) — nouvel essai au prochain cycle.", exc)
        await asyncio.sleep(max(1, settings.meteo_sync_minutes) * 60)


# ---------- Moteur expert automatique (toutes les 5 min) ----------
async def _moteur_expert_periodique() -> None:
    """Tâche de fond : le moteur expert recalcule les prescriptions de
    toutes les parcelles à intervalle régulier (MOTEUR_EXPERT_MINUTES).

    On attend d'abord un court délai au démarrage pour laisser la
    première synchronisation météo remplir la base — sinon le tout
    premier calcul se ferait sans prévisions. Une erreur globale
    n'arrête jamais la boucle (le service tourne sans surveillance).
    """
    settings = get_settings()
    await asyncio.sleep(90)  # laisser le sync météo initial se faire
    while True:
        try:
            bilan = await moteur_expert.executer()
            logger.info(
                "Moteur expert exécuté : %s parcelle(s), %s prescription(s) générée(s).",
                bilan["parcelles_analysees"], bilan["prescriptions_creees"],
            )
        except Exception as exc:
            logger.warning("Moteur expert automatique échoué (%s) — nouvel essai au prochain cycle.", exc)
        await asyncio.sleep(max(1, settings.moteur_expert_minutes) * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarre les tâches de fond (météo + moteur expert) avec
    l'application et les arrête proprement à l'extinction du serveur."""
    taches = [
        asyncio.create_task(_sync_meteo_periodique()),
        asyncio.create_task(_moteur_expert_periodique()),
    ]
    yield
    for tache in taches:
        tache.cancel()


# ---------- Création de l'application ----------
app = FastAPI(
    lifespan=lifespan,
    title="TERRA API",
    description=(
        "Backend du projet TERRA — plateforme d'irrigation intelligente.\n\n"
        "Approche **API-first** (contrats Pydantic → doc auto) et **temps réel** "
        "via WebSocket (`/ws`). Les données externes (OpenWeather) sont d'abord "
        "**stockées** dans Supabase puis **exposées** par l'API."
    ),
    version="0.1.0",
)

# ---------- CORS ----------
# Autorise le frontend (servi sur un autre port) à appeler l'API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Erreurs de configuration ----------
@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ---------- Routeurs REST ----------
app.include_router(auth.router)           # connexion admin / agriculteur
app.include_router(agriculteurs.router)   # gestion des comptes agriculteurs (admin)
app.include_router(parcelles.router)      # parcelles de l'agriculteur (+ jour_actuel)
app.include_router(capteurs.router)       # capteurs + signalement de panne
app.include_router(alertes.router)        # workflow des alertes (admin)
app.include_router(mesures.router)        # mesures capteurs (API frontend, JWT)
app.include_router(iot.router)            # ingestion IoT (passerelle ESP32, clé device)
app.include_router(prescriptions.router)  # prescriptions (manuelles + Moteur Expert)
app.include_router(profil_culture.router) # référentiel agronomique (lecture seule)
app.include_router(moteur_expert_router.router)  # nalyse + diagnostic)
app.include_router(meteo.router)          # météo (sync + expositionmoteur expert (a)


# ---------- Fichiers statiques (page de démo temps réel) ----------
# http://localhost:8000/static/ws_demo.html : console live du WebSocket
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# ---------- Route de santé ----------
@app.get("/", tags=["Santé"], summary="Vérifier que l'API répond")
def health() -> dict:
    """Utilisée par le frontend (et les tests) pour savoir si le backend est en vie."""
    return {"status": "ok", "service": "TERRA API", "docs": "/docs"}


# ---------- WebSocket temps réel ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Canal temps réel unique du projet.

    Le frontend s'y connecte :  new WebSocket("ws://localhost:8000/ws")
    et reçoit des messages JSON typés :  { "type": "meteo_update", "data": {...} }
    """
    await manager.connect(websocket)
    try:
        # On garde la connexion ouverte ; le client peut envoyer un
        # "ping" (ou n'importe quoi) — on ne fait que maintenir le canal.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Déconnexion propre côté client → on nettoie la liste
        manager.disconnect(websocket)
