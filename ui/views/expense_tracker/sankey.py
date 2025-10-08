"""Sankey diagram tab for expense tracker.

Visualizes cash flow from total expenses through categories to subcategories.
"""

import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from constants import ColumnNames
from data.calculations import calculate_expense_summary
from ui.views.expense_tracker.overview import _render_summary_metrics

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


def render_sankey_tab(df, budgets, num_months):
    """
    Render the cash flow Sankey diagram tab.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
        
    Returns:
        None
    """
    st.subheader("Sankey Chart")
    
    if df.empty:
        st.info("No transaction data available for the selected period.")
        return
    
    summary = calculate_expense_summary(df, budgets, num_months)
    _render_summary_metrics(summary)

    # Generate Sankey data
    try:
        sankey_data = _generate_sankey_data(df)
        _render_sankey_diagram(sankey_data)
    except Exception as e:
        st.error(f"Error generating cash flow diagram: {str(e)}")
        return


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
    import json
    
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
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    border-radius: 16px;
                    padding: 32px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
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
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}
                .subtitle {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 12px;
                }}
                .controls {{
                    display: flex;
                    gap: 12px;
                    flex-wrap: wrap;
                    align-items: center;
                }}

                .btn {{
                    padding: 10px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }}
                .btn:active {{
                    transform: translateY(0);
                }}
                .btn-secondary {{
                    background: white;
                    color: #667eea;
                    border: 2px solid #667eea;
                }}
                .btn-secondary:hover {{
                    background: #f9fafb;
                }}
                #chart {{ 
                    background: white;
                    width: 100%;
                    height: auto;
                    border-radius: 8px;
                }}
                .chart-wrapper {{
                    position: relative;
                    overflow: hidden;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
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
                    filter: blur(3px);
                }}
                .node-label {{
                    font-size: 13px;
                    font-weight: 500;
                    pointer-events: none;
                    line-height: 1.4;
                    transition: font-weight 0.2s ease;
                }}
                .node.highlighted .node-label {{
                    font-weight: 700;
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
                        <button class="btn" onclick="resetView()">Reset View</button>
                        <button class="btn btn-secondary" onclick="exportPNG()">Save as PNG</button>
                    </div>
                </div>
                
                <div class="chart-wrapper">
                    <svg id="chart"></svg>
                </div>
            </div>
            
            <script>
                const data = {json.dumps(data)};
                
                // Color scheme
                const colorPalette = [
                    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
                    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
                    '#06b6d4', '#84cc16', '#f43f5e', '#6366f1'
                ];
                
                let selectedNode = null;
                let selectedLink = null;
                let currentTransform = d3.zoomIdentity;
                
                function getResponsiveWidth() {{
                    const containerWidth = document.querySelector('.container').clientWidth - 64;
                    const minWidth = 900;
                    const maxWidth = 1600;
                    return Math.min(maxWidth, Math.max(minWidth, containerWidth));
                }}
                
                const width = getResponsiveWidth();
                const height = 1000;
                
                function resetView() {{
                    selectedNode = null;
                    selectedLink = null;
                    d3.selectAll('.link').classed("highlighted", false).classed("dimmed", false);
                    d3.selectAll('.node').classed("selected", false).classed("dimmed", false).classed("highlighted", false);
                    
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
                    
                    // Clone SVG and prepare for export
                    const exportSvg = svgElement.cloneNode(true);
                    
                    // Inline all CSS styles
                    const styleElement = document.createElement('style');
                    styleElement.textContent = `
                        .node rect {{
                            stroke: #fff;
                            stroke-width: 2px;
                        }}
                        .link {{
                            fill: none;
                            stroke-opacity: 0.3;
                        }}
                        .node-label {{
                            font-size: 13px;
                            font-weight: 500;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        }}
                    `;
                    exportSvg.insertBefore(styleElement, exportSvg.firstChild);
                    
                    // Set proper dimensions
                    exportSvg.setAttribute('width', bbox.width + padding * 2);
                    exportSvg.setAttribute('height', bbox.height + padding * 2);
                    exportSvg.setAttribute('viewBox', `${{bbox.x - padding}} ${{bbox.y - padding}} ${{bbox.width + padding * 2}} ${{bbox.height + padding * 2}}`);
                    exportSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    exportSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
                    
                    const svgData = new XMLSerializer().serializeToString(exportSvg);
                    
                    // Create canvas
                    const canvas = document.createElement('canvas');
                    const scale = 2; // Higher resolution
                    canvas.width = (bbox.width + padding * 2) * scale;
                    canvas.height = (bbox.height + padding * 2) * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.scale(scale, scale);
                    
                    // Create image
                    const img = new Image();
                    img.onload = function() {{
                        // White background
                        ctx.fillStyle = 'white';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        
                        // Draw SVG
                        ctx.drawImage(img, 0, 0, bbox.width + padding * 2, bbox.height + padding * 2);
                        
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
                    
                    // Assign colors to nodes without colors
                    const colorScale = d3.scaleOrdinal()
                        .domain(data.nodes.map((d, i) => d.category || i))
                        .range(colorPalette);
                    
                    data.nodes.forEach((node, i) => {{
                        if (!node.color) {{
                            node.color = colorScale(node.category || i);
                        }}
                        node.index = i;
                    }});
                    
                    const svg = d3.select("#chart")
                        .attr("width", width)
                        .attr("height", height)
                        .attr("viewBox", [0, 0, width, height])
                        .attr("preserveAspectRatio", "xMidYMid meet");
                    
                    const g = svg.append("g")
                        .attr("class", "main");
                    
                    // Add zoom behavior
                    const zoom = d3.zoom()
                        .scaleExtent([0.5, 3])
                        .on("zoom", (event) => {{
                            currentTransform = event.transform;
                            g.attr("transform", event.transform);
                        }});
                    
                    svg.call(zoom);
                    window.zoom = zoom; // Make zoom accessible globally
                    
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
                        .nodePadding(50)
                        .nodeAlign(d3.sankeyJustify)
                        .nodeSort((a, b) => a.y0 - b.y0)
                        .linkSort((a, b) => a.source.y0 - b.source.y0)
                        .iterations(50)
                        .extent([[50, 50], [width - 50, height - 50]]);
                    
                    const graph = sankey(data);
                    
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
                        .attr("x", d => d.x0 < width / 2 ? d.x1 + 10 : d.x0 - 210)
                        .attr("y", d => (d.y1 + d.y0) / 2 - 15)
                        .attr("width", 200)
                        .attr("height", 50)
                        .attr("pointer-events", "none")
                        .append("xhtml:div")
                        .attr("class", "node-label")
                        .style("text-align", d => d.x0 < width / 2 ? "left" : "right")
                        .html(d => '<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">' + (d.displayName || d.name) + '</div>');
                }}
                
                // Render the diagram
                renderSankey();
                
                // Handle window resize
                let resizeTimer;
                window.addEventListener('resize', () => {{
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(() => {{
                        location.reload();
                    }}, 500);
                }});
            </script>
        </body>
        </html>
        """
    
    # Assuming you're using Streamlit
    try:
        import streamlit.components.v1 as components
        components.html(html_content, height=1400, scrolling=True)
    except ImportError:
        # If not using Streamlit, save to file or display differently
        with open('sankey_diagram.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Sankey diagram saved to sankey_diagram.html")