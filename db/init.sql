-- db/init.sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'professeur', 'etudiant') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL
);

CREATE TABLE classe_etudiants (
    classe_id INT, etudiant_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id),
    FOREIGN KEY (etudiant_id) REFERENCES users(id)
);

CREATE TABLE evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(200) NOT NULL,
    classe_id INT,
    professeur_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id),
    FOREIGN KEY (professeur_id) REFERENCES users(id)
);

CREATE TABLE notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    etudiant_id INT, evaluation_id INT,
    valeur DECIMAL(4,2),
    FOREIGN KEY (etudiant_id) REFERENCES users(id),
    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
);

CREATE TABLE emplois_du_temps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classe_id INT, jour VARCHAR(20),
    heure_debut TIME, heure_fin TIME,
    matiere VARCHAR(100), professeur_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id)
);

-- Seed data (mots de passe = bcrypt hash de "Password123!")
INSERT INTO users (username, password_hash, role) VALUES
('admin', '$2b$12$XXXX...', 'admin'),
('prof_dupont', '$2b$12$XXXX...', 'professeur'),
('etudiant_martin', '$2b$12$XXXX...', 'etudiant');