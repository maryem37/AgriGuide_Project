# Guide équipe — qui fait quoi

## Répartition suggérée (5 lots de travail indépendants)

| Lot | Dossier | Dépend de | Livre |
|---|---|---|---|
| 1. Agriculture Advisor | `backend/agent_agriculture/` | rien (backend déjà existant à réutiliser) | `land_profiles`, `crop_recommendations` |
| 2. Business Advisor | `backend/agent_business/` | Lot 1 (besoin des crop_recommendations) | `business_scenarios`, `farmer_decisions` |
| 3. Régulation Advisor | `backend/agent_regulation/` | rien (peut démarrer en parallèle, le RAG est indépendant) | `regulation_documents`, `dossiers_administratifs` |
| 4. Monitoring + Marketplace | `backend/agent_monitoring/`, `backend/marketplace/` | Lots 1 et 2 (a besoin des dates de maturité et décisions confirmées) | `alerts`, `monitoring_logs`, `annonces` |
| 5. Orchestrateur + Frontend | `backend/orchestrator/`, `frontend/` | tous les agents exposent au moins un endpoint stub | routage LangGraph, intégration Lovable |
| 6. Auth | `backend/auth/` | rien (indépendant, premier module connecté à une vraie PostgreSQL) | `users.role`, `farmer_equipements`, `terrains` |

**Conseil** : commencez tous les lots par un stub qui renvoie des données
factices respectant le schéma (`database/schema.sql`) — ça permet à
l'orchestrateur et au frontend d'avancer en parallèle sans attendre que
chaque agent soit fini.

## Ordre de développement conseillé (MVP)

1. Schéma DB (fait — `database/schema.sql`) + `docker-compose up` fonctionnel pour tous
2. Agent Agriculture (base déjà existante, le plus rapide à livrer)
3. Agent Business (scoring)
4. Orchestrateur minimal (routage entre 1 et 2)
5. Agent Régulation (RAG — le plus long, prévoir large)
6. Agent Monitoring + Marketplace (en dernier, dépend des tables amont)
7. Intégration frontend complète

## Règles communes

- **Chaque agent lit/écrit uniquement ses tables** (voir `ARCHITECTURE.md`
  section 3) — pas d'accès direct croisé, on passe par l'API du module
  concerné pour éviter les incohérences.
- **RGPD** : toute donnée de géolocalisation précise ou de budget est
  sensible. Consentement explicite à l'onboarding, stockage chiffré au repos
  pour les champs `budget_input`, `contact_telephone`, `contact_email`.
- **Tests** : chaque module doit avoir au moins un test qui vérifie le format
  de sortie attendu par le module suivant (ex: agent_agriculture → format
  exact attendu par agent_business).
- **Variables d'environnement** : toutes les clés API externes vont dans
  `.env` (jamais commitées) — voir `.env.example` à la racine.

## Convention de branches Git

- `main` — toujours déployable
- `feature/agent-<nom>` — une branche par lot de travail
- Pull request obligatoire avant merge sur `main`, même en solo, pour garder
  un historique propre.
