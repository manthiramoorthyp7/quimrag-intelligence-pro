"""Design system v2: colourful, friendly, light. Real color (not one muted
accent), rounded corners, soft shadows, a distinct hue per category/chart
series -- a deliberate pivot from the earlier restrained dark system, per
direct user request. Still: clear hierarchy, readable contrast, no dead
controls, real data only.
"""
import streamlit as st

# ---- core palette --------------------------------------------------------
BG = "#FFFFFF"
SURFACE = "#F5F4FE"          # soft lavender-tinted card background
SURFACE_RAISED = "#FFFFFF"
BORDER = "#E6E3FB"
TEXT = "#1F2430"
TEXT_MUTED = "#6B7280"
TEXT_FAINT = "#9CA3AF"

# vivid, named accent colors -- used deliberately, not randomly
VIOLET = "#6C5CE7"           # primary
TEAL = "#00BFA6"
CORAL = "#FF6B6B"
AMBER = "#FFB020"
SKY = "#2F9BFF"
PINK = "#F368E0"
LIME = "#7BCB4C"
INDIGO = "#4C5FD5"

ACCENT = VIOLET
SUCCESS = TEAL
WARNING = AMBER
ERROR = CORAL
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

# qualitative palette for charts / per-item color coding, in preferred order
CATEGORY_COLORS = [VIOLET, TEAL, CORAL, AMBER, SKY, PINK, LIME, INDIGO]

_CSS = f"""
<style>
.block-container {{
  max-width: 1320px;
  padding-top: 1.6rem;
  padding-bottom: 3rem;
}}

/* ---- typography ---- */
h1, h2, h3 {{
  font-weight: 700 !important;
  letter-spacing: -0.01em;
  color: {TEXT} !important;
}}
h1 {{ font-size: 1.7rem !important; }}
h2 {{ font-size: 1.25rem !important; }}
h3 {{ font-size: 1.05rem !important; }}
p, li, span, label {{ color: {TEXT}; }}
code, .mono {{ font-family: {MONO} !important; }}

/* ---- page header block ---- */
.qr-pagehead {{
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 18px 22px; margin-bottom: 22px; border-radius: 16px;
  background: linear-gradient(120deg, {VIOLET}14, {SKY}10 60%, {TEAL}10);
  border: 1px solid {BORDER};
}}
.qr-pagehead .qr-title {{ font-size: 1.55rem; font-weight: 750; color: {TEXT}; letter-spacing: -0.01em; }}
.qr-pagehead .qr-sub {{ color: {TEXT_MUTED}; font-size: 0.88rem; margin-top: 3px; }}
.qr-pagehead .qr-eyebrow {{ color: {VIOLET}; font-size: 0.74rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; }}

/* ---- section header (within a page) ---- */
.qr-section {{ font-size: 1.0rem; font-weight: 750; color: {TEXT}; margin: 1.7rem 0 0.5rem 0; display: flex; align-items: center; gap: 8px; }}
.qr-section::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: {VIOLET}; display: inline-block; }}
.qr-section-sub {{ color: {TEXT_MUTED}; font-size: 0.84rem; margin-bottom: 0.9rem; }}

/* ---- status pill (vivid, colour-coded) ---- */
.qr-pill {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 700;
  letter-spacing: 0.01em; border: 1px solid transparent;
}}
.qr-pill-dot {{ width: 7px; height: 7px; border-radius: 50%; }}
.qr-pill-done {{ background: {TEAL}1A; color: #00917E; border-color: {TEAL}44; }}
.qr-pill-done .qr-pill-dot {{ background: {TEAL}; }}
.qr-pill-running {{ background: {AMBER}1A; color: #A6700A; border-color: {AMBER}44; }}
.qr-pill-running .qr-pill-dot {{ background: {AMBER}; }}
.qr-pill-blocked {{ background: {CORAL}1A; color: #D43D3D; border-color: {CORAL}44; }}
.qr-pill-blocked .qr-pill-dot {{ background: {CORAL}; }}
.qr-pill-notstarted {{ background: #EEF0F4; color: {TEXT_FAINT}; border-color: {BORDER}; }}
.qr-pill-notstarted .qr-pill-dot {{ background: {TEXT_FAINT}; }}
.qr-pill-limited {{ background: {VIOLET}1A; color: #5444C9; border-color: {VIOLET}44; }}
.qr-pill-limited .qr-pill-dot {{ background: {VIOLET}; }}

/* ---- card / panel ---- */
.qr-panel {{
  background: {SURFACE_RAISED}; border: 1px solid {BORDER}; border-radius: 14px;
  padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(108,92,231,0.06);
}}
.qr-panel-tight {{ padding: 12px 16px; }}

/* ---- data stat ---- */
.qr-stat-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 8px 0 6px 0; }}
.qr-stat {{
  min-width: 128px; padding: 12px 16px; border-radius: 12px;
  background: {SURFACE}; border: 1px solid {BORDER};
}}
.qr-stat .qr-stat-label {{ color: {TEXT_MUTED}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }}
.qr-stat .qr-stat-value {{ font-family: {MONO}; font-size: 1.45rem; font-weight: 750; color: {VIOLET}; margin-top: 3px; }}
.qr-stat .qr-stat-caption {{ color: {TEXT_FAINT}; font-size: 0.72rem; margin-top: 2px; }}

/* ---- empty state ---- */
.qr-empty {{
  border: 2px dashed {BORDER}; border-radius: 16px; padding: 32px 22px;
  text-align: center; color: {TEXT_MUTED}; background: {SURFACE};
}}
.qr-empty .qr-empty-title {{ color: {TEXT}; font-weight: 700; margin-bottom: 4px; font-size: 1.02rem; }}

/* ---- note / caveat strip ---- */
.qr-note {{
  border-left: 3px solid {SKY}; padding: 8px 14px; color: {TEXT_MUTED};
  font-size: 0.84rem; background: {SKY}0D; border-radius: 0 10px 10px 0;
}}

/* ---- sidebar ---- */
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {SURFACE}, #FFFFFF 40%); border-right: 1px solid {BORDER}; }}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}

/* ---- widgets: rounded, colourful ---- */
div[data-testid="stMetric"] {{
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px;
}}
div[data-testid="stExpander"] {{ border: 1px solid {BORDER} !important; border-radius: 12px !important; overflow: hidden; }}
.stButton>button, .stDownloadButton>button {{ border-radius: 10px; border: 1px solid {BORDER}; font-weight: 600; }}
.stButton>button[kind="primary"] {{ background: linear-gradient(120deg, {VIOLET}, {INDIGO}); border: none; color: white; }}
hr {{ border-color: {BORDER} !important; }}
div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
div[data-testid="stTabs"] button {{ border-radius: 10px 10px 0 0; }}

/* ---- nav ---- */
div[data-testid="stSidebarNav"] a {{ font-size: 0.88rem; border-radius: 10px; }}
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str = ""):
    st.markdown(
        f"""<div class="qr-pagehead">
            <div><div class="qr-eyebrow">{eyebrow}</div>
                 <div class="qr-title">{title}</div>
                 <div class="qr-sub">{subtitle}</div></div>
        </div>""",
        unsafe_allow_html=True,
    )
