"""One shared QuIMRAG instance per process (modular monolith -- see
ARCHITECTURE_DECISIONS.md #2), guarded by a lock because FastAPI runs
BackgroundTasks in a threadpool and QuIMRAG.add_document/remove_document/
reindex() mutate shared, non-thread-safe state (self.chunks, self.matrix).
Every call that touches the engine must hold ENGINE_LOCK."""
import os
import threading

from quimrag import adaptive as EAR
from quimrag.core import QuIMRAG

from . import config

ENGINE_LOCK = threading.RLock()
_engine: QuIMRAG | None = None
_ear_model: EAR.EARModel | None = None


def get_engine() -> QuIMRAG:
    global _engine
    if _engine is None:
        with ENGINE_LOCK:
            if _engine is None:
                _engine = QuIMRAG()
    return _engine


def get_ear_model() -> EAR.EARModel:
    """Loads the calibrated model produced by research/run_benchmark_v2.py
    (document-disjoint split, see research/FINAL_VALIDATION/). Falls back to
    an uncalibrated default (coef=0) if the file is missing, clearly logged,
    rather than silently crashing the /ask endpoint -- a missing calibration
    file is a real, reportable condition, not something to hide."""
    global _ear_model
    if _ear_model is None:
        with ENGINE_LOCK:
            if _ear_model is None:
                if os.path.exists(config.EAR_CALIBRATION_PATH):
                    _ear_model = EAR.EARModel.load(config.EAR_CALIBRATION_PATH)
                else:
                    _ear_model = EAR.EARModel()  # uncalibrated default, documented above
    return _ear_model
