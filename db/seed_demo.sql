-- =========================================================
-- TERRA — Jeu de données de démonstration (INSERTs)
--
-- ⚠️ OBSOLÈTE DEPUIS LE PASSAGE EN PRODUCTION (2026-07-16) :
-- le format des mesures a changé (voir db/migration_prod.sql) et
-- les données doivent venir des capteurs réels. Conservé pour
-- référence historique uniquement — NE PLUS EXÉCUTER tel quel.
--
-- ⚠️ CES DONNÉES ONT DÉJÀ ÉTÉ INSÉRÉES le 2026-07-15 (via l'API).
-- Chaque insert est protégé par WHERE NOT EXISTS : vous pouvez
-- ré-exécuter ce fichier sans créer de doublons. Pour repartir
-- de zéro : videz d'abord les tables (section tout en bas).
--
-- Le jeu de données est ALIGNÉ sur votre table profil_culture
-- (humidité volumétrique du sol : seuils 20–33 %, cycle 200 j) :
--   - Parcelle Nord : plantée il y a 90 j  → stade Floraison
--   - Parcelle Sud  : plantée il y a 20 j  → stade Levée / reprise
-- =========================================================

-- ---------------------------------------------------------
-- 1) PARCELLES — attribuées à l'agriculteur Dakaud
-- ---------------------------------------------------------
insert into parcelle (id_agriculteur, nom, culture, date_plantation, superficie, lat, lon)
select (select id from agriculteur where email = 'dakaudjury@gmail.com'),
       'Parcelle Nord', 'Tomate', current_date - 90, 0.8, 6.02078, -4.36861
where not exists (select 1 from parcelle where nom = 'Parcelle Nord');

insert into parcelle (id_agriculteur, nom, culture, date_plantation, superficie, lat, lon)
select (select id from agriculteur where email = 'dakaudjury@gmail.com'),
       'Parcelle Sud', 'Tomate', current_date - 20, 0.4, 6.01950, -4.37020
where not exists (select 1 from parcelle where nom = 'Parcelle Sud');

-- ---------------------------------------------------------
-- 2) CAPTEURS — types reconnus par le frontend :
--    humidite_sol (%) | temperature_air (°C) | humidite_air (%) | pluie (mm)
-- ---------------------------------------------------------
insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Nord'),
       'Sonde humidité sol — rang 3', 'humidite_sol', '%', 'actif', 88, 'Zone racinaire — rang 3'
where not exists (select 1 from capteur where nom = 'Sonde humidité sol — rang 3');

insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Nord'),
       'Capteur air DHT22 — nord', 'temperature_air', '°C', 'actif', 76, 'Poteau nord'
where not exists (select 1 from capteur where nom = 'Capteur air DHT22 — nord');

insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Nord'),
       'Hygromètre air — nord', 'humidite_air', '%', 'actif', 81, 'Poteau nord'
where not exists (select 1 from capteur where nom = 'Hygromètre air — nord');

insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Nord'),
       'Pluviomètre — abri', 'pluie', 'mm', 'panne', 12, 'Abri technique'
where not exists (select 1 from capteur where nom = 'Pluviomètre — abri');

insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Sud'),
       'Sonde humidité sol — rang 1', 'humidite_sol', '%', 'actif', 95, 'Zone racinaire — rang 1'
where not exists (select 1 from capteur where nom = 'Sonde humidité sol — rang 1');

insert into capteur (id_parcelle, nom, type, unite, etat, batterie, emplacement)
select (select id from parcelle where nom = 'Parcelle Sud'),
       'Capteur air DHT22 — sud', 'temperature_air', '°C', 'actif', 90, 'Poteau sud'
where not exists (select 1 from capteur where nom = 'Capteur air DHT22 — sud');

-- ---------------------------------------------------------
-- 3) MESURES — 7 jours d'historique, 1 mesure / 6 h / capteur actif.
--    Valeurs alignées sur profil_culture :
--    humidité du sol 20–34 %, température 22–35 °C, air 45–90 %.
-- ---------------------------------------------------------
insert into mesure (id_capteur, date, donnees)
select c.id,
       now() - (n * interval '6 hours'),
       jsonb_build_object(
         'valeur',
         round(case c.type
           when 'humidite_sol'    then 27 + 6*sin(n/3.0) + (random()*3 - 1.5)
           when 'temperature_air' then 28 + 5*sin(n/2.0) + (random()*2 - 1)
           when 'humidite_air'    then 65 + 15*sin(n/2.5) + (random()*6 - 3)
           else case when random() < 0.8 then 0 else round((random()*7)::numeric, 1) end
         end::numeric, 1),
         'unite', c.unite)
