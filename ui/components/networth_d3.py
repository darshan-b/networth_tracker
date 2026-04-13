"""Reusable D3 chart assets for product-style net worth views."""

import json
from typing import Any
from urllib.parse import quote

import streamlit as st


def _render_d3_html(element_id: str, payload: dict[str, Any], body_js: str, height: int) -> None:
    """Render a reusable D3 container with the supplied payload and body script."""
    html = f"""
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        overflow: visible;
        background: transparent;
      }}
      #{element_id} {{
        min-height: {height + 80}px;
        padding: 10px 10px 34px 10px;
        overflow: visible;
        border-radius: 24px;
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(248,250,252,0.98) 100%);
        box-shadow:
          0 12px 34px rgba(15, 23, 42, 0.06),
          0 1px 0 rgba(255, 255, 255, 0.75) inset;
        box-sizing: border-box;
      }}
      #{element_id} svg {{
        overflow: visible;
        display: block;
        border-radius: 18px;
      }}
    </style>
    <div id="{element_id}"></div>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
    const payload = {json.dumps(payload)};
    const container = document.getElementById("{element_id}");
    if (!container) {{
      throw new Error("D3 container not found");
    }}
    {body_js}
    </script>
    """
    st.iframe(f"data:text/html;charset=utf-8,{quote(html)}", height=height + 120)


