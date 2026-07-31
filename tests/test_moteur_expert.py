# -*- coding: utf-8 -*-
"""
=========================================================
TERRA — Suite de tests du Moteur Expert
=========================================================
Couvre : la formule d'évaporation (FAO-56 Hargreaves-Samani), le
calcul de volume/durée (dépendant de la surface), l'arbre de
décision complet (règles FAO F0-F5 + règles ANADER A1-A3), et les
garanties de format (pas de plan sur plusieurs apports, pas
d'émoji, pas de doublon).

Les capteurs sont simulés (monkeypatch de `_mesures_capteurs`) —
aucune connexion Supabase n'est nécessaire pour ces tests, ils
valident uniquement le RAISONNEMENT du moteur.

Lancer : depuis Backend/,  ./venv/Scripts/python -m pytest -q
=========================================================
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.services import moteur_expert as M
from app.services.mesure_service import extraire_grandeurs


# =========================================================
# 1) ÉVAPORATION — FAO-56 Hargreaves-Samani
# =========================================================
class TestEvaporation:
    def test_rayonnement_plausible_zone_tropicale(self):
        ra = M.rayonnement_extraterrestre(6.02, 196)  # 6° N, mi-juillet
        assert 14 <= ra <= 17

    def test_et0_journee_chaude_plausible(self):
        et0 = M.et0_hargreaves(28, 23, 33, 6.02, 196)
        assert 3.5 <= et0 <= 7

    def test_et0_croit_avec_la_temperature(self):
        base = M.et0_hargreaves(28, 23, 33, 6.02, 196)
        plus_chaud = M.et0_hargreaves(32, 27, 37, 6.02, 196)
        assert plus_chaud > base

    def test_et0_croit_avec_l_amplitude_thermique(self):
        base = M.et0_hargreaves(28, 23, 33, 6.02, 196)
        plus_ample = M.et0_hargreaves(28, 20, 36, 6.02, 196)
        assert plus_ample > base

    def test_et0_amplitude_nulle_ne_plante_pas(self):
        assert M.et0_hargreaves(28, 28, 28, 6.02, 196) >= 0

    def test_et0_jamais_negatif(self):
        assert M.et0_hargreaves(-5, -10, -2, 6.02, 196) >= 0


class TestProfondeurRacinaire:
    def test_jeune_plant_moins_profond_que_floraison(self):
        assert M._profondeur_racinaire_mm("Semis") < M._profondeur_racinaire_mm("Floraison")

    def test_ne_regresse_pas_apres_floraison(self):
        assert M._profondeur_racinaire_mm("Maturation") >= M._profondeur_racinaire_mm("Floraison")

    def test_stade_inconnu_repli_documente(self):
        assert M._profondeur_racinaire_mm("Stade Fantaisiste") == M.PROFONDEUR_RACINAIRE_MM


# =========================================================
# 2) LECTEUR DE MESURES — extraire_grandeurs (format JSONB réel)
# =========================================================
class TestExtraireGrandeurs:
    def test_dht22_deux_grandeurs(self):
        g = extraire_grandeurs("dht22", {"temperature": 27.6, "humidite": 30})
        assert g == {"temperature": 27.6, "humidite_air": 30}

    def test_capacitif_sol(self):
        g = extraire_grandeurs("humidite_sol", {"humidite": 27.6})
        assert g == {"humidite_sol": 27.6}

    def test_ancien_format_tolere(self):
        g = extraire_grandeurs("humidite_sol", {"valeur": 25.0, "unite": "%"})
        assert g == {"humidite_sol": 25.0}

    def test_payload_invalide_vide(self):
        assert extraire_grandeurs("dht22", {"foo": "bar"}) == {}

    def test_type_capteur_inconnu_expose_les_cles_numeriques(self):
        """Repli documenté : un type non reconnu expose les valeurs
        numériques telles quelles (mieux que de les perdre silencieusement)."""
        assert extraire_grandeurs("", {"humidite": 20}) == {"humidite": 20}

    def test_type_capteur_inconnu_ignore_les_cles_non_numeriques(self):
        assert extraire_grandeurs("", {"texte": "bruit"}) == {}


# =========================================================
# 3) VOLUME & DURÉE — dépendent de la SURFACE de la parcelle
# =========================================================
class TestVolumeDuree:
    def test_conversion_litres(self):
        d = M.calcul_volume_duree(5.0, 0.8)  # 5mm x 0.8ha
        assert d["litres_total"] == 40000

    def test_duree_decomposee(self):
        d = M.calcul_volume_duree(5.0, 0.8)
        assert d["minutes"] == 80 and d["secondes"] == 0

    def test_minutes_arrondies_stockees(self):
        d = M.calcul_volume_duree(5.0, 0.8)
        assert d["duree_minutes_arrondi"] == 80

    def test_secondes_millisecondes_sur_valeurs_non_rondes(self):
        d = M.calcul_volume_duree(3.7, 0.55)
        assert d["secondes"] != 0 or d["millisecondes"] != 0

    def test_surface_inconnue_pas_de_duree(self):
        d = M.calcul_volume_duree(5.0, None)
        assert d["duree_minutes_arrondi"] is None

    def test_parcelle_plus_grande_arrosage_plus_long(self):
        petite = M.calcul_volume_duree(5.0, 0.4)
        grande = M.calcul_volume_duree(5.0, 0.8)
        assert grande["duree_minutes_arrondi"] > petite["duree_minutes_arrondi"]


# =========================================================
# 4) ARBRE DE DÉCISION — F0-F5 + A1-A3
# =========================================================
PROFILS = [
    {"stade": "Floraison", "debut_jour": 76, "fin_jour": 125, "kc": 1.15,
     "seuil_bas": 26, "seuil_cible": 33, "humidite_min": 25, "humidite_max": 36},
]
PARCELLE = {"id": 1, "nom": "Test", "lat": 6.02, "superficie": 0.5,
            "date_plantation": (date.today() - timedelta(days=90)).isoformat()}
METEO_SEC = {"disponible": True, "tmin": 24, "tmax": 34, "tmoy": 29, "pluie_mm": 0.0}
METEO_PLUIE = {"disponible": True, "tmin": 22, "tmax": 28, "tmoy": 25, "pluie_mm": 12.0}
METEO_CONFORT = {"disponible": True, "tmin": 23, "tmax": 26, "tmoy": 24.5, "pluie_mm": 5.0}


def _analyser(hum, meteo=METEO_SEC, t_air=None, h_air=None):
    """Exécute analyser_parcelle avec des capteurs simulés (monkeypatch)."""
    orig = M._mesures_capteurs
    M._mesures_capteurs = lambda sb, pid: {
        "humidite_sol": hum, "temperature": t_air, "humidite_air": h_air,
    }
    try:
        return M.analyser_parcelle(MagicMock(), PARCELLE, PROFILS, meteo)
    finally:
        M._mesures_capteurs = orig


class TestArbreDecision:
    def test_etc_toujours_calculee_meme_sans_action(self):
        r = _analyser(32, METEO_CONFORT)
        assert r["prescription"] is None
        assert r["etc_mm"] is not None and r["etc_mm"] > 0

    def test_f0_capteur_muet(self):
        r = _analyser(None)
        p = r["prescription"]
        assert p is not None
        assert "capteur" in p["action"].lower()
        assert "24 heures" in p["justification"]
        assert p["volume_eau"] == 0
        assert r["duree_min"] is None

    def test_f1_stress_severe_priorite_haute(self):
        r = _analyser(23)
        p = r["prescription"]
        assert "lancez l'irrigation" in p["action"].lower()
        assert p["priorite"] == "haute"
        assert p["volume_eau"] > 0
        assert r["duree_min"] is not None

    def test_f1_action_donne_minutes_et_litres(self):
        p = _analyser(23)["prescription"]
        assert "minutes" in p["action"] and "litres" in p["action"].lower()

    def test_f1_signature_moteur_presente(self):
        p = _analyser(23)["prescription"]
        assert M.MARQUE in p["justification"]

    def test_f2_sec_sans_pluie_irrigue(self):
        p = _analyser(25.5, METEO_SEC)["prescription"]
        assert "lancez l'irrigation" in p["action"].lower()
        assert p["priorite"] == "haute"

    def test_f2_pluie_suffisante_reporte(self):
        p = _analyser(25.5, METEO_PLUIE)["prescription"]
        action = p["action"].lower()
        assert "laissez la pluie" in action or "n'arrosez pas" in action
        assert p["volume_eau"] == 0

    def test_f3_entretien_climatique(self):
        p = _analyser(30, METEO_SEC)["prescription"]
        assert "lancez l'irrigation" in p["action"].lower()
        assert p["priorite"] == "moyenne"

    def test_f4_sol_sature_conseille_drainage(self):
        p = _analyser(37)["prescription"]
        assert "n'arrosez pas" in p["action"].lower()
        assert "drainage" in p["action"].lower() or "évacue" in p["action"].lower()
        assert p["volume_eau"] == 0

    def test_f5_plage_confortable_silence(self):
        r = _analyser(32, METEO_CONFORT)
        assert r["prescription"] is None

    def test_a2_canicule_conseille_paillage(self):
        p = _analyser(25.5, METEO_SEC, t_air=36)["prescription"]
        assert "paillez" in p["action"].lower()

    def test_a3_mildiou_air_humide_en_floraison(self):
        p = _analyser(32, METEO_CONFORT, h_air=90)["prescription"]
        assert p is not None
        assert "mildiou" in p["justification"].lower()
        assert p["volume_eau"] == 0

    def test_dose_plafonnee_au_maximum_securite(self):
        p = _analyser(10)["prescription"]
        assert p["volume_eau"] <= M.DOSE_MAX_MM

    def test_justification_appuyee_sur_donnee_reelle(self):
        p = _analyser(24)["prescription"]
        assert "24 %" in p["justification"]


# =========================================================
# 5) GARANTIES DE FORMAT — aucune régression sur les demandes
#    explicites de l'utilisateur au fil du projet
# =========================================================
class TestFormatRecommandation:
    def test_aucun_emoji_goutte(self):
        p = _analyser(24)["prescription"]
        assert "💧" not in p["action"]
        assert "💧" not in p["justification"]

    def test_pas_de_plan_sur_plusieurs_apports(self):
        """Le moteur ne doit JAMAIS planifier plusieurs arrosages à
        l'avance (ex. « matin et soir ») — il se ré-évalue lui-même
        toutes les 5 min sur les mesures réelles suivantes."""
        for hum in (5, 10, 15, 20, 23):
            p = _analyser(hum)["prescription"]
            assert "matin et soir" not in p["action"].lower()
            assert "2 apports" not in p["action"].lower()
            assert "fractionn" not in p["action"].lower()

    def test_pas_de_constante_fractionnement_residuelle(self):
        assert not hasattr(M, "SEUIL_FRACTIONNEMENT_MM")
