"""
Unit tests for extraction batching (agents/knowledge_base._build_batches and
agents/extractor.ExtractorAgent.extract_batch).

The property that matters most here: batching an entire research pass into
a handful of LLM calls must never lose a source or blur which evidence
belongs to which source. No network calls are made in this file -- the LLM
is a fake that records how many times it was invoked and returns
pre-scripted batch responses.
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.extractor import ExtractorAgent
from agents.knowledge_base import _build_batches
from models import ExtractionStatus, SearchResult, SourceType
from services.llm_service import LLMService


def make_source(i: int, chars: int = 500, doi: Optional[str] = None) -> SearchResult:
    return SearchResult(
        source_type=SourceType.ACADEMIC_PAPER,
        title=f"Source {i}",
        doi=doi if doi is not None else f"10.1234/source{i}",
        url=f"https://example.com/{i}",
        authors=["A. Author"],
        published_year=2020,
        snippet="x" * chars,
    )


class FakeLLMService(LLMService):
    """Records call count; returns a scripted response instead of hitting the network."""

    def __init__(self, response) -> None:
        self.response = response
        self.calls = 0

    def complete(self, system_prompt, user_prompt, temperature=None, max_tokens=4000) -> str:
        raise NotImplementedError("Tests use complete_json only.")

    def complete_json(self, system_prompt, user_prompt, temperature=None, max_tokens=4000):
        self.calls += 1
        return self.response(user_prompt) if callable(self.response) else self.response


def _waste_entry(label: str) -> dict:
    return {
        "name": f"Waste {label}",
        "canonical_name": f"Waste {label}",
        "description": f"A documented byproduct described in passage {label}, with real extracted detail.",
        "confidence": 0.9,
        "evidence_strength": "HIGH",
    }


def _batch_response_all_success(sources: list[SearchResult]):
    def response(_user_prompt: str) -> dict:
        return {
            "results": [
                {
                    "source_id": f"S{i + 1}",
                    "crop": "Rice",
                    "scientific_name": "",
                    "aliases": [],
                    "status": "SUCCESS",
                    "wastes": [_waste_entry(f"S{i + 1}")],
                }
                for i in range(len(sources))
            ]
        }

    return response


# ---------------------------------------------------------------------------
# _build_batches
# ---------------------------------------------------------------------------

def test_build_batches_loses_no_source() -> None:
    sources = [make_source(i) for i in range(30)]
    batches = _build_batches(sources, batch_size=6, max_chars=24000)
    assert len(batches) == 5
    assert sum(len(b) for b in batches) == 30


def test_build_batches_respects_char_budget() -> None:
    sources = [make_source(i, chars=12000) for i in range(4)]
    batches = _build_batches(sources, batch_size=6, max_chars=24000)
    assert all(len(b) <= 2 for b in batches)
    assert sum(len(b) for b in batches) == 4


def test_build_batches_size_one_is_one_batch_per_source() -> None:
    sources = [make_source(i) for i in range(5)]
    batches = _build_batches(sources, batch_size=1, max_chars=24000)
    assert batches == [[s] for s in sources]


def test_build_batches_oversized_single_source_gets_its_own_batch() -> None:
    sources = [make_source(0, chars=50000)]
    batches = _build_batches(sources, batch_size=6, max_chars=24000)
    assert len(batches) == 1
    assert len(batches[0]) == 1


# ---------------------------------------------------------------------------
# ExtractorAgent.extract_batch
# ---------------------------------------------------------------------------

def test_extract_batch_makes_exactly_one_llm_call_for_a_full_batch() -> None:
    sources = [make_source(i) for i in range(6)]
    fake = FakeLLMService(_batch_response_all_success(sources))
    extractor = ExtractorAgent(llm_service=fake)

    results = extractor.extract_batch(sources, requested_crop="Rice")

    assert fake.calls == 1
    assert len(results) == 6


def test_extract_batch_preserves_each_sources_own_doi() -> None:
    sources = [make_source(0, doi="10.1111/aaa"), make_source(1, doi="10.2222/bbb")]
    fake = FakeLLMService(_batch_response_all_success(sources))
    extractor = ExtractorAgent(llm_service=fake)

    results = extractor.extract_batch(sources, requested_crop="Rice")

    result_a = results[extractor._source_key(sources[0])]
    result_b = results[extractor._source_key(sources[1])]
    assert result_a.wastes[0].references[0].doi == "10.1111/aaa"
    assert result_b.wastes[0].references[0].doi == "10.2222/bbb"


def test_extract_batch_records_unknown_for_source_the_model_forgot() -> None:
    sources = [make_source(0), make_source(1)]

    def response(_user_prompt: str) -> dict:
        return {
            "results": [
                {
                    "source_id": "S1",
                    "crop": "Rice",
                    "status": "SUCCESS",
                    "wastes": [_waste_entry("S1")],
                }
                # S2 is missing from the model's output entirely.
            ]
        }

    fake = FakeLLMService(response)
    extractor = ExtractorAgent(llm_service=fake)
    results = extractor.extract_batch(sources, requested_crop="Rice")

    assert len(results) == 2
    forgotten = results[extractor._source_key(sources[1])]
    assert forgotten.status == ExtractionStatus.UNKNOWN


def test_extract_batch_discards_an_invented_source_id() -> None:
    sources = [make_source(0), make_source(1)]

    def response(_user_prompt: str) -> dict:
        return {
            "results": [
                {"source_id": "S1", "crop": "Rice", "status": "SUCCESS", "wastes": [_waste_entry("S1")]},
                {"source_id": "S2", "crop": "Rice", "status": "SUCCESS", "wastes": [_waste_entry("S2")]},
                {"source_id": "S99", "crop": "Ghost", "status": "SUCCESS", "wastes": [_waste_entry("ghost")]},
            ]
        }

    fake = FakeLLMService(response)
    extractor = ExtractorAgent(llm_service=fake)
    results = extractor.extract_batch(sources, requested_crop="Rice")

    assert len(results) == 2
    assert extractor._source_key(sources[0]) in results
    assert extractor._source_key(sources[1]) in results


# ---------------------------------------------------------------------------
# Pre-filter
# ---------------------------------------------------------------------------

def test_pre_filter_discards_thin_source_and_keeps_substantial_one() -> None:
    extractor = ExtractorAgent(llm_service=FakeLLMService({}))
    thin = make_source(0, chars=20)
    thick = make_source(1, chars=2000)

    assert extractor.is_worth_extracting(thin) is False
    assert extractor.is_worth_extracting(thick) is True
