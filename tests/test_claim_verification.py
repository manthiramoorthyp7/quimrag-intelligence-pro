"""Unit tests for backend/claim_verification.py's parsing and lineage-
assembly logic, with the judge LLM call mocked out (deterministic, no
Ollama required) -- these test the EICV-RAG claim verification pipeline's
own code, not the judge model's actual reasoning quality (that requires a
real model and is covered separately by the integration test in
test_backend_api.py, which is skipped when Ollama is unavailable)."""
from unittest.mock import patch

from backend import claim_verification as CV

EVIDENCE = [
    {"chunk_id": "C1", "document": "doc-a", "page": 1, "text": "Revenue was $42 million in 2024.",
     "source": "native", "ocr_confidence": None, "score": 0.9},
    {"chunk_id": "C2", "document": "doc-a", "page": 2, "text": "Headcount was 310 employees.",
     "source": "native", "ocr_confidence": None, "score": 0.5},
]


def test_extract_claims_strips_citation_markers_before_sending_to_judge():
    captured = {}

    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        captured["prompt"] = prompt
        return "1. Revenue was $42 million in 2024.\n2. Headcount was 310 employees."

    with patch.object(CV, "generate", fake_generate):
        claims = CV.extract_claims("Revenue was $42 million in 2024. [C1] Headcount was 310 employees. [C2]")
    assert "[C1]" not in captured["prompt"]
    assert "[C2]" not in captured["prompt"]
    assert claims == ["Revenue was $42 million in 2024.", "Headcount was 310 employees."]


def test_extract_claims_returns_empty_list_for_empty_answer():
    assert CV.extract_claims("") == []
    assert CV.extract_claims("   ") == []


def test_attribute_claims_parses_supported_with_chunk_ids():
    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        return "1. SUPPORTED [C1]\n2. UNSUPPORTED"

    with patch.object(CV, "generate", fake_generate):
        out = CV._attribute_claims(["Revenue was $42M.", "Something not in evidence."], EVIDENCE, "fake-model")
    assert out[1] == {"status": "SUPPORTED", "chunk_ids": ["C1"]}
    assert out[2] == {"status": "UNSUPPORTED", "chunk_ids": []}


def test_attribute_claims_parses_multiple_chunk_ids():
    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        return "1. SUPPORTED [C1,C2]"

    with patch.object(CV, "generate", fake_generate):
        out = CV._attribute_claims(["Multi-source claim."], EVIDENCE, "fake-model")
    assert set(out[1]["chunk_ids"]) == {"C1", "C2"}


def test_attribute_claims_ignores_unparseable_lines():
    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        return "some preamble the judge wasn't supposed to write\n1. SUPPORTED [C1]"

    with patch.object(CV, "generate", fake_generate):
        out = CV._attribute_claims(["Revenue was $42M."], EVIDENCE, "fake-model")
    assert out[1]["status"] == "SUPPORTED"


def test_lineage_only_includes_requested_chunks_with_real_fields():
    lineage = CV._lineage_for_chunks(["C1"], EVIDENCE)
    assert len(lineage) == 1
    assert lineage[0]["chunk_id"] == "C1"
    assert lineage[0]["document_id"] == "doc-a"
    assert lineage[0]["retrieval_rank"] == 1  # C1 is evidence[0]
    assert lineage[0]["ocr_confidence"] is None  # not fabricated when absent


def test_verify_answer_end_to_end_with_mocked_judge_detects_counterfactual_sensitivity():
    """Mocks the judge to always find C1 supporting, then (on the
    counterfactual re-check with C1 removed) UNSUPPORTED -- the exact
    behavior the real Ollama-backed test observed in manual verification."""
    call_count = {"n": 0}

    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        call_count["n"] += 1
        if "List each distinct factual claim" in prompt:
            return "1. Revenue was $42 million in 2024."
        # NOTE: can't naively check "C1" in prompt -- the instruction
        # template's own format example "[C12]" contains "C1" as a
        # substring. Check the EVIDENCE PASSAGES section specifically.
        evidence_section = prompt.split("CLAIMS:")[0]
        if "[C1]" in evidence_section:  # first attribution call, C1 still present
            return "1. SUPPORTED [C1]"
        return "1. UNSUPPORTED"  # counterfactual re-check, C1 removed

    with patch.object(CV, "generate", fake_generate):
        result = CV.verify_answer("Revenue was $42 million in 2024. [C1]", EVIDENCE, judge_model="fake-model")

    assert result["overall"]["n_claims"] == 1
    assert result["claims"][0]["support_status"] == "SUPPORTED"
    assert result["claims"][0]["supporting_chunk_ids"] == ["C1"]
    assert result["claims"][0]["counterfactual"]["support_changed"] is True
    assert result["claims"][0]["counterfactual"]["support_after_removal"] == "UNSUPPORTED"
    assert result["overall"]["n_counterfactual_sensitive"] == 1


def test_verify_answer_does_not_run_counterfactual_when_disabled():
    def fake_generate(prompt, model=None, timeout=60, temperature=None):
        if "List each distinct factual claim" in prompt:
            return "1. Revenue was $42 million in 2024."
        return "1. SUPPORTED [C1]"

    with patch.object(CV, "generate", fake_generate):
        result = CV.verify_answer("Revenue was $42 million in 2024. [C1]", EVIDENCE,
                                   judge_model="fake-model", run_counterfactual=False)
    assert result["claims"][0]["counterfactual"] is None
    assert result["overall"]["n_counterfactual_tested"] == 0


def test_verify_answer_handles_no_claims_gracefully():
    with patch.object(CV, "generate", lambda *a, **k: ""):
        result = CV.verify_answer("", EVIDENCE)
    assert result["claims"] == []
    assert result["overall"]["n_claims"] == 0
    assert result["overall"]["claim_support_rate"] is None
