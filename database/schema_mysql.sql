-- TEXTQAI – Schema MySQL / MariaDB (đầy đủ bảng, PK, FK, UNIQUE)
-- Chạy SAU init_mysql.sql, đã chọn database luanvan_ai:
--   mysql -u root -p luanvan_ai < database/schema_mysql.sql
--
-- Hoặc dùng: python init_db.py (db.create_all() — tương đương schema này)

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(100) UNIQUE,
    email           VARCHAR(255) UNIQUE,
    display_name    VARCHAR(255),
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    is_admin        TINYINT(1) NOT NULL DEFAULT 0,
    credits         INT NOT NULL DEFAULT 5,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    terms_agreed_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── user_auth_providers ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_auth_providers (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NOT NULL,
    provider          VARCHAR(50) NOT NULL,
    provider_user_id  VARCHAR(255),
    provider_email    VARCHAR(255),
    password_hash     VARCHAR(255),
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_uap_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_provider_user
        UNIQUE (provider, provider_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_uap_user_id ON user_auth_providers(user_id);

-- ── documents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(255) NOT NULL,
    filename     VARCHAR(255),
    content      LONGTEXT,
    upload_date  DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id      INT,
    CONSTRAINT fk_documents_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_documents_user_id ON documents(user_id);

-- ── qa_results ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS qa_results (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    content          LONGTEXT,
    question         LONGTEXT,
    answer           LONGTEXT,
    bloom_level      VARCHAR(50),
    algorithm        VARCHAR(50),
    process_time     DOUBLE,
    section_mapping  VARCHAR(500),
    total_points     DOUBLE DEFAULT 0,
    sub_points_count INT DEFAULT 0,
    points_breakdown LONGTEXT,
    batch_id         VARCHAR(20),
    user_id          INT,
    document_id      INT,
    CONSTRAINT fk_qa_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_qa_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_qa_results_user_id ON qa_results(user_id);
CREATE INDEX ix_qa_results_document_id ON qa_results(document_id);

-- ── agent evaluation logs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent1_evaluation_logs (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    request_id        VARCHAR(64) NOT NULL,
    user_id           INT,
    document_id       INT,
    source_type       VARCHAR(32),
    attempt           INT DEFAULT 1,
    extraction_method VARCHAR(32),
    decision          VARCHAR(16) NOT NULL,
    terminal_status   VARCHAR(32),
    quality_score     DOUBLE DEFAULT 0,
    reasons_json      LONGTEXT NOT NULL,
    metrics_json      LONGTEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a1_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a1_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent2_evaluation_logs (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    request_id             VARCHAR(64) NOT NULL,
    user_id                INT,
    document_id            INT,
    attempt                INT DEFAULT 1,
    decision               VARCHAR(16) NOT NULL,
    terminal_status        VARCHAR(32),
    quality_score          DOUBLE DEFAULT 0,
    reasons_json           LONGTEXT NOT NULL,
    structure_summary_json LONGTEXT,
    plan_summary_json      LONGTEXT,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a2_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a2_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent3_evaluation_logs (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    request_id                VARCHAR(64) NOT NULL,
    user_id                   INT,
    document_id               INT,
    plan_item_id              VARCHAR(64),
    attempt                   INT DEFAULT 1,
    decision                  VARCHAR(16) NOT NULL,
    terminal_status           VARCHAR(32),
    quality_score             DOUBLE DEFAULT 0,
    reasons_json              LONGTEXT NOT NULL,
    target_bloom              VARCHAR(32),
    generated_bloom           VARCHAR(32),
    validated_bloom           VARCHAR(32),
    bloom_match_type          VARCHAR(32),
    source_faithfulness_score DOUBLE DEFAULT 0,
    scoreability_score        DOUBLE DEFAULT 0,
    created_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_a3_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_a3_document
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── payment packages ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS credit_packages (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    credits    INT NOT NULL,
    price_vnd  INT NOT NULL,
    is_active  TINYINT(1) DEFAULT 1,
    is_popular TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subscription_packages (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    credits   INT NOT NULL,
    price_vnd INT NOT NULL,
    period    VARCHAR(20) DEFAULT 'tháng',
    is_active TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── transactions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    package_id     INT,
    sub_package_id INT,
    order_code     VARCHAR(64) NOT NULL,
    amount_vnd     INT NOT NULL,
    credits_added  INT NOT NULL,
    status         VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(50),
    payos_data     LONGTEXT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at        DATETIME NULL,
    CONSTRAINT fk_tx_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_tx_credit_pkg
        FOREIGN KEY (package_id) REFERENCES credit_packages(id) ON DELETE SET NULL,
    CONSTRAINT fk_tx_sub_pkg
        FOREIGN KEY (sub_package_id) REFERENCES subscription_packages(id) ON DELETE SET NULL,
    CONSTRAINT uq_transactions_order_code
        UNIQUE (order_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_transactions_user_id ON transactions(user_id);

-- ── feedbacks ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedbacks (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    message    LONGTEXT NOT NULL,
    is_read    TINYINT(1) NOT NULL DEFAULT 0,
    user_id    INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedbacks_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── system_settings ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
    `key`   VARCHAR(100) PRIMARY KEY,
    `value` LONGTEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
