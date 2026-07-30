# Auth

**Rôle** : inscription / connexion, et gestion du profil farmer (matériel
agricole détenu + terrains déclarés). C'est le premier service du projet
réellement connecté à PostgreSQL (les autres agents utilisent encore des
données simulées, voir `docs/team_guide.md`).

## Rôles

- `farmer` : accès à toutes les fonctionnalités (conseillers, marketplace en
  écriture...). Doit déclarer à l'inscription son matériel agricole détenu et
  au moins un terrain (tracé sur la carte + nom de zone).
- `acheteur` : accès en lecture seule au marketplace uniquement (ne peut pas
  déposer d'annonce).

## Lancer le service

```bash
cd backend/auth
pip install -r requirements.txt
# Nécessite une base PostgreSQL démarrée avec database/schema.sql :
docker compose up -d db   # depuis la racine du repo — expose le port hôte 5434
                            # (5432 est souvent déjà pris par un Postgres natif)
python -m app.tests.test_endpoints     # tests des endpoints FastAPI
uvicorn app.main:app --reload --port 8001   # lancer le serveur (docs sur /docs)
```

Variables d'environnement (voir `.env.example`) :
- `DATABASE_URL` — connexion PostgreSQL
- `JWT_SECRET_KEY` — secret de signature des tokens de session

## Endpoints

- `POST /auth/signup` — `{email, password, nom, telephone?, role, equipements?, terrains?}`
  → crée le compte (+ matériel/terrains si `role = farmer`) et retourne un token
- `POST /auth/signin` — `{email, password}` → token + profil utilisateur
- `GET /auth/me` — profil complet de l'utilisateur connecté (`Authorization: Bearer <token>`)
- `PUT /auth/me/equipements` — remplace la liste de matériel déclaré (farmer uniquement)
- `POST /auth/me/terrains` — ajoute un terrain
- `PUT /auth/me/terrains/{id}` — modifie un terrain (nom, contour, région)
- `DELETE /auth/me/terrains/{id}` — supprime un terrain

Toutes ces routes "modifiables après" répondent à la contrainte : "ces
informations sont changeables après dans la plateforme" (page Profil côté
frontend).

## Matériel agricole (`EquipementType`)

`tracteur`, `cultivateur`, `fraise_rotative`, `planteuse`,
`moissonneuse_batteuse`, `remorque_agricole`, `pulverisateur`,
`tunnel_plastique`. Affichés avec une icône générique en attendant les
vraies images (voir `frontend/src/lib/equipements.ts`).

## Sécurité

- Mots de passe hachés avec bcrypt (`passlib`), jamais stockés en clair.
- Session par JWT (7 jours), transmis par le frontend dans l'en-tête
  `Authorization: Bearer <token>`.
- `CORS` ouvert en dev uniquement (`app/main.py`) — à restreindre en prod.

## Sortie (écrit en base)
- `users` (colonne `role` ajoutée à la table existante)
- `farmer_equipements` (nouvelle table)
- `terrains` (réutilise la table existante — `nom` sert de nom de zone)
