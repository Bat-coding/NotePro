-- db/init.sql

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'professeur', 'etudiant') NOT NULL DEFAULT 'etudiant',
    telephone VARCHAR(20) NULL,
    avatar VARCHAR(255) NULL,
    totp_secret VARCHAR(32) NULL,
    totp_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS classe_etudiants (
    classe_id INT,
    etudiant_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (etudiant_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(200) NOT NULL,
    classe_id INT,
    professeur_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE SET NULL,
    FOREIGN KEY (professeur_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    etudiant_id INT,
    evaluation_id INT,
    valeur DECIMAL(4,2),
    FOREIGN KEY (etudiant_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
    UNIQUE KEY unique_note (etudiant_id, evaluation_id)
);

CREATE TABLE IF NOT EXISTS emplois_du_temps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT,
    date_cours DATE NULL,
    jour VARCHAR(20),
    heure_debut TIME,
    heure_fin TIME,
    matiere VARCHAR(100),
    salle VARCHAR(50) NULL,
    professeur_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- ── AGENDA ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agenda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT,
    professeur_id INT,
    titre VARCHAR(200) NOT NULL,
    description TEXT,
    date_event DATE NOT NULL,
    type_event ENUM('devoir', 'examen', 'sortie', 'reunion', 'autre') DEFAULT 'autre',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (professeur_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ── ABSENCES ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS absences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    etudiant_id INT,
    professeur_id INT,
    classe_id INT,
    date_absence DATE NOT NULL,
    type_absence ENUM('absence', 'retard') DEFAULT 'absence',
    motif VARCHAR(255),
    justifiee BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (etudiant_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (professeur_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE SET NULL
);

-- ── MENU CANTINE ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS menu_cantine (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date_menu DATE NOT NULL,
    entree VARCHAR(200),
    plat_principal VARCHAR(200) NOT NULL,
    accompagnement VARCHAR(200),
    dessert VARCHAR(200),
    regime_special VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (date_menu)
);

-- ── AFFECTATIONS (PROF -> CLASSE / MATIERE) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS classe_professeurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT,
    professeur_id INT,
    matiere VARCHAR(100) NOT NULL,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (professeur_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_prof_classe_matiere (classe_id, professeur_id, matiere)
);

-- ── ABSENCES PROFESSEUR ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS professeur_absences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    professeur_id INT,
    date_absence DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professeur_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_abs_prof_date (professeur_id, date_absence)
);

-- ── MESSAGES ADMIN ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages_admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contenu TEXT NOT NULL,
    actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$yvOfHsu582tx/W2juMDgkecf/4YUuK09eMsY31Vj5GDJkghLwOn8m', 'admin');