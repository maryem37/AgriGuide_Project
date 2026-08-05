"""
Example programmatic usage of the Agricultural Waste Intelligence Agent,
without going through the Streamlit UI. Useful for scripting, batch
research jobs, or testing your API keys.

Run with:
    python examples/example_queries.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.knowledge_base import KnowledgeBaseAgent
from agents.reasoner import ReasonerAgent


def example_research_a_crop() -> None:
    """Trigger autonomous research for a single crop and print a summary."""
    kb_agent = KnowledgeBaseAgent()

    def progress(msg: str, frac: float) -> None:
        print(f"[{frac:5.0%}] {msg}")

    summary = kb_agent.research_and_sync_crop("Rice", progress_cb=progress)
    print("\n--- Research summary ---")
    for k, v in summary.as_dict().items():
        print(f"{k}: {v}")


def example_batch_research(crops: list[str]) -> None:
    """Research multiple crops in sequence, building up the knowledge base."""
    kb_agent = KnowledgeBaseAgent()
    for crop in crops:
        print(f"\n=== Researching {crop} ===")
        summary = kb_agent.research_and_sync_crop(crop)
        print(f"  -> {summary.wastes_added_or_updated} wastes synced "
              f"({summary.sources_used}/{summary.sources_found} sources used)")


def example_ask_a_question() -> None:
    """Ask a free-form question; the reasoner will use the knowledge base and,
    if needed, trigger live research automatically."""
    reasoner = ReasonerAgent()
    result = reasoner.answer(
        "What can Rice husk be transformed into?",
        crop_hint="Rice",
    )
    print("\n--- Answer ---")
    print(result.answer)
    print(f"\nStatus: {result.status.value} | Live research triggered: {result.triggered_live_research}")
    print(f"References: {len(result.references)}")


def example_compare_crops() -> None:
    reasoner = ReasonerAgent()
    result = reasoner.compare_crops(["Rice", "Wheat"])
    print("\n--- Comparison ---")
    print(result.answer)


def example_inspect_knowledge_base() -> None:
    kb_agent = KnowledgeBaseAgent()
    kb = kb_agent.get_knowledge_base()
    print("\n--- Knowledge base stats ---")
    print(kb.stats())
    for crop in kb.crops:
        print(f"\n{crop.name} ({crop.scientific_name}) - {len(crop.wastes)} waste(s)")
        for waste in crop.wastes:
            print(f"  - {waste.canonical_name} (confidence={waste.confidence:.2f}, "
                  f"{len(waste.transformations)} transformation(s))")


if __name__ == "__main__":
    print("This script requires MISTRAL_API_KEY and a web search key (TAVILY_API_KEY or "
          "SERPER_API_KEY) to be set in your environment or .env file.\n")

    # Uncomment the examples you want to run:

    # example_research_a_crop()
    # example_batch_research(["Rice", "Banana", "Coffee"])
    # example_ask_a_question()
    # example_compare_crops()
    example_inspect_knowledge_base()
