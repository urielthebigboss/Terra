-- =========================================================
-- TERRA — Politiques RLS (Row Level Security) pour TOUTES les tables
-- À exécuter dans Supabase (Dashboard → SQL Editor). Idempotent :
-- ré-exécutable sans erreur.
--
-- POURQUOI : le backend utilise la clé service_role, qui CONTOURNE
-- le RLS — il applique déjà les règles métier dans ses services.
-- Ces politiques sont la DEUXIÈME ligne de défense : si la clé anon
-- fuit (elle est visible côté client), la base reste protégée et
-- chacun ne voit que ce qui lui appartient.
--
-- RÈGLE MÉTIER TRADUITE ICI :
--   - l'ADMINISTRATEUR voit et gère tout ;
--   - l'AGRICULTEUR ne voit que SES données (parcelles → capteurs
--     → mesures / prescriptions / alertes) ;
--   - les personnes non connectées (rôle anon) n'ont accès à RIEN
--     (aucune politique ne les mentionne → tout est refusé).
-- =========================================================


-- ---------------------------------------------------------
-- 0) FONCTIONS D'AIDE
-- SECURITY DEFINER : elles lisent administrateur/agriculteur en
-- ignorant le RLS de l'appelant — indispensable pour éviter la
-- récursion (la politique de `agriculteur` appelle une fonction
-- qui lit `agriculteur`…).
-- ---------------------------------------------------------
create or replace function public.est_admin()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from administrateur where id_uuid = auth.uid()
  );
$$;

create or replace function public.mon_id_agriculteur()
returns bigint
language sql stable security definer
set search_path = public
as $$
  select id from agriculteur where id_uuid = auth.uid();
$$;


-- ---------------------------------------------------------
-- 1) ADMINISTRATEUR — table sensible : lisible par les admins
-- seulement ; jamais modifiable via l'API publique (le backend
-- passe par service_role, qui ignore le RLS).
-- ---------------------------------------------------------
alter table administrateur enable row level security;

drop policy if exists "admin_select" on administrateur;
create policy "admin_select" on administrateur
  for select to authenticated
  using (est_admin());
-- Pas de politique insert/update/delete → refusés pour tous
-- (seul le backend service_role peut écrire).


-- ---------------------------------------------------------
-- 2) AGRICULTEUR — l'admin voit tout ; un agriculteur ne voit
-- que sa propre fiche. Création/suppression : backend uniquement
-- (elles impliquent aussi Supabase Auth).
-- ---------------------------------------------------------
alter table agriculteur enable row level security;

drop policy if exists "agriculteur_select" on agriculteur;
create policy "agriculteur_select" on agriculteur
  for select to authenticated
  using (est_admin() or id_uuid = auth.uid());

drop policy if exists "agriculteur_update_admin" on agriculteur;
create policy "agriculteur_update_admin" on agriculteur
  for update to authenticated
  using (est_admin())
  with check (est_admin());


-- ---------------------------------------------------------
-- 3) PARCELLE — cœur du cloisonnement : tout le reste (capteurs,
-- mesures, prescriptions) hérite de la propriété de la parcelle.
-- ---------------------------------------------------------
alter table parcelle enable row level security;

drop policy if exists "parcelle_select" on parcelle;
create policy "parcelle_select" on parcelle
  for select to authenticated
  using (est_admin() or id_agriculteur = mon_id_agriculteur());

drop policy if exists "parcelle_insert" on parcelle;
create policy "parcelle_insert" on parcelle
  for insert to authenticated
  -- seul l'ADMIN crée les parcelles (et les attribue à un agriculteur)
  with check (est_admin());

drop policy if exists "parcelle_update" on parcelle;
create policy "parcelle_update" on parcelle
  for update to authenticated
  -- l'agriculteur ne touche que SA parcelle (le backend limite en plus
  -- ses modifications à date_plantation) ; l'admin modifie tout
  using (est_admin() or id_agriculteur = mon_id_agriculteur())
  -- empêche de « donner » sa parcelle à un autre agriculteur
  with check (est_admin() or id_agriculteur = mon_id_agriculteur());

drop policy if exists "parcelle_delete" on parcelle;
create policy "parcelle_delete" on parcelle
  for delete to authenticated
  using (est_admin());


-- ---------------------------------------------------------
-- 4) CAPTEUR — accessible si la parcelle m'appartient (ou admin).
-- NB : la règle « seul l'admin change l'ÉTAT » est une règle de
-- COLONNE, hors de portée du RLS (qui filtre des LIGNES) — elle
-- reste garantie par le backend (capteur_service.modifier).
-- ---------------------------------------------------------
alter table capteur enable row level security;

