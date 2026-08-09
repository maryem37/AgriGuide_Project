# Agent Business

**Rôle** : à partir des `crop_recommendations` réelles de l'agent Agriculture
et du budget, proposer 3 scénarios financièrement détaillés, enregistrer le
choix du farmer et fournir le contexte de culture à l'agent Monitoring.

Le score final est déterministe :

```text
35% rentabilité + 20% maîtrise du risque + 20% adéquation budget
+ 25% compatibilité agronomique Agriculture
```

Le LLM peut résumer les documents de marché, mais ne calcule ni les finances
ni le score de classement.

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
| Prix €/kg | Barème absolu + tendance réelle IPPAP (IPPAP = indice, pas €) |
| Rendement | Historique FAOSTAT, fallback barème explicite |
| Coûts | CSV opérateur ou calcul des intrants Agriculture, fallback explicite |
| Risques | Compatibilité Agriculture + marché + volatilité + qualité des coûts |

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
- `GET /business/decisions/{terrain_id}/latest` — contexte persistant Monitoring

Chaque scénario contient revenu brut, coût total, profit, marge, ROI, seuils
de rentabilité, écart au budget, explications de risque et confiance des
données. Les scénarios et décisions sont persistés dans PostgreSQL.
Les endpoints Business exigent le JWT Bearer émis par Auth. Le terrain et
son propriétaire sont vérifiés côté serveur; la superficie PostgreSQL est
utilisée à la place de la valeur fournie par le navigateur.

Pour une base déjà créée, appliquer une fois :

```bash
psql "$DATABASE_URL" -f database/migration_business_financials.sql
```

### Sources financières configurables

```text
BUSINESS_FAO_YIELD_CSV=/data/profit/faostat.csv
BUSINESS_COST_DATA_CSV=/data/profit/costs.csv
```

Le CSV de coûts accepte `culture` (ou `crop`), `cost_per_ha_eur` (ou
`cout_eur_par_ha`), et optionnellement `source`, `year`. Sans ce CSV, le
service calcule les intrants depuis `besoins_engrais`, `besoins_irrigation`
et `besoins_pesticides`; un barème de secours n'est utilisé que si ces
quantités sont absentes, et le scénario est alors marqué `cout_fallback`.

Pour les tests hors PostgreSQL :

```text
BUSINESS_PERSISTENCE_MODE=memory
BUSINESS_AUTH_DISABLED=1
```

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
