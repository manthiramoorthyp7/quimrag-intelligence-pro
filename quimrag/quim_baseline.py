"""A faithful-as-available reproduction of QuIM-RAG's core mechanism (Saha,
Saha & Malik, IEEE Access 2024): inverted question-matching retrieval --
generate a representative question per chunk, embed the QUESTION (not the
chunk), and at query time retrieve the chunks whose question embedding is
nearest the query. This is the paper's proposed method; quimrag.core's
"Dense only" mode already is its baseline ("Traditional RAG": direct
chunk-embedding cosine retrieval) -- no new code needed for that side.

Documented deviations from the original paper (see
research/NDSU_REPRODUCTION_REPORT.md for the full discussion):
  - Question generation: the paper uses GPT-3.5-turbo-instruct to generate
    several candidate questions per chunk, manually reviewed by two
    researchers. This reproduction uses quimrag.question_tree.
    heuristic_question (template-based, one question per chunk) -- no LLM
    API key is available in this environment.
  - Embedding model: the paper uses BAAI/bge-large-en-v1.5. This
    reproduction uses all-MiniLM-L6-v2, the embedding model already used
    throughout this project, so the comparison against this project's other
    retrieval modes is on identical embeddings.
  - Indexing: the paper buckets question embeddings by nearest K-Means
    prototype for sub-linear lookup. This reproduction does direct
    brute-force nearest-question search -- functionally equivalent in
    retrieval accuracy, just without the indexing-speed optimization, which
    is irrelevant at this corpus's size.
"""
import numpy as np

from .question_tree import heuristic_question


class QuIMBaselineIndex:
    def __init__(self, engine):
        self.engine = engine
        self.questions = []
        self.question_matrix = None

    def build(self):
        self.questions = [heuristic_question(c["text"]) for c in self.engine.chunks]
        if self.engine.model:
            self.question_matrix = np.asarray(self.engine.model.encode(
                self.questions, batch_size=32, normalize_embeddings=True, show_progress_bar=False))
        else:
            self.question_matrix = self.engine.vectorizer.transform(self.questions).toarray()
        return self

    def retrieve(self, query, k=5):
        from sklearn.metrics.pairwise import cosine_similarity
        if self.engine.model:
            qv = self.engine.model.encode([query], normalize_embeddings=True)
        else:
            qv = self.engine.vectorizer.transform([query]).toarray()
        scores = cosine_similarity(qv, self.question_matrix)[0]
        ids = np.argsort(-scores)[:k]
        return [dict(self.engine.chunks[i], score=float(scores[i]), method="QuIM-style question-matching",
                     matched_question=self.questions[i]) for i in ids]


def make_quim_retriever(engine):
    idx = QuIMBaselineIndex(engine).build()
    return (lambda q, k: idx.retrieve(q, k)), idx
