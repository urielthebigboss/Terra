# TERRA — Backend (FastAPI + Supabase + WebSocket)

Backend **API-first** du projet TERRA : les contrats de données (Pydantic)
génèrent automatiquement la documentation interactive sur `/docs`.
Principe météo : **on stocke** (OpenWeather → Supabase), **puis on expose**
(Supabase → API → frontend). Le frontend ne parle jamais à OpenWeather.

## Architecture

```
Backend/
├── requirements.txt          # Dépendances Python
├── .env.example              # Modèle de configuration (à copier en .env)
├── db/
│   └── meteo_tables.sql      # SQL de référence des tables météo
└── app/
    ├── main.py               # Point d'entrée : CORS, routeurs, WebSocket /ws
    ├── config.py             # Configuration centralisée (.env)
    ├── database.py           # Client Supabase partagé
    ├── schemas/meteo.py      # Contrats de données (API-first)
    ├── services/
    │   ├── openweather.py    # Appels OpenWeather → schémas internes
    │   └── meteo_service.py  # Orchestration : stocker puis exposer
    ├── routers/meteo.py      # Routes REST /api/v1/meteo
    └── websocket/manager.py  # Diffusion temps réel aux clients connectés
```

## Installation

```bash
cd Backend

# 1. Environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows  (Linux/Mac : source venv/bin/activate)

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration — remplissez VOS clés
copy .env.example .env       # Windows  (Linux/Mac : cp .env.example .env)
#   → SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
#   → OPENWEATHER_API_KEY

# 4. Démarrage
uvicorn app.main:app --reload
```

API disponible sur `http://localhost:8000` — doc interactive : `http://localhost:8000/docs`

