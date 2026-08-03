# market_analysis → intégré dans l'agent Business

Ce dossier standalone a été intégré dans :

```
backend/agent_business/app/market_intelligence/
```

Les fichiers `data/FDS_IPPAP_*.csv` et `data/FranceAgriMer_*.pdf` sont consommés
directement par l'agent Business.

```bash
cd backend/agent_business
.venv\Scripts\activate          # Windows
python -m app.market_intelligence.rag.ingest   # index PDF (une fois)
uvicorn app.main:app --reload --port 8000
```

Voir `backend/agent_business/README.md`.
N