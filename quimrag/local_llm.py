"""Local LLM generation and judging via Ollama (http://localhost:11434) --
no API key, no cost, fully offline. Mirrors quimrag.llm_answer.generate_answer's
grounded, citation-enforcing prompt, but runs locally against whatever models
`ollama list` reports installed."""
import requests

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:latest"
FAST_MODEL = "llama3.2:1b"


def ollama_available():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return r.ok
    except Exception:
        return False


def list_local_models():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def generate(prompt, model=DEFAULT_MODEL, system=None, timeout=90, temperature=None):
    """Raw single-turn generation call -- the primitive every function below builds on.
    `temperature=0` is used for judge/classification calls (ragas_eval.py) to
    reduce run-to-run inconsistency; left at Ollama's default for free-form answers."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def generate_answer_local(query, evidence, model=DEFAULT_MODEL, max_chars=6000):
    """Same contract as quimrag.llm_answer.generate_answer: grounded strictly
    in the supplied evidence, citing [chunk_id] after every claim."""
    context = "\n\n".join(
        f"[{e['chunk_id']}] ({e['document']}, page {e['page']}): {e['text']}" for e in evidence
    )[:max_chars]
    system = (
        "Answer strictly and only using the CONTEXT passages below; do not use outside "
        "knowledge. After every factual claim, cite the source like [C12]. If the context "
        "does not contain enough information to answer, say so explicitly instead of guessing. "
        "Be concise."
    )
    prompt = f"CONTEXT:\n{context}\n\nQUESTION: {query}"
    return generate(prompt, model=model, system=system)
