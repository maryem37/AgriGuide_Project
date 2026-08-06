-- ============================================================
-- AgriAdvisor — Schéma de base de données complet
-- PostgreSQL + PostGIS (données géo) + pgvector (RAG légal)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. UTILISATEURS
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    nom             VARCHAR(150) NOT NULL,
    telephone       VARCHAR(30),
    role            VARCHAR(20) NOT NULL DEFAULT 'farmer',  -- 'farmer' | 'acheteur'
    langue_preferee VARCHAR(5) DEFAULT 'fr',   -- 'fr' | 'en'
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Matériel agricole déclaré par le farmer au sign up (modifiable ensuite depuis son profil).
-- Sans objet pour le rôle 'acheteur' (accès marketplace en lecture seule uniquement).
CREATE TABLE farmer_equipements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type_equipement VARCHAR(50) NOT NULL,  -- 'tracteur' | 'cultivateur' | 'fraise_rotative' | 'planteuse' |
                                            -- 'moissonneuse_batteuse' | 'remorque_agricole' | 'pulverisateur' | 'tunnel_plastique'
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, type_equipement)
);

CREATE TABLE notification_preferences (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    canal       VARCHAR(20) NOT NULL,   -- 'email' | 'sms' | 'whatsapp'
    frequence   VARCHAR(20) DEFAULT 'quotidien',  -- 'quotidien' | 'hebdo' | 'urgent_only'
    actif       BOOLEAN DEFAULT true,
    UNIQUE (user_id, canal)
);

-- ============================================================
-- 2. TERRAINS & LAND PROFILE (Feature: Agriculture Advisor)
-- ============================================================

CREATE TABLE terrains (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nom             VARCHAR(150),
    geometry        GEOMETRY(POLYGON, 4326) NOT NULL,   -- PostGIS, WGS84
    superficie_ha   NUMERIC(8,2) NOT NULL,
    region          VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_terrains_geom ON terrains USING GIST (geometry);

-- Un LandProfile par terrain (régénérable, on garde l'historique)
CREATE TABLE land_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id          UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    sol_data            JSONB NOT NULL,      -- SoilGrids: pH, texture, matière organique...
    satellite_data      JSONB NOT NULL,      -- Sentinel-2: NDVI, historique végétation
    rpg_historique       JSONB,               -- Registre Parcellaire Graphique
    cultures_voisines    JSONB,               -- estimation via RPG voisinage
    climat_data         JSONB NOT NULL,      -- NASA POWER / Open-Meteo
    elevation_m         NUMERIC(6,1),        -- Open-Elevation
    date_generation     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_land_profiles_terrain ON land_profiles(terrain_id);

-- Top 5 recommandations générées par le RandomForest
CREATE TABLE crop_recommendations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    land_profile_id     UUID NOT NULL REFERENCES land_profiles(id) ON DELETE CASCADE,
    rang                SMALLINT NOT NULL,          -- 1 à 5
    culture             VARCHAR(100) NOT NULL,
    score_compatibilite NUMERIC(5,2) NOT NULL,      -- 0-100
    besoins_pesticides  JSONB,
    besoins_engrais     JSONB,
    besoins_irrigation  JSONB,
    feature_importance  JSONB,                       -- explicabilité du modèle
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_crop_reco_profile ON crop_recommendations(land_profile_id);

-- ============================================================
-- 3. BUSINESS ADVISOR (scénarios + décision finale)
-- ============================================================

CREATE TABLE business_scenarios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id          UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    budget_input        NUMERIC(12,2) NOT NULL,
    culture             VARCHAR(100) NOT NULL,
    quantite_par_ha     NUMERIC(10,2),
    profit_estime       NUMERIC(12,2),
    risque_score        NUMERIC(5,2),        -- normalisé 0-1
    risque_description  TEXT,
    solution_risque     TEXT,
    matching_score      NUMERIC(5,2) NOT NULL,   -- formule pondérée (voir README business agent)
    etude_marche        JSONB,               -- estimation temporelle, prix RNM utilisés
    created_at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_scenarios_terrain ON business_scenarios(terrain_id);

-- Décision finale du farmer (Human-in-the-loop)
CREATE TABLE farmer_decisions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id          UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    statut              VARCHAR(20) DEFAULT 'pending', -- pending | confirmed | monitoring
    cout_final          NUMERIC(12,2),
    created_at          TIMESTAMPTZ DEFAULT now(),
    confirmed_at        TIMESTAMPTZ
);

-- Répartition des hectares par culture choisie (plusieurs cultures possibles)
CREATE TABLE decision_allocations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id         UUID NOT NULL REFERENCES farmer_decisions(id) ON DELETE CASCADE,
    scenario_id         UUID NOT NULL REFERENCES business_scenarios(id),
    culture             VARCHAR(100) NOT NULL,
    hectares_alloues    NUMERIC(8,2) NOT NULL,
    date_maturite_prevue DATE                -- utilisé par l'agent de suivi pour anticiper le marketplace
);

-- ============================================================
-- 4. RÉGULATION ADVISOR (RAG légal)
-- ============================================================

