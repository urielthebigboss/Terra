-- =========================================================
-- TERRA — SQL de RÉFÉRENCE pour les tables météo
-- Votre base Supabase est déjà conçue : ce fichier sert à
-- VÉRIFIER que vos tables correspondent à ce que le backend
-- attend (noms de tables et de colonnes).
-- Si vos noms diffèrent, adaptez TABLE_MESURES / TABLE_PREVISIONS
-- dans app/services/meteo_service.py.
-- =========================================================

-- Conditions actuelles, horodatées (une ligne par synchronisation)
create table if not exists meteo_mesures (
  id             uuid primary key default gen_random_uuid(),
  parcelle_id    text,                    -- parcelle associée (optionnel)
  lat            double precision not null,
  lon            double precision not null,
  temperature    double precision not null,  -- °C
  humidite       double precision not null,  -- %
  pression       double precision,           -- hPa
  vent_vitesse   double precision,           -- m/s
  vent_direction double precision,           -- degrés
  pluie_1h       double precision default 0, -- mm sur la dernière heure
  nuages         double precision,           -- % de couverture
  description    text,                       -- ex. « ciel dégagé »
  mesure_le      timestamptz not null,       -- horodatage de la mesure
  cree_le        timestamptz default now()
);

-- Index : la lecture « dernière mesure » est le chemin chaud du dashboard
create index if not exists idx_meteo_mesures_date on meteo_mesures (mesure_le desc);

-- Prévisions 5 jours / pas de 3 h (remplacées à chaque synchronisation)
create table if not exists meteo_previsions (
  id           uuid primary key default gen_random_uuid(),
  lat          double precision not null,
  lon          double precision not null,
  prevu_pour   timestamptz not null,        -- échéance de la prévision
  temperature  double precision not null,   -- °C
  humidite     double precision not null,   -- %
  pluie_3h     double precision default 0,  -- mm sur le créneau de 3 h
  vent_vitesse double precision,            -- m/s
  description  text,
  recupere_le  timestamptz not null         -- date de récupération du lot
);

create index if not exists idx_meteo_previsions_echeance on meteo_previsions (prevu_pour asc);
