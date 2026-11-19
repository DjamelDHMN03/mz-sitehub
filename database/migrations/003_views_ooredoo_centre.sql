-- 003_views_ooredoo_centre.sql
-- Vues analytiques pour le module Suivi Ooredoo Centre.
-- 100 % additif : ne modifie aucune table existante.
-- Peut etre rejoue sans risque (CREATE OR REPLACE VIEW).

-- 1. KPIs globaux du suivi centre
CREATE OR REPLACE VIEW v_dashboard_ooredoo_centre AS
SELECT
    COUNT(*)                                                        AS total_sites,
    COUNT(*) FILTER (WHERE progress_category = 'BOUCLE')           AS sites_boucles,
    COUNT(*) FILTER (WHERE progress_category = 'EN_COURS')         AS sites_en_cours,
    COUNT(*) FILTER (WHERE progress_category = 'BLOQUE')           AS sites_bloques,
    COUNT(*) FILTER (WHERE progress_category IS NULL)               AS sites_sans_categorie,
    ROUND(AVG(doc_b_delay_days)
          FILTER (WHERE doc_b_delay_days IS NOT NULL), 1)           AS delai_moyen_doc_b,
    ROUND(AVG(rent_negotiated)
          FILTER (WHERE rent_negotiated > 0), 0)                    AS loyer_moyen_da,
    COUNT(*) FILTER (WHERE rent_negotiated > 0)                     AS sites_avec_loyer,
    COUNT(*) FILTER (WHERE geom IS NOT NULL)                        AS sites_avec_gps
FROM sites
WHERE deleted_at IS NULL
  AND project IS NOT NULL;

-- 2. Performance par negociateur
CREATE OR REPLACE VIEW v_stats_negociateurs AS
SELECT
    COALESCE(n.name, 'NON ASSIGNE')    AS negociateur,
    n.kind                             AS type_contrat,
    COUNT(s.id)                        AS total_sites,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BOUCLE')    AS boucles,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'EN_COURS')  AS en_cours,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BLOQUE')    AS bloques,
    ROUND(AVG(s.doc_b_delay_days), 1)  AS delai_moyen_doc_b,
    ROUND(AVG(s.rent_negotiated) FILTER (WHERE s.rent_negotiated > 0), 0) AS loyer_moyen_da
FROM sites s
LEFT JOIN negotiators n ON s.negotiator_id = n.id
WHERE s.deleted_at IS NULL
  AND s.project IS NOT NULL
GROUP BY n.name, n.kind
ORDER BY total_sites DESC;

-- 3. Repartition par wilaya
CREATE OR REPLACE VIEW v_sites_par_wilaya AS
SELECT
    COALESCE(w.name, s.commune_name, 'INCONNUE') AS wilaya,
    s.wilaya_id,
    COUNT(s.id)                                   AS total,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BOUCLE')   AS boucles,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'EN_COURS') AS en_cours,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BLOQUE')   AS bloques
FROM sites s
LEFT JOIN wilayas w ON s.wilaya_id = w.id
WHERE s.deleted_at IS NULL
  AND s.project IS NOT NULL
GROUP BY w.name, s.wilaya_id, s.commune_name
ORDER BY total DESC;
