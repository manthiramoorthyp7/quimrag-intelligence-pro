"""Citation validation: every [C123]-style marker in a generated answer must
reference a chunk_id that was actually in the evidence set passed to the
generator (Phase 5: "A citation must reference a real source document and
valid page/chunk metadata", Phase 8: guard against the model inventing a
citation that looks plausible but points nowhere)."""
import re

_CITATION_RE = re.compile(r"\[(C\d+)\]")


def extract_citation_ids(answer_text: str) -> set[str]:
    return set(_CITATION_RE.findall(answer_text or ""))


def verify_citations(answer_text: str, evidence: list[dict]) -> bool:
    """True iff every citation marker in the answer resolves to a chunk_id
    that is actually present in `evidence` (the exact set the generator was
    given). An answer with zero citation markers is NOT auto-passed -- the
    caller decides separately whether that's acceptable (e.g. abstention
    text legitimately has none); this function only checks that whatever
    citations DO appear are not fabricated/dangling."""
    cited = extract_citation_ids(answer_text)
    if not cited:
        return True
    known = {e["chunk_id"] for e in evidence}
    return cited.issubset(known)
