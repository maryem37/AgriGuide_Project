# AgriGuide — Plateforme d'Aide à la Décision Agricole par IA Multi-Agents

**AgriGuide** est une plateforme SaaS complète d'aide à la décision pour les agriculteurs, coopératives et conseillers agronomiques en France. Elle combine données satellitaires (Copernicus Sentinel-2), géomatique officielle (Cadastre, IGN LiDAR HD, RPG), modèles de Deep Learning / Machine Learning, et un écosystème d'agents IA autonomes (LangGraph, Mistral AI, Qdrant).

---

## 🌟 Fonctionnalités Principales

- 🗺️ **Conseiller Parcellaire & Agro-Écologique** (`/agriculture`) :
  - Détection parcellaire automatique (Cadastre API Carto & Registre Parcellaire Graphique WFS).
  - Analyse physico-chimique du sol (SoilGrids ISRIC) et historique climatique (Open-Meteo).
  - Végétation & vigueur par satellite Sentinel-2 (NDVI, NDWI, NDMI).
  - Modélisation du terrain en 3D interactif (Three.js + LiDAR HD IGN) et carte Mapbox GL JS.
  - Recommandation culturale multicritère (RandomForest + TempCNN BreizhCrops) et modulation d'azote VRA (format ISOBUS / CSV).
  - Estimateur de séquestration carbone et revenus de crédits carbone.
- 💬 **Assistant Agronomique RAG & Chat Flottant** :
  - Chatbot conversationnel contextualisé à la parcelle sélectionnée et au profil connecté.
  - RAG hybride basé sur le corpus documentaire technique (ARVALIS, Terres Inovia, ITB, HAL).
- ⚖️ **Agent Réglementation & PAC** (`/regulation`) :
  - RAG juridique sur le Code Rural, les normes BCAE, éco-régimes et arrêtés ministériels.
  - Moteur de synchronisation et de recherche des subventions et aides financières en temps réel (Tavily).
- 📈 **Bourse Agricole & Vente à Terme** (`/trading`) :
  - Cotations des marchés de matières premières agricoles (Euronext / MATIF) en direct et séries historiques.
  - Simulateur de décision commerciale pour agriculteurs (Vendre, Stocker au hangar ou Patienter).
  - Alertes de marché et signaux de couverture contre la volatilité des cours.
- 🔬 **Scanner & Diagnostic Phytosanitaire par Vision IA** (`/diagnostic`) :
  - Reconnaissance automatique de plus de 40 pathologies végétales, maladies fongiques et insectes ravageurs via Vision IA (Mistral Pixtral).
  - Détection des auxiliaires bénéfiques (coccinelles, syrphes) et recommandations de biocontrôle.
- 🐛 **Agent Détection d'Insectes & Cartes d'Alerte** (`backend/agent_insects`) :
  - Détection des ravageurs par traitement d'images et génération de cartes d'alerte territorialisées avec LangGraph.
- ♻️ **Valorisation des Déchets & Coproduits** (`backend/waste_agents`) :
  - Base de connaissances et marketplace de valorisation des résidus de récolte (méthanisation, compostage, paillage).
- 🌦️ **Dashboard Météo Agricole & Pulvérisation** (`/weather`) :
  - Fenêtres météo optimales de traitement, cumul pluviométrique et alertes gel/canicule.
- 📊 **Étude Économique & Business Plan** (`/business`) :
  - Modélisation technico-économique, marges brutes, rentabilité prévisionnelle basée sur les séries FAOSTAT.

---

## 🏛️ Architecture Multi-Agents & Ports Backend

Le backend est architecturé en micro-services spécialisés FastAPI interconnectés :

