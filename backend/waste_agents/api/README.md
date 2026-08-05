# Agent Déchets — API AgriGuide

Expose `knowledge/canonical_knowledge.json` to the React app (Agriculture →
Business → Marketplace). **No LLM keys required** for these endpoints.

## Run

```bash
cd backend/waste_agents
pip install -r requirements.txt   # includes fastapi + uvicorn
uvicorn api.main:app --reload --port 8004
```

Health: `GET http://localhost:8004/health`

## Endpoints

| Method | Path | Role |
|--------|------|------|
| `POST` | `/waste/for-crops` | Body `{ "cultures": ["ble_tendre", "mais", ...] }` → waste profiles for the top-5 agri crops |
| `GET` | `/waste/marketplace-suggestions?culture=mais` | Wastes to list on the marketplace after harvest |
| `POST` | `/waste/reload` | Clear in-memory KB cache after editing the JSON |

## Frontend

Set `VITE_AGENT_WASTE_URL=http://localhost:8004` (optional; this is the default).

Live research / enrichment of the KB remains available via:

```bash
streamlit run ui/streamlit_app.py
```
