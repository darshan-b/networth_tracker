"""Sankey diagram tab for expense tracker.

Visualizes cash flow from total expenses through categories to subcategories.
"""

import streamlit as st
import pandas as pd
import json
from typing import TypedDict
from urllib.parse import quote
from app_constants import ColumnNames
from data.calculations import calculate_expense_summary, calculate_net_outflow
from data.expense_intelligence import get_month_over_month_change, get_top_change_driver
from ui.views.expense_tracker.overview import _render_summary_metrics
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_page_hero,
    render_section_intro,
)

# https://pixelied.com/colors/color-palette-generator
# Color scheme for categories
CATEGORY_COLORS = {
    'Housing':'#4d908e',
    'Income': '#277da1',
    'Transportation':'#f94144',
    'Food & Dining':'#f3722c',
    'Shopping':'#f8961e',
    'Medical':'#f9844a', 
    'Entertainment':'#f9c74f',
    'Fees':'#90be6d',
    'Education':'#43aa8b',
    'Miscellaneous':'#4d908e',
    'Utilities':'#577590',
    'Total': '#3b82f6'
}


DEFAULT_COLOR = '#94a3b8'


class SankeyNode(TypedDict):
    """Serialized Sankey node payload sent to the client renderer."""

    name: str
    displayName: str
    labelText: str
    level: int
    percent: float | None
    parentPercent: float | None
    parentName: str | None
    aggregated: bool
    color: str
    column: int
    sortOrder: int


class SankeyLink(TypedDict):
    """Serialized Sankey link payload sent to the client renderer."""

    source: int
    target: int
    value: float


class SankeyData(TypedDict):
    """Top-level Sankey data payload."""

    nodes: list[SankeyNode]
    links: list[SankeyLink]


def _format_currency(amount: float) -> str:
    """Format a numeric amount for chart labels."""
    return f"${amount:,.2f}"


def _build_display_name(name: str, amount: float, percent: float | None = None) -> str:
    """Build the full node label shown in tooltips and detailed labels."""
    value_text = _format_currency(amount)
    if percent is None:
        return f"{name}<br/>{value_text}"
    return f"{name}<br/>{value_text} ({percent:.1f}%)"


def _build_subcategory_label(name: str, percent: float, show_percent: bool) -> str:
    """Build the compact on-canvas label for a subcategory."""
    if not show_percent:
        return name
    return f"{name}<br/>({percent:.1f}%)"


def _append_node(
    nodes: list[SankeyNode],
    node_map: dict[str, int],
    name: str,
    display_name: str,
    color: str,
    node_idx: int,
    column: int,
    order: int,
    label_text: str | None = None,
    level: int | None = None,
    percent: float | None = None,
    parent_percent: float | None = None,
    parent_name: str | None = None,
    aggregated: bool = False,
) -> int:
    """Append a node with stable layout metadata for deterministic Sankey ordering."""
    nodes.append({
        "name": name,
        "displayName": display_name,
        "labelText": label_text or display_name,
        "level": level if level is not None else column,
        "percent": percent,
        "parentPercent": parent_percent,
        "parentName": parent_name,
        "aggregated": aggregated,
        "color": color,
        "column": column,
        "sortOrder": order,
    })
    node_map[name] = node_idx
    return node_idx + 1


def render_sankey_tab(df, budgets, num_months):
    """
    Render the cash flow Sankey diagram tab.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
        
    Returns:
        None
    """
    inject_surface_styles()
    render_page_hero(
        "Expenses",
        "Flow",
        "Trace how income and expenses flow through categories and subcategories.",
        "Use this view to understand movement, not just totals.",
    )
    
    if df.empty:
        st.info("No transaction data available for the selected period.")
        return
    
    df = df[df[ColumnNames.SUBCATEGORY]!='Transfer']
    summary = calculate_expense_summary(df, budgets, num_months)
    render_section_intro(
        "Snapshot",
        "Start with the top-line totals before reading the flow.",
    )
    _render_summary_metrics(summary, num_months)
    _render_sankey_brief(df, summary)

    # Generate Sankey data
    try:
        render_section_intro(
            "Flow Diagram",
            "Follow how money moves from income into the largest spending buckets.",
        )
        sankey_data = _generate_sankey_data(df)
        _render_sankey_diagram(sankey_data)
    except Exception as e:
        st.error(f"Error generating cash flow diagram: {str(e)}")
        return


def _generate_sankey_data(df: pd.DataFrame) -> SankeyData:
    """
    Generate nodes and links for a Sankey diagram showing income and expenses.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    
    Returns:
        dict: Sankey data with 'nodes' and 'links' keys.
    """
    nodes: list[SankeyNode] = []
    links: list[SankeyLink] = []
    node_map: dict[str, int] = {}
    node_idx = 0

    # Separate income and expenses
    income_df = df[df[ColumnNames.CATEGORY] == 'Income']
    expense_df = df[df[ColumnNames.CATEGORY] != 'Income']

    total_income = income_df[ColumnNames.AMOUNT].sum()

    # === Income Sources ===
    income_sources = _collect_income_sources(income_df)

    # Add income source nodes
    sorted_income_sources = sorted(income_sources.items(), key=lambda x: x[1], reverse=True)

    for order, (name, amount) in enumerate(sorted_income_sources):
        pct = (amount / total_income * 100) if total_income > 0 else 0
        node_idx = _append_node(
            nodes,
            node_map,
            name,
            _build_display_name(name, amount, pct),
            CATEGORY_COLORS.get('Total', '#3b82f6'),
            node_idx,
            column=0,
            order=order,
            level=0,
            percent=pct,
        )

    # Total Income node
    total_income_idx = node_idx
    node_idx = _append_node(
        nodes,
        node_map,
        "Total Income",
        _build_display_name("Total Income", total_income),
        CATEGORY_COLORS['Total'],
        node_idx,
        column=1,
        order=0,
        level=1,
    )

    # Links: Income sources → Total Income
    for name, amount in sorted_income_sources:
        links.append({
            "source": node_map[name],
            "target": total_income_idx,
            "value": float(amount)
        })

    # === Expenses by Category ===
    category_totals = _calculate_category_totals(expense_df)
    total_expenses = category_totals.sum()

    for order, (category, amount) in enumerate(category_totals.items()):
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
        node_idx = _append_node(
            nodes,
            node_map,
            category,
            _build_display_name(category, amount, pct),
            CATEGORY_COLORS.get(category, DEFAULT_COLOR),
            node_idx,
            column=2,
            order=order,
            label_text=_build_display_name(category, amount, pct),
            level=2,
            percent=pct,
        )
        links.append({
            "source": total_income_idx,
            "target": node_map[category],
            "value": float(amount)
        })

    # === Subcategories (as end nodes) ===
    for category_order, category in enumerate(category_totals.index):
        node_idx = _add_subcategory_nodes(
            expense_df,
            category,
            category_totals[category],
            node_map,
            nodes,
            links,
            node_idx,
            category_order,
        )

    # === Savings (Remaining) as a direct branch ===
    remaining = total_income - total_expenses
    if remaining > 0:
        pct = (remaining / total_income * 100)
        node_idx = _append_node(
            nodes,
            node_map,
            "Savings",
            _build_display_name("Savings", remaining, pct),
            CATEGORY_COLORS.get('Savings', 'blue'),
            node_idx,
            column=2,
            order=len(category_totals),
            level=2,
            percent=pct,
        )
        links.append({
            "source": total_income_idx,
            "target": node_map["Savings"],
            "value": float(remaining)
        })

    return {"nodes": nodes, "links": links}