| Service | Port | Description |
| :--- | :---: | :--- |
| **Business Agent** | `8000` | Scénarios économiques, rentabilité, historique FAOSTAT |
| **Auth Service** | `8001` | Authentification JWT, gestion des rôles (*farmer* / *acheteur*) et profils |
| **Agriculture Agent** | `8002` | Cadastre, RPG, SoilGrids, Sentinel-2, Relief 3D, Diagnostic Vision |
| **Monitoring Agent** | `8003` | Surveillance quotidienne, suivi d'exploitation et alertes |
| **Waste Agent** | `8004` | Valorisation des coproduits et déchets agricoles |
| **Regulation Agent** | `8005` | RAG Réglementaire PAC, BCAE, subventions et aides en direct |
| **Weather Agent** | `8006` | Données météorologiques haute précision et fenêtres de traitement |
| **Trading Agent** | `8007` | Cotations Euronext/MATIF, signaux de vente et stratégies de marché |
| **Orchestrator** | `8008` | Agent superviseur LangGraph pour le routage et handoffs multi-agents |
| **Insects Agent** | `8009` | Détection d'insectes, sévérité et cartographie des alertes |

---

## 🚀 Démarrage Rapide

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Node.js 20+

### 1. Variables d'environnement
À la racine du projet :
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```
Ouvrez `.env` et renseignez votre clé **`MISTRAL_API_KEY`** (compte gratuit sur [console.mistral.ai](https://console.mistral.ai/)).
Optionnellement, renseignez `SENTINEL_HUB_CLIENT_ID` / `SENTINEL_HUB_CLIENT_SECRET`, `VITE_MAPBOX_TOKEN`, et `WEB_SEARCH_API_KEY` (Tavily).

### 2. Démarrer la base de données PostgreSQL / PostGIS
```bash
docker compose up -d db
```
*(Le schéma `database/schema.sql` est initialisé automatiquement au premier lancement).*

### 3. Installer les dépendances Python
Utilisez le virtualenv partagé du projet :
```powershell
# Windows
.\scripts\setup_venv.ps1
```
```bash
# Linux / macOS
./scripts/setup_venv.sh
```

### 4. Lancer tous les agents Backend
Lancez l'ensemble des agents et la base de données en une seule commande :
```bash
python scripts/run_backend.py --with-db
```
*Pour vérifier la santé des services : rendez-vous sur `http://localhost:8002/health`, `http://localhost:8005/health`, etc.*

### 5. Démarrer le Frontend (React / Vite / TanStack Start)
Dans un nouveau terminal :
```bash
cd frontend
npm install
npm run dev
```
Ouvrez votre navigateur sur **`http://localhost:8080`** (ou l'URL locale affichée par Vite).

---

## 📂 Structure du Répertoire

```
AgriGuide_Project/
├── backend/
│   ├── agent_agriculture/   # Cadastre, RPG, sol, satellite, 3D LiDAR, Diagnostic Vision
│   ├── agent_business/      # Modèles financiers, scénarios, FAOSTAT
│   ├── agent_insects/       # Détection d'insectes & cartographie des alertes (LangGraph)
│   ├── agent_monitoring/    # Suivi d'exploitation et alertes
│   ├── agent_regulation/    # RAG réglementaire PAC, subventions & aides
│   ├── agent_trading/       # Bourse Euronext/MATIF & stratégie de commercialisation
│   ├── agent_weather/       # Météorologie & fenêtres de pulvérisation
│   ├── auth/                # Authentification, JWT, profils agriculteurs
│   ├── orchestrator/        # Superviseur & coordination LangGraph
│   ├── waste_agents/        # Valorisation des coproduits & marketplace déchets
│   └── shared/              # Modèles et clients partagés
├── database/
│   ├── schema.sql           # Schéma PostgreSQL + PostGIS
│   └── migrations/          # Scripts de migration incrémentaux
├── frontend/                # Application React 19 / TanStack Router & Start / TailwindCSS
├── scripts/                 # Scripts d'automatisation (run_backend.py, setup, etc.)
└── docker-compose.yml       # Stack PostgreSQL PostGIS
```

---

## 🛠️ Dépannage Courant

- **Erreur 429 Mistral (Rate Limit)** :
  Assurez-vous que votre modèle est configuré sur un modèle compatible avec votre plan dans `.env` :
  ```env
  MISTRAL_MODEL=open-mistral-7b
  ```
- **Base de données / migrations** :
  Si vous devez réinitialiser la base de données locale à neuf :
  ```bash
  docker compose down -v
  docker compose up -d db
  ```
- **Dépendances Frontend** :
  En cas de problème avec des modules graphiques (Three.js, Mapbox, Leaflet) :
  ```bash
  cd frontend && npm install
  ```
