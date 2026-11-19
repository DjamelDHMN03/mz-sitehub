-- ============================================================
-- MZ SITEHUB — Migration 002 : index manquants sur les clés étrangères
-- Découvert lors de l'audit d'optimisation (Phase 23, section 84).
--
-- PostgreSQL n'indexe PAS automatiquement les colonnes de clé étrangère
-- (contrairement à la clé primaire). Toutes les routes construites depuis
-- la Phase 10 filtrent par site_id/contact_id/document_id/contract_id sans
-- qu'aucun index ne les couvre — un simple SELECT ... WHERE site_id = X
-- ferait un scan complet de la table dès que le volume grossit
-- (10 000 sites / 100 000 documents, cible affichée en section 84).
--
-- Convention : migration additive, ne modifie jamais la migration 001.
-- ============================================================

-- --- CRM Contacts ---
CREATE INDEX idx_contacts_site_id ON contacts (site_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_contact_interactions_contact_id ON contact_interactions (contact_id);
CREATE INDEX idx_contact_interactions_site_id ON contact_interactions (site_id);

-- --- GED ---
CREATE INDEX idx_documents_site_id ON documents (site_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_category ON documents (category) WHERE deleted_at IS NULL;
CREATE INDEX idx_document_versions_document_id ON document_versions (document_id);

-- --- Doc B / APS ---
CREATE INDEX idx_doc_b_site_id ON doc_b (site_id);
CREATE INDEX idx_aps_documents_site_id ON aps_documents (site_id);

-- --- Contrats ---
CREATE INDEX idx_contracts_site_id ON contracts (site_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_contracts_date_expiration ON contracts (date_expiration) WHERE deleted_at IS NULL;
CREATE INDEX idx_contract_signatories_contract_id ON contract_signatories (contract_id);

-- --- Tâches / Actions (section 54-56, filtré par site/statut/échéance) ---
CREATE INDEX idx_tasks_site_id ON tasks (site_id);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_due_date ON tasks (due_date);
CREATE INDEX idx_tasks_responsible_user_id ON tasks (responsible_user_id);

-- --- Cartographie ---
CREATE INDEX idx_map_features_layer_id ON map_features (layer_id);
CREATE INDEX idx_map_feature_sites_map_feature_id ON map_feature_sites (map_feature_id);
CREATE INDEX idx_map_feature_sites_site_id ON map_feature_sites (site_id);

-- --- Partage documentaire (section 47 : vérifié à chaque téléchargement) ---
CREATE INDEX idx_document_share_links_site_id ON document_share_links (site_id);
CREATE INDEX idx_document_share_history_link_id ON document_share_history (share_link_id);
CREATE INDEX idx_document_share_recipients_link_id ON document_share_recipients (share_link_id);
-- Remarque : document_share_links.token a déjà un index implicite via sa
-- contrainte UNIQUE (migration 001) — pas dupliqué ici.

-- --- RAG ---
CREATE INDEX idx_ai_document_chunks_document_id ON ai_document_chunks (document_id);
CREATE INDEX idx_ai_messages_conversation_id ON ai_messages (conversation_id);

-- --- Notifications / Historique ---
CREATE INDEX idx_notifications_user_id ON notifications (user_id) WHERE is_read IS FALSE;
CREATE INDEX idx_site_history_site_id ON site_history (site_id);

-- ============================================================
-- Fin migration 002
-- ============================================================