def _render_sankey_brief(df: pd.DataFrame, summary: dict) -> None:
    """Add a concise narrative above the Sankey chart."""
    expense_df = df[df[ColumnNames.CATEGORY] != "Income"]
    category_totals = _calculate_category_totals(expense_df)
    top_categories = list(category_totals.head(3).items())
    change = get_month_over_month_change(df)
    driver = get_top_change_driver(df, change["current_month"], change["previous_month"]) if change else None

    pills = [
        ("Savings Rate", f"{summary.get('savings_rate', 0):.1f}%"),
        *[
            (f"Top {idx}", f"{name} ${amount:,.0f}")
            for idx, (name, amount) in enumerate(top_categories, start=1)
        ],
    ]
    if driver:
        pills.append(("Change Driver", f"{driver['category']} ${abs(driver['delta']):,.0f}"))
    if pills:
        render_accent_pills(pills)


def _collect_income_sources(income_df: pd.DataFrame) -> dict[str, float]:
    """Collect income-source totals, splitting by subcategory when present."""
    income_sources: dict[str, float] = {}
    for category in income_df[ColumnNames.CATEGORY].unique():
        cat_df = income_df[income_df[ColumnNames.CATEGORY] == category]
        if (cat_df[ColumnNames.SUBCATEGORY].notna() & (cat_df[ColumnNames.SUBCATEGORY] != "")).any():
            sub_totals = (
                cat_df[cat_df[ColumnNames.SUBCATEGORY].notna() & (cat_df[ColumnNames.SUBCATEGORY] != "")]
                .groupby(ColumnNames.SUBCATEGORY)[ColumnNames.AMOUNT]
                .sum()
            )
            for sub, amount in sub_totals.items():
                income_sources[f"{category} - {sub}"] = float(amount)
        else:
            income_sources[category] = float(cat_df[ColumnNames.AMOUNT].sum())
    return income_sources


def _calculate_category_totals(expense_df: pd.DataFrame) -> pd.Series:
    """Calculate positive net outflow totals by category."""
    category_totals = (
        expense_df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .pipe(calculate_net_outflow)
    )
    return category_totals[category_totals > 0].sort_values(ascending=False)


