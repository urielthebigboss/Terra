-- =========================================================
-- TERRA — MIGRATION PRODUCTION (à exécuter dans Supabase,
-- Dashboard → SQL Editor → Run). Idempotent : ré-exécutable.
--
-- 1) parcelle.eau_utilisee   : consommation d'eau TOTALE et réelle
--    de la parcelle (L/m²). Cumulée par le backend à chaque mission
--    validée par l'agriculteur. Sert à toutes les statistiques.
-- 2) parcelle.evaporation_mm : dernière évapotranspiration ETc
--    calculée par le moteur expert (mm/jour), affichée en temps réel.
-- 3) Migration du format des mesures : le JSONB ne stocke plus
--    d'unité, et porte des clés par grandeur (le DHT22 envoie
--    deux valeurs dans la même mesure) :
--        capacitif sol : {"humidite": 27.6}
--        DHT22         : {"temperature": 27.6, "humidite": 30}
-- =========================================================

-- ---------------------------------------------------------
-- 1) + 2) Nouvelles colonnes de parcelle
-- ---------------------------------------------------------
alter table parcelle add column if not exists eau_utilisee double precision not null default 0;
alter table parcelle add column if not exists evaporation_mm double precision;
-- Nombre de plants de la parcelle (affiché dans les détails)
alter table parcelle add column if not exists nombre_plant integer;

-- ---------------------------------------------------------
-- 4) prescription.duree_irrigation_minutes : durée d'arrosage
--    recommandée (minutes), calculée par le moteur expert à partir
--    du volume total et du débit du réseau.
-- ---------------------------------------------------------
alter table prescription add column if not exists duree_irrigation_minutes integer;

-- Reprise d'historique : l'eau déjà appliquée (missions validées)
-- initialise le compteur — uniquement si le compteur est encore à 0.
update parcelle p
set eau_utilisee = coalesce(
  (select sum(volume_eau) from prescription
   where id_parcelle = p.id and etat = 'faite'), 0)
where p.eau_utilisee = 0;

-- ---------------------------------------------------------
-- 3) Migration du JSONB des mesures existantes
--    (ancien format {"valeur": x, "unite": u} → nouveau format)
-- ---------------------------------------------------------
-- Capteurs d'humidité du sol → {"humidite": x}
update mesure m
set donnees = jsonb_build_object('humidite', (m.donnees->>'valeur')::numeric)
from capteur c
where c.id = m.id_capteur
  and c.type = 'humidite_sol'
  and m.donnees ? 'valeur';

-- Anciens capteurs « temperature_air » → {"temperature": x}
update mesure m
set donnees = jsonb_build_object('temperature', (m.donnees->>'valeur')::numeric)
from capteur c
where c.id = m.id_capteur
  and c.type = 'temperature_air'
  and m.donnees ? 'valeur';

-- Anciens capteurs « humidite_air » → {"humidite": x}
update mesure m
set donnees = jsonb_build_object('humidite', (m.donnees->>'valeur')::numeric)
from capteur c
where c.id = m.id_capteur
  and c.type = 'humidite_air'
  and m.donnees ? 'valeur';

-- Pluviomètres → {"pluie": x}
update mesure m
set donnees = jsonb_build_object('pluie', (m.donnees->>'valeur')::numeric)
from capteur c
where c.id = m.id_capteur
  and c.type = 'pluie'
  and m.donnees ? 'valeur';

-- ---------------------------------------------------------
-- VÉRIFICATION (après exécution) :
--   select donnees from mesure limit 5;             → plus de clé "valeur"
--   select nom, eau_utilisee, evaporation_mm from parcelle;
-- =========================================================
