"""Raisonnement Mistral pour le briefing quotidien."""
from __future__ import annotations

import json

try:
    from mistralai import Mistral
except ImportError:  # SDK 0.x / 1.0 early layout
    from mistralai.client import Mistral  # type: ignore[attr-defined]

from app.config import settings
from app.models.schemas import AnalysisResult, AnalyzeRequest, CropAlert, WeatherSummary

SYSTEM_PROMPT = """Tu es un agent agricole expert. Analyse la météo du jour, les cultures actives et le matériel disponible pour produire un briefing opérationnel en français.

RÈGLES MÉTÉO:
- Base-toi UNIQUEMENT sur les valeurs numériques (températures, précipitations, vent).
- has_alert = true seulement s'il y a une menace imminente (canicule forte, pluie > 70% de proba, vent dangereux, gel, etc.).

RÈGLES CONSEILS:
- daily_advice: 2-3 phrases actionnables, en tenant compte de TOUTES les cultures listées.
- water_saving_technique: 1-2 phrases de sobriété hydrique adaptées au matériel listé dans hardware_inventory (n'invente pas d'équipement absent).
- tasks: 3 à 6 tâches concrètes du jour (phrases courtes, une action chacune).
- crop_alerts: une entrée par culture avec vigilance du jour (risque low/medium/high), message court, action recommandée. Pas de données phytosanitaires inventées hors contexte météo/culture.

FORMAT:
Retourne UNIQUEMENT un objet JSON valide avec les clés:
has_alert (bool), alert_message (string|null), daily_advice (string),
water_saving_technique (string), tasks (string[]),
crop_alerts (array of {crop, risk, message, action}).
Pas de markdown, pas de commentaire."""


def run_mistral_analysis(request: AnalyzeRequest, weather: WeatherSummary) -> AnalysisResult:
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY is missing. Set it in the .env file.")

    client = Mistral(api_key=settings.mistral_api_key)
    user_payload = {
        "farmer_name": request.farmer_name,
        "location": request.location.model_dump(),
        "crops": [c.model_dump() for c in request.crops],
        "hardware_inventory": request.hardware_inventory,
        "weather_data": weather.model_dump(),
    }

    response = client.chat.complete(
        model=settings.mistral_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ],
    )
    content = response.choices[0].message.content
    parsed = json.loads(content)

    crop_alerts: list[CropAlert] = []
    for raw in parsed.get("crop_alerts") or []:
        if not isinstance(raw, dict):
            continue
        crop = str(raw.get("crop") or "").strip()
        if not crop:
            continue
        risk = str(raw.get("risk") or "low").lower()
        if risk not in {"low", "medium", "high"}:
            risk = "low"
        crop_alerts.append(
            CropAlert(
                crop=crop,
                risk=risk,
                message=str(raw.get("message") or "").strip() or "Surveillance recommandée.",
                action=str(raw.get("action") or "").strip() or "Inspecter la parcelle.",
            )
        )

    tasks = [str(t).strip() for t in (parsed.get("tasks") or []) if str(t).strip()]

    return AnalysisResult(
        has_alert=bool(parsed.get("has_alert")),
        alert_message=parsed.get("alert_message"),
        daily_advice=str(parsed.get("daily_advice") or "").strip()
        or "Surveillez vos parcelles et adaptez l'irrigation aux conditions du jour.",
        water_saving_technique=str(parsed.get("water_saving_technique") or "").strip()
        or "Arrosez de préférence en fin de journée pour limiter l'évaporation.",
        tasks=tasks,
        crop_alerts=crop_alerts,
    )
