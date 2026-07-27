"""
=========================================================
TERRA — Service Parcelles

Une parcelle appartient à un agriculteur. `jour_actuel`
(jours écoulés depuis la plantation) est calculé à la volée :
c'est la donnée-clé du suivi du cycle de la plante, elle ne
doit JAMAIS être stockée (elle changerait chaque jour).
=========================================================
"""

from datetime import date

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.auth import MeResponse
from app.schemas.parcelle import ParcelleCreate, ParcelleOut, ParcelleUpdate
from app.services.acces import est_admin, get_parcelle_ou_404, verifier_acces_parcelle

TABLE = "parcelle"


def _avec_jour_actuel(row: dict) -> ParcelleOut:
    """Transforme une ligne DB en ParcelleOut + jour_actuel calculé."""
    plantation = date.fromisoformat(str(row["date_plantation"]))
    jour_actuel = max(0, (date.today() - plantation).days)
    return ParcelleOut(**row, jour_actuel=jour_actuel)


def lister(user: MeResponse, id_agriculteur: int | None = None) -> list[ParcelleOut]:
    """Admin → toutes (filtrables par agriculteur) ; agriculteur → les siennes."""
    query = get_supabase().table(TABLE).select("*").order("id")
    if est_admin(user):
        if id_agriculteur is not None:
            query = query.eq("id_agriculteur", id_agriculteur)
    else:
        query = query.eq("id_agriculteur", user.profil.id)
    return [_avec_jour_actuel(row) for row in query.execute().data]


def obtenir(user: MeResponse, id_parcelle: int) -> ParcelleOut:
    parcelle = get_parcelle_ou_404(id_parcelle)
    verifier_acces_parcelle(user, parcelle)
    return _avec_jour_actuel(parcelle)


def creer(user: MeResponse, corps: ParcelleCreate) -> ParcelleOut:
    """RÉSERVÉ à l'administrateur : il crée la parcelle et l'attribue
    à un agriculteur (id_agriculteur obligatoire)."""
    if not est_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur crée les parcelles — contactez-le pour en obtenir une.",
        )

    ligne = {
        "id_agriculteur": corps.id_agriculteur,
        "nom": corps.nom,
        "culture": corps.culture,
        "date_plantation": corps.date_plantation.isoformat(),
        "superficie": corps.superficie,
        "nombre_plant": corps.nombre_plant,
        "lat": corps.lat,
        "lon": corps.lon,
    }
    result = get_supabase().table(TABLE).insert(ligne).execute()
    return _avec_jour_actuel(result.data[0])


# Le seul champ qu'un agriculteur peut modifier sur SA parcelle :
# il saisit la date de plantation pour démarrer le suivi du cycle.
CHAMPS_AGRICULTEUR = {"date_plantation"}


def modifier(user: MeResponse, id_parcelle: int, corps: ParcelleUpdate) -> ParcelleOut:
    parcelle = get_parcelle_ou_404(id_parcelle)
    verifier_acces_parcelle(user, parcelle)

    # On ne pousse que les champs réellement envoyés
    patch = corps.model_dump(exclude_none=True)

    if not est_admin(user):
        interdits = set(patch) - CHAMPS_AGRICULTEUR
        if interdits:
            raise HTTPException(
                status_code=403,
                detail="Un agriculteur ne modifie que la date de plantation — le reste est géré par l'administrateur.",
            )

    if "date_plantation" in patch:
        patch["date_plantation"] = patch["date_plantation"].isoformat()
    if not patch:
        return _avec_jour_actuel(parcelle)

    result = get_supabase().table(TABLE).update(patch).eq("id", id_parcelle).execute()
    return _avec_jour_actuel(result.data[0])


def supprimer(user: MeResponse, id_parcelle: int) -> None:
    """Supprime la parcelle (cascade DB) — administrateur uniquement."""
    if not est_admin(user):
        raise HTTPException(status_code=403, detail="Seul l'administrateur supprime une parcelle.")
    get_parcelle_ou_404(id_parcelle)
    get_supabase().table(TABLE).delete().eq("id", id_parcelle).execute()
