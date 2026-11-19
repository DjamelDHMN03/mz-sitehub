CREATE OR REPLACE VIEW v_dashboard_ooredoo_centre AS
SELECT
    COUNT(s.id) AS total_sites,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BOUCLE') AS sites_boucles,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'EN_COURS') AS sites_en_cours,
    COUNT(s.id) FILTER (WHERE s.progress_category = 'BLOQUE') AS sites_bloques,
    COUNT(s.id) FILTER (WHERE COALESCE(pr.needs_review, FALSE) IS TRUE) AS sites_a_verifier,
    COUNT(s.id) FILTER (WHERE s.doc_b_date IS NOT NULL) AS sites_doc_b,
    COUNT(s.id) FILTER (WHERE s.tss_date IS NOT NULL) AS sites_tss,
    COUNT(s.id) FILTER (WHERE s.contract_date IS NOT NULL) AS sites_contrats,
    ROUND(AVG(s.rent_negotiated)::numeric, 2) AS loyer_moyen,
    ROUND(AVG(s.doc_b_delay_days)::numeric, 1) AS delai_moyen_doc_b_jours,
    ROUND(
        (
            COUNT(s.id) FILTER (WHERE s.progress_category = 'BOUCLE')::numeric
            / NULLIF(COUNT(s.id), 0)
        ) * 100,
        2
    ) AS taux_boucle_pct
FROM sites s
LEFT JOIN progress_rules pr
    ON pr.progress_key = s.progress_raw;