from capteur c, generate_series(0, 27) n
where c.etat = 'actif'
  and not exists (select 1 from mesure m where m.id_capteur = c.id);

-- ---------------------------------------------------------
-- 4) PRESCRIPTIONS — historique « fait » + missions à faire
--    (volumes en L/m² ; justifications alignées sur vos seuils)
-- ---------------------------------------------------------
insert into prescription (id_parcelle, date, action, justification, volume_eau, priorite, etat, date_faite)
select p.id, d.date, d.action, d.justification, d.volume_eau, d.priorite, d.etat, d.date_faite
from parcelle p
join (values
  ('Parcelle Nord', current_date,     'Irriguer 12 L/m²',      'Humidité du sol à 24 % — sous le seuil bas (26 %) du stade Floraison, aucune pluie significative prévue.', 12.0, 'haute',   'a_faire', null),
  ('Parcelle Nord', current_date,     'Vérifier le paillage',  'Températures > 33 °C annoncées : limiter l''évaporation pendant la floraison.',                            0.0, 'moyenne', 'a_faire', null),
  ('Parcelle Nord', current_date - 1, 'Irriguer 10 L/m²',      'Humidité à 23 % en fin de journée chaude — retour vers la cible (33 %).',                                 10.0, 'haute',   'faite',   current_date - 1),
  ('Parcelle Nord', current_date - 3, 'Irrigation reportée',   'Pluie de 6 mm enregistrée par le pluviomètre — réserve du sol suffisante.',                                0.0, 'basse',   'faite',   current_date - 3),
  ('Parcelle Nord', current_date - 5, 'Irriguer 14 L/m²',      'Deux jours consécutifs sous le seuil bas pendant la floraison.',                                          14.0, 'haute',   'faite',   current_date - 5),
  ('Parcelle Sud',  current_date,     'Irriguer 6 L/m²',       'Jeune plant en levée : maintenir l''humidité près de la cible (30 %) — arrosages courts et fréquents.',    6.0, 'moyenne', 'a_faire', null),
  ('Parcelle Sud',  current_date - 2, 'Irriguer 5 L/m²',       'Humidité à 24 % — la levée est très sensible au stress hydrique.',                                         5.0, 'moyenne', 'faite',   current_date - 2),
  ('Parcelle Sud',  current_date - 4, 'Irriguer 5 L/m²',       'Sol proche du seuil bas après deux jours sans pluie.',                                                     5.0, 'moyenne', 'faite',   current_date - 4)
) as d(parcelle, date, action, justification, volume_eau, priorite, etat, date_faite)
  on d.parcelle = p.nom
where not exists (select 1 from prescription where id_parcelle = p.id);

-- ---------------------------------------------------------
-- 5) ALERTES — le pluviomètre en panne (workflow admin) +
--    une alerte déjà clôturée (historique)
-- ---------------------------------------------------------
insert into alerte (date, texte, etat, id_capteur, id_agriculteur)
select current_date, '[Pluviomètre — abri] Batterie critique (12 %) — ne remonte plus de données depuis cette nuit.',
       'en_attente',
       (select id from capteur where nom = 'Pluviomètre — abri'),
       (select id from agriculteur where email = 'dakaudjury@gmail.com')
where not exists (select 1 from alerte where texte like '%Pluviomètre — abri%');

insert into alerte (date, texte, etat, id_capteur, id_agriculteur)
select current_date - 6, '[Capteur air DHT22 — nord] Micro-coupures réseau détectées puis rétablies.',
       'cloture',
       (select id from capteur where nom = 'Capteur air DHT22 — nord'),
       (select id from agriculteur where email = 'dakaudjury@gmail.com')
where not exists (select 1 from alerte where texte like '%Micro-coupures%');

-- =========================================================
-- POUR REPARTIR DE ZÉRO (décommentez puis ré-exécutez le fichier) :
-- delete from mesure; delete from prescription; delete from alerte;
-- delete from capteur; delete from parcelle;
-- =========================================================
