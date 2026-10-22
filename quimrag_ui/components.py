"""Reusable UI primitives shared across pages, built on top of theme.py's CSS
classes. Kept deliberately plain -- data tables and precise typography over
decorative cards, per the design brief."""
import streamlit as st

_PILL_CLASS = {
    "done": "qr-pill-done",
    "running": "qr-pill-running",
    "blocked": "qr-pill-blocked",
    "not_started": "qr-pill-notstarted",
    "limited": "qr-pill-limited",
    "failed": "qr-pill-blocked",
}
_PILL_LABEL = {
    "done": "Completed",
    "running": "Running",
    "blocked": "Blocked — missing data",
    "not_started": "Not started",
    "limited": "Completed with limitations",
    "failed": "Failed",
}


def status_pill(status: str, label: str = None):
    cls = _PILL_CLASS.get(status, "qr-pill-notstarted")
    text = label or _PILL_LABEL.get(status, status)
    st.markdown(f'<span class="qr-pill {cls}"><span class="qr-pill-dot"></span>{text}</span>', unsafe_allow_html=True)


def section(title: str, subtitle: str = ""):
    sub = f'<div class="qr-section-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="qr-section">{title}</div>{sub}', unsafe_allow_html=True)


def stat_row(items):
    """items: list of (label, value, caption_or_None)"""
    cells = []
    for label, value, caption in items:
        cap = f'<div class="qr-stat-caption">{caption}</div>' if caption else ""
        cells.append(f'<div class="qr-stat"><div class="qr-stat-label">{label}</div>'
                      f'<div class="qr-stat-value">{value}</div>{cap}</div>')
    st.markdown(f'<div class="qr-stat-row">{"".join(cells)}</div>', unsafe_allow_html=True)


def empty_state(title: str, body: str):
    st.markdown(f'<div class="qr-empty"><div class="qr-empty-title">{title}</div>{body}</div>', unsafe_allow_html=True)


def note(text: str):
    st.markdown(f'<div class="qr-note">{text}</div>', unsafe_allow_html=True)


def panel_start():
    st.markdown('<div class="qr-panel">', unsafe_allow_html=True)


def panel_end():
    st.markdown('</div>', unsafe_allow_html=True)
