"""Sankey diagram tab for expense tracker.

Visualizes cash flow from total expenses through categories to subcategories.
"""

import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from constants import ColumnNames


# Color scheme for categories
CATEGORY_COLORS = {
    'Total': '#3b82f6',
    'Housing': '#ef4444',
    'Utilities': '#f59e0b',
    'Food & Dining': '#10b981',
    'Entertainment': '#8b5cf6',
    'Transportation': '#ec4899',
    'Miscellaneous': '#6b7280',
}

DEFAULT_COLOR = '#94a3b8'


def render_sankey_tab(df):
    """
    Render the cash flow Sankey diagram tab.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
        
    Returns:
        None
    """
    st.subheader("Cash Flow")
    
    if df.empty:
        st.info("No transaction data available for the selected period.")
        return
    
    # Generate Sankey data
    try:
        sankey_data = _generate_sankey_data(df)
        _render_sankey_diagram(sankey_data)
    except Exception as e:
        st.error(f"Error generating cash flow diagram: {str(e)}")
        return
    
    st.divider()
    
    # Display summary metrics
    _render_sankey_summary(df)


def _generate_sankey_data(df):
    """
    Generate nodes and links for a Sankey diagram showing income and expenses.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    
    Returns:
        dict: Sankey data with 'nodes' and 'links' keys.
    """
    nodes = []
    links = []
    node_map = {}
    node_idx = 0

    # Separate income and expenses
    income_df = df[df[ColumnNames.CATEGORY] == 'Income']
    expense_df = df[df[ColumnNames.CATEGORY] != 'Income']

    total_income = income_df[ColumnNames.AMOUNT].sum()
    total_expenses = abs(expense_df[ColumnNames.AMOUNT].sum())

    # === Income Sources ===
    income_sources = {}
    for category in income_df[ColumnNames.CATEGORY].unique():
        cat_df = income_df[income_df[ColumnNames.CATEGORY] == category]
        if (cat_df[ColumnNames.SUBCATEGORY].notna() & (cat_df[ColumnNames.SUBCATEGORY] != '')).any():
            sub_totals = (
                cat_df[cat_df[ColumnNames.SUBCATEGORY].notna() & (cat_df[ColumnNames.SUBCATEGORY] != '')]
                .groupby(ColumnNames.SUBCATEGORY)[ColumnNames.AMOUNT]
                .sum()
            )
            for sub, amount in sub_totals.items():
                source_name = f"{category} - {sub}"
                income_sources[source_name] = amount
        else:
            income_sources[category] = cat_df[ColumnNames.AMOUNT].sum()

    # Add income source nodes
    for name, amount in sorted(income_sources.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / total_income * 100) if total_income > 0 else 0
        nodes.append({
            "name": name,
            "displayName": f"{name}<br/>${amount:,.2f} ({pct:.1f}%)",
            "color": CATEGORY_COLORS.get('Total', '#3b82f6')
        })
        node_map[name] = node_idx
        node_idx += 1

    # Total Income node
    total_income_idx = node_idx
    nodes.append({
        "name": "Total Income",
        "displayName": f"Total Income<br/>${total_income:,.2f}",
        "color": CATEGORY_COLORS['Total']
    })
    node_map['Total Income'] = node_idx
    node_idx += 1

    # Links: Income sources → Total Income
    for name, amount in income_sources.items():
        links.append({
            "source": node_map[name],
            "target": total_income_idx,
            "value": float(amount)
        })

    # === Expenses by Category ===
    category_totals = (
        expense_df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .apply(lambda x: abs(x.sum()))
        .sort_values(ascending=False)
    )

    for category, amount in category_totals.items():
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
        nodes.append({
            "name": category,
            "displayName": f"{category}<br/>${amount:,.2f} ({pct:.1f}%)",
            "color": CATEGORY_COLORS.get(category, DEFAULT_COLOR)
        })
        node_map[category] = node_idx
        links.append({
            "source": total_income_idx,
            "target": node_idx,
            "value": float(amount)
        })
        node_idx += 1

    # === Subcategories (as end nodes) ===
    for category in category_totals.index:
        node_idx = _add_subcategory_nodes(
            expense_df,
            category,
            category_totals[category],
            node_map,
            nodes,
            links,
            node_idx
        )

    # === Savings (Remaining) as End Node ===
    remaining = total_income - total_expenses
    if remaining > 0:
        pct = (remaining / total_income * 100)
        nodes.append({
            "name": "Savings",
            "displayName": f"Savings<br/>${remaining:,.2f} ({pct:.1f}%)",
            "color": CATEGORY_COLORS.get('Savings', 'blue')
        })
        links.append({
            "source": total_income_idx,
            "target": node_idx,
            "value": float(remaining)
        })
        node_idx += 1

    return {"nodes": nodes, "links": links}




