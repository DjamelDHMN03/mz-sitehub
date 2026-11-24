-- 005 : suivi Energie par site et historique des versements provisoires
-- Additif : ne modifie pas les tables existantes.

CREATE TABLE IF NOT EXISTS public.site_energy (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid NOT NULL UNIQUE
    REFERENCES public.sites(id) ON DELETE CASCADE,

-- SONELGAZ ou SOUS_COMPTAGE
  mode text NOT NULL DEFAULT 'SONELGAZ'
    CHECK (mode IN ('SONELGAZ', 'SOUS_COMPTAGE')),

demande_deposee boolean NOT NULL DEFAULT false,
  demande_deposee_le date,
  etude_effectuee boolean NOT NULL DEFAULT false,
  etude_effectuee_le date,
  devis_paye boolean NOT NULL DEFAULT false,
  devis_paye_le date,
  site_raccorde boolean NOT NULL DEFAULT false,
  site_raccorde_le date,

sous_comptage_permanent boolean NOT NULL DEFAULT false,

-- Provisoire facultatif pendant l'attente du raccordement Sonelgaz
  provisoire_actif boolean NOT NULL DEFAULT false,
  provisoire_debut date,
  provisoire_fin date,
  montant_mensuel integer NOT NULL DEFAULT 18000
    CHECK (montant_mensuel >= 0),

necessite_extension boolean NOT NULL DEFAULT false,
  aps_pret boolean NOT NULL DEFAULT false,
  plan_situation_pret boolean NOT NULL DEFAULT false,
  demande_sonelgaz_prete boolean NOT NULL DEFAULT false,

observation text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Complète une éventuelle table créée avec la requête antérieure.
ALTER TABLE public.site_energy
  ADD COLUMN IF NOT EXISTS demande_deposee boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS demande_deposee_le date,
  ADD COLUMN IF NOT EXISTS etude_effectuee boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS etude_effectuee_le date,
  ADD COLUMN IF NOT EXISTS devis_paye boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS devis_paye_le date,
  ADD COLUMN IF NOT EXISTS site_raccorde boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS site_raccorde_le date,
  ADD COLUMN IF NOT EXISTS sous_comptage_permanent boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS provisoire_actif boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS provisoire_debut date,
  ADD COLUMN IF NOT EXISTS provisoire_fin date,
  ADD COLUMN IF NOT EXISTS montant_mensuel integer NOT NULL DEFAULT 18000,
  ADD COLUMN IF NOT EXISTS necessite_extension boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS aps_pret boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS plan_situation_pret boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS demande_sonelgaz_prete boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS observation text,
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.site_energy_payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid NOT NULL
    REFERENCES public.sites(id) ON DELETE CASCADE,
  mois date NOT NULL CHECK (EXTRACT(DAY FROM mois) = 1),
  date_paiement date NOT NULL DEFAULT current_date,
  montant integer NOT NULL DEFAULT 18000 CHECK (montant >= 0),
  observation text,
  created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_site_energy_payments_site_mois
  ON public.site_energy_payments (site_id, mois);

CREATE INDEX IF NOT EXISTS idx_site_energy_payments_mois
  ON public.site_energy_payments (mois);

-- Les autorisations sont vérifiées par le backend FastAPI.
-- Aucune règle RLS n'est activée ici.
