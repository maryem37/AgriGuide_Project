# Agent Business

**Rôle** : à partir des crop_recommendations + budget, proposer 3 scénarios
chiffrés (quantité/ha, profit estimé, risque, solution au risque).

## Pipeline marché (réel)

```
data/
  FDS_IPPAP_*.csv          → tendances d'indice Agreste (pandas)
  FranceAgriMer_*.pdf     → bulletins (RAG Chroma + Mistral)
        ↓
market_intelligence.provider.get_market_price()
        ↓
market_study.estimer_marche() → scénarios Business
```

| Signal | Source |
|--------|--------|
| Tendance de prix | Agreste IPPAP (CSV) |
| Demande / concurrence / justification | FranceAgriMer PDF via RAG + Mistral |
| Prix €/kg + rendement | Barème de référence (IPPAP = indice, pas €) |
| Risques / coûts de production | Encore simulés |

RAG s'active **automatiquement** si l'index vectoriel local existe et
`MISTRAL_API_KEY` est défini. Désactiver avec `MARKET_RAG_ENABLED=0`.

## Setup local

```bash
cd backend/agent_business
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt

# 1) Indexer les PDF + CSV du dossier data/ (à faire une fois, ou après ajout de fichiers)
python -m app.market_intelligence.rag.ingest

# 2) Lancer l'API (utiliser le venv)
uvicorn app.main:app --reload --port 8000
```

Vérifier : `GET http://127.0.0.1:8000/health` → `market.rag_active: true` une fois
l'index créé (`app/market_intelligence/rag/vector_store/`).

L'index utilise les embeddings **Mistral** (`mistral-embed`) — nécessite
`MISTRAL_API_KEY` dans le `.env` racine.

### Données

Par défaut : `AgriGuide/data/` (CSVs + PDFs). Surcharge possible :

```
MARKET_DATA_DIR=C:\chemin\vers\data
```

## Endpoints

- `GET /health` — statut + diagnostics marché
- `POST /business/scenarios` — 3 scénarios
- `POST /business/decision` — confirmation farmer

## Matching score (déterministe)

```
score = w1 * profit_normalise + w2 * (1 - risque_normalise) + w3 * fit_budget
```

Le LLM enrichit l'étude de marché (justification, demande, concurrence), jamais
le matching_score.

## Prochaines étapes

1. Flux RNM live pour les prix €/kg
2. BSV réel pour les risques
3. Planning PDF après confirmation de scénario
4. Persistance PostgreSQL des décisions