def _add_subcategory_nodes(
    df: pd.DataFrame,
    category: str,
    category_total: float,
    node_map: dict[str, int],
    nodes: list[SankeyNode],
    links: list[SankeyLink],
    node_idx: int,
    category_order: int,
) -> int:
    """
    Add subcategory nodes and links for a given category.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
        category (str): category name
        category_total (float): Total amount for the category
        node_map (dict): Mapping of node names to indices
        nodes (list): List of node dictionaries
        links (list): List of link dictionaries
        node_idx (int): Current node index
        
    Returns:
        int: Updated node index
    """
    category_df = df[df[ColumnNames.CATEGORY] == category]
    subcategory_df = category_df[
        category_df[ColumnNames.SUBCATEGORY].notna() & 
        (category_df[ColumnNames.SUBCATEGORY] != '')
    ]
    
    if subcategory_df.empty:
        return node_idx
    
    subcategory_totals = (
        subcategory_df.groupby(ColumnNames.SUBCATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .pipe(calculate_net_outflow)
    )
    subcategory_totals = (
        subcategory_totals[subcategory_totals > 0]
        .sort_values(ascending=False)
    )

    if subcategory_totals.empty:
        return node_idx

    total_expenses = (
        df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .pipe(calculate_net_outflow)
        .sum()
    )
    category_percent = (category_total / total_expenses * 100) if total_expenses > 0 else 0
    
    show_subcategory_pct = len(subcategory_totals) > 1

    for subcategory_order, (subcategory, amount) in enumerate(subcategory_totals.items()):
        pct = (amount / category_total * 100) if category_total > 0 else 0
        subcategory_label = _build_subcategory_label(subcategory, pct, show_subcategory_pct)
        node_idx = _append_node(
            nodes,
            node_map,
            f"{category}::{subcategory}",
            _build_display_name(subcategory, amount, pct),
            CATEGORY_COLORS.get(category, DEFAULT_COLOR),
            node_idx,
            column=3,
            order=(category_order * 1000) + subcategory_order,
            label_text=subcategory_label,
            level=3,
            percent=pct,
            parent_percent=category_percent,
            parent_name=category,
        )
        
        links.append({
            "source": node_map[category],
            "target": node_map[f"{category}::{subcategory}"],
            "value": float(amount)
        })
    
    return node_idx


def _render_sankey_diagram(data: dict) -> None:
    """
    Render an enhanced D3.js-based Sankey diagram.
    
    Args:
        data (dict): Sankey data containing:
            - nodes: List of dicts with 'name', optional 'color', 'category'
            - links: List of dicts with 'source', 'target', 'value'
    
    Raises:
        ValueError: If data structure is invalid
    """
    # Validate input data
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")
    if 'nodes' not in data or 'links' not in data:
        raise ValueError("Data must contain 'nodes' and 'links' keys")
    if not data['nodes'] or not data['links']:
        raise ValueError("Nodes and links cannot be empty")
    
    # Validate node structure
    for i, node in enumerate(data['nodes']):
        if 'name' not in node:
            raise ValueError(f"Node at index {i} missing 'name' field")
    
    # Validate link structure
    for i, link in enumerate(data['links']):
        required_fields = ['source', 'target', 'value']
        for field in required_fields:
            if field not in link:
                raise ValueError(f"Link at index {i} missing '{field}' field")

    node_count = len(data["nodes"])
    chart_height = max(1000, min(2200, 320 + (node_count * 38)))
    iframe_height = chart_height + 240
    
    html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
            <style>
                * {{
                    box-sizing: border-box;
                }}
                body {{
                    margin: 0;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%);
                    min-height: 100vh;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.96);
                    border-radius: 20px;
                    padding: 32px;
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.10);
                    max-width: 1800px;
                    margin: 0 auto;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 24px;
                    flex-wrap: wrap;
                    gap: 16px;
                }}
                .title-section {{
                    flex: 1;
                    min-width: 300px;
                }}
                .title {{
                    font-size: 32px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    color: #1a1a1a;
                    background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}
                .subtitle {{
                    font-size: 14px;
                    color: #64748b;
                    margin-bottom: 12px;
                }}
                .controls {{
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    align-items: center;
                }}
                .control-group {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 7px 11px;
                    border-radius: 999px;
                    background: rgba(255, 255, 255, 0.78);
                    border: 1px solid rgba(148, 163, 184, 0.16);
                    color: #475569;
                    font-size: 12px;
                    font-weight: 600;
                    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.75) inset;
                }}
                .control-group input[type="range"] {{
                    width: 108px;
                    accent-color: #2563eb;
                }}
                .control-group input[type="checkbox"] {{
                    accent-color: #2563eb;
                }}
                .control-value {{
                    min-width: 32px;
                    text-align: right;
                    color: #2563eb;
                    font-variant-numeric: tabular-nums;
                }}

                .btn {{
                    padding: 9px 18px;
                    background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
                    color: white;
                    border: none;
                    border-radius: 999px;
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22);
                }}
                .btn:active {{
                    transform: translateY(0);
                }}
                .btn-secondary {{
                    background: rgba(255, 255, 255, 0.9);
                    color: #2563eb;
                    border: 1px solid rgba(37, 99, 235, 0.18);
                }}
                .btn-secondary:hover {{
                    background: #f8fbff;
                }}
                #chart {{ 
                    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.98) 100%);
                    width: 100%;
                    height: auto;
                    border-radius: 16px;
                }}
                .chart-wrapper {{
                    position: relative;
                    overflow: hidden;
                    border-radius: 16px;
                    border: 1px solid rgba(226, 232, 240, 0.95);
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
                }}
                .node rect {{
                    stroke: #fff;
                    stroke-width: 1.5px;
                    cursor: pointer;
                    transition: opacity 0.2s ease, stroke-width 0.2s ease;
                }}
                .node rect:hover {{ 
                    opacity: 0.9;
                }}
                .node.selected rect {{
                    stroke-width: 3px;
                    stroke: rgba(15, 23, 42, 0.8);
                }}
                .node.dimmed {{
                    filter: blur(0.6px);
                }}
                .node.dimmed rect {{
                    opacity: 0.24;
                }}
                .node.dimmed foreignObject {{
                    filter: blur(0.6px);
                    opacity: 0.28;
                }}
                .link {{
                    fill: none;
                    stroke-opacity: 0.22;
                    transition: stroke-opacity 0.2s ease, stroke-width 0.2s ease, filter 0.2s ease;
                    cursor: pointer;
                }}
                .link:hover {{ 
                    stroke-opacity: 0.36;
                }}
                .link.highlighted {{
                    stroke-opacity: 0.82;
                }}
                .link.dimmed {{
                    stroke-opacity: 0.07;
                    filter: blur(0.5px);
                }}
                .node-label {{
                    font-size: 12px;
                    font-weight: 600;
                    pointer-events: none;
                    line-height: 1.35;
                    color: #243244;
                    transition: font-weight 0.2s ease;
                }}
                .node.highlighted .node-label {{
                    font-weight: 700;
                }}
                .node-label-shell {{
                    display: inline-flex;
                    flex-direction: column;
                    gap: 2px;
                    max-width: 100%;
                    padding: 6px 10px;
                    border-radius: 12px;
                    background: rgba(255, 255, 255, 0.74);
                    border: 1px solid rgba(148, 163, 184, 0.14);
                    box-shadow:
                        0 6px 18px rgba(15, 23, 42, 0.06),
                        inset 0 1px 0 rgba(255, 255, 255, 0.78);
                    backdrop-filter: blur(8px);
                }}
                .node.highlighted .node-label-shell {{
                    background: rgba(255, 255, 255, 0.88);
                    border-color: rgba(37, 99, 235, 0.18);
                }}
                .node-label-primary {{
                    font-size: 12.5px;
                    font-weight: 700;
                    color: #1e293b;
                    letter-spacing: -0.01em;
                }}
                .node-label-secondary {{
                    font-size: 10.5px;
                    font-weight: 600;
                    color: #64748b;
                    letter-spacing: 0.01em;
                }}
                .node-label-content {{
                    display: -webkit-box;
                    overflow: hidden;
                    -webkit-box-orient: vertical;
                    -webkit-line-clamp: 2;
                    white-space: normal;
                    word-break: break-word;
                    text-wrap: balance;
                }}
                .tooltip {{
                    position: absolute;
                    z-index: 20;
                    max-width: 260px;
                    padding: 8px 10px;
                    border-radius: 10px;
                    background: rgba(15, 23, 42, 0.92);
                    color: #f8fafc;
                    font-size: 12px;
                    line-height: 1.4;
                    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
                    pointer-events: none;
                    opacity: 0;
                    transform: translateY(4px);
                    transition: opacity 0.15s ease, transform 0.15s ease;
                }}
                .tooltip.visible {{
                    opacity: 1;
                    transform: translateY(0);
                }}
                .column-header {{
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 0.04em;
                    fill: #334155;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                }}
                .column-header-chip {{
                    fill: rgba(255, 255, 255, 0.88);
                    stroke: rgba(148, 163, 184, 0.22);
                    stroke-width: 1;
                }}
                .column-header-rule {{
                    stroke: rgba(37, 99, 235, 0.14);
                    stroke-width: 2;
                    stroke-linecap: round;
                }}
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(10px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .node {{
                    animation: fadeIn 0.6s ease-out forwards;
                    opacity: 0;
                }}
                .link {{
                    animation: fadeIn 0.8s ease-out forwards;
                    opacity: 0;
                }}
                @media (max-width: 768px) {{
                    .container {{
                        padding: 16px;
                    }}
                    .title {{
                        font-size: 24px;
                    }}
                    .controls {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="title-section">
                        <div class="title">Cash Flow Visualization</div>
                        <div class="subtitle">Interactive Sankey Diagram • Click nodes/links to highlight • Use mouse wheel to zoom</div>
                    </div>
                    <div class="controls">
                        <label class="control-group" for="label-threshold">
                            <span>Detail Threshold</span>
                            <input id="label-threshold" type="range" min="0" max="10" step="1" value="5">
                            <span id="label-threshold-value" class="control-value">5%</span>
                        </label>
                        <label class="control-group" for="compact-mode">
                            <input id="compact-mode" type="checkbox">
                            <span>Compact Mode</span>
                        </label>
                        <button class="btn" onclick="resetView()">Reset View</button>
                        <button class="btn btn-secondary" onclick="exportPNG()">Save as PNG</button>
                    </div>
                </div>
                
                <div class="chart-wrapper">
                    <svg id="chart"></svg>
                    <div id="tooltip" class="tooltip"></div>
                </div>
            </div>
            
            <script>
                const baseData = {json.dumps(data)};
                
                // Color scheme
                const colorPalette = [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
                    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
                    '#06b6d4', '#84cc16', '#f43f5e', '#6366f1'
                ];
                
                let selectedNode = null;
                let selectedLink = null;
                let currentTransform = d3.zoomIdentity;
                let zoom = null;
                let currentGraph = null;
                let labelThreshold = 5;
                let compactMode = false;
                let currentChartWidth = getResponsiveWidth();
                
                function getResponsiveWidth() {{
                    const containerWidth = document.querySelector('.container').clientWidth - 64;
                    const minWidth = 900;
                    const maxWidth = 1600;
                    return Math.min(maxWidth, Math.max(minWidth, containerWidth));
                }}
                
                const height = {chart_height};
                const nodeCount = baseData.nodes.length;
                const baseNodePadding = Math.max(32, Math.min(68, Math.round((height - 120) / Math.max(nodeCount + 2, 1) * 0.62)));
                const chartWrapper = document.querySelector('.chart-wrapper');
                const tooltip = document.getElementById('tooltip');
                const thresholdInput = document.getElementById('label-threshold');
                const thresholdValue = document.getElementById('label-threshold-value');
                const compactModeToggle = document.getElementById('compact-mode');

                function formatTooltipContent(text) {{
                    return String(text).replaceAll('<br/>', '<br>').replaceAll('<br>', '<br>');
                }}

                function escapeHtml(text) {{
                    return String(text)
                        .replaceAll('&', '&amp;')
                        .replaceAll('<', '&lt;')
                        .replaceAll('>', '&gt;')
                        .replaceAll('"', '&quot;')
                        .replaceAll("'", '&#39;');
                }}

                function getPrimaryLabel(node) {{
                    if (node.labelText) {{
                        return String(node.labelText).split('<br/>')[0];
                    }}
                    if (node.displayName) {{
                        return String(node.displayName).split('<br/>')[0];
                    }}
                    return node.name || '';
                }}

                function getRenderedLabel(node) {{
                    if (node.aggregated) {{
                        return node.displayName || node.labelText || node.name || '';
                    }}
                    const percent = typeof node.percent === 'number' ? node.percent : null;
                    const parentPercent = typeof node.parentPercent === 'number' ? node.parentPercent : null;
                    if (node.level === 2 && percent !== null && percent < labelThreshold) {{
                        return getPrimaryLabel(node);
                    }}
                    if (node.level === 3) {{
                        if (parentPercent !== null && parentPercent < labelThreshold) {{
                            return getPrimaryLabel(node);
                        }}
                        if (percent !== null && percent < labelThreshold) {{
                            return getPrimaryLabel(node);
                        }}
                    }}
                    return node.labelText || node.displayName || node.name || '';
                }}

                function makeDisplayName(name, value, percent = null) {{
                    const valueText = '$' + value.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                    return percent === null
                        ? `${{name}}<br/>${{valueText}}`
                        : `${{name}}<br/>${{valueText}} (${{percent.toFixed(1)}}%)`;
                }}

                function findBaseNodeByName(name) {{
                    return baseData.nodes.find(node => node.name === name) || null;
                }}

                function getIncomingValue(incomingByTarget, node) {{
                    const nodeIndex = baseData.nodes.indexOf(node);
                    const incoming = incomingByTarget.get(nodeIndex) || [];
                    return incoming.reduce((sum, link) => sum + link.value, 0);
                }}

                function createAggregatedNode(name, displayName, level, percent, color, column, sortOrder, extras = {{}}) {{
                    return {{
                        name,
                        displayName,
                        labelText: displayName,
                        level,
                        percent,
                        color,
                        column,
                        sortOrder,
                        aggregated: true,
                        ...extras,
                    }};
                }}

                function buildCompactData() {{
                    const nodeByIndex = new Map(baseData.nodes.map((node, index) => [index, node]));
                    const incomingByTarget = new Map();
                    const compactDefaultColor = '#94a3b8';

                    baseData.links.forEach((link) => {{
                        if (!incomingByTarget.has(link.target)) {{
                            incomingByTarget.set(link.target, []);
                        }}
                        incomingByTarget.get(link.target).push(link);
                    }});

                    const nodes = [];
                    const links = [];
                    const nodeIndexByName = new Map();
                    const linkIndexByPair = new Map();

                    function addNode(node) {{
                        if (nodeIndexByName.has(node.name)) {{
                            return nodeIndexByName.get(node.name);
                        }}
                        const clonedNode = {{ ...node, index: nodes.length }};
                        nodes.push(clonedNode);
                        nodeIndexByName.set(clonedNode.name, clonedNode.index);
                        return clonedNode.index;
                    }}

                    function addLink(sourceName, targetName, value) {{
                        if (!value || value <= 0) {{
                            return;
                        }}
                        const source = nodeIndexByName.get(sourceName);
                        const target = nodeIndexByName.get(targetName);
                        if (source === undefined || target === undefined) {{
                            return;
                        }}
                        const linkKey = `${{source}}->${{target}}`;
                        if (linkIndexByPair.has(linkKey)) {{
                            links[linkIndexByPair.get(linkKey)].value += value;
                            return;
                        }}
                        linkIndexByPair.set(linkKey, links.length);
                        links.push({{ source, target, value }});
                    }}

                    baseData.nodes
                        .filter(node => node.level === 0 || node.level === 1)
                        .forEach(node => addNode(node));

                    const smallCategories = baseData.nodes.filter(node =>
                        node.level === 2 &&
                        node.name !== 'Savings' &&
                        typeof node.percent === 'number' &&
                        node.percent < labelThreshold
                    );
                    const smallCategoryNames = new Set(smallCategories.map(node => node.name));
                    const otherCategoriesValue = smallCategories.reduce((sum, node) => sum + getIncomingValue(incomingByTarget, node), 0);
                    const otherCategoriesPct = smallCategories.reduce((sum, node) => sum + (node.percent || 0), 0);

                    baseData.nodes
                        .filter(node => node.level === 2 && !smallCategoryNames.has(node.name))
                        .forEach(node => addNode(node));

                    if (otherCategoriesValue > 0) {{
                        addNode(createAggregatedNode(
                            'Other Categories',
                            makeDisplayName('Other Categories', otherCategoriesValue, otherCategoriesPct),
                            2,
                            otherCategoriesPct,
                            compactDefaultColor,
                            2,
                            9998,
                        ));
                    }}

                    const groupedSubcategoryValues = new Map();
                    const groupedSubcategoryPercents = new Map();

                    baseData.nodes
                        .filter(node => node.level === 3)
                        .forEach((node) => {{
                            const parentName = node.parentName;
                            if (!parentName || smallCategoryNames.has(parentName)) {{
                                return;
                            }}
                            const shouldGroup = typeof node.percent === 'number' && node.percent < labelThreshold;
                            if (!shouldGroup) {{
                                addNode(node);
                                return;
                            }}

                            const value = getIncomingValue(incomingByTarget, node);
                            const key = parentName;
                            groupedSubcategoryValues.set(key, (groupedSubcategoryValues.get(key) || 0) + value);
                            groupedSubcategoryPercents.set(key, (groupedSubcategoryPercents.get(key) || 0) + (node.percent || 0));
                        }});

                    groupedSubcategoryValues.forEach((value, parentName) => {{
                        const percent = groupedSubcategoryPercents.get(parentName) || null;
                        const parentNode = findBaseNodeByName(parentName);
                        addNode(createAggregatedNode(
                            `${{parentName}}::Other`,
                            makeDisplayName('Other', value, percent),
                            3,
                            percent,
                            parentNode?.color || compactDefaultColor,
                            3,
                            9999,
                            {{
                                parentPercent: parentNode?.percent ?? null,
                                parentName,
                            }}
                        ));
                    }});

                    baseData.links.forEach((link) => {{
                        const sourceNode = nodeByIndex.get(link.source);
                        const targetNode = nodeByIndex.get(link.target);
                        if (!sourceNode || !targetNode) {{
                            return;
                        }}

                        if (sourceNode.level === 0 && targetNode.level === 1) {{
                            addLink(sourceNode.name, targetNode.name, link.value);
                            return;
                        }}

                        if (sourceNode.level === 1 && targetNode.level === 2) {{
                            const targetName = smallCategoryNames.has(targetNode.name) ? 'Other Categories' : targetNode.name;
                            addLink(sourceNode.name, targetName, link.value);
                            return;
                        }}

                        if (sourceNode.level === 2 && targetNode.level === 3) {{
                            if (smallCategoryNames.has(sourceNode.name)) {{
                                return;
                            }}
                            const targetName = (typeof targetNode.percent === 'number' && targetNode.percent < labelThreshold)
                                ? `${{sourceNode.name}}::Other`
                                : targetNode.name;
                            addLink(sourceNode.name, targetName, link.value);
                        }}
                    }});

                    return {{ nodes, links }};
                }}

                function getDisplayData() {{
                    if (!compactMode) {{
                        return {{
                            nodes: baseData.nodes.map((node) => ({{ ...node }})),
                            links: baseData.links.map((link) => ({{ ...link }})),
                        }};
                    }}
                    return buildCompactData();
                }}

                function getExportStyleText() {{
                    return `
                        .node rect {{
                            stroke: #fff;
                            stroke-width: 2px;
                        }}
                        .link {{
                            fill: none;
                            stroke-opacity: 0.3;
                        }}
                        .node-label {{
                            font-size: 15px;
                            font-weight: 500;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        }}
                        .node-label-shell {{
                            display: inline-flex;
                            flex-direction: column;
                            gap: 2px;
                            max-width: 100%;
                            padding: 6px 10px;
                            border-radius: 12px;
                            background: rgba(255, 255, 255, 0.86);
                            border: 1px solid rgba(148, 163, 184, 0.18);
                            box-shadow:
                                0 6px 18px rgba(15, 23, 42, 0.06),
                                inset 0 1px 0 rgba(255, 255, 255, 0.82);
                        }}
                        .node-label-content {{
                            display: -webkit-box;
                            overflow: hidden;
                            -webkit-box-orient: vertical;
                            -webkit-line-clamp: 2;
                            white-space: normal;
                            word-break: break-word;
                        }}
                        .node-label-primary {{
                            font-size: 15px;
                            font-weight: 700;
                            color: #1e293b;
                            letter-spacing: -0.01em;
                        }}
                        .node-label-secondary {{
                            font-size: 12px;
                            font-weight: 600;
                            color: #64748b;
                            letter-spacing: 0.01em;
                        }}
                        .column-header {{
                            font-size: 15px;
                            font-weight: 700;
                            letter-spacing: 0.04em;
                            fill: #334155;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        }}
                        .column-header-chip {{
                            fill: rgba(255, 255, 255, 0.88);
                            stroke: rgba(148, 163, 184, 0.22);
                            stroke-width: 1;
                        }}
                        .column-header-rule {{
                            stroke: rgba(37, 99, 235, 0.14);
                            stroke-width: 2;
                            stroke-linecap: round;
                        }}
                    `;
                }}

                function cloneExportTextLayers(exportSvg, exportMainGroup, exportScaleX) {{
                    const svgNs = 'http://www.w3.org/2000/svg';
                    const exportHeaderLayer = document.createElementNS(svgNs, 'g');
                    exportHeaderLayer.setAttribute('class', 'export-column-headers');
                    const exportLabelLayer = document.createElementNS(svgNs, 'g');
                    exportLabelLayer.setAttribute('class', 'export-labels');

                    exportMainGroup.querySelectorAll('.nodes g').forEach((nodeGroup) => {{
                        const rect = nodeGroup.querySelector('rect');
                        const label = nodeGroup.querySelector('foreignObject');
                        if (!rect || !label) {{
                            return;
                        }}

                        const rectX = Number(rect.getAttribute('x') || 0);
                        const rectWidth = Number(rect.getAttribute('width') || 0);
                        const scaledRectX = rectX * exportScaleX;
                        const scaledRectWidth = rectWidth * exportScaleX;

                        const labelX = Number(label.getAttribute('x') || 0);
                        const labelY = Number(label.getAttribute('y') || 0);
                        const labelWidth = Number(label.getAttribute('width') || 0);
                        const labelHeight = Number(label.getAttribute('height') || 0);
                        const isRightSideLabel = labelX < rectX;
                        const newLabelX = isRightSideLabel
                            ? scaledRectX - labelWidth - 10
                            : scaledRectX + scaledRectWidth + 10;

                        const exportLabel = document.createElementNS(svgNs, 'foreignObject');
                        exportLabel.setAttribute('x', String(newLabelX));
                        exportLabel.setAttribute('y', String(labelY));
                        exportLabel.setAttribute('width', String(labelWidth));
                        exportLabel.setAttribute('height', String(labelHeight));
                        exportLabel.setAttribute('pointer-events', 'none');

                        if (label.firstElementChild) {{
                            exportLabel.appendChild(label.firstElementChild.cloneNode(true));
                        }}

                        exportLabelLayer.appendChild(exportLabel);
                        label.setAttribute('display', 'none');
                    }});

                    exportMainGroup.querySelectorAll('.column-headers g').forEach((headerGroup) => {{
                        const transform = headerGroup.getAttribute('transform') || '';
                        const match = transform.match(/translate\(([-0-9.]+),\s*([-0-9.]+)\)/);
                        if (!match) {{
                            return;
                        }}

                        const x = Number(match[1]);
                        const y = Number(match[2]);
                        const exportHeader = document.createElementNS(svgNs, 'g');
                        exportHeader.setAttribute('transform', `translate(${{x * exportScaleX}}, ${{y}})`);

                        headerGroup.childNodes.forEach((child) => {{
                            exportHeader.appendChild(child.cloneNode(true));
                        }});

                        exportHeaderLayer.appendChild(exportHeader);
                        headerGroup.setAttribute('display', 'none');
                    }});

                    exportSvg.appendChild(exportHeaderLayer);
                    exportSvg.appendChild(exportLabelLayer);
                }}

                function formatLabelHtml(rawLabel) {{
                    const parts = String(rawLabel || '').split(/<br\\s*\\/?>/i);
                    const primary = escapeHtml(parts[0] || '');
                    const secondaryRaw = parts.slice(1).join(' ').trim();
                    const secondary = secondaryRaw ? escapeHtml(secondaryRaw) : '';
                    return '<div class="node-label-shell"><div class="node-label-content"><div class="node-label-primary">' +
                        primary +
                        '</div>' +
                        (secondary ? '<div class="node-label-secondary">' + secondary + '</div>' : '') +
                        '</div></div>';
                }}

                function showTooltip(event, content) {{
                    const wrapperRect = chartWrapper.getBoundingClientRect();
                    tooltip.innerHTML = formatTooltipContent(content);
                    tooltip.classList.add('visible');

                    const tooltipWidth = tooltip.offsetWidth || 180;
                    const tooltipHeight = tooltip.offsetHeight || 48;
                    const left = Math.min(
                        wrapperRect.width - tooltipWidth - 16,
                        Math.max(16, event.clientX - wrapperRect.left + 12)
                    );
                    const top = Math.min(
                        wrapperRect.height - tooltipHeight - 16,
                        Math.max(16, event.clientY - wrapperRect.top - tooltipHeight - 10)
                    );

                    tooltip.style.left = `${{left}}px`;
                    tooltip.style.top = `${{top}}px`;
                }}

                function hideTooltip() {{
                    tooltip.classList.remove('visible');
                }}
                
                function resetView() {{
                    selectedNode = null;
                    selectedLink = null;
                    d3.selectAll('.link').classed("highlighted", false).classed("dimmed", false);
                    d3.selectAll('.node').classed("selected", false).classed("dimmed", false).classed("highlighted", false);
                    hideTooltip();
                    
                    // Reset zoom
                    d3.select("#chart")
                        .transition()
                        .duration(750)
                        .call(zoom.transform, d3.zoomIdentity);
                }}
                
                function exportPNG() {{
                    const svgElement = document.getElementById('chart');
                    const mainGroup = svgElement.querySelector('.main');
                    
                    // Get the bounding box of actual content
                    const bbox = mainGroup.getBBox();
                    const padding = 40;
                    const exportAspectWidth = Math.max((bbox.height + padding * 2) * 1.5, currentChartWidth);
                    const exportWidth = Math.max(exportAspectWidth, bbox.width + padding * 2);
                    const exportHeight = bbox.height + padding * 2;
                    const exportScaleX = exportWidth / currentChartWidth;
                    const exportY = bbox.y - padding;
                    
                    // Clone SVG and prepare for export
                    const exportSvg = svgElement.cloneNode(true);
                    const exportMainGroup = exportSvg.querySelector('.main');
                    
                    // Inline all CSS styles
                    const styleElement = document.createElement('style');
                    styleElement.textContent = getExportStyleText();
                    exportSvg.insertBefore(styleElement, exportSvg.firstChild);

                    if (exportMainGroup) {{
                        const existingTransform = exportMainGroup.getAttribute('transform') || '';
                        exportMainGroup.setAttribute('transform', `${{existingTransform}} scale(${{exportScaleX}}, 1)`.trim());

                        if (currentGraph) {{
                            exportMainGroup.querySelectorAll('.links path').forEach((path, index) => {{
                                const linkDatum = currentGraph.links[index];
                                if (!linkDatum) {{
                                    return;
                                }}
                                const exportStroke = linkDatum.target?.color || linkDatum.source?.color || '#999';
                                path.setAttribute('stroke', exportStroke);
                            }});
                        }}
                        cloneExportTextLayers(exportSvg, exportMainGroup, exportScaleX);

                        exportSvg.querySelectorAll('linearGradient').forEach((gradient) => {{
                            const x1 = Number(gradient.getAttribute('x1') || 0);
                            const x2 = Number(gradient.getAttribute('x2') || 0);
                            gradient.setAttribute('x1', String(x1 * exportScaleX));
                            gradient.setAttribute('x2', String(x2 * exportScaleX));
                        }});
                    }}
                    
                    // Set proper dimensions
                    exportSvg.setAttribute('width', exportWidth);
                    exportSvg.setAttribute('height', exportHeight);
                    exportSvg.setAttribute('viewBox', `0 ${{exportY}} ${{exportWidth}} ${{exportHeight}}`);
                    exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    exportSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
                    
                    const svgData = new XMLSerializer().serializeToString(exportSvg);
                    
                    // Create canvas
                    const canvas = document.createElement('canvas');
                    const scale = 2; // Higher resolution
                    canvas.width = exportWidth * scale;
                    canvas.height = exportHeight * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.scale(scale, scale);
                    
                    // Create image
                    const img = new Image();
                    img.onload = function() {{
                        // White background
                        ctx.fillStyle = 'white';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        
                        // Draw SVG
                        ctx.drawImage(img, 0, 0, exportWidth, exportHeight);
                        
                        // Download
                        canvas.toBlob(function(blob) {{
                            const link = document.createElement('a');
                            link.href = URL.createObjectURL(blob);
                            link.download = 'sankey-diagram-' + new Date().getTime() + '.png';
                            link.click();
                        }}, 'image/png');
                    }};
                    
                    img.onerror = function(e) {{
                        console.error('Error loading SVG:', e);
                        alert('Error exporting PNG. Please try using your browser\\'s screenshot feature instead.');
                    }};
                    
                    const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
                    img.src = URL.createObjectURL(svgBlob);
                }}
                
                function renderSankey() {{
                    d3.select("#chart").selectAll("*").remove();
                    
                    const data = getDisplayData();

                    // Assign colors to nodes without colors
                    const colorScale = d3.scaleOrdinal()
                        .domain(data.nodes.map((d, i) => d.category || i))
                        .range(colorPalette);
                    
                    data.nodes.forEach((node, i) => {{
                        if (!node.color) {{
                            node.color = colorScale(node.category || i);
                        }}
                        node.index = i;
                        node.column = node.column ?? 0;
                        node.sortOrder = node.sortOrder ?? i;
                        node.level = node.level ?? node.column ?? 0;
                    }});

                    const width = getResponsiveWidth();
                    currentChartWidth = width;
                    const nodePadding = baseNodePadding;
                    const labelWidth = 190;
                    const labelHeight = 58;
                    
                    const svg = d3.select("#chart")
                        .attr("width", width)
                        .attr("height", height)
                        .attr("viewBox", [0, 0, width, height])
                        .attr("preserveAspectRatio", "xMidYMid meet");
                    
                    const g = svg.append("g")
                        .attr("class", "main");
                    
                    // Add zoom behavior
                    zoom = d3.zoom()
                        .scaleExtent([0.5, 3])
                        .on("zoom", (event) => {{
                            currentTransform = event.transform;
                            g.attr("transform", event.transform);
                        }});
                    
                    svg.call(zoom);
                    
                    // Click on background to deselect
                    svg.on("click", function(event) {{
                        if (event.target === this) {{
                            selectedNode = null;
                            selectedLink = null;
                            link.classed("highlighted", false).classed("dimmed", false);
                            node.classed("selected", false).classed("dimmed", false).classed("highlighted", false);
                        }}
                    }});
                    
                    const defs = g.append("defs");
                    
                    const sankey = d3.sankey()
                        .nodeId(d => d.index)
                        .nodeWidth(40)
                        .nodePadding(nodePadding)
                        .nodeAlign((node, totalColumns) => {{
                            const explicitColumn = node.column;
                            if (Number.isFinite(explicitColumn)) {{
                                return Math.max(0, Math.min(totalColumns - 1, explicitColumn));
                            }}
                            return d3.sankeyJustify(node, totalColumns);
                        }})
                        .nodeSort((a, b) => {{
                            const columnDelta = (a.column || 0) - (b.column || 0);
                            if (columnDelta !== 0) {{
                                return columnDelta;
                            }}
                            return (a.sortOrder || 0) - (b.sortOrder || 0);
                        }})
                        .linkSort((a, b) => {{
                            const sourceOrderDelta = (a.source.sortOrder || 0) - (b.source.sortOrder || 0);
                            if (sourceOrderDelta !== 0) {{
                                return sourceOrderDelta;
                            }}
                            return (a.target.sortOrder || 0) - (b.target.sortOrder || 0);
                        }})
                        .iterations(50)
                        .extent([[50, 50], [width - 50, height - 50]]);
                    
                    const graph = sankey(data);
                    currentGraph = graph;

                    const columnTitles = {{
                        0: "Income Sources",
                        1: "Income",
                        2: "Categories",
                        3: "Subcategories",
                    }};
                    const columns = [...new Set(graph.nodes.map(n => n.column))].sort((a, b) => a - b);
                    const headerData = columns.map(column => {{
                        const nodesInColumn = graph.nodes.filter(node => node.column === column);
                        if (!nodesInColumn.length) {{
                            return null;
                        }}
                        return {{
                            column,
                            title: columnTitles[column] || `Column ${{column + 1}}`,
                            x: d3.mean(nodesInColumn, node => (node.x0 + node.x1) / 2),
                        }};
                    }}).filter(Boolean);

                    const headerGroup = g.append("g")
                        .attr("class", "column-headers");

                    const headerEnter = headerGroup.selectAll("g")
                        .data(headerData)
                        .join("g")
                        .attr("transform", d => `translate(${{d.x}}, 24)`);

                    headerEnter.append("line")
                        .attr("class", "column-header-rule")
                        .attr("y1", -18)
                        .attr("y2", -18);

                    headerEnter.append("rect")
                        .attr("class", "column-header-chip")
                        .attr("y", -12)
                        .attr("height", 24)
                        .attr("rx", 12)
                        .attr("ry", 12);

                    headerEnter.append("text")
                        .attr("class", "column-header")
                        .attr("text-anchor", "middle")
                        .attr("dominant-baseline", "middle")
                        .text(d => d.title);

                    headerEnter.each(function() {{
                        const headerNode = d3.select(this);
                        const textNode = headerNode.select("text").node();
                        const textWidth = textNode ? textNode.getComputedTextLength() : 72;
                        const chipWidth = Math.max(88, Math.ceil(textWidth + 28));
                        const halfChipWidth = chipWidth / 2;

                        headerNode.select("rect")
                            .attr("x", -halfChipWidth)
                            .attr("width", chipWidth);

                        headerNode.select("line")
                            .attr("x1", -(halfChipWidth - 10))
                            .attr("x2", halfChipWidth - 10);
                    }});
                    
                    // Create links
                    const link = g.append("g")
                        .attr("class", "links")
                        .selectAll("path")
                        .data(graph.links)
                        .join("path")
                        .attr("class", "link")
                        .attr("d", d3.sankeyLinkHorizontal())
                        .attr("stroke", d => {{
                            const gradientId = 'gradient-' + d.source.index + '-' + d.target.index;
                            const gradient = defs.append("linearGradient")
                                .attr("id", gradientId)
                                .attr("gradientUnits", "userSpaceOnUse")
                                .attr("x1", d.source.x1)
                                .attr("x2", d.target.x0);
                            
                            gradient.append("stop")
                                .attr("offset", "0%")
                                .attr("stop-color", d.source.color || '#999');
                            
                            gradient.append("stop")
                                .attr("offset", "100%")
                                .attr("stop-color", d.target.color || '#999');
                            
                            return 'url(#' + gradientId + ')';
                        }})
                        .attr("stroke-width", d => Math.max(2, d.width))
                        .style("animation-delay", (d, i) => (i * 0.02) + "s")
                        .on("mousemove", function(event, d) {{
                            showTooltip(
                                event,
                                d.source.name + " -> " + d.target.name + "<br>$" +
                                d.value.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})
                            );
                        }})
                        .on("mouseleave", hideTooltip)
                        .on("click", function(event, d) {{
                            event.stopPropagation();
                            
                            link.classed("highlighted", false);
                            node.classed("selected", false).classed("highlighted", false);
                            
                            if (selectedLink === d) {{
                                selectedLink = null;
                                link.classed("dimmed", false);
                                node.classed("dimmed", false);
                            }} else {{
                                selectedLink = d;
                                selectedNode = null;
                                
                                // Highlight the clicked link
                                d3.select(this).classed("highlighted", true);
                                
                                // Find all downstream nodes and links
                                const connectedNodes = new Set();
                                const connectedLinks = new Set();
                                connectedLinks.add(d);
                                connectedNodes.add(d.source);
                                connectedNodes.add(d.target);
                                
                                // Traverse downstream from target
                                function traverseDownstream(node) {{
                                    graph.links.forEach(l => {{
                                        if (l.source === node) {{
                                            connectedLinks.add(l);
                                            connectedNodes.add(l.target);
                                            traverseDownstream(l.target);
                                        }}
                                    }});
                                }}
                                
                                traverseDownstream(d.target);
                                
                                // Highlight all connected links and nodes
                                link.classed("dimmed", l => !connectedLinks.has(l));
                                link.filter(l => connectedLinks.has(l) && l !== d)
                                    .classed("highlighted", true);
                                node.classed("dimmed", n => !connectedNodes.has(n));
                                node.filter(n => connectedNodes.has(n))
                                    .classed("highlighted", true);
                            }}
                        }});
                    
                    // Create nodes
                    const node = g.append("g")
                        .attr("class", "nodes")
                        .selectAll("g")
                        .data(graph.nodes)
                        .join("g")
                        .attr("class", "node")
                        .style("animation-delay", (d, i) => (i * 0.05) + "s");
                    
                    node.append("rect")
                        .attr("x", d => d.x0)
                        .attr("y", d => d.y0)
                        .attr("height", d => d.y1 - d.y0)
                        .attr("width", d => d.x1 - d.x0)
                        .attr("fill", d => d.color || '#69b3a2')
                        .attr("role", "button")
                        .attr("tabindex", 0)
                        .attr("aria-label", d => d.name)
                        .on("mousemove", function(event, d) {{
                            showTooltip(event, d.displayName || d.name);
                        }})
                        .on("mouseleave", hideTooltip)
                        .on("click", function(event, d) {{
                            event.stopPropagation();
                            
                            link.classed("highlighted", false).classed("dimmed", false);
                            node.classed("selected", false).classed("dimmed", false).classed("highlighted", false);
                            
                            if (selectedNode === d) {{
                                selectedNode = null;
                            }} else {{
                                selectedNode = d;
                                selectedLink = null;
                                d3.select(this.parentNode).classed("selected", true).classed("highlighted", true);
                                
                                link.classed("dimmed", true);
                                link.filter(l => l.source === d || l.target === d)
                                    .classed("dimmed", false)
                                    .classed("highlighted", true);
                                
                                const connectedNodes = new Set();
                                connectedNodes.add(d);
                                graph.links.forEach(l => {{
                                    if (l.source === d || l.target === d) {{
                                        connectedNodes.add(l.source);
                                        connectedNodes.add(l.target);
                                    }}
                                }});
                                node.classed("dimmed", n => !connectedNodes.has(n));
                                node.filter(n => connectedNodes.has(n))
                                    .classed("highlighted", true);
                            }}
                        }});
                    
                    node.append("foreignObject")
                        .attr("x", d => d.x0 < width / 2 ? d.x1 + 10 : d.x0 - labelWidth - 10)
                        .attr("y", d => (d.y1 + d.y0) / 2 - (labelHeight / 2))
                        .attr("width", labelWidth)
                        .attr("height", labelHeight)
                        .attr("pointer-events", "none")
                        .append("xhtml:div")
                        .attr("class", "node-label")
                        .style("text-align", d => d.x0 < width / 2 ? "left" : "right")
                        .html(d => formatLabelHtml(getRenderedLabel(d)));
                }}
                
                // Render the diagram
                renderSankey();

                thresholdInput.addEventListener('input', (event) => {{
                    labelThreshold = Number(event.target.value);
                    thresholdValue.textContent = labelThreshold + '%';
                    renderSankey();
                }});

                compactModeToggle.addEventListener('change', (event) => {{
                    compactMode = event.target.checked;
                    renderSankey();
                }});
                
                // Handle window resize
                let resizeTimer;
                window.addEventListener('resize', () => {{
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(() => {{
                        renderSankey();
                    }}, 500);
                }});
            </script>
        </body>
        </html>
        """
    
    st.iframe(f"data:text/html;charset=utf-8,{quote(html_content)}", height=iframe_height)
