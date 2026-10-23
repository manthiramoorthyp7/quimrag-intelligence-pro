"""Generation-provider abstraction (Phase 7: "clean interface between...
generation models", "never silently send private documents to an external
API"). Three providers, selected explicitly, never implicitly upgraded:
- "local"       Ollama (quimrag.local_llm) -- the default, fully offline.
- "extractive"  No model call at all (quimrag.llm_answer.extractive_answer).
- "anthropic"   Only used if ANTHROPIC_API_KEY is set AND explicitly
                requested per-call or via QUIMRAG_GENERATION_PROVIDER --
                never a silent fallback from "local"."""
from quimrag.llm_answer import extractive_answer, generate_answer
from quimrag.local_llm import generate_answer_local, ollama_available

from . import config


class GenerationError(Exception):
    pass


def generate(query: str, evidence: list[dict], provider: str, model: str | None = None) -> tuple[str, str]:
    """Returns (answer_text, provider_actually_used). Falls back to
    extractive ONLY within the same trust boundary (no external call), and
    always reports which provider actually produced the answer so the API
    response is never misleading about where the text came from. `model`
    overrides the provider's own default model string when given (e.g. a
    specific locally-installed Ollama tag, or a specific Claude model id) --
    ignored for provider="extractive", which never calls a model at all."""
    if provider == "extractive":
        return extractive_answer(query, evidence), "extractive"

    if provider == "anthropic":
        if not config.ANTHROPIC_API_KEY:
            raise GenerationError("provider=anthropic requested but ANTHROPIC_API_KEY is not set")
        kwargs = {"model": model} if model else {}
        answer = generate_answer(query, evidence, api_key=config.ANTHROPIC_API_KEY, **kwargs)
        return answer, "anthropic"

    # default: local (Ollama)
    if not ollama_available():
        # explicit, visible fallback -- never silently claim "local" succeeded
        return extractive_answer(query, evidence), "extractive (ollama unavailable)"
    kwargs = {"model": model} if model else {}
    answer = generate_answer_local(query, evidence, **kwargs)
    return answer, "local"
