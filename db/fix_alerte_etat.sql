-- =========================================================
-- TERRA — CORRECTIF à exécuter dans Supabase (SQL Editor)
--
-- Problème détecté : le type enum « etat_capteur » de la colonne
-- alerte.etat a été créé avec une coquille — il ne contient qu'UNE
-- valeur littérale : 'active, en_panne' (la virgule est à l'intérieur
-- des guillemets). Résultat : AUCUN état d'alerte valide ne peut être
-- inséré ('en_attente', 'repare'… sont tous refusés).
--
-- Correction : on repasse la colonne en texte simple, comme les
-- autres colonnes d'état du projet (capteur.etat, prescription.etat).
-- =========================================================

alter table alerte alter column etat drop default;
alter table alerte alter column etat type text using etat::text;
alter table alerte alter column etat set default 'en_attente';

-- L'enum défectueux n'est plus utilisé par aucune table : on le supprime.
drop type if exists etat_capteur;