> ⚠️ **Avant la première utilisation des routes métier** : exécutez
> [db/terra_tables.sql](db/terra_tables.sql) dans Supabase
> (Dashboard → SQL Editor) pour créer les tables `parcelle`, `capteur`,
> `mesure`, `prescription`, `profil_culture` et compléter `agriculteur` / `alerte`.
>
> ⚠️ **Passage en production** : exécutez aussi
> [db/migration_prod.sql](db/migration_prod.sql) — colonnes
> `parcelle.eau_utilisee` (consommation d'eau réelle cumulée) et
> `parcelle.evaporation_mm` (ETc du moteur expert), plus la migration
> du format JSONB des mesures.

## Capteurs réels (ESP32 → POST /api/v1/mesures)

Deux capteurs physiques, envoi automatique toutes les **5 heures** —
le JSONB ne contient QUE des valeurs numériques (les unités sont
affichées par l'interface) :

```json
// Capteur capacitif du sol (type "humidite_sol")
{ "id_capteur": 1, "donnees": { "humidite": 27.6 } }

// Capteur DHT22 (type "dht22") — DEUX grandeurs par envoi
{ "id_capteur": 2, "donnees": { "temperature": 27.6, "humidite": 30 } }
```

Chaque mesure reçue est validée selon le type du capteur (422 sinon),
stockée, puis diffusée en WebSocket (`mesure_update`).

## Moteur expert

Toutes les **5 min** (config `MOTEUR_EXPERT_MINUTES`), le moteur calcule
l'évaporation (ET₀ Hargreaves FAO-56 × Kc), applique les règles FAO et
ANADER et écrit ses prescriptions (diffusées en WebSocket). Déclenchement
manuel : `POST /api/v1/moteur-expert/executer` (admin). Documentation
complète : [../docs/MOTEUR_EXPERT.md](../docs/MOTEUR_EXPERT.md).

## Sessions permanentes

`POST /api/v1/auth/refresh` échange le `refresh_token` contre une
nouvelle paire de tokens — le frontend l'appelle automatiquement sur
401 : aucune déconnexion intempestive. La vérification des tokens est
mise en cache 5 min côté backend (performance).

## Endpoints métier

| Méthode | Route | Qui | Rôle |
|---|---|---|---|
| `POST` | `/api/v1/agriculteurs` | admin | Créer un agriculteur (nom + email + mot de passe) |
| `GET` | `/api/v1/agriculteurs` | admin | Lister les agriculteurs |
| `PATCH` | `/api/v1/agriculteurs/{id}` | admin | Renommer / réinitialiser le mot de passe |
| `DELETE` | `/api/v1/agriculteurs/{id}` | admin | Supprimer (profil + compte Auth, cascade) |
| `GET/POST` | `/api/v1/parcelles` | tous | Mes parcelles (avec `jour_actuel` calculé) / en créer |
| `PATCH/DELETE` | `/api/v1/parcelles/{id}` | propriétaire ou admin | Modifier / supprimer |
| `GET/POST` | `/api/v1/capteurs` | tous | Capteurs visibles / déclarer un capteur |
| `PATCH` | `/api/v1/capteurs/{id}` | admin pour `etat` | Gérer l'état (actif, panne, hors_ligne, maintenance) |
| `POST` | `/api/v1/capteurs/{id}/signaler` | agriculteur | Signaler une panne → capteur en `panne` + Alerte |
| `GET` | `/api/v1/alertes` | tous | Admin : toutes ; agriculteur : les siennes |
| `PATCH` | `/api/v1/alertes/{id}` | admin | en_attente → en_intervention → repare → cloture |
| `GET/POST` | `/api/v1/mesures` | tous | Lire / ingérer une mesure (futur contrat IoT) |
| `POST` | `/api/v1/mesures/simuler` | tous | Mesures **fictives** plausibles (démo) |
| `GET/POST` | `/api/v1/prescriptions` | tous | Lire / créer une prescription |
| `POST` | `/api/v1/prescriptions/{id}/faite` | propriétaire | Confirmer l'irrigation effectuée |
| `POST` | `/api/v1/prescriptions/simuler` | tous | Prescriptions **fictives** (avant Moteur Expert) |

## Temps réel (WebSocket `/ws`)

**Toutes les mutations** de l'API sont diffusées aux clients connectés —
l'affichage se met à jour sans recharger. Page de démonstration live :
`http://localhost:8000/static/ws_demo.html`. Côté frontend, le module
`Frontend/assets/js/realtime.js` redistribue chaque message en événement
DOM `terra:<type>`.

| Type de message | Émis quand |
|---|---|
| `meteo_update` | synchronisation OpenWeather |
| `mesure_update` | une mesure unitaire arrive (futur IoT réel) |
| `mesures_bulk` | lot de mesures simulées (recharger les graphiques) |
| `alerte_update` | alerte créée (signalement) ou changée d'état |
| `capteur_update` | capteur créé / état changé (panne, réparé…) |
| `capteur_delete` / `parcelle_delete` | suppression |
| `parcelle_update` | parcelle créée ou modifiée |
| `prescription_update` | prescription créée ou marquée faite |
| `prescriptions_bulk` | lot de prescriptions simulées |

### Test de bout en bout

```bash
# API démarrée + SQL exécuté, puis :
python scripts/test_flux_complet.py --email <admin@email> --mot-de-passe <motdepasse>
```

## Endpoints météo

| Méthode | Route | Rôle |
|---|---|---|
| `POST` | `/api/v1/meteo/sync` | OpenWeather → Supabase (+ diffusion WebSocket) |
| `GET` | `/api/v1/meteo/actuelle` | Dernière mesure stockée |
| `GET` | `/api/v1/meteo/historique?limit=50` | Mesures passées (graphiques) |
| `GET` | `/api/v1/meteo/previsions` | Prévisions 5 jours stockées |
| `WS` | `/ws` | Temps réel : `{ "type": "meteo_update", "data": {...} }` |

### Exemple d'utilisation

```bash
# 1. Synchroniser (stocke en base + diffuse en WebSocket)
curl -X POST "http://localhost:8000/api/v1/meteo/sync"

# 2. Lire depuis la base
curl "http://localhost:8000/api/v1/meteo/actuelle"
curl "http://localhost:8000/api/v1/meteo/previsions"
```

### Côté frontend (JavaScript vanilla)

```js
// Temps réel : le dashboard se met à jour sans recharger
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "meteo_update") majMeteo(msg.data);
};
```

## Base de données

Les tables attendues sont décrites dans [db/meteo_tables.sql](db/meteo_tables.sql)
(météo) et [db/terra_tables.sql](db/terra_tables.sql) (métier).
Si vos noms de tables diffèrent, adaptez `TABLE_MESURES` / `TABLE_PREVISIONS`
en haut de `app/services/meteo_service.py`.

### Sécurité RLS

[db/rls_policies.sql](db/rls_policies.sql) active le Row Level Security sur
**toutes** les tables : l'admin voit tout, un agriculteur ne voit que ses
données, les non-connectés n'ont accès à rien. Le backend (clé `service_role`)
contourne le RLS — ces politiques sont la deuxième ligne de défense si la clé
`anon` est exposée côté client.
