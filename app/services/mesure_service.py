"""
=========================================================
TERRA — Service Mesures (capteurs réels)

FORMAT DU JSONB `donnees` — une mesure peut porter PLUSIEURS
grandeurs (le DHT22 renvoie deux valeurs dans le même envoi) :

  Capteur capacitif du sol (type « humidite_sol ») :
      { "humidite": 27.6 }
  Capteur DHT22 (type « dht22 ») :
      { "temperature": 27.6, "humidite": 30 }

Les UNITÉS ne sont PAS stockées : la base ne contient que des
valeurs numériques, l'interface ajoute « °C » / « % » à
l'affichage. Les capteurs envoient automatiquement toutes les
5 heures sur POST /mesures (contrat identique pour l'ESP32).

`extraire_grandeurs()` est LE point unique de lecture : il
normalise aussi l'ancien format {"valeur": x, "unite": u}
encore présent dans les lignes historiques.
=========================================================
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.auth import MeResponse
from app.schemas.mesure import MesureCreate, MesureOut
from app.services.acces import (
    get_capteur_ou_404,
    get_parcelle_ou_404,
    ids_parcelles_de,
    verifier_acces_capteur,
    verifier_acces_parcelle,
)

TABLE = "mesure"


# ---------------------------------------------------------
# Lecture normalisée d'une mesure — POINT UNIQUE de vérité.
# Retourne un dict grandeur → valeur numérique, quel que soit
# le type de capteur et l'âge du format stocké.
# Grandeurs possibles : humidite_sol, temperature, humidite_air, pluie
# ---------------------------------------------------------
def extraire_grandeurs(type_capteur: str, donnees: dict) -> dict:
    if not isinstance(donnees, dict):
        return {}
    t = (type_capteur or "").lower()
    valeurs: dict[str, float] = {}

    def _num(x):
        return x if isinstance(x, (int, float)) else None

    # Ancien format {"valeur": x, "unite": u} : la grandeur est
    # déduite du type du capteur (compatibilité des historiques).
    ancien = _num(donnees.get("valeur"))

    if "humidite_sol" in t or "capacitif" in t:
        v = _num(donnees.get("humidite"))
        if v is None:
            v = ancien
        if v is not None:
            valeurs["humidite_sol"] = v
    elif "dht" in t:
        vt = _num(donnees.get("temperature"))
        vh = _num(donnees.get("humidite"))
        if vt is not None:
            valeurs["temperature"] = vt
        if vh is not None:
            valeurs["humidite_air"] = vh
    elif "temperature" in t:  # ancien type « temperature_air »
        v = _num(donnees.get("temperature"))
        if v is None:
            v = ancien
        if v is not None:
            valeurs["temperature"] = v
    elif "humidite_air" in t:  # ancien type « humidite_air »
        v = _num(donnees.get("humidite"))
        if v is None:
            v = ancien
        if v is not None:
            valeurs["humidite_air"] = v
    elif "pluie" in t:
        v = _num(donnees.get("pluie"))
        if v is None:
            v = ancien
        if v is not None:
            valeurs["pluie"] = v
    else:
        # Type inconnu : on expose les clés numériques telles quelles
        valeurs = {k: v for k, v in donnees.items() if isinstance(v, (int, float))}
    return valeurs


def lister(
    user: MeResponse,
    id_capteur: int | None = None,
    id_parcelle: int | None = None,
    limit: int = 100,
) -> list[MesureOut]:
    """Mesures visibles, de la plus récente à la plus ancienne.
    Filtrer par capteur OU par parcelle (tous ses capteurs)."""
    supabase = get_supabase()

    if id_capteur is not None:
        capteur = get_capteur_ou_404(id_capteur)
        verifier_acces_capteur(user, capteur)
        capteurs_vises = [id_capteur]
    else:
        if id_parcelle is not None:
            parcelle = get_parcelle_ou_404(id_parcelle)
            verifier_acces_parcelle(user, parcelle)
            parcelles = [id_parcelle]
        else:
            parcelles = ids_parcelles_de(user)
        if not parcelles:
            return []
        rows = supabase.table("capteur").select("id").in_("id_parcelle", parcelles).execute().data
        capteurs_vises = [r["id"] for r in rows]
        if not capteurs_vises:
            return []

    result = (
        supabase.table(TABLE)
        .select("*")
        .in_("id_capteur", capteurs_vises)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return [MesureOut(**row) for row in result.data]


def ajouter(user: MeResponse, corps: MesureCreate) -> tuple[MesureOut, dict]:
    """Enregistre UNE mesure envoyée par un capteur (ESP32 → HTTP).

    Le JSONB doit contenir au moins une valeur numérique reconnue
    pour le type du capteur — on refuse les payloads vides ou
    malformés plutôt que de stocker du bruit. Met aussi à jour
    derniere_comm du capteur (supervision du parc).

    Retourne (mesure, capteur) — le capteur (avec son id_parcelle et
    son type) est renvoyé pour permettre au router de déclencher les
    alertes immédiates sans requête supplémentaire."""
    capteur = get_capteur_ou_404(corps.id_capteur)
    verifier_acces_capteur(user, capteur)

    if not extraire_grandeurs(capteur["type"], corps.donnees):
        raise HTTPException(
            status_code=422,
            detail=(
                "Payload de mesure invalide pour ce capteur. Formats attendus : "
                'humidite_sol → {"humidite": 27.6} · dht22 → {"temperature": 27.6, "humidite": 30}'
            ),
        )

    supabase = get_supabase()
    quand = (corps.date or datetime.now(timezone.utc)).isoformat()
    result = supabase.table(TABLE).insert(
        {"id_capteur": corps.id_capteur, "date": quand, "donnees": corps.donnees}
    ).execute()

    supabase.table("capteur").update({"derniere_comm": quand}).eq("id", corps.id_capteur).execute()
    return MesureOut(**result.data[0]), capteur
