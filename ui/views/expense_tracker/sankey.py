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
    Generate nodes and links data for Sankey diagram.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
        
    Returns:
        dict: Dictionary containing 'nodes' and 'links' lists
    """
    nodes = []
    links = []
    node_map = {}
    
    # Calculate total expenses (use absolute value)
    total_expenses = abs(df[ColumnNames.AMOUNT].sum())
    
    # Add total node
    nodes.append({
        "name": "Total Expenses",
        "displayName": f"Total Expenses<br/>${total_expenses:,.2f}",
        "color": CATEGORY_COLORS['Total']
    })
    node_map['Total'] = 0
    node_idx = 1
    
    # Group by category
    category_totals = (
        df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .apply(lambda x: abs(x.sum()))
        .sort_values(ascending=False)
    )
    
    # Add category nodes and links
    for category, amount in category_totals.items():
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
        
        nodes.append({
            "name": category,
            "displayName": f"{category}<br/>${amount:,.2f} ({pct:.1f}%)",
            "color": CATEGORY_COLORS.get(category, DEFAULT_COLOR)
        })
        node_map[category] = node_idx
        
        links.append({
            "source": 0,
            "target": node_idx,
            "value": float(amount)
        })
        node_idx += 1
    
    # Add subcategory nodes
    for category in category_totals.index:
        node_idx = _add_subcategory_nodes(
            df, 
            category, 
            category_totals[category],
            node_map,
            nodes,
            links,
            node_idx
        )
    
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
    Render the D3.js-based Sankey diagram.
    
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
            body {{
                margin: 0;
                padding: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: white;
            }}
            #chart {{ background: white; }}
            .node rect {{
                stroke: #fff;
                stroke-width: 2px;
                cursor: pointer;
            }}
            .node rect:hover {{ opacity: 0.8; }}
            .link {{
                fill: none;
                stroke-opacity: 0.4;
            }}
            .link:hover {{ stroke-opacity: 0.7; }}
            .node-label {{
                font-size: 14px;
                font-weight: 500;
                pointer-events: none;
            }}
            .title {{
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="title">Cash Flow Visualization</div>
        <svg id="chart"></svg>
        <script>
            const data = {json.dumps(data)};
            
            const width = 1400;
            const height = 800;
            
            const svg = d3.select("#chart")
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", [0, 0, width, height]);
            
            const sankey = d3.sankey()
                .nodeId(d => d.index)
                .nodeWidth(35)
                .nodePadding(25)
                .extent([[1, 1], [width - 1, height - 6]]);
            
            data.nodes.forEach((node, i) => node.index = i);
            
            const graph = sankey(data);
            
            // Add links
            const link = svg.append("g")
                .attr("class", "links")
                .selectAll("path")
                .data(graph.links)
                .join("path")
                .attr("class", "link")
                .attr("d", d3.sankeyLinkHorizontal())
                .attr("stroke", d => d.source.color)
                .attr("stroke-width", d => Math.max(1, d.width))
                .style("stroke-opacity", 0.4);
            
            link.append("title")
                .text(d => d.source.name + ' → ' + d.target.name + '\\n$' + 
                      d.value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}));
            
            // Add nodes
            const node = svg.append("g")
                .attr("class", "nodes")
                .selectAll("g")
                .data(graph.nodes)
                .join("g");
            
            node.append("rect")
                .attr("x", d => d.x0)
                .attr("y", d => d.y0)
                .attr("height", d => d.y1 - d.y0)
                .attr("width", d => d.x1 - d.x0)
                .attr("fill", d => d.color);
            
            node.append("title")
                .text(d => d.displayName.replace(/<br\\/>/g, '\\n'));
            
            // Add labels
            node.append("foreignObject")
                .attr("x", d => d.x0 < width / 2 ? d.x1 + 8 : d.x0 - 8)
                .attr("y", d => (d.y1 + d.y0) / 2 - 30)
                .attr("width", 200)
                .attr("height", 60)
                .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
                .append("xhtml:div")
                .attr("class", "node-label")
                .style("text-align", d => d.x0 < width / 2 ? "left" : "right")
                .html(d => d.displayName);
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=900, scrolling=False)


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