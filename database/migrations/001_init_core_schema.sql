-- ============================================================
-- MZ SITEHUB — Migration 001 : schéma cœur
-- PostgreSQL 15+
-- Convention : toutes les tables métier ont :
--   id UUID, created_at, updated_at, deleted_at (soft delete)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "postgis";       -- géométries (points/lignes/polygones)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- recherche floue (codes, noms)
CREATE EXTENSION IF NOT EXISTS "citext";        -- casse insensible pour emails
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector pour les embeddings IA

-- ------------------------------------------------------------
-- 1. RÉFÉRENTIEL GÉOGRAPHIQUE ALGÉRIE
-- ------------------------------------------------------------
CREATE TABLE wilayas (
    id          SMALLINT PRIMARY KEY,      -- code officiel 01-58
    name        TEXT NOT NULL
);

CREATE TABLE communes (
    id          SERIAL PRIMARY KEY,
    wilaya_id   SMALLINT NOT NULL REFERENCES wilayas(id),
    daira       TEXT,
    name        TEXT NOT NULL
);

-- ------------------------------------------------------------
-- 2. UTILISATEURS / RÔLES (RBAC)
-- ------------------------------------------------------------
CREATE TABLE roles (
    id          SMALLSERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,      -- ADMIN, MANAGER, ACQUISITION, LECTURE
    label       TEXT NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO roles (code, label, permissions) VALUES
 ('ADMIN', 'Administrateur', '{"all": true}'),
 ('MANAGER', 'Manager', '{"sites": "write", "contacts": "write", "contracts": "write", "users": "read"}'),
 ('ACQUISITION', 'Acquisition', '{"sites": "write_own", "contacts": "write_own"}'),
 ('LECTURE', 'Lecture seule', '{"*": "read"}');

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    role_id         SMALLINT NOT NULL REFERENCES roles(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

-- CITEXT nécessite l'extension ; sinon fallback TEXT + index unique lower(email)
CREATE EXTENSION IF NOT EXISTS citext;

-- ------------------------------------------------------------
-- 3. STATUTS CONFIGURABLES (workflow acquisition)
-- ------------------------------------------------------------
CREATE TABLE site_status (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,
    label       TEXT NOT NULL,
    color       TEXT NOT NULL DEFAULT '#4C9FE8',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO site_status (code, label, color, sort_order) VALUES
 ('NOUVEAU', 'Nouveau', '#B15CC9', 1),
 ('RECHERCHE_TERRAIN', 'Recherche terrain', '#B15CC9', 2),
 ('PROPOSITION', 'Proposition', '#4C9FE8', 3),
 ('DOCB_A_PREPARER', 'Doc B à préparer', '#4C9FE8', 4),
 ('DOCB_DEPOSE', 'Doc B déposé', '#4C9FE8', 5),
 ('ACCORD_PRINCIPE', 'Accord de principe', '#4C9FE8', 6),
 ('NEGOCIATION', 'En négociation', '#E0A438', 7),
 ('ATTENTE_DOCUMENTS', 'En attente documents', '#E0A438', 8),
 ('APS_DEMANDE', 'APS demandé', '#E0A438', 9),
 ('APS_RECU', 'APS reçu', '#4C9FE8', 10),
 ('VALIDATION_RADIO', 'Validation Radio', '#4C9FE8', 11),
 ('AUTORISATION_EN_COURS', 'Autorisation en cours', '#E0A438', 12),
 ('CONTRAT_PREPARATION', 'Contrat en préparation', '#4C9FE8', 13),
 ('CONTRAT_ENVOYE', 'Contrat envoyé', '#4C9FE8', 14),
 ('CONTRAT_SIGNATURE', 'Contrat en signature', '#E0A438', 15),
 ('CONTRAT_SIGNE', 'Contrat signé', '#2FB477', 16),
 ('INSTALLATION_AUTORISEE', 'Installation autorisée', '#2FB477', 17),
 ('TRAVAUX_EN_COURS', 'Travaux en cours', '#2FB477', 18),
 ('OPERATIONNEL', 'Site opérationnel', '#2FB477', 19),
 ('BLOQUE', 'Bloqué', '#E5484D', 20),
 ('REFUSE', 'Refusé', '#6E687A', 21),
 ('ABANDONNE', 'Abandonné', '#6E687A', 22),
 ('ARCHIVE', 'Archivé', '#6E687A', 23);

-- ------------------------------------------------------------
-- 4. SITES
-- ------------------------------------------------------------
CREATE TABLE sites (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                TEXT UNIQUE NOT NULL,          -- ex: AL6328
    previous_codes      TEXT[] NOT NULL DEFAULT '{}',  -- historique des anciens codes
    name                TEXT,
    wilaya_id           SMALLINT REFERENCES wilayas(id),
    commune_id          INTEGER REFERENCES communes(id),
    address             TEXT,
    geom                GEOMETRY(Point, 4326),         -- NULL si GPS inconnu (jamais inventé)
    site_type           TEXT,
    owner_name          TEXT,
    organisme           TEXT,
    status_id           INTEGER NOT NULL REFERENCES site_status(id),
    priority            SMALLINT NOT NULL DEFAULT 2,   -- 1=haute 2=normale 3=basse
    responsible_user_id UUID REFERENCES users(id),
    secondary_responsible_user_id UUID REFERENCES users(id),
    next_action         TEXT,
    observation         TEXT,
    is_favorite         BOOLEAN NOT NULL DEFAULT FALSE,
    custom_fields       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by          UUID REFERENCES users(id),
    updated_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ                     -- soft delete -> corbeille
);

CREATE INDEX idx_sites_geom ON sites USING GIST (geom);
CREATE INDEX idx_sites_code_trgm ON sites USING GIN (code gin_trgm_ops);
CREATE INDEX idx_sites_status ON sites (status_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sites_wilaya ON sites (wilaya_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sites_not_deleted ON sites (deleted_at) WHERE deleted_at IS NULL;

-- Historique des changements de statut/valeurs importantes (distinct de l'audit générique)
CREATE TABLE site_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id     UUID NOT NULL REFERENCES sites(id),
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    changed_by  UUID REFERENCES users(id),
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 5. CHAMPS PERSONNALISÉS (no-code, ADMIN)
-- ------------------------------------------------------------
CREATE TABLE custom_fields (
    id          SERIAL PRIMARY KEY,
    entity      TEXT NOT NULL DEFAULT 'sites',   -- extensible à d'autres entités plus tard
    key         TEXT NOT NULL,
    label       TEXT NOT NULL,
    field_type  TEXT NOT NULL CHECK (field_type IN ('text','number','date','boolean','select')),
    options     JSONB,                            -- pour type select
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (entity, key)
);

-- Note : les valeurs sont stockées directement dans sites.custom_fields (JSONB)
-- pour simplicité et performance ; custom_field_values réservé à un usage
-- multi-entités futur (contacts, contrats, etc.) si nécessaire.
CREATE TABLE custom_field_values (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    custom_field_id INTEGER NOT NULL REFERENCES custom_fields(id),
    entity_id       UUID NOT NULL,
    value           TEXT
);

-- ------------------------------------------------------------
-- 6. CRM CONTACTS
-- ------------------------------------------------------------
CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID NOT NULL REFERENCES sites(id),
    first_name      TEXT,
    last_name       TEXT,
    role_label      TEXT,           -- DG, DRH, PDG, Propriétaire, APC, OPGI, ...
    organisme       TEXT,
    phone           TEXT,
    phone_secondary TEXT,
    whatsapp        TEXT,
    email           TEXT,
    address         TEXT,
    notes           TEXT,
    last_contact_at DATE,
    next_followup_at DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE contact_roles (
    id      SERIAL PRIMARY KEY,
    code    TEXT UNIQUE NOT NULL,
    label   TEXT NOT NULL
);
INSERT INTO contact_roles (code, label) VALUES
 ('DG','DG'),('DRH','DRH'),('PDG','PDG'),('PROPRIETAIRE','Propriétaire'),
 ('REPRESENTANT_PROPRIETAIRE','Représentant propriétaire'),
 ('RESP_TECHNIQUE','Responsable technique'),('RESP_ADMIN','Responsable administratif'),
 ('RESP_IMMOBILIER','Responsable immobilier'),('MAINTENANCE','Maintenance'),
 ('APC','APC'),('OPGI','OPGI'),('ADE','ADE'),('EPIC','EPIC'),('DOMAINES','Domaines'),
 ('GEOMETRE','Expert géomètre'),('HUISSIER','Huissier'),('ARCHITECTE','Architecte'),
 ('ENTREPRISE','Entreprise'),('GARDIEN','Gardien'),('AUTRE','Autre');

CREATE TABLE contact_interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id      UUID NOT NULL REFERENCES contacts(id),
    site_id         UUID NOT NULL REFERENCES sites(id),
    user_id         UUID REFERENCES users(id),
    interaction_type TEXT NOT NULL CHECK (interaction_type IN
                        ('APPEL','WHATSAPP','EMAIL','REUNION','VISITE','COURRIER','AUTRE')),
    summary         TEXT,
    result          TEXT,
    next_action     TEXT,
    followup_at     DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 7. GED — DOCUMENTS
-- ------------------------------------------------------------
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID NOT NULL REFERENCES sites(id),
    category        TEXT NOT NULL CHECK (category IN
                        ('DOC_B','APS','CONTRATS','AUTORISATIONS','PV','PHOTOS',
                         'CORRESPONDANCES','CARTOGRAPHIE','AUTRES')),
    filename        TEXT NOT NULL,
    storage_key      TEXT NOT NULL,       -- chemin dans Supabase Storage / futur stockage local
    mime_type       TEXT,
    size_bytes      BIGINT,
    detected_code   TEXT,                 -- code site détecté automatiquement dans le nom
    detected_type   TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE document_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    version         INTEGER NOT NULL,
    storage_key     TEXT NOT NULL,
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE doc_b (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID NOT NULL REFERENCES sites(id),
    date_preparation DATE,
    date_depot      DATE,
    organisme       TEXT,
    reference       TEXT,
    status          TEXT,
    document_id     UUID REFERENCES documents(id),
    version         INTEGER NOT NULL DEFAULT 1,
    observation     TEXT
);

CREATE TABLE aps_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID NOT NULL REFERENCES sites(id),
    aps_type        TEXT,     -- APS_V1, APS_V2, PLAN_GC, PLAN_STRUCTURE, TSS, PHOTO_TECHNIQUE...
    version         INTEGER NOT NULL DEFAULT 1,
    document_id     UUID REFERENCES documents(id),
    observation     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID NOT NULL REFERENCES sites(id),
    document_id     UUID REFERENCES documents(id),
    caption         TEXT,
    taken_at        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 8. CONTRATS
-- ------------------------------------------------------------
CREATE TABLE contracts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id             UUID NOT NULL REFERENCES sites(id),
    reference           TEXT,
    contract_type       TEXT,
    owner_party         TEXT,
    duration_years      NUMERIC,
    date_start          DATE,
    date_end            DATE,
    amount              NUMERIC,
    periodicity         TEXT,
    revision_clause     TEXT,
    conditions          TEXT,
    status              TEXT,
    date_sent           DATE,
    date_signed         DATE,
    date_expiration     DATE,
    observation         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE TABLE contract_signatories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id),
    party           TEXT NOT NULL CHECK (party IN ('PROPRIETAIRE','OOREDOO')),
    name            TEXT,
    role_label      TEXT,
    has_signing_power BOOLEAN,
    proof_document_id UUID REFERENCES documents(id)
);

-- ------------------------------------------------------------
-- 9. TÂCHES / ACTIONS
-- ------------------------------------------------------------
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id         UUID REFERENCES sites(id),
    title           TEXT NOT NULL,
    responsible_user_id UUID REFERENCES users(id),
    priority        SMALLINT NOT NULL DEFAULT 2,
    due_date        DATE,
    status          TEXT NOT NULL DEFAULT 'A_FAIRE' CHECK (status IN ('A_FAIRE','EN_COURS','TERMINE','ANNULE')),
    comment         TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 10. CARTOGRAPHIE — COUCHES KMZ/KML
-- ------------------------------------------------------------
CREATE TABLE map_layers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN ('KML','KMZ','GEOJSON')),
    original_filename TEXT,
    storage_key     TEXT,               -- fichier original conservé (téléchargeable)
    uploaded_by     UUID REFERENCES users(id),
    is_visible      BOOLEAN NOT NULL DEFAULT TRUE,
    feature_count   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE map_features (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer_id        UUID NOT NULL REFERENCES map_layers(id),
    name            TEXT,
    description     TEXT,
    geometry_type   TEXT NOT NULL,      -- Point, LineString, Polygon, MultiGeometry...
    geom            GEOMETRY(Geometry, 4326),
    style           JSONB,              -- couleur, épaisseur, transparence lus du KML
    detected_code   TEXT,               -- code site détecté (ex: AL6328 depuis AL6328_TSS.kmz)
    raw_attributes  JSONB
);

CREATE INDEX idx_map_features_geom ON map_features USING GIST (geom);

-- Rattachement (n-n) entre une feature importée et un site existant
CREATE TABLE map_feature_sites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_feature_id  UUID NOT NULL REFERENCES map_features(id),
    site_id         UUID NOT NULL REFERENCES sites(id),
    linked_by       UUID REFERENCES users(id),
    linked_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 11. PARTAGE DOCUMENTAIRE
-- ------------------------------------------------------------
CREATE TABLE document_share_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token           TEXT UNIQUE NOT NULL,      -- token opaque, jamais l'URL de storage réelle
    created_by      UUID REFERENCES users(id),
    site_id         UUID REFERENCES sites(id),
    document_ids    UUID[] NOT NULL,
    platform        TEXT CHECK (platform IN ('OUTLOOK','WHATSAPP','TELEGRAM','LIEN')),
    expires_at      TIMESTAMPTZ,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    download_count  INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_share_recipients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_link_id   UUID NOT NULL REFERENCES document_share_links(id),
    recipient       TEXT      -- email ou numéro, si connu
);

CREATE TABLE document_share_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_link_id   UUID NOT NULL REFERENCES document_share_links(id),
    accessed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address      TEXT
);

-- ------------------------------------------------------------
-- 12. NOTIFICATIONS
-- ------------------------------------------------------------
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    type            TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT,
    site_id         UUID REFERENCES sites(id),
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 13. AUDIT (traçabilité générique — section 19)
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    entity          TEXT NOT NULL,      -- ex: 'sites'
    entity_id       UUID,
    action          TEXT NOT NULL,      -- CREATE, UPDATE, DELETE, RESTORE, LOGIN...
    field           TEXT,
    old_value       TEXT,
    new_value       TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_entity ON audit_logs (entity, entity_id);

-- ------------------------------------------------------------
-- 14. IA / RAG
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector, pour les embeddings locaux

CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    title           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id),
    role            TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content         TEXT NOT NULL,
    sources         JSONB,              -- {document, page, section} si RAG utilisé
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id),
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    page_number     INTEGER
);

CREATE TABLE ai_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        UUID NOT NULL REFERENCES ai_document_chunks(id),
    embedding       VECTOR(768)   -- dimension selon modèle local (ex: nomic-embed-text)
);
CREATE INDEX idx_ai_embeddings_vector ON ai_embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- Fin migration 001
-- ============================================================