-- Corpus documentaire indexé (Code Rural, Cerfa, SRDEA, aides...)
CREATE TABLE regulation_documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    titre           VARCHAR(255) NOT NULL,
    source          VARCHAR(100) NOT NULL,     -- 'Code Rural' | 'Cerfa' | 'FranceAgriMer' ...
    url_source      TEXT,
    contenu_brut    TEXT NOT NULL,
    embedding       VECTOR(1024),               -- selon modèle d'embedding choisi
    date_publication DATE,
    date_indexation TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_regulation_embedding ON regulation_documents USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE regulation_chat_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    terrain_id      UUID REFERENCES terrains(id),
    question        TEXT NOT NULL,
    reponse         TEXT NOT NULL,
    sources_citees  JSONB,             -- liste des regulation_documents.id utilisés
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dossiers_administratifs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    terrain_id      UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    type_dossier    VARCHAR(100) NOT NULL,   -- 'Cerfa 11534' | 'Certification bio' ...
    statut          VARCHAR(30) DEFAULT 'en_cours',  -- en_cours | pret | soumis
    documents       JSONB,               -- champs pré-remplis, pièces jointes
    date_creation   TIMESTAMPTZ DEFAULT now(),
    date_maj        TIMESTAMPTZ DEFAULT now()
);

-- Aides financières agricoles (subventions, appels à projets) trouvées par le
-- Subsidy Search de l'agent Régulation (voir agent_regulation/app/services/
-- subsidy_sync_service.py) et mises en cache ici pour que le frontend les
-- affiche sans relancer une recherche web à chaque ouverture.
-- `source_url` sert de clé de dédoublonnage lors de la synchronisation
-- (une aide = une page source).
CREATE TABLE subsidies (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    eligibility             TEXT,
    amount                  TEXT,
    region                  VARCHAR(100),
    start_date              DATE,
    end_date                DATE,
    application_procedure   TEXT,
    source_name             VARCHAR(150) NOT NULL,
    source_url              TEXT NOT NULL,
    is_official             BOOLEAN DEFAULT false,
    last_verified_at        TIMESTAMPTZ DEFAULT now(),
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source_url)
);
-- Recherche rapide des aides actives triées par échéance la plus proche.
CREATE INDEX idx_subsidies_end_date ON subsidies(end_date);

-- ============================================================
-- 5. SUIVI QUOTIDIEN (Monitoring Agent)
-- ============================================================

CREATE TABLE monitoring_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id      UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    type_action     VARCHAR(50) NOT NULL,   -- 'irrigation' | 'traitement' | 'fertilisation' | 'recolte'
    description     TEXT,
    date_action     DATE NOT NULL,
    cout            NUMERIC(10,2),
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_monitoring_terrain ON monitoring_logs(terrain_id);

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id      UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    type_alerte     VARCHAR(50) NOT NULL,   -- 'meteo' | 'insecte' | 'echeance_admin' | 'irrigation'
    message         TEXT NOT NULL,
    niveau_urgence  VARCHAR(20) DEFAULT 'info',  -- info | warning | critique
    lu              BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_alerts_terrain ON alerts(terrain_id, lu);

CREATE TABLE cost_tracking (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terrain_id      UUID NOT NULL REFERENCES terrains(id) ON DELETE CASCADE,
    categorie       VARCHAR(50) NOT NULL,   -- 'semences' | 'irrigation' | 'traitement' | 'main_oeuvre'
    montant         NUMERIC(10,2) NOT NULL,
    date_depense    DATE NOT NULL,
    description     TEXT
);

-- ============================================================
-- 6. MARKETPLACE & ÉCONOMIE CIRCULAIRE
-- ============================================================

CREATE TABLE annonces (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    terrain_id          UUID REFERENCES terrains(id),
    type_annonce        VARCHAR(20) NOT NULL,  -- 'recolte' | 'dechet'
    culture_source      VARCHAR(100),           -- ex: 'tomate' (pour tracer l'origine du déchet)
    titre               VARCHAR(150) NOT NULL,
    description         TEXT NOT NULL,           -- utilité générée/éditée (pour les déchets)
    quantite            NUMERIC(10,2) NOT NULL,
    unite               VARCHAR(20) NOT NULL,    -- 'kg' | 'tonne' | 'unite'
    prix                NUMERIC(10,2),           -- NULL possible pour les déchets ("à convenir"/gratuit)
    prix_suggere_source VARCHAR(50),             -- ex: 'RNM_FranceAgriMer'
    contact_telephone   VARCHAR(30),
    contact_email       VARCHAR(255),
    statut              VARCHAR(20) DEFAULT 'disponible', -- disponible | reserve | expire
    date_creation       TIMESTAMPTZ DEFAULT now(),
    date_expiration     TIMESTAMPTZ
);
CREATE INDEX idx_annonces_statut ON annonces(statut, type_annonce);

-- Référentiel : déchets typiques par culture (alimente les suggestions de l'agent de suivi)
CREATE TABLE dechets_reference (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    culture         VARCHAR(100) NOT NULL,
    type_dechet     VARCHAR(150) NOT NULL,   -- ex: 'fanes de tomate'
    utilites        JSONB NOT NULL           -- ex: ['compost', 'paillage', 'alimentation animale']
);

-- ============================================================
-- Notes d'implémentation
-- ============================================================
-- - Toutes les FK en CASCADE sur users/terrains pour simplifier le RGPD (suppression de compte).
-- - embedding VECTOR(1024): à ajuster selon le modèle d'embedding réellement utilisé (ex: 1024 pour
--   certains modèles multilingues, 384/768 pour d'autres — vérifier avant migration).
-- - Toute donnée sensible (localisation précise, budget) doit être soumise au consentement RGPD
--   décrit dans docs/team_guide.md.
