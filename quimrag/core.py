import io,re
import numpy as np, pymupdf
from PIL import Image,ImageOps,ImageEnhance,ImageFilter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from .bm25 import BM25Index
_MODEL=None
def device_name():
 try:
  import torch
  if torch.backends.mps.is_available():return "MPS"
  if torch.cuda.is_available():return "CUDA"
 except Exception:pass
 return "CPU"
def load_model(dev):
 global _MODEL
 if _MODEL is None:
  from sentence_transformers import SentenceTransformer
  _MODEL=SentenceTransformer("all-MiniLM-L6-v2",device=dev.lower() if dev!="MPS" else "mps")
 return _MODEL
def _ocr_page(im):
 """Runs Tesseract once via image_to_data (not image_to_string) so we get both
 the text and real per-word confidence, reconstructing line breaks from
 (block,par,line) grouping so paragraph detection in chunks_from still works."""
 import pytesseract
 from pytesseract import Output
 data=pytesseract.image_to_data(im,config="--psm 3",output_type=Output.DICT)
 lines={};confs=[]
 for i,w in enumerate(data["text"]):
  w=w.strip()
  if not w:continue
  try:
   c=int(data["conf"][i])
   if c>=0:confs.append(c)
  except (ValueError,KeyError):pass
  key=(data["block_num"][i],data["par_num"][i],data["line_num"][i])
  lines.setdefault(key,[]).append(w)
 text="\n".join(" ".join(ws) for ws in lines.values())
 conf=(sum(confs)/len(confs))/100.0 if confs else None
 return text.strip(),conf
def extract_pdf(data,ocr=True):
 doc=pymupdf.open(stream=data,filetype="pdf");out=[];notes=[];meta=[]
 for n,p in enumerate(doc):
  text=p.get_text("text").strip();source="native";conf=None
  if not text and ocr:
   try:
    pix=p.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),alpha=False)
    im=Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    im=ImageEnhance.Contrast(ImageOps.autocontrast(im.filter(ImageFilter.MedianFilter()))).enhance(1.25)
    text,conf=_ocr_page(im);source="ocr"
    if not text:notes.append(f"Page {n+1}: OCR returned no text.")
   except Exception as ex:notes.append(f"Page {n+1}: OCR unavailable: {ex}");source="ocr_failed"
  out.append(text);meta.append({"source":source,"ocr_confidence":conf})
 doc.close();return out,notes,meta
def chunks_from(text,limit=950,overlap=100):
 paras=[re.sub(r"\s+"," ",s).strip() for s in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-Z0-9])",text) if s.strip()]
 out=[];buf=""
 for p in paras:
  if len(p)>limit:
   if buf:out.append(buf);buf=""
   out.extend(p[i:i+limit] for i in range(0,len(p),limit-overlap))
  elif len(buf)+len(p)>limit:
   if buf:out.append(buf)
   buf=(buf[-overlap:]+" "+p).strip()
  else:buf=(buf+" "+p).strip()
 if buf:out.append(buf)
 return out
class QuIMRAG:
 def __init__(self):
  self.documents={};self.chunks=[];self.matrix=None;self.vectorizer=None;self.dev=device_name();self.model=None;self.backend="TF-IDF fallback";self.reranker=None;self.bm25=BM25Index()
  try:self.model=load_model(self.dev);self.backend="all-MiniLM-L6-v2"
  except Exception:pass
  try:
   from sentence_transformers import CrossEncoder
   self.reranker=CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2",device=self.dev.lower() if self.dev!="MPS" else "mps")
  except Exception:pass
 def add_document(self,name,pages,page_meta=None,embed=True):
  self.documents[name]=pages
  meta=page_meta or [{"source":"native","ocr_confidence":None}]*len(pages)
  for pno,(text,m) in enumerate(zip(pages,meta),1):
   for part in chunks_from(text):
    self.chunks.append({"chunk_id":f"C{len(self.chunks)+1}","document":name,"page":pno,"text":part,
                         "source":m.get("source","native"),"ocr_confidence":m.get("ocr_confidence")})
  if embed:self.reindex()
 def remove_document(self,name,embed=True):
  """Removes a document and every chunk derived from it (and, after reindex(),
  every vector/BM25 posting derived from those chunks) -- used by the backend's
  delete endpoint, which must be able to verify no trace of a deleted document's
  content remains retrievable. Returns the number of chunks removed."""
  if name not in self.documents:return 0
  del self.documents[name]
  before=len(self.chunks)
  self.chunks=[c for c in self.chunks if c["document"]!=name]
  removed=before-len(self.chunks)
  if embed:self.reindex()
  return removed
 def reindex(self):
  """(Re)embeds every chunk from scratch. Called automatically by add_document(embed=True,
  the default, used by the live UI); callers bulk-loading many documents (e.g. a benchmark
  harness) should pass embed=False per document and call this once at the end instead,
  otherwise each add_document call would re-embed an ever-growing corpus from scratch."""
  if not self.chunks:return
  texts=[c["text"] for c in self.chunks]
  if self.model:self.matrix=np.asarray(self.model.encode(texts,batch_size=32,normalize_embeddings=True,show_progress_bar=False))
  else:
   self.vectorizer=TfidfVectorizer(ngram_range=(1,2),max_features=16000);self.matrix=self.vectorizer.fit_transform(texts).toarray()
  self.bm25.build(texts)
 def retrieve(self,q,k=5,mode="Hybrid",rerank=False):
  if not self.chunks:return []
  texts=[c["text"] for c in self.chunks]
  if self.model:
   dense=cosine_similarity(self.model.encode([q],normalize_embeddings=True),self.matrix)[0]
  else:
   self.vectorizer=TfidfVectorizer(ngram_range=(1,2),max_features=16000);self.matrix=self.vectorizer.fit_transform(texts).toarray()
   dense=cosine_similarity(self.vectorizer.transform([q]).toarray(),self.matrix)[0]
  lex=self.bm25.scores(q)
  if mode=="Dense only":scores=dense;method="Dense"
  elif mode=="Lexical only":scores=lex;method="Lexical"
  else:
   scores=np.zeros(len(texts))
   for arr in (dense,lex):
    for rank,idx in enumerate(np.argsort(-arr)):scores[idx]+=1/(60+rank+1)
   method="RRF hybrid"
  ids=np.argsort(-scores)[:min(len(scores),k*3 if rerank and self.reranker else k)]
  if rerank and self.reranker:
   try:
    rank=np.argsort(-np.asarray(self.reranker.predict([[q,texts[i]] for i in ids])))[:k]
    return [dict(self.chunks[ids[j]],score=float(1/(j+1)),method="Cross-encoder rerank") for j in rank]
   except Exception:pass
  return [dict(self.chunks[i],score=float(scores[i]),method=method) for i in ids[:k]]
 def pca_coords(self):
  """Raw 2D PCA projection (xy array aligned with self.chunks) for callers that
  want their own interactive plot instead of the static matplotlib figure below."""
  return PCA(n_components=2).fit_transform(np.asarray(self.matrix))
 def plot(self):
  xy=PCA(n_components=2).fit_transform(np.asarray(self.matrix));fig,ax=plt.subplots(figsize=(9,5))
  names=[c["document"] for c in self.chunks]
  for name in dict.fromkeys(names):
   ix=[i for i,n in enumerate(names) if n==name];ax.scatter(xy[ix,0],xy[ix,1],label=name,alpha=.7)
  ax.set(title="PCA projection of chunk embeddings",xlabel="PC1",ylabel="PC2")
  if len(set(names))<10:ax.legend()
  fig.tight_layout();return fig
