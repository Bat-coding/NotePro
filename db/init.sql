-- db/init.sql

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'professeur', 'etudiant') NOT NULL DEFAULT 'etudiant',
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
    jour VARCHAR(20),
    heure_debut TIME,
    heure_fin TIME,
    matiere VARCHAR(100),
    professeur_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- admin / Password123!
INSERT IGNORE INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RVmkNe6Gy', 'admin');