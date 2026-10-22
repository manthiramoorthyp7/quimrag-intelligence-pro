"""These tests call the real local Ollama server (llama3.2 models) -- skipped
automatically if Ollama isn't reachable, since CI/other machines may not have
it installed. Not mocked: the whole point is to test real judge behavior."""
import pytest

from quimrag.local_llm import ollama_available
from quimrag import ragas_eval as R

pytestmark = pytest.mark.skipif(not ollama_available(), reason="Ollama server not running locally")

CONTEXT = ["The quarterly revenue for the finance division was 842 million dollars in Q1 2021."]


def test_faithfulness_high_for_grounded_answer():
    ans = "The finance division revenue was 842 million dollars in Q1 2021."
    score, _ = R.faithfulness(ans, CONTEXT)
    assert score is not None and score >= 0.5


def test_faithfulness_low_for_fabricated_answer():
    ans = "The finance division revenue was 1.5 billion dollars, and the CEO resigned in protest."
    score, _ = R.faithfulness(ans, CONTEXT)
    assert score is not None and score <= 0.5


def test_harmfulness_zero_for_benign_answer():
    score, _ = R.harmfulness("The revenue was 842 million dollars.")
    assert score == 0


def test_context_precision_in_range():
    score, _ = R.context_precision("What was the revenue?", CONTEXT)
    assert score is None or 0.0 <= score <= 1.0


def test_context_recall_high_when_attributable():
    score, _ = R.context_recall("Revenue was 842 million dollars in Q1 2021.", CONTEXT)
    assert score is not None and score >= 0.5


def test_answer_relevancy_in_range():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    score, _ = R.answer_relevancy("What was the revenue?", "Revenue was 842 million dollars.", model)
    assert score is None or -1.0 <= score <= 1.0
