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

## Démarrage rapide

```bash
cp .env.example .env    # remplir les clés API (voir .env.example)
docker compose up -d    # lance postgres, redis, et les services backend
```

## Équipe — répartition suggérée

Chaque dossier sous `backend/` est un lot de travail quasi indépendant.
Voir `docs/team_guide.md` pour la répartition détaillée et les interfaces
entre modules (ce que chaque agent reçoit / renvoie).
