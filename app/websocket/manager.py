"""
=========================================================
TERRA — Gestionnaire de connexions WebSocket
Le frontend se connecte sur /ws : dès qu'une donnée change
côté serveur (ex. nouvelle météo synchronisée), on la diffuse
à tous les clients connectés — pas besoin de rafraîchir la page.

Format des messages diffusés (JSON) :
    { "type": "meteo_update", "data": { ... } }
Le champ "type" permettra d'ajouter d'autres flux plus tard
(capteurs IoT, alertes, recommandations) sans casser le frontend.
=========================================================
"""

from fastapi import WebSocket


class ConnectionManager:
    """Tient la liste des clients WebSocket connectés et
    permet de leur diffuser des messages JSON."""

    def __init__(self) -> None:
        # Liste vivante des connexions actives
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepte une nouvelle connexion et l'enregistre."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Retire une connexion fermée de la liste."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """Envoie un message JSON à TOUS les clients connectés.
        Les connexions mortes sont nettoyées silencieusement."""
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Client déconnecté brutalement → à retirer
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


# Instance unique partagée par toute l'application
manager = ConnectionManager()
