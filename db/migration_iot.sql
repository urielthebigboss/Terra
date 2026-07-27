-- =========================================================
-- TERRA — Migration IoT (prototype capteurs réels ESP32)
-- À exécuter UNE FOIS dans le SQL Editor de Supabase.
-- Idempotent : ré-exécutable sans risque.
-- =========================================================
--
-- CONTEXTE
--   Un NŒUD DE CAPTEURS physique (ESP32 + DHT22 + capacitif) est
--   représenté dans TERRA par DEUX lignes `capteur` sur la MÊME
--   parcelle :
--     - une de type « dht22 »        → température + humidité de l'air
--     - une de type « humidite_sol » → humidité du sol (capacitif)
--   La passerelle envoie un identifiant de nœud (node_id, ex.
--   « SENSOR_NODE_001 »). Pour router chaque grandeur vers le bon
--   capteur, les deux lignes du nœud PARTAGENT le même `node_id`.
--
--   Le backend (services/iot_service.py) résout :
--     node_id + grandeur  →  id_capteur
--   puis insère les mesures au format JSONB habituel (sans unité) :
--     dht22        : {"temperature": 27.6, "humidite": 30}
--     humidite_sol : {"humidite": 45.8}
-- =========================================================

-- 1) Identifiant matériel du nœud sur chaque capteur ------------
alter table capteur add column if not exists node_id text;

-- Recherche rapide « capteurs d'un nœud » lors de l'ingestion.
create index if not exists idx_capteur_node_id on capteur (node_id);

comment on column capteur.node_id is
  'Identifiant du nœud IoT physique (ESP32). Les capteurs dht22 et '
  'humidite_sol d''un même nœud partagent ce node_id. NULL pour les '
  'capteurs non rattachés à un nœud réel.';

-- 2) (Optionnel mais recommandé) garde-fou anti-doublon ---------
--    Empêche d'insérer deux fois la MÊME mesure (même capteur, même
--    horodatage) en cas de renvoi réseau de la passerelle. Le backend
--    vérifie déjà l'existence avant insert ; cet index rend la garantie
--    atomique côté base. On l'ignore si des doublons historiques
--    existent déjà (créer l'index échouerait) — à activer sur une base
--    propre.
-- create unique index if not exists uq_mesure_capteur_date
--   on mesure (id_capteur, date);

-- =========================================================
-- EXEMPLE DE PROVISIONING D'UN NŒUD (à adapter à vos parcelles)
-- Remplacez :ID_PARCELLE par l'id réel d'une de vos parcelles.
-- =========================================================
-- insert into capteur (id_parcelle, nom, type, unite, etat, node_id, emplacement)
-- values
--   (:ID_PARCELLE, 'DHT22 — air (nœud 001)',      'dht22',        '°C/%', 'actif', 'SENSOR_NODE_001', 'Abri météo — rang central'),
--   (:ID_PARCELLE, 'Capacitif — sol (nœud 001)',  'humidite_sol', '%',    'actif', 'SENSOR_NODE_001', 'Zone racinaire — 15 cm');