drop policy if exists "capteur_select" on capteur;
create policy "capteur_select" on capteur
  for select to authenticated
  using (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = capteur.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "capteur_insert" on capteur;
create policy "capteur_insert" on capteur
  for insert to authenticated
  with check (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = capteur.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "capteur_update" on capteur;
create policy "capteur_update" on capteur
  for update to authenticated
  using (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = capteur.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  )
  with check (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = capteur.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "capteur_delete_admin" on capteur;
create policy "capteur_delete_admin" on capteur
  for delete to authenticated
  using (est_admin());  -- retirer un capteur du parc = admin


-- ---------------------------------------------------------
-- 5) ALERTE — l'agriculteur crée (signalement) et suit SES alertes ;
-- l'admin voit tout et fait avancer le workflow.
-- ---------------------------------------------------------
alter table alerte enable row level security;

drop policy if exists "alerte_select" on alerte;
create policy "alerte_select" on alerte
  for select to authenticated
  using (est_admin() or id_agriculteur = mon_id_agriculteur());

drop policy if exists "alerte_insert" on alerte;
create policy "alerte_insert" on alerte
  for insert to authenticated
  with check (
    est_admin()
    or (
      -- je signale en mon nom…
      id_agriculteur = mon_id_agriculteur()
      -- …et uniquement sur un capteur d'une de MES parcelles
      and exists (
        select 1 from capteur c
        join parcelle p on p.id = c.id_parcelle
        where c.id = alerte.id_capteur
          and p.id_agriculteur = mon_id_agriculteur()
      )
    )
  );

drop policy if exists "alerte_update_admin" on alerte;
create policy "alerte_update_admin" on alerte
  for update to authenticated
  using (est_admin())          -- seul l'admin change l'état
  with check (est_admin());

drop policy if exists "alerte_delete_admin" on alerte;
create policy "alerte_delete_admin" on alerte
  for delete to authenticated
  using (est_admin());


-- ---------------------------------------------------------
-- 6) MESURE — lisible si le capteur est sur une de mes parcelles.
-- Une mesure ne se modifie JAMAIS (donnée brute de capteur) :
-- pas de politique update. Suppression : admin seulement.
-- Les capteurs IoT réels écriront via le backend (service_role).
-- ---------------------------------------------------------
alter table mesure enable row level security;

drop policy if exists "mesure_select" on mesure;
create policy "mesure_select" on mesure
  for select to authenticated
  using (
    est_admin() or exists (
      select 1 from capteur c
      join parcelle p on p.id = c.id_parcelle
      where c.id = mesure.id_capteur
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "mesure_insert" on mesure;
create policy "mesure_insert" on mesure
  for insert to authenticated
  with check (
    est_admin() or exists (
      select 1 from capteur c
      join parcelle p on p.id = c.id_parcelle
      where c.id = mesure.id_capteur
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "mesure_delete_admin" on mesure;
create policy "mesure_delete_admin" on mesure
  for delete to authenticated
  using (est_admin());


-- ---------------------------------------------------------
-- 7) PRESCRIPTION — l'agriculteur lit celles de SES parcelles et
-- les marque « faites » (update). Le Moteur Expert écrira via le
-- backend (service_role), donc pas concerné par ces politiques.
-- ---------------------------------------------------------
alter table prescription enable row level security;

drop policy if exists "prescription_select" on prescription;
create policy "prescription_select" on prescription
  for select to authenticated
  using (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = prescription.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "prescription_insert" on prescription;
create policy "prescription_insert" on prescription
  for insert to authenticated
  with check (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = prescription.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "prescription_update" on prescription;
create policy "prescription_update" on prescription
  for update to authenticated
  using (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = prescription.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  )
  with check (
    est_admin() or exists (
      select 1 from parcelle p
      where p.id = prescription.id_parcelle
        and p.id_agriculteur = mon_id_agriculteur()
    )
  );

drop policy if exists "prescription_delete_admin" on prescription;
create policy "prescription_delete_admin" on prescription
  for delete to authenticated
  using (est_admin());


-- ---------------------------------------------------------
-- 8) PROFIL_CULTURE — référentiel agronomique (stades, Kc, seuils) :
-- lecture pour tout utilisateur connecté, écriture réservée admin.
-- ---------------------------------------------------------
alter table profil_culture enable row level security;

drop policy if exists "profil_culture_select" on profil_culture;
create policy "profil_culture_select" on profil_culture
  for select to authenticated
  using (true);

drop policy if exists "profil_culture_insert_admin" on profil_culture;
create policy "profil_culture_insert_admin" on profil_culture
  for insert to authenticated
  with check (est_admin());

drop policy if exists "profil_culture_update_admin" on profil_culture;
create policy "profil_culture_update_admin" on profil_culture
  for update to authenticated
  using (est_admin())
  with check (est_admin());

drop policy if exists "profil_culture_delete_admin" on profil_culture;
create policy "profil_culture_delete_admin" on profil_culture
  for delete to authenticated
  using (est_admin());


-- ---------------------------------------------------------
-- 9) MÉTÉO (meteo_mesures, meteo_previsions) — données communes,
-- non sensibles : lecture pour tout connecté. Écriture : uniquement
-- le backend lors du sync OpenWeather (service_role → pas de
-- politique nécessaire).
-- ---------------------------------------------------------
alter table meteo_mesures enable row level security;

drop policy if exists "meteo_mesures_select" on meteo_mesures;
create policy "meteo_mesures_select" on meteo_mesures
  for select to authenticated
  using (true);

alter table meteo_previsions enable row level security;

drop policy if exists "meteo_previsions_select" on meteo_previsions;
create policy "meteo_previsions_select" on meteo_previsions
  for select to authenticated
  using (true);


-- =========================================================
-- VÉRIFICATION RAPIDE (à lancer après exécution) :
--   select tablename, policyname, cmd
--   from pg_policies where schemaname = 'public'
--   order by tablename, policyname;
-- Toutes les tables doivent aussi afficher rowsecurity = true :
--   select relname, relrowsecurity from pg_class
--   where relnamespace = 'public'::regnamespace and relkind = 'r';
-- =========================================================
