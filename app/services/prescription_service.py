"""
=========================================================
TERRA — Service Prescriptions

Les prescriptions sont produites par le MOTEUR EXPERT
(services/moteur_expert.py, toutes les 5 h) ou saisies à la
main. Quand l'agriculteur VALIDE une mission (« faite »), le
volume d'eau appliqué est CUMULÉ dans parcelle.eau_utilisee :
c'est la consommation d'eau réelle et totale de la parcelle,
utilisée par toutes les statistiques.
=========================================================
"""

import logging
from datetime import date

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.auth import MeResponse
from app.schemas.prescription import PrescriptionCreate, PrescriptionOut
from app.services.acces import get_parcelle_ou_404, ids_parcelles_de, verifier_acces_parcelle

logger = logging.getLogger("terra")

TABLE = "prescription"


def lister(
    user: MeResponse,
    id_parcelle: int | None = None,
    etat: str | None = None,
    limit: int = 100,
) -> list[PrescriptionOut]:
    """Prescriptions visibles, des plus récentes aux plus anciennes."""
    if id_parcelle is not None:
        parcelle = get_parcelle_ou_404(id_parcelle)
        verifier_acces_parcelle(user, parcelle)
        parcelles = [id_parcelle]
    else:
        parcelles = ids_parcelles_de(user)
    if not parcelles:
        return []

    query = (
        get_supabase()
        .table(TABLE)
        .select("*")
        .in_("id_parcelle", parcelles)
        .order("date", desc=True)
        .limit(limit)
    )
    if etat:
        query = query.eq("etat", etat)
    return [PrescriptionOut(**row) for row in query.execute().data]


def creer(user: MeResponse, corps: PrescriptionCreate) -> PrescriptionOut:
    """Création MANUELLE d'une prescription (conseil saisi par un
    humain — le moteur expert écrit directement dans la table)."""
    parcelle = get_parcelle_ou_404(corps.id_parcelle)
    verifier_acces_parcelle(user, parcelle)

    result = get_supabase().table(TABLE).insert(corps.model_dump()).execute()
    return PrescriptionOut(**result.data[0])


def marquer_faite(user: MeResponse, id_prescription: int) -> PrescriptionOut:
    """L'agriculteur confirme avoir appliqué la prescription.

    Effets :
      1. etat = faite + date_faite (alimente l'historique) ;
      2. le volume d'eau est CUMULÉ dans parcelle.eau_utilisee —
         le compteur de consommation réelle de la parcelle.
    """
    supabase = get_supabase()
    result = supabase.table(TABLE).select("*").eq("id", id_prescription).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Prescription {id_prescription} introuvable.")
    prescription = result.data[0]

    parcelle = get_parcelle_ou_404(prescription["id_parcelle"])
    verifier_acces_parcelle(user, parcelle)

    if prescription["etat"] == "faite":
        # Idempotence : re-valider une mission déjà faite ne doit pas
        # compter l'eau deux fois.
        return PrescriptionOut(**prescription)

    maj = (
        supabase.table(TABLE)
        .update({"etat": "faite", "date_faite": date.today().isoformat()})
        .eq("id", id_prescription)
        .execute()
    )

    # --- Cumul de la consommation d'eau réelle de la parcelle ---
    volume = prescription.get("volume_eau") or 0
    if volume > 0:
        try:
            total = (parcelle.get("eau_utilisee") or 0) + volume
            supabase.table("parcelle").update({"eau_utilisee": round(total, 1)}).eq(
                "id", parcelle["id"]
            ).execute()
        except Exception as exc:
            # Colonne absente (migration SQL pas encore exécutée) :
            # la validation de la mission reste acquise, on trace.
            logger.warning(
                "eau_utilisee non cumulée (exécutez db/migration_prod.sql) : %s", exc
            )

    return PrescriptionOut(**maj.data[0])
