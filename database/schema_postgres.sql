-- TEXTQAI – Schema PostgreSQL (đầy đủ bảng, PK, FK, UNIQUE)
-- Chạy SAU init_postgres.sql, đã kết nối vào database luanvan_ai:
--   psql -U postgres -d luanvan_ai -f database/schema_postgres.sql
--
-- Hoặc dùng: python init_db.py (db.create_all() — tương đương schema này)

BEGIN;

-- ── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE,
    email           VARCHAR(255) UNIQUE,
    display_name    VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    credits         INTEGER NOT NULL DEFAULT 5,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    terms_agreed_at TIMESTAMP
);

-- ── user_auth_providers ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_auth_providers (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL,
    provider          VARCHAR(50) NOT NULL,
    provider_user_id  VARCHAR(255),
    provider_email    VARCHAR(255),
    password_hash     VARCHAR(255),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_uap_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_provider_user
        UNIQUE (provider, provider_user_id)
);

CREATE INDEX IF NOT EXISTS ix_uap_user_id ON user_auth_providers(user_id);

-- ── documents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    filename     VARCHAR(255),
    content      TEXT,
    upload_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id      INTEGER,
    CONSTRAINT fk_documents_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents(user_id);

-- ── qa_results ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS qa_results (
    id               SERIAL PRIMARY KEY,
    content          TEXT,
    question         TEXT,
    answer           TEXT,
    bloom_level      VARCHAR(50),
    algorithm        VARCHAR(50),
    process_time     DOUBLE PRECISION,
    section_mapping  VARCHAR(500),
    total_points     DOUBLE PRECISION DEFAULT 0,
    sub_points_count INTEGER DEFAULT 0,
    points_breakdown TEXT,
    batch_id         VARCHAR(20),
    user_id          INTEGER,
    document_id      INTEGER,
    CONSTRAINT fk_qa_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_qa_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_qa_results_user_id ON qa_results(user_id);
CREATE INDEX IF NOT EXISTS ix_qa_results_document_id ON qa_results(document_id);

-- ── agent evaluation logs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent1_evaluation_logs (
    id                SERIAL PRIMARY KEY,
    request_id        VARCHAR(64) NOT NULL,
    user_id           INTEGER,
    document_id       INTEGER,
    source_type       VARCHAR(32),
    attempt           INTEGER DEFAULT 1,
    extraction_method VARCHAR(32),
    decision          VARCHAR(16) NOT NULL,
    terminal_status   VARCHAR(32),
    quality_score     DOUBLE PRECISION DEFAULT 0,
    reasons_json      TEXT NOT NULL,
    metrics_json      TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a1_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a1_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent2_evaluation_logs (
    id                     SERIAL PRIMARY KEY,
    request_id             VARCHAR(64) NOT NULL,
    user_id                INTEGER,
    document_id            INTEGER,
    attempt                INTEGER DEFAULT 1,
    decision               VARCHAR(16) NOT NULL,
    terminal_status        VARCHAR(32),
    quality_score          DOUBLE PRECISION DEFAULT 0,
    reasons_json           TEXT NOT NULL,
    structure_summary_json TEXT,
    plan_summary_json      TEXT,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a2_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a2_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS agent3_evaluation_logs (
    id                        SERIAL PRIMARY KEY,
    request_id                VARCHAR(64) NOT NULL,
    user_id                   INTEGER,
    document_id               INTEGER,
    plan_item_id              VARCHAR(64),
    attempt                   INTEGER DEFAULT 1,
    decision                  VARCHAR(16) NOT NULL,
    terminal_status           VARCHAR(32),
    quality_score             DOUBLE PRECISION DEFAULT 0,
    reasons_json              TEXT NOT NULL,
    target_bloom              VARCHAR(32),
    generated_bloom           VARCHAR(32),
    validated_bloom           VARCHAR(32),
    bloom_match_type          VARCHAR(32),
    source_faithfulness_score DOUBLE PRECISION DEFAULT 0,
    scoreability_score        DOUBLE PRECISION DEFAULT 0,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a3_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a3_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- ── payment packages (không FK đi vào) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS credit_packages (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    credits    INTEGER NOT NULL,
    price_vnd  INTEGER NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE,
    is_popular BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS subscription_packages (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    credits   INTEGER NOT NULL,
    price_vnd INTEGER NOT NULL,
    period    VARCHAR(20) DEFAULT 'tháng',
    is_active BOOLEAN DEFAULT TRUE
);

-- ── transactions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL,
    package_id     INTEGER,
    sub_package_id INTEGER,
    order_code     VARCHAR(64) NOT NULL UNIQUE,
    amount_vnd     INTEGER NOT NULL,
    credits_added  INTEGER NOT NULL,
    status         VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(50),
    payos_data     TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at        TIMESTAMP,
    CONSTRAINT fk_tx_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_tx_credit_pkg
        FOREIGN KEY (package_id) REFERENCES credit_packages(id) ON DELETE SET NULL,
    CONSTRAINT fk_tx_sub_pkg
        FOREIGN KEY (sub_package_id) REFERENCES subscription_packages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions(user_id);

-- ── feedbacks ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedbacks (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    user_id    INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedbacks_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ── system_settings ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
    key   VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
);

COMMIT;
