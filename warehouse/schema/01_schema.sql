CREATE DATABASE IF NOT EXISTS press_warehouse
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE press_warehouse;

-- ── DIMENSION DATE ───────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    date_complete  DATE        NOT NULL UNIQUE,
    annee          SMALLINT    NOT NULL,
    trimestre      TINYINT     NOT NULL,
    mois           TINYINT     NOT NULL,
    nom_mois       VARCHAR(20) NOT NULL,
    semaine        TINYINT     NOT NULL,
    jour           TINYINT     NOT NULL,
    nom_jour       VARCHAR(15) NOT NULL,
    est_weekend    BOOLEAN     NOT NULL DEFAULT 0
);

-- ── DIMENSION SOURCE ─────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_source (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    nom_source          VARCHAR(100) NOT NULL UNIQUE,
    type_source         ENUM('national','international','agence') DEFAULT 'international',
    pays                VARCHAR(50),
    langue_principale   VARCHAR(10)
);

-- ── DIMENSION CATEGORIE ──────────────────────────────
CREATE TABLE IF NOT EXISTS dim_categorie (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nom_categorie   VARCHAR(100) NOT NULL UNIQUE
);

-- ── TABLE DE FAITS ───────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_articles (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    titre            VARCHAR(500) NOT NULL,
    auteur           VARCHAR(200),
    date_id          INT NOT NULL,
    source_id        INT NOT NULL,
    categorie_id     INT NOT NULL,
    nb_mots          INT  DEFAULT 0,
    langue_detectee  VARCHAR(10),
    url              VARCHAR(1000) UNIQUE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (date_id)      REFERENCES dim_date(id),
    FOREIGN KEY (source_id)    REFERENCES dim_source(id),
    FOREIGN KEY (categorie_id) REFERENCES dim_categorie(id),

    INDEX idx_date      (date_id),
    INDEX idx_source    (source_id),
    INDEX idx_categorie (categorie_id)
);