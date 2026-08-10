# AgriAdvisor

Plateforme d'aide à la décision agricole (France) : réglementation, choix de
culture, étude business, suivi quotidien et marketplace communautaire —
propulsée par des agents IA.

## Vue d'ensemble

Voir `docs/ARCHITECTURE.md` pour l'architecture multi-agents complète et
`database/schema.sql` pour le schéma de données.

## Structure du repo

```
agriadvisor/
├── backend/
│   ├── orchestrator/        # Agent superviseur (LangGraph) — routage
│   ├── auth/                 # Sign up/sign in, rôles farmer/acheteur, profil
│   ├── agent_regulation/     # RAG légal (Code Rural, Cerfa, aides)
│   ├── agent_agriculture/    # Analyse géo/sol/climat + RandomForest
│   ├── agent_business/       # Scoring des scénarios + étude de marché
│   ├── agent_monitoring/     # Suivi quotidien, alertes, déclenchement marketplace
│   ├── waste_agents/         # Déchets & valorisation (KB + API port 8004)
│   ├── marketplace/          # Module CRUD annonces (récolte + déchets)
│   └── shared/               # Modèles de données, clients API externes communs
├── database/
│   └── schema.sql            # Schéma complet PostgreSQL + PostGIS + pgvector
├── frontend/                 # Interface (générée via Lovable, voir README dédié)
├── docs/
│   ├── ARCHITECTURE.md       # Architecture technique détaillée
│   └── team_guide.md         # Qui fait quoi, RGPD, conventions
└── docker-compose.yml
```

## Démarrage rapide (après `git clone`)

Prérequis : [Docker Desktop](https://www.docker.com/products/docker-desktop/),
Python 3.11+, Node.js 20+.

### 1. Configurer les variables d'environnement

```bash
cp .env.example .env    # macOS/Linux — sur Windows : Copy-Item .env.example .env
```

Ouvrez `.env` et renseignez au minimum `MISTRAL_API_KEY` (clé gratuite sur
[console.mistral.ai](https://console.mistral.ai)) — les autres clés (Sentinel
Hub, Mapbox, Tavily...) sont optionnelles pour un premier lancement mais
certaines fonctionnalités seront dégradées sans elles (voir les commentaires
dans `.env.example`).

**Important** : l'Agent Régulation et l'Agent Waste ont chacun leur propre
`.env` (Qdrant Cloud déjà provisionné avec les données) :

```bash
cp backend/agent_regulation/.env.example backend/agent_regulation/.env
cp backend/waste_agents/.env.example backend/waste_agents/.env
```

Ces identifiants Qdrant/Tavily ne se régénèrent pas tout seuls — demandez-les
directement au porteur du projet (ne jamais commiter de vrai `.env`, ils sont
dans `.gitignore`).

### 2. Démarrer PostgreSQL (crée les tables automatiquement)

```bash
docker compose up -d db
```

Au tout premier démarrage, Postgres exécute automatiquement
`database/schema.sql` (monté sur `/docker-entrypoint-initdb.d/`) et crée
toutes les tables. Rien d'autre à faire.

> Si vous récupérez un volume Postgres déjà existant (pas le cas sur un clone
> tout neuf), les tables ne seront PAS recréées automatiquement — voir
> [Dépannage](#dépannage) plus bas pour appliquer le schéma/les migrations à
> la main.

### 3. Installer les dépendances Python (un seul venv partagé)

```powershell
# Windows
.\scripts\setup_venv.ps1
```

```bash
# macOS / Linux
./scripts/setup_venv.sh
```

### 4. Lancer tous les agents backend

```powershell
.\dev.ps1
```

```bash
./dev.sh
```

Ports locaux :

| Service        | Port |
|----------------|------|
| Business       | 8000 |
| Auth           | 8001 |
| Agriculture    | 8002 |
| Monitoring     | 8003 |
| Waste          | 8004 |
| Regulation     | 8005 |

Vérifiez que tout tourne : `curl http://localhost:8001/health` (idem pour les
autres ports) doit répondre `{"status":"ok",...}`.

### 5. Lancer le frontend

Dans un nouveau terminal :

```bash
cd frontend
npm install
npm run dev
```

L'app est disponible sur l'URL affichée dans le terminal (ligne `Local:`).
Créez un compte via la page d'inscription pour vous
connecter — il n'y a pas de compte de démo pré-créé (la base démarre vide).

Les `requirements.txt` dans chaque dossier `backend/*` restent valides pour Docker.
Le venv global (`.venv/`) sert uniquement au développement local multi-agents.

## Dépannage

**`column "..." does not exist` / autre erreur SQL** — le volume Postgres est
plus vieux que le schéma actuel (`schema.sql` ne s'exécute qu'à la toute
première création du volume, pas aux redémarrages suivants). Appliquez les
migrations manquantes (sans danger de les rejouer, elles sont idempotentes) :

```bash
docker compose exec -T db psql -U agriadvisor -d agriadvisor < database/migration_business_financials.sql
docker compose exec -T db psql -U agriadvisor -d agriadvisor < database/migration_decision_allocations_scenario_cascade.sql
```

> `database/schema.sql`, lui, n'est PAS rejouable tel quel sur une base qui a
> déjà des tables (`CREATE TABLE` sans `IF NOT EXISTS` → erreur "already
> exists"). Il ne sert qu'à l'initialisation d'un volume neuf. Pour repartir
> d'une base totalement vide : `docker compose down -v` puis `docker compose up -d db`
> (⚠️ `-v` supprime tous les volumes Docker du projet, données Postgres comprises).

**`Failed to resolve import "three"` (frontend)** — `node_modules` désynchronisé
du `package-lock.json` : `cd frontend && npm install`.

**401 Unauthorized en boucle** — session invalide en cache dans le navigateur.
Déconnectez-vous/reconnectez-vous, ou dans la console DevTools :
`localStorage.removeItem("agriguide.session")` puis rechargez.

**Agent Régulation renvoie 503 / erreur au démarrage** — `backend/agent_regulation/.env`
manquant ou incomplet (voir étape 1). Cet agent a besoin de `MISTRAL_API_KEY`,
`QDRANT_URL` et `QDRANT_COLLECTION_NAME` pour démarrer.

## Équipe — répartition suggérée

Chaque dossier sous `backend/` est un lot de travail quasi indépendant.
Voir `docs/team_guide.md` pour la répartition détaillée et les interfaces
entre modules (ce que chaque agent reçoit / renvoie).
