# Agent Business

**Rôle** : à partir des crop_recommendations + budget, proposer 3 scénarios
chiffrés (quantité/ha, profit estimé, risque, solution au risque).

## État actuel

Implémenté avec données **simulées** (voir `app/data/`) pour permettre le
développement indépendant des autres agents. À remplacer progressivement par
de vraies sources (RNM/FranceAgriMer, BSV régional, barèmes de coûts).

```
app/
├── main.py                        # point d'entrée FastAPI
├── models/schemas.py               # Pydantic, alignés sur schema.sql
├── data/
│   ├── mock_crop_recommendations.py   # simule la sortie de l'agent Agriculture
│   ├── mock_market_prices.py          # simule RNM/FranceAgriMer
│   ├── mock_risks.py                  # simule le croisement BSV régional
│   └── mock_production_costs.py       # coûts de production par ha
├── services/
│   ├── market_study.py              # prix, rendement, date de récolte estimée
│   ├── risk_study.py                # risque_score = probabilite * impact
│   ├── scoring.py                   # formule explicite du matching_score
│   ├── scenario_generator.py        # assemble tout -> N scénarios triés
│   └── decision_service.py          # human-in-the-loop, calcule cout_final
├── routers/business.py              # POST /business/scenarios, /business/decision
└── tests/
    ├── demo_pipeline.py              # démo bout-en-bout en local (sans serveur)
    └── test_endpoints.py             # tests des endpoints FastAPI
```

## Lancer la démo

```bash
cd backend/agent_business
pip install -r requirements.txt
python -m app.tests.demo_pipeline      # pipeline complet en console
python -m app.tests.test_endpoints     # tests des endpoints FastAPI
uvicorn app.main:app --reload          # lancer le serveur (docs sur /docs)
```

## Prochaines étapes (remplacement progressif des mocks)

1. Brancher `mock_market_prices.py` sur la vraie API RNM/FranceAgriMer
2. Brancher `mock_risks.py` sur les Bulletins de Santé du Végétal régionaux réels
3. Remplacer `mock_crop_recommendations.py` par un appel HTTP à l'agent Agriculture
4. Persister les résultats dans PostgreSQL (`business_scenarios`,
   `farmer_decisions`, `decision_allocations`) au lieu de les retourner en
   mémoire uniquement
5. Calibrer les poids `POIDS_PROFIT / POIDS_RISQUE / POIDS_BUDGET_FIT` dans
   `scoring.py` avec l'équipe une fois de vraies données disponibles

## Entrée
- `crop_recommendations` (top 5 + besoins) du terrain
- `budget_input` fourni par le farmer

## Calcul du matching score (formule explicite, PAS le LLM)
```
score = w1 * profit_normalise + w2 * (1 - risque_normalise) + w3 * fit_budget
```
Les poids w1/w2/w3 sont à calibrer et documenter ici une fois fixés.
Le LLM (Mistral) sert uniquement à rédiger la narration/explication du
scénario, jamais à calculer le score lui-même.

## Sources de données
Prix de marché réels via RNM / FranceAgriMer (pas une pure estimation LLM).

## Sortie (écrit en base)
- `business_scenarios` : 3 scénarios par culture retenue
- Après confirmation du farmer (human-in-the-loop) :
  `farmer_decisions` + `decision_allocations`
  (inclut `date_maturite_prevue`, utilisée plus tard par l'agent Monitoring)