def render_networth_overview_d3(payload: dict[str, Any], height: int = 660) -> None:
    """Render a stacked-area net worth overview chart with total overlay."""
    body_js = """
    const width = container.clientWidth || 980;
    const height = payload.frameHeight || 700;
    const margin = { top: 46, right: 34, bottom: 108, left: 84 };
    const rows = payload.rows;
    const categories = payload.categories;
    const layerPalette = payload.colors && payload.colors.length
      ? payload.colors
      : ["#F38181", "#F6A6A6", "#FCE38A", "#F9E9B7", "#EAFFD0", "#CFEFBE", "#95E1D3", "#6FCFC3"];
    const monochromeRange = categories.map((_, index) => layerPalette[index % layerPalette.length]);
    const colorScale = d3.scaleOrdinal()
      .domain(categories)
      .range(monochromeRange);

    container.innerHTML = "";
    container.style.position = "relative";

    const legendHost = d3.select(container)
      .append("div")
      .style("display", "flex")
      .style("flex-wrap", "wrap")
      .style("justify-content", "center")
      .style("gap", "10px")
      .style("margin", "4px 0 18px 0");

    const svg = d3.select(container)
      .append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("width", "100%")
      .attr("height", height).style("height", `${height}px`)
      .style("font-family", "Aptos, Segoe UI, sans-serif");

    svg.append("rect")
      .attr("x", margin.left)
      .attr("y", margin.top)
      .attr("width", width - margin.left - margin.right)
      .attr("height", height - margin.top - margin.bottom)
      .attr("rx", 24)
      .attr("fill", "#F7FAFC");

    const defs = svg.append("defs");
    const totalGradient = defs.append("linearGradient")
      .attr("id", "networth-total-fill")
      .attr("x1", "0%")
      .attr("x2", "0%")
      .attr("y1", "0%")
      .attr("y2", "100%");

    totalGradient.append("stop")
      .attr("offset", "0%")
      .attr("stop-color", "#0F172A")
      .attr("stop-opacity", 0.08);

    totalGradient.append("stop")
      .attr("offset", "100%")
      .attr("stop-color", "#0F172A")
      .attr("stop-opacity", 0.02);

    const x = d3.scalePoint()
      .domain(rows.map(d => d.label))
      .range([margin.left, width - margin.right])
      .padding(0.45);

    const totals = rows.map(d => d.total || 0);
    const stackMax = d3.max(rows, row => d3.sum(Object.values(row.categories).filter(value => value > 0))) || 0;
    const maxReference = d3.max([...totals, stackMax]) || 0;
    const minReference = Math.min(d3.min(totals) || 0, 0);
    const padding = Math.max((maxReference - minReference) * 0.18, Math.abs(maxReference || 1) * 0.08);

    const y = d3.scaleLinear()
      .domain([Math.min(minReference - padding, 0), maxReference + padding])
      .nice()
      .range([height - margin.bottom, margin.top]);

    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll("line").remove())
      .call(g => g.selectAll("text")
        .attr("fill", "#64748B")
        .attr("font-size", 13)
        .attr("transform", "rotate(-35)")
        .style("text-anchor", "end"));

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => d3.format("$,.2s")(d).replace("G", "B")))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll(".tick line")
        .attr("x2", width - margin.left - margin.right)
        .attr("stroke", "rgba(148, 163, 184, 0.18)"))
      .call(g => g.selectAll("text")
        .attr("fill", "#64748B")
        .attr("font-size", 13));

    if (payload.milestones && payload.milestones.length) {
      payload.milestones.forEach(value => {
        svg.append("line")
          .attr("x1", margin.left)
          .attr("x2", width - margin.right)
          .attr("y1", y(value))
          .attr("y2", y(value))
          .attr("stroke", "rgba(192, 132, 87, 0.38)")
          .attr("stroke-dasharray", "4 6");

        svg.append("text")
          .attr("x", width - margin.right)
          .attr("y", y(value) - 8)
          .attr("text-anchor", "end")
          .attr("fill", "#9A6B39")
          .attr("font-size", 12)
          .attr("font-weight", 700)
          .text(d3.format("$,.2s")(value).replace("G", "B"));
      });
    }

    const totalArea = d3.area()
      .x(d => x(d.label))
      .y0(y(0))
      .y1(d => y(d.total))
      .curve(d3.curveMonotoneX);

    const totalLine = d3.line()
      .x(d => x(d.label))
      .y(d => y(d.total))
      .curve(d3.curveMonotoneX);

    const stackedInput = rows.map(d => ({ label: d.label, ...d.categories }));
    const stackedSeries = d3.stack().keys(categories)(stackedInput);
    const stackedArea = d3.area()
      .x(d => x(d.data.label))
      .y0(d => y(d[0]))
      .y1(d => y(d[1]))
      .curve(d3.curveMonotoneX);

    svg.append("g")
      .selectAll("path")
      .data(stackedSeries)
      .join("path")
      .attr("fill", d => colorScale(d.key))
      .attr("opacity", 0.92)
      .attr("stroke", "rgba(255,255,255,0.68)")
      .attr("stroke-width", 1.1)
      .attr("d", stackedArea);

    svg.append("path")
      .datum(rows)
      .attr("fill", "url(#networth-total-fill)")
      .attr("d", totalArea);

    svg.append("path")
      .datum(rows)
      .attr("fill", "none")
      .attr("stroke", "#0F172A")
      .attr("stroke-width", 3.6)
      .attr("stroke-linecap", "round")
      .attr("stroke-linejoin", "round")
      .attr("d", totalLine);

    if (payload.showTrendLine) {
      svg.append("g")
        .selectAll("circle")
        .data(rows)
        .join("circle")
        .attr("cx", d => x(d.label))
        .attr("cy", d => y(d.total))
        .attr("r", 4.5)
        .attr("fill", "#FFFFFF")
        .attr("stroke", "#0F172A")
        .attr("stroke-width", 2.5);
    }

    if (payload.showRollingAvg) {
      const rollingLine = d3.line()
        .defined(d => d.rollingAvg !== null)
        .x(d => x(d.label))
        .y(d => y(d.rollingAvg))
        .curve(d3.curveMonotoneX);

      svg.append("path")
        .datum(rows)
        .attr("fill", "none")
        .attr("stroke", "#B7791F")
        .attr("stroke-width", 2.1)
        .attr("stroke-dasharray", "6 6")
        .attr("d", rollingLine);
    }

    if (payload.showPeriodPct) {
      svg.append("g")
        .selectAll("text")
        .data(rows.filter(d => d.pctText))
        .join("text")
        .attr("x", d => x(d.label))
        .attr("y", d => y(d.total) - 16)
        .attr("text-anchor", "middle")
        .attr("fill", d => d.pctValue >= 0 ? "#2F6B57" : "#9A564B")
        .attr("font-size", 13)
        .attr("font-weight", 700)
        .text(d => d.pctText);
    }

    if (payload.highlightExtremes && rows.length > 1) {
      const best = rows.reduce((acc, item) => item.total > acc.total ? item : acc, rows[0]);
      const worst = rows.reduce((acc, item) => item.total < acc.total ? item : acc, rows[0]);
      [
        { point: best, label: "Peak", color: "#2F6B57", offset: -22 },
        { point: worst, label: "Low", color: "#9A564B", offset: 28 },
      ].forEach(item => {
        svg.append("text")
          .attr("x", x(item.point.label))
          .attr("y", y(item.point.total) + item.offset)
          .attr("text-anchor", "middle")
          .attr("fill", item.color)
          .attr("font-size", 13)
          .attr("font-weight", 700)
          .text(`${item.label} | ${d3.format("$,.2s")(item.point.total).replace("G", "B")}`);
      });
    }

    const tooltip = d3.select(container)
      .append("div")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("opacity", 0)
      .style("background", "rgba(15, 23, 42, 0.92)")
      .style("color", "#fff")
      .style("padding", "14px 16px")
      .style("border-radius", "14px")
      .style("font-size", "14px")
      .style("line-height", "1.4")
      .style("border", "1px solid rgba(255,255,255,0.08)")
      .style("box-shadow", "0 12px 30px rgba(15, 23, 42, 0.20)");

    svg.append("g")
      .selectAll("rect")
      .data(rows)
      .join("rect")
      .attr("x", d => x(d.label) - 20)
      .attr("y", margin.top)
      .attr("width", 40)
      .attr("height", height - margin.top - margin.bottom)
      .attr("fill", "transparent")
      .on("mouseenter", function(event, d) {
        const categoryRows = Object.entries(d.categories)
          .filter(([, value]) => value !== 0)
          .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
          .slice(0, 5)
          .map(([name, value]) => `<div style="display:flex;justify-content:space-between;gap:14px;"><span>${name}</span><strong>${d3.format("$,.0f")(value)}</strong></div>`)
          .join("");

        tooltip
          .style("opacity", 1)
          .html(`
            <div style="font-weight:700;margin-bottom:8px;">${d.label}</div>
            <div style="display:grid;gap:4px;">
              <div style="display:flex;justify-content:space-between;gap:14px;"><span>Net Worth</span><strong>${d3.format("$,.0f")(d.total)}</strong></div>
            </div>
            ${d.pctText ? `<div style="margin:8px 0;color:${d.pctValue >= 0 ? "#86EFAC" : "#FCA5A5"};">${d.pctText} vs prior period</div>` : ""}
            <div style="padding-top:8px;border-top:1px solid rgba(255,255,255,0.14);display:grid;gap:4px;">
              ${categoryRows || "<span>No leading buckets</span>"}
            </div>
          `);
      })
      .on("mousemove", function(event) {
        tooltip
          .style("left", `${event.offsetX + 16}px`)
          .style("top", `${event.offsetY - 20}px`);
      })
      .on("mouseleave", function() {
        tooltip.style("opacity", 0);
      });

    const legendItems = [
      { label: "Net Worth", color: "#0F172A", dash: false },
      ...categories.map(category => ({ label: category, color: colorScale(category), dash: false })),
      ...(payload.showRollingAvg ? [{ label: "Rolling Avg", color: "#B7791F", dash: true }] : []),
    ];

    legendItems.forEach((item, index) => {
      const itemBox = legendHost.append("div")
        .style("display", "inline-flex")
        .style("align-items", "center")
        .style("gap", "10px")
        .style("padding", "10px 14px")
        .style("border-radius", "14px")
        .style("background", "rgba(255,255,255,0.82)")
        .style("border", "1px solid rgba(148,163,184,0.22)")
        .style("box-shadow", "0 8px 20px rgba(15,23,42,0.04)");

      const marker = itemBox.append("div")
        .style("display", "inline-flex")
        .style("align-items", "center")
        .style("justify-content", "center")
        .style("width", "24px")
        .style("height", "12px")
        .style("position", "relative");

      if (item.dash) {
        marker.append("div")
          .style("width", "24px")
          .style("border-top", `3px dashed ${item.color}`);
      } else if (item.label === "Net Worth") {
        marker.append("div")
          .style("width", "24px")
          .style("border-top", `3px solid ${item.color}`)
          .style("position", "absolute");

        marker.append("div")
          .style("width", "8px")
          .style("height", "8px")
          .style("border-radius", "999px")
          .style("background", "#FFFFFF")
          .style("border", `2px solid ${item.color}`)
          .style("position", "absolute");
      } else {
        marker.append("div")
          .style("width", "20px")
          .style("height", "12px")
          .style("border-radius", "4px")
          .style("background", item.color)
          .style("border", "1px solid rgba(255,255,255,0.65)");
      }

      itemBox.append("div")
        .style("color", "#1F2937")
        .style("font-size", "13px")
        .style("font-weight", "700")
        .text(item.label);
    });
    """
    render_height = max(height, 700)
    payload = {**payload, "frameHeight": render_height}
    _render_d3_html("networth-overview-d3", payload, body_js, render_height)


