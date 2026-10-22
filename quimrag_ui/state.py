"""Idempotent session-state initialization shared by every page."""
import os

import streamlit as st

from quimrag.core import QuIMRAG
from quimrag import adaptive as EAR

_EAR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "data", "ear_calibration.json")


def init_state():
    if "engine" not in st.session_state:
        st.session_state.engine = QuIMRAG()
    if "hallucination_log" not in st.session_state:
        st.session_state.hallucination_log = []
    if "ocr_eval_log" not in st.session_state:
        st.session_state.ocr_eval_log = []
    if "ear_model" not in st.session_state:
        st.session_state.ear_model = EAR.EARModel.load(_EAR_PATH) if os.path.exists(_EAR_PATH) else EAR.EARModel()
        st.session_state.ear_calibrated = os.path.exists(_EAR_PATH)
    if "conversation" not in st.session_state:
        st.session_state.conversation = []  # list of {q, res, lat, queries_used, generated}


def engine():
    return st.session_state.engine
