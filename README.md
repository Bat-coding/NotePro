# NotePro — Guide de Démarrage Rapide

Ce dépôt contient la plateforme de gestion académique "NotePro".

## 🚀 Installation & Lancement

### 1. Nettoyage complet (Optionnel mais recommandé)
Dans le dossier du projet, lance :
```bash
docker-compose down -v
```
*Cette commande arrête les conteneurs et **supprime les volumes** (données de la base).*

### 2. Configuration Environnement
Créez un fichier nommé `.env` à la racine.

### 3. Lancement
Pour construire les images et démarrer l'application avec une nouvelle base de données toute neuve :
```bash
docker-compose up --build
```

---

## 🛠️ Commandes Utiles

- **Arrêter le projet** : `docker-compose stop`
- **Redémarrer après modification du code** : `docker-compose up -d --build web`
- **Voir les logs** : `docker-compose logs -f web`

## 🐧 Notes pour Windows
- Assurez-vous que **Docker Desktop** est bien lancé.
- Si vous utilisez **WSL2**, lancez les commandes dans votre terminal Linux préféré.


Commande pour Baptiste le chacal : docker compose down -v && docker compose up -d --build


docker compose down; docker compose up -d --build

