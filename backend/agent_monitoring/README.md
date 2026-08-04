# Agent Monitoring (Suivi quotidien)

**Rôle** : briefing opérationnel une fois la décision de culture confirmée —
météo du jour, conseils d'irrigation, alertes et tâches.

## Lancer en local

```bash
cd backend/agent_monitoring
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
# MISTRAL_API_KEY doit être dans le .env racine ou exporté
uvicorn app.main:app --reload --port 8003
```

URL frontend : `VITE_AGENT_MONITORING_URL=http://localhost:8003`

## API

### `GET /health`

### `POST /monitoring/analyze`

Corps (contexte réel — plus de `mock_db`) :

```json
{
  "farmer_name": "Alice Dupont",
  "terrain_id": "uuid-optionnel",
  "location": { "latitude": 46.8, "longitude": 2.3, "label": "Berry" },
  "crops": [
    { "crop_name": "tomate", "hectares": 4.5, "water_sensitivity": "high" }
  ],
  "hardware_inventory": ["tracteur", "pulverisateur"]
}
```

Réponse : `weather_summary` + `analysis` (`has_alert`, `daily_advice`,
`water_saving_technique`, `tasks`, `crop_alerts`).

## Pipeline LangGraph

1. `fetch_weather` — Open-Meteo (lat/lon du terrain)
2. `mistral_reasoning` — conseils structurés JSON

## Hors scope (plus tard)

- Fenêtre de récolte → suggestion marketplace
- Jobs Celery Beat / persistance `alerts` / BSV phytosanitaire
- Lecture directe PostgreSQL des `farmer_decisions` (en attendant, le
  frontend envoie le contexte depuis Auth + décision confirmée)