def render_networth_drivers_d3(payload: dict[str, Any], height: int = 560) -> None:
    """Render a product-style change-drivers chart."""
    body_js = """
    const width = container.clientWidth || 980;
    const rowCount = payload.rows.length || 1;
    const height = payload.frameHeight || Math.max(560, rowCount * 26 + 240);
    const margin = { top: 42, right: 32, bottom: 112, left: 84 };
    const rows = payload.rows;

    container.innerHTML = "";
    container.style.position = "relative";

    const svg = d3.select(container)
      .append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("width", "100%")
      .attr("height", height).style("height", `${height}px`)
      .style("font-family", "Aptos, Segoe UI, sans-serif");

    svg.append("rect")
      .attr("x", margin.left)
      .attr("y", margin.top)
      .attr("width", width - margin.left - margin.right)
      .attr("height", height - margin.top - margin.bottom)
      .attr("rx", 24)
      .attr("fill", "#FBFCFE");

    const maxPositive = d3.max(rows, d => d.delta > 0 ? d.delta : 0) || 0;
    const minNegative = d3.min(rows, d => d.delta < 0 ? d.delta : 0) || 0;
    const positivePadding = maxPositive ? maxPositive * 0.18 : 0;
    const negativePadding = minNegative ? Math.abs(minNegative) * 0.18 : 0;
    const x = d3.scaleBand()
      .domain(rows.map(d => d.label))
      .range([margin.left, width - margin.right])
      .padding(0.34);

    const y = d3.scaleLinear()
      .domain([minNegative - negativePadding, maxPositive + positivePadding])
      .nice()
      .range([height - margin.bottom, margin.top]);

    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll("line").remove())
      .call(g => g.selectAll("text")
        .attr("fill", "#64748B")
        .attr("font-size", 13)
        .attr("transform", "rotate(-35)")
        .style("text-anchor", "end"));

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => d3.format("$,.2s")(d).replace("G", "B")))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll(".tick line")
        .attr("x2", width - margin.left - margin.right)
        .attr("stroke", "rgba(148, 163, 184, 0.18)"))
      .call(g => g.selectAll("text").attr("fill", "#475569").attr("font-size", 13));

    svg.append("line")
      .attr("x1", margin.left)
      .attr("x2", width - margin.right)
      .attr("y1", y(0))
      .attr("y2", y(0))
      .attr("stroke", "#94A3B8")
      .attr("stroke-width", 1.4)
      .attr("stroke-dasharray", "4 4");

    const tooltip = d3.select(container)
      .append("div")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("opacity", 0)
      .style("background", "rgba(15, 23, 42, 0.96)")
      .style("color", "#fff")
      .style("padding", "14px 16px")
      .style("border-radius", "14px")
      .style("font-size", "14px")
      .style("line-height", "1.4")
      .style("border", "1px solid rgba(255,255,255,0.08)")
      .style("box-shadow", "0 12px 30px rgba(15, 23, 42, 0.20)");

    svg.append("g")
      .selectAll("rect")
      .data(rows)
      .join("rect")
      .attr("x", d => x(d.label))
      .attr("y", d => d.delta >= 0 ? y(d.delta) : y(0))
      .attr("width", x.bandwidth())
      .attr("height", d => Math.abs(y(d.delta) - y(0)))
      .attr("rx", 8)
      .attr("fill", d => d.delta >= 0 ? "#2F855A" : "#A44A3F")
      .on("mouseenter", function(event, d) {
        tooltip
          .style("opacity", 1)
          .html(`
            <div style="font-weight:700;margin-bottom:8px;">${d.label}</div>
            <div style="display:grid;gap:4px;">
              <div style="display:flex;justify-content:space-between;gap:14px;"><span>${payload.fromLabel}</span><strong>${d3.format("$,.0f")(d.previous)}</strong></div>
              <div style="display:flex;justify-content:space-between;gap:14px;"><span>${payload.toLabel}</span><strong>${d3.format("$,.0f")(d.current)}</strong></div>
              <div style="display:flex;justify-content:space-between;gap:14px;color:${d.delta >= 0 ? "#86EFAC" : "#FCA5A5"};"><span>Change</span><strong>${d.delta >= 0 ? "+" : ""}${d3.format("$,.0f")(d.delta)}</strong></div>
            </div>
          `);
      })
      .on("mousemove", function(event) {
        tooltip
          .style("left", `${event.offsetX + 16}px`)
          .style("top", `${event.offsetY - 20}px`);
      })
      .on("mouseleave", function() {
        tooltip.style("opacity", 0);
      });

    svg.append("g")
      .selectAll("text")
      .data(rows)
      .join("text")
      .attr("x", d => x(d.label) + x.bandwidth() / 2)
      .attr("y", d => d.delta >= 0 ? y(d.delta) - 8 : y(d.delta) + 18)
      .attr("text-anchor", "middle")
      .attr("fill", "#0F172A")
      .attr("font-size", 13)
      .attr("font-weight", 700)
      .text(d => `${d.delta >= 0 ? "+" : ""}${d3.format("$,.2s")(d.delta).replace("G", "B")}`);
    """
    row_count = len(payload.get("rows", []))
    render_height = max(height, row_count * 26 + 240)
    payload = {**payload, "frameHeight": render_height}
    _render_d3_html("networth-drivers-d3", payload, body_js, render_height)


