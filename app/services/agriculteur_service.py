"""
=========================================================
TERRA — Service Agriculteurs (réservé à l'administrateur)

Créer un agriculteur = DEUX écritures qui doivent rester
cohérentes :
  1. le compte de connexion dans Supabase Auth (auth.users)
  2. le profil métier dans la table `agriculteur`
Si la 2e échoue, on SUPPRIME le compte Auth créé (rollback
manuel) pour ne pas laisser de compte orphelin.
=========================================================
"""

from fastapi import HTTPException

from app.config.database import get_supabase
from app.schemas.agriculteur import AgriculteurCreate, AgriculteurOut, AgriculteurUpdate

TABLE = "agriculteur"


def lister() -> list[AgriculteurOut]:
    """Tous les agriculteurs, du plus récent au plus ancien."""
    result = get_supabase().table(TABLE).select("*").order("id", desc=True).execute()
    return [AgriculteurOut(**row) for row in result.data]


def obtenir(id_agriculteur: int) -> AgriculteurOut:
    result = get_supabase().table(TABLE).select("*").eq("id", id_agriculteur).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agriculteur {id_agriculteur} introuvable.")
    return AgriculteurOut(**result.data[0])


def creer(corps: AgriculteurCreate) -> AgriculteurOut:
    """Crée le compte Auth PUIS le profil métier (avec rollback)."""
    supabase = get_supabase()

    # 1) Compte de connexion — email_confirm=True : pas d'email de
    #    validation à envoyer, l'admin communique lui-même les identifiants.
    try:
        reponse = supabase.auth.admin.create_user(
            {"email": corps.email, "password": corps.mot_de_passe, "email_confirm": True}
        )
    except Exception as exc:
        # Cas le plus courant : email déjà utilisé
        raise HTTPException(
            status_code=409,
            detail=f"Impossible de créer le compte ({exc.__class__.__name__}) — cet email est peut-être déjà utilisé.",
        )
    id_uuid = reponse.user.id

    # 2) Profil métier — en cas d'échec, rollback du compte Auth
    try:
        insertion = (
            supabase.table(TABLE)
            .insert({"id_uuid": id_uuid, "nom": corps.nom, "email": corps.email})
            .execute()
        )
        return AgriculteurOut(**insertion.data[0])
    except Exception:
        supabase.auth.admin.delete_user(id_uuid)
        raise HTTPException(
            status_code=500,
            detail="Compte Auth créé mais profil agriculteur impossible à insérer — "
            "avez-vous exécuté db/terra_tables.sql dans Supabase ?",
        )


def modifier(id_agriculteur: int, corps: AgriculteurUpdate) -> AgriculteurOut:
    """Renomme l'agriculteur et/ou réinitialise son mot de passe."""
    supabase = get_supabase()
    agriculteur = obtenir(id_agriculteur)

    if corps.nom:
        supabase.table(TABLE).update({"nom": corps.nom}).eq("id", id_agriculteur).execute()

    if corps.mot_de_passe:
        # Le mot de passe vit dans Supabase Auth, pas dans notre table
        try:
            supabase.auth.admin.update_user_by_id(
                agriculteur.id_uuid, {"password": corps.mot_de_passe}
            )
        except Exception:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour du mot de passe.")

    return obtenir(id_agriculteur)


def supprimer(id_agriculteur: int) -> None:
    """Supprime le profil (cascade : parcelles, capteurs, mesures,
    prescriptions) PUIS le compte Auth."""
    supabase = get_supabase()
    agriculteur = obtenir(id_agriculteur)

    supabase.table(TABLE).delete().eq("id", id_agriculteur).execute()
    try:
        supabase.auth.admin.delete_user(agriculteur.id_uuid)
    except Exception:
        # Le profil est déjà parti : on signale sans bloquer
        raise HTTPException(
            status_code=500,
            detail="Profil supprimé mais compte Auth restant — supprimez-le dans le dashboard Supabase.",
        )