def _add_subcategory_nodes(df, category, category_total, node_map, nodes, links, node_idx):
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
        .apply(lambda x: abs(x.sum()))
        .sort_values(ascending=False)
    )
    
    for subcategory, amount in subcategory_totals.items():
        pct = (amount / category_total * 100) if category_total > 0 else 0
        
        nodes.append({
            "name": subcategory,
            "displayName": f"{subcategory}<br/>${amount:,.2f} ({pct:.1f}%)",
            "color": CATEGORY_COLORS.get(category, DEFAULT_COLOR)
        })
        
        links.append({
            "source": node_map[category],
            "target": node_idx,
            "value": float(amount)
        })
        node_idx += 1
    
    return node_idx

def _render_sankey_diagram(data):
    """
    Render an enhanced D3.js-based Sankey diagram with improved interactivity and styling.
    
    Args:
        data (dict): Sankey data containing nodes and links
    """
    html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
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
                    background: #fafafa;
                }}
                .container {{
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }}
                #chart {{ 
                    background: white;
                    width: 100%;
                    height: auto;
                }}
                .node rect {{
                    stroke: #fff;
                    stroke-width: 2px;
                    cursor: pointer;
                    transition: opacity 0.2s ease, stroke-width 0.2s ease;
                }}
                .node rect:hover {{ 
                    opacity: 0.85;
                }}
                .node.selected rect {{
                    stroke-width: 4px;
                    stroke: #333;
                }}
                .node.dimmed {{
                    filter: blur(1.5px);
                }}
                .node.dimmed rect {{
                    opacity: 0.3;
                }}
                .node.dimmed foreignObject {{
                    filter: blur(1.5px);
                    opacity: 0.3;
                }}
                .link {{
                    fill: none;
                    stroke-opacity: 0.3;
                    transition: stroke-opacity 0.2s ease, stroke-width 0.2s ease, filter 0.2s ease;
                    mix-blend-mode: multiply;
                    cursor: pointer;
                }}
                .link:hover {{ 
                    stroke-opacity: 0.5;
                }}
                .link.highlighted {{
                    stroke-opacity: 0.85;
                    mix-blend-mode: normal;
                }}
                .link.dimmed {{
                    stroke-opacity: 0.15;
                    filter: blur(2px);
                }}
                .node-label {{
                    font-size: 13px;
                    font-weight: 500;
                    pointer-events: none;
                    line-height: 1.4;
                }}
                .node-value {{
                    font-size: 11px;
                    color: #666;
                    font-weight: 400;
                }}
                .title {{
                    font-size: 26px;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #1a1a1a;
                }}
                .subtitle {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 24px;
                }}
                .tooltip {{
                    position: absolute;
                    padding: 12px 16px;
                    background: rgba(0, 0, 0, 0.9);
                    color: white;
                    border-radius: 6px;
                    font-size: 13px;
                    pointer-events: none;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                    z-index: 1000;
                    max-width: 280px;
                    line-height: 1.5;
                }}
                .tooltip.visible {{
                    opacity: 1;
                }}
                .tooltip-header {{
                    font-weight: 600;
                    margin-bottom: 6px;
                    font-size: 14px;
                }}
                .tooltip-row {{
                    display: flex;
                    justify-content: space-between;
                    margin: 4px 0;
                }}
                .tooltip-label {{
                    color: #ccc;
                }}
                .tooltip-value {{
                    font-weight: 500;
                    margin-left: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">Cash Flow Visualization</div>
                <div class="subtitle">Click on nodes or links to highlight connections • Click background to deselect</div>
                <svg id="chart"></svg>
                <div class="tooltip" id="tooltip"></div>
            </div>
            <script>
                const data = {json.dumps(data)};
                
                const containerWidth = document.querySelector('.container').clientWidth - 48;
                const width = Math.max(1200, containerWidth);
                const height = 900;
                
                const tooltip = d3.select("#tooltip");
                
                function formatCurrency(value) {{
                    return '$' + value.toLocaleString('en-US', {{ 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                    }});
                }}
                
                function showTooltip(content, event) {{
                    tooltip
                        .html(content)
                        .classed("visible", true)
                        .style("left", (event.pageX + 15) + "px")
                        .style("top", (event.pageY - 15) + "px");
                }}
                
                function hideTooltip() {{
                    tooltip.classed("visible", false);
                }}
                
                function renderSankey() {{
                    d3.select("#chart").selectAll("*").remove();
                    
                    const svg = d3.select("#chart")
                        .attr("width", width)
                        .attr("height", height)
                        .attr("viewBox", [0, 0, width, height])
                        .attr("preserveAspectRatio", "xMidYMid meet")
                        .on("click", function() {{
                            selectedNode = null;
                            selectedLink = null;
                            link.classed("highlighted", false).classed("dimmed", false);
                            node.classed("selected", false).classed("dimmed", false);
                            hideTooltip();
                        }});
                    
                    const defs = svg.append("defs");
                    
                    const sankey = d3.sankey()
                        .nodeId(d => d.index)
                        .nodeWidth(40)
                        .nodePadding(50)
                        .nodeAlign(d3.sankeyJustify)
                        .nodeSort((a, b) => a.y0 - b.y0)
                        .linkSort((a, b) => a.source.y0 - b.source.y0)
                        .iterations(50)
                        .extent([[50, 50], [width - 50, height - 50]]);
                    
                    data.nodes.forEach((node, i) => node.index = i);
                    
                    const graph = sankey(data);
                    
                    let selectedNode = null;
                    let selectedLink = null;
                    
                    const totalFlow = d3.sum(graph.links, d => d.value);
                    
                    function formatPercent(value) {{
                        return ((value / totalFlow) * 100).toFixed(1) + '%';
                    }}
                    
                    const link = svg.append("g")
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
                        .on("click", function(event, d) {{
                            event.stopPropagation();
                            
                            link.classed("highlighted", false);
                            node.classed("selected", false);
                            
                            if (selectedLink === d) {{
                                selectedLink = null;
                                link.classed("dimmed", false);
                                node.classed("dimmed", false);
                            }} else {{
                                selectedLink = d;
                                selectedNode = null;
                                d3.select(this).classed("highlighted", true);
                                link.filter(l => l !== d).classed("dimmed", true);
                                node.classed("dimmed", n => n !== d.source && n !== d.target);
                            }}
                        }})
                        .on("mouseover", function(event, d) {{
                            if (!selectedLink && !selectedNode) {{
                                const tooltipContent = 
                                    '<div class="tooltip-header">' + d.source.name + ' → ' + d.target.name + '</div>' +
                                    '<div class="tooltip-row">' +
                                        '<span class="tooltip-label">Amount:</span>' +
                                        '<span class="tooltip-value">' + formatCurrency(d.value) + '</span>' +
                                    '</div>' +
                                    '<div class="tooltip-row">' +
                                        '<span class="tooltip-label">Percentage:</span>' +
                                        '<span class="tooltip-value">' + formatPercent(d.value) + '</span>' +
                                    '</div>';
                                showTooltip(tooltipContent, event);
                            }}
                        }})
                        .on("mousemove", function(event) {{
                            if (!selectedLink && !selectedNode) {{
                                tooltip
                                    .style("left", (event.pageX + 15) + "px")
                                    .style("top", (event.pageY - 15) + "px");
                            }}
                        }})
                        .on("mouseout", function() {{
                            if (!selectedLink && !selectedNode) {{
                                hideTooltip();
                            }}
                        }});
                    
                    const node = svg.append("g")
                        .attr("class", "nodes")
                        .selectAll("g")
                        .data(graph.nodes)
                        .join("g")
                        .attr("class", "node");
                    
                    node.append("rect")
                        .attr("x", d => d.x0)
                        .attr("y", d => d.y0)
                        .attr("height", d => d.y1 - d.y0)
                        .attr("width", d => d.x1 - d.x0)
                        .attr("fill", d => d.color || '#69b3a2')
                        .on("click", function(event, d) {{
                            event.stopPropagation();
                            
                            link.classed("highlighted", false).classed("dimmed", false);
                            node.classed("selected", false).classed("dimmed", false);
                            
                            if (selectedNode === d) {{
                                selectedNode = null;
                                link.classed("dimmed", false);
                                node.classed("dimmed", false);
                            }} else {{
                                selectedNode = d;
                                selectedLink = null;
                                d3.select(this.parentNode).classed("selected", true);
                                
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
                            }}
                        }})
                        .on("mouseover", function(event, d) {{
                            if (!selectedNode && !selectedLink) {{
                                const nodeValue = d3.sum(graph.links.filter(l => 
                                    l.source === d || l.target === d
                                ), l => l.value);
                                
                                const tooltipContent = 
                                    '<div class="tooltip-header">' + d.name + '</div>' +
                                    '<div class="tooltip-row">' +
                                        '<span class="tooltip-label">Total Flow:</span>' +
                                        '<span class="tooltip-value">' + formatCurrency(nodeValue) + '</span>' +
                                    '</div>' +
                                    '<div class="tooltip-row">' +
                                        '<span class="tooltip-label">Percentage:</span>' +
                                        '<span class="tooltip-value">' + formatPercent(nodeValue) + '</span>' +
                                    '</div>';
                                showTooltip(tooltipContent, event);
                            }}
                        }})
                        .on("mousemove", function(event) {{
                            if (!selectedNode && !selectedLink) {{
                                tooltip
                                    .style("left", (event.pageX + 15) + "px")
                                    .style("top", (event.pageY - 15) + "px");
                            }}
                        }})
                        .on("mouseout", function() {{
                            if (!selectedNode && !selectedLink) {{
                                hideTooltip();
                            }}
                        }});
                    
                    node.append("foreignObject")
                        .attr("x", d => d.x0 < width / 2 ? d.x1 + 10 : d.x0 - 210)
                        .attr("y", d => (d.y1 + d.y0) / 2 - 25)
                        .attr("width", 200)
                        .attr("height", 80)
                        .append("xhtml:div")
                        .attr("class", "node-label")
                        .style("text-align", d => d.x0 < width / 2 ? "left" : "right")
                        .html(d => {{
                            const nodeValue = d3.sum(graph.links.filter(l => 
                                l.source === d || l.target === d
                            ), l => l.value);
                            return '<div>' + (d.displayName || d.name) + '</div>' +
                                '<div class="node-value">' + formatCurrency(nodeValue) + '</div>';
                        }});
                }}
                
                renderSankey();
            </script>
        </body>
        </html>
        """
    
    components.html(html_content, height=1000, scrolling=True)


def _render_sankey_summary(df):
    """
    Display summary metrics for the Sankey diagram.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    col1, col2, col3, col4 = st.columns(4)
    
    total_expenses = abs(df[ColumnNames.AMOUNT].sum())
    
    with col1:
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
    
    with col2:
        num_categories = df[ColumnNames.CATEGORY].nunique()
        st.metric("Categories", num_categories)
    
    with col3:
        if not df.empty:
            category_totals = (
                df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
                .apply(lambda x: abs(x.sum()))
                .sort_values(ascending=False)
            )
            
            if not category_totals.empty:
                largest_category = category_totals.index[0]
                largest_amount = category_totals.iloc[0]
                st.metric("Largest category", largest_category)
                st.caption(f"${largest_amount:,.2f}")
    
    with col4:
        avg_transaction = abs(df[ColumnNames.AMOUNT].mean())
        st.metric("Avg Transaction", f"${avg_transaction:,.2f}")