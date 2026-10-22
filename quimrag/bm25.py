import re
import numpy as np
_TOKEN_RE=re.compile(r"[A-Za-z0-9]+")
def tokenize(text):
 return [t.lower() for t in _TOKEN_RE.findall(text)]
class BM25Index:
 """IDF-weighted, length-normalized BM25 (rank_bm25.BM25Okapi). Replaces the
 earlier substring term-overlap score used for 'Lexical only' mode. Rebuilt
 whenever the corpus changes, same cadence as the dense embedding matrix."""
 def __init__(self):
  self._bm25=None;self._n=0
 def build(self,texts):
  self._n=len(texts)
  if not texts:
   self._bm25=None;return
  from rank_bm25 import BM25Okapi
  self._bm25=BM25Okapi([tokenize(t) for t in texts])
 def scores(self,query):
  if self._bm25 is None:return np.zeros(self._n)
  return np.asarray(self._bm25.get_scores(tokenize(query)),dtype=float)