def render_networth_composition_d3(payload: dict[str, Any], height: int = 620) -> None:
    """Render a stacked composition chart that keeps smaller buckets visible."""
    body_js = """
    const width = container.clientWidth || 980;
    const height = payload.frameHeight || 620;
    const margin = { top: 42, right: 34, bottom: 108, left: 84 };
    const rows = payload.rows;
    const categories = payload.categories;
    const colorScale = d3.scaleOrdinal()
      .domain(categories)
      .range(payload.colors.slice(0, categories.length));

    container.innerHTML = "";
    container.style.position = "relative";

    const svg = d3.select(container)
      .append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("width", "100%")
      .attr("height", height).style("height", `${height}px`)
      .style("font-family", "Aptos, Segoe UI, sans-serif");

    svg.append("rect")
      .attr("x", margin.left)
      .attr("y", margin.top)
      .attr("width", width - margin.left - margin.right)
      .attr("height", height - margin.top - margin.bottom)
      .attr("rx", 24)
      .attr("fill", "#FBFCFE");

    const x = d3.scalePoint()
      .domain(rows.map(d => d.label))
      .range([margin.left, width - margin.right])
      .padding(0.45);

    const maxStack = d3.max(rows, row => d3.sum(Object.values(row.categories).filter(value => value > 0))) || 0;
    const y = d3.scaleLinear()
      .domain([0, maxStack * 1.08])
      .nice()
      .range([height - margin.bottom, margin.top]);

    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll("line").remove())
      .call(g => g.selectAll("text")
        .attr("fill", "#64748B")
        .attr("font-size", 13)
        .attr("transform", "rotate(-35)")
        .style("text-anchor", "end"));

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => d3.format("$,.2s")(d).replace("G", "B")))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll(".tick line")
        .attr("x2", width - margin.left - margin.right)
        .attr("stroke", "rgba(148, 163, 184, 0.18)"))
      .call(g => g.selectAll("text")
        .attr("fill", "#64748B")
        .attr("font-size", 13));

    const stackedInput = rows.map(d => ({ label: d.label, ...d.categories }));
    const stackedSeries = d3.stack().keys(categories)(stackedInput);
    const area = d3.area()
      .x(d => x(d.data.label))
      .y0(d => y(d[0]))
      .y1(d => y(d[1]))
      .curve(d3.curveMonotoneX);

    svg.append("g")
      .selectAll("path")
      .data(stackedSeries)
      .join("path")
      .attr("fill", d => colorScale(d.key))
      .attr("opacity", 0.92)
      .attr("d", area);

    const tooltip = d3.select(container)
      .append("div")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("opacity", 0)
      .style("background", "rgba(15, 23, 42, 0.92)")
      .style("color", "#fff")
      .style("padding", "14px 16px")
      .style("border-radius", "14px")
      .style("font-size", "14px")
      .style("line-height", "1.4")
      .style("box-shadow", "0 12px 30px rgba(15, 23, 42, 0.24)");

    svg.append("g")
      .selectAll("rect")
      .data(rows)
      .join("rect")
      .attr("x", d => x(d.label) - 22)
      .attr("y", margin.top)
      .attr("width", 44)
      .attr("height", height - margin.top - margin.bottom)
      .attr("fill", "transparent")
      .on("mouseenter", function(event, d) {
        const categoryRows = Object.entries(d.categories)
          .filter(([, value]) => value !== 0)
          .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
          .map(([name, value]) => `<div style="display:flex;justify-content:space-between;gap:14px;"><span>${name}</span><strong>${d3.format("$,.0f")(value)}</strong></div>`)
          .join("");

        tooltip
          .style("opacity", 1)
          .html(`
            <div style="font-weight:700;margin-bottom:8px;">${d.label}</div>
            <div style="display:flex;justify-content:space-between;gap:14px;margin-bottom:8px;">
              <span>Total Visible Mix</span><strong>${d3.format("$,.0f")(d.totalVisible)}</strong>
            </div>
            <div style="padding-top:8px;border-top:1px solid rgba(255,255,255,0.14);display:grid;gap:4px;">
              ${categoryRows || "<span>No visible buckets</span>"}
            </div>
          `);
      })
      .on("mousemove", function(event) {
        tooltip
          .style("left", `${event.offsetX + 16}px`)
          .style("top", `${event.offsetY - 20}px`);
      })
      .on("mouseleave", function() {
        tooltip.style("opacity", 0);
      });

    const legend = svg.append("g")
      .attr("transform", `translate(${margin.left},${height - 52})`);

    categories.forEach((category, index) => {
      const item = legend.append("g")
        .attr("transform", `translate(${(index % 4) * 180},${Math.floor(index / 4) * 24})`);

      item.append("rect")
        .attr("width", 12)
        .attr("height", 12)
        .attr("rx", 3)
        .attr("fill", colorScale(category));

      item.append("text")
        .attr("x", 18)
        .attr("y", 10)
        .attr("fill", "#475569")
        .attr("font-size", 13)
        .text(category);
    });
    """
    render_height = max(height, 640)
    payload = {**payload, "frameHeight": render_height}
    _render_d3_html("networth-composition-d3", payload, body_js, render_height)
