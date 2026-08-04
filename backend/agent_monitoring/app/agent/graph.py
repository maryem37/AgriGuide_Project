from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, AnalysisResult, WeatherSummary
from app.services.mistral_service import run_mistral_analysis
from app.services.weather_service import fetch_weather_summary


class AgentState(TypedDict):
    request: AnalyzeRequest
    weather_data: Optional[WeatherSummary]
    analysis: Optional[AnalysisResult]
    error: Optional[str]


def fetch_weather_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    req = state["request"]
    weather = fetch_weather_summary(
        latitude=req.location.latitude,
        longitude=req.location.longitude,
        location_label=req.location.label,
    )
    return {**state, "weather_data": weather}


def mistral_reasoning_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    req = state["request"]
    weather = state["weather_data"]
    if weather is None:
        return {**state, "error": "Données météo manquantes."}
    try:
        analysis = run_mistral_analysis(req, weather)
        return {**state, "analysis": analysis}
    except Exception as exc:  # noqa: BLE001 — surface as agent error
        return {**state, "error": f"Analyse Mistral échouée: {exc}"}


def build_monitoring_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("fetch_weather", fetch_weather_node)
    workflow.add_node("mistral_reasoning", mistral_reasoning_node)
    workflow.add_edge(START, "fetch_weather")
    workflow.add_edge("fetch_weather", "mistral_reasoning")
    workflow.add_edge("mistral_reasoning", END)
    return workflow.compile()


monitoring_agent = build_monitoring_graph()


def run_analysis(request: AnalyzeRequest) -> AnalyzeResponse:
    initial: AgentState = {
        "request": request,
        "weather_data": None,
        "analysis": None,
        "error": None,
    }
    result: dict[str, Any] = monitoring_agent.invoke(initial)
    if result.get("error"):
        raise RuntimeError(result["error"])

    weather: WeatherSummary = result["weather_data"]
    analysis: AnalysisResult = result["analysis"]
    return AnalyzeResponse(
        farmer_name=request.farmer_name,
        location=request.location.label,
        terrain_id=request.terrain_id,
        crops=request.crops,
        weather_summary=weather,
        analysis=analysis,
    )
