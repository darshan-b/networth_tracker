"""Reusable visual surface helpers for polished app sections."""

from html import escape
from typing import Iterable

import streamlit as st


def inject_surface_styles() -> None:
    """Inject shared product-surface styles once per page render."""
    st.markdown(
        """
        <style>
        .app-hero {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 34%),
                linear-gradient(135deg, #f7faf9 0%, #eef7f3 52%, #f8f5ef 100%);
            border: 1px solid rgba(15, 118, 110, 0.16);
            border-radius: 24px;
            padding: 1.5rem 1.7rem;
            margin-bottom: 1.15rem;
            box-shadow:
                0 18px 42px rgba(15, 23, 42, 0.06),
                0 1px 0 rgba(255, 255, 255, 0.82) inset;
        }
        .app-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
            font-weight: 600;
            color: #0f766e;
            margin-bottom: 0.45rem;
        }
        .app-title {
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 700;
            color: #111827;
            margin: 0;
        }
        .app-subtitle {
            margin-top: 0.6rem;
            color: #4b5563;
            font-size: 0.98rem;
            max-width: 54rem;
        }
        .app-hero-meta {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 1rem;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.8);
            color: #1f2937;
            font-size: 0.88rem;
        }
        .app-card {
            background: linear-gradient(180deg, #ffffff 0%, #fbfcfd 100%);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 22px;
            padding: 1rem 1.05rem;
            min-height: 148px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        }
        .app-card-label {
            color: #6b7280;
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }
        .app-card-value {
            color: #111827;
            font-size: 1.75rem;
            line-height: 1.1;
            font-weight: 700;
            margin-top: 0.55rem;
        }
        .app-card-delta {
            margin-top: 0.55rem;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .app-card-delta.positive { color: #0f766e; }
        .app-card-delta.negative { color: #b91c1c; }
        .app-card-delta.neutral { color: #475569; }
        .app-card-caption {
            color: #6b7280;
            font-size: 0.88rem;
            margin-top: 0.7rem;
        }
        .app-section-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.25rem;
        }
        .app-section-copy {
            color: #6b7280;
            font-size: 0.95rem;
            margin-bottom: 0.95rem;
        }
        .app-accent-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-bottom: 1rem;
        }
        .app-accent-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.75rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(15, 23, 42, 0.08);
            color: #334155;
            font-size: 0.86rem;
        }
        .app-panel-head {
            border-radius: 20px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.6rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: linear-gradient(180deg, #ffffff 0%, #f8fbfa 100%);
        }
        .app-panel-head.assets {
            background: linear-gradient(180deg, #f5fbf7 0%, #edf8f2 100%);
            border-color: rgba(15, 118, 110, 0.12);
        }
        .app-panel-head.liabilities {
            background: linear-gradient(180deg, #fff7f7 0%, #fff0f0 100%);
            border-color: rgba(185, 28, 28, 0.12);
        }
        .app-panel-head.neutral {
            background: linear-gradient(180deg, #f8fafc 0%, #f2f6f9 100%);
            border-color: rgba(96, 125, 139, 0.12);
        }
        .app-panel-kicker {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.76rem;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 0.3rem;
        }
        .app-panel-title {
            color: #0f172a;
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .app-panel-copy {
            color: #64748b;
            font-size: 0.9rem;
        }
        .app-panel-stat {
            margin-top: 0.75rem;
            font-size: 0.88rem;
            color: #1f2937;
            font-weight: 600;
        }
        .app-panel-note {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: linear-gradient(180deg, #f9fafb 0%, #f3f6f8 100%);
            border: 1px dashed rgba(100, 116, 139, 0.35);
            color: #475569;
        }
        div[data-testid="stPlotlyChart"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(248,250,252,0.98) 100%);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 24px;
            padding: 0.55rem 0.55rem 0.15rem 0.55rem;
            box-shadow:
                0 12px 34px rgba(15, 23, 42, 0.06),
                0 1px 0 rgba(255, 255, 255, 0.75) inset;
            margin-bottom: 0.35rem;
        }
        div[data-testid="stPlotlyChart"] > div {
            border-radius: 18px;
            overflow: visible;
        }
        div[data-testid="stPlotlyChart"] .js-plotly-plot .plotly .main-svg {
            border-radius: 18px;
        }
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container,
        div[data-testid="stPlotlyChart"] .modebar {
            overflow: visible !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.45rem;
            background: rgba(248, 250, 252, 0.86);
            border: 1px solid rgba(15, 23, 42, 0.07);
            border-radius: 18px;
            padding: 0.35rem;
            margin-bottom: 1rem;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            height: auto;
            border-radius: 14px;
            padding: 0.52rem 0.95rem;
            background: transparent;
            color: #475569;
            font-weight: 600;
            transition: all 140ms ease;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            background: rgba(255, 255, 255, 0.74);
            color: #0f172a;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,250,249,0.96) 100%);
            color: #0f172a;
            box-shadow:
                0 10px 24px rgba(15, 23, 42, 0.06),
                0 1px 0 rgba(255,255,255,0.88) inset;
            border: 1px solid rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(249,250,251,0.98) 100%);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
            overflow: hidden;
        }
        div[data-testid="stExpander"] details summary {
            padding-top: 0.2rem;
            padding-bottom: 0.2rem;
        }
        div[data-testid="stExpander"] details summary p {
            color: #0f172a;
            font-weight: 600;
        }
        div[data-testid="stSegmentedControl"] {
            background: rgba(248, 250, 252, 0.86);
            border: 1px solid rgba(15, 23, 42, 0.07);
            border-radius: 16px;
            padding: 0.22rem;
        }
        div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button {
            border-radius: 12px;
            font-weight: 600;
        }
        div[data-testid="stSegmentedControl"] [aria-pressed="true"] {
            background: linear-gradient(180deg, #ffffff 0%, #f5faf8 100%);
            color: #0f172a;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stMarkdownContainer"] p {
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(eyebrow: str, title: str, subtitle: str, meta_text: str) -> None:
    """Render a reusable hero header."""
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-eyebrow">{escape(eyebrow)}</div>
            <p class="app-title">{escape(title)}</p>
            <div class="app-subtitle">{escape(subtitle)}</div>
            <div class="app-hero-meta">{escape(meta_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, delta: str, caption: str, tone: str = "neutral") -> None:
    """Render a reusable metric card."""
    st.markdown(
        f"""
        <div class="app-card">
            <div class="app-card-label">{escape(label)}</div>
            <div class="app-card-value">{escape(value)}</div>
            <div class="app-card-delta {escape(tone)}">{escape(delta)}</div>
            <div class="app-card-caption">{escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_intro(title: str, copy: str) -> None:
    """Render a reusable section intro."""
    st.markdown(
        f"""
        <div class="app-section-title">{escape(title)}</div>
        <div class="app-section-copy">{escape(copy)}</div>
        """,
        unsafe_allow_html=True,
    )


def render_accent_pills(items: Iterable[tuple[str, str]]) -> None:
    """Render compact summary pills."""
    pills_html = "".join(
        [
            f"<div class='app-accent-pill'><strong>{escape(label)}</strong><span>{escape(value)}</span></div>"
            for label, value in items
        ]
    )
    st.markdown(f"<div class='app-accent-row'>{pills_html}</div>", unsafe_allow_html=True)


def render_panel_head(tone: str, kicker: str, title: str, copy: str, stat_text: str) -> None:
    """Render a reusable panel header."""
    st.markdown(
        f"""
        <div class="app-panel-head {escape(tone)}">
            <div class="app-panel-kicker">{escape(kicker)}</div>
            <div class="app-panel-title">{escape(title)}</div>
            <div class="app-panel-copy">{escape(copy)}</div>
            <div class="app-panel-stat">{escape(stat_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel_note(title: str, copy: str) -> None:
    """Render a reusable empty/info note."""
    st.markdown(
        f"""
        <div class="app-panel-note">
            <strong>{escape(title)}</strong><br>
            {escape(copy)}
        </div>
        """,
        unsafe_allow_html=True,
    )
