"""Generate static HTML site with interactive Chart.js charts."""

import json
from pathlib import Path
from datetime import datetime

from .config import PROJECT_ROOT
from .portfolio import PortfolioHistory, PublicSnapshot
from .regions import get_region, get_region_color, get_region_order, REGION_CONFIG


# Use docs/ for GitHub Pages compatibility
SITE_DIR = PROJECT_ROOT / "docs"


def _generate_html(history: PortfolioHistory) -> str:
    """Generate the complete HTML page with embedded data and charts."""

    # Prepare data for charts
    dates = [s.date for s in history.snapshots]
    index_values = [round(s.index_value, 2) for s in history.snapshots]
    returns = [round(s.period_return_pct, 2) if s.period_return_pct is not None else None
               for s in history.snapshots]
    cash_pcts = [round(s.cash_pct, 2) for s in history.snapshots]
    other_pcts = [round(s.other_pct, 2) for s in history.snapshots]

    # Get top symbols across all snapshots
    symbol_totals: dict[str, float] = {}
    for snapshot in history.snapshots:
        for pos in snapshot.positions:
            symbol_totals[pos.symbol] = symbol_totals.get(pos.symbol, 0) + pos.allocation_pct
    top_symbols = sorted(symbol_totals.keys(), key=lambda s: symbol_totals[s], reverse=True)[:6]

    # Build allocation series for each symbol
    allocation_series = {}
    for symbol in top_symbols:
        allocation_series[symbol] = []
        for snapshot in history.snapshots:
            pos_map = {p.symbol: p.allocation_pct for p in snapshot.positions}
            allocation_series[symbol].append(round(pos_map.get(symbol, 0), 2))

    # Calculate "other stocks" (not in top symbols, not cash, not hidden)
    other_stocks = []
    for i, snapshot in enumerate(history.snapshots):
        top_sum = sum(allocation_series[s][i] for s in top_symbols)
        other_stocks.append(round(max(0, snapshot.invested_pct - top_sum - snapshot.other_pct), 2))

    # Latest snapshot for current allocation
    latest = history.snapshots[-1] if history.snapshots else None

    # Prepare current allocation data
    current_allocation = []
    if latest:
        for pos in latest.positions[:10]:
            current_allocation.append({"symbol": pos.symbol, "pct": round(pos.allocation_pct, 2)})
        if latest.other_pct > 0:
            current_allocation.append({"symbol": "Other Positions", "pct": round(latest.other_pct, 2)})
        if latest.cash_pct > 0:
            current_allocation.append({"symbol": "Cash", "pct": round(latest.cash_pct, 2)})

    # Calculate regional allocation for latest snapshot
    regional_allocation = []
    if latest:
        region_totals: dict[str, float] = {}
        for pos in latest.positions:
            region = get_region(pos.symbol)
            region_totals[region] = region_totals.get(region, 0) + pos.allocation_pct

        # Sort by allocation percentage (descending)
        sorted_regions = sorted(region_totals.items(), key=lambda x: -x[1])
        for region, pct in sorted_regions:
            regional_allocation.append({
                "region": region,
                "pct": round(pct, 2),
                "color": get_region_color(region)
            })

        # Add Other Positions and Cash
        if latest.other_pct > 0:
            regional_allocation.append({
                "region": "Other Positions",
                "pct": round(latest.other_pct, 2),
                "color": "#64748b"
            })
        if latest.cash_pct > 0:
            regional_allocation.append({
                "region": "Cash",
                "pct": round(latest.cash_pct, 2),
                "color": "#22c55e"
            })

    # Calculate regional allocation history
    all_regions = set()
    for snapshot in history.snapshots:
        for pos in snapshot.positions:
            all_regions.add(get_region(pos.symbol))

    # Sort regions by display order
    sorted_region_names = sorted(all_regions, key=get_region_order)

    regional_series: dict[str, list[float]] = {r: [] for r in sorted_region_names}
    for snapshot in history.snapshots:
        region_totals = {r: 0.0 for r in sorted_region_names}
        for pos in snapshot.positions:
            region = get_region(pos.symbol)
            if region in region_totals:
                region_totals[region] += pos.allocation_pct
        for region in sorted_region_names:
            regional_series[region].append(round(region_totals[region], 2))

    # Get region colors for the chart
    region_colors = {r: get_region_color(r) for r in sorted_region_names}

    # Parse dates
    def parse_date(d: str) -> datetime | None:
        for fmt in ["%Y%m%d", "%Y-%m-%d"]:
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                continue
        return None

    parsed_dates = [parse_date(d) for d in dates]
    valid_dates = [d for d in parsed_dates if d is not None]

    # Determine date format based on data span
    if len(valid_dates) >= 2:
        span_days = (max(valid_dates) - min(valid_dates)).days
        spans_multiple_years = max(valid_dates).year != min(valid_dates).year
    else:
        span_days = 0
        spans_multiple_years = False

    def format_date(d: str) -> str:
        parsed = parse_date(d)
        if parsed is None:
            return d
        if spans_multiple_years:
            return parsed.strftime("%b %d '%y")  # "Jan 05 '25"
        elif span_days > 90:
            return parsed.strftime("%b %d")  # "Jan 05"
        else:
            return parsed.strftime("%m/%d")  # "01/05"

    formatted_dates = [format_date(d) for d in dates]

    # Build the data object for JavaScript
    chart_data = {
        "dates": formatted_dates,
        "rawDates": dates,
        "indexValues": index_values,
        "returns": returns,
        "cashPcts": cash_pcts,
        "otherPcts": other_pcts,
        "topSymbols": top_symbols,
        "allocationSeries": allocation_series,
        "currentAllocation": current_allocation,
        "regionalAllocation": regional_allocation,
        "regions": sorted_region_names,
        "regionalSeries": regional_series,
        "regionColors": region_colors,
        "latest": {
            "date": latest.date if latest else "",
            "indexValue": round(latest.index_value, 2) if latest else 100,
            "totalReturn": round(latest.total_return_pct, 2) if latest and latest.total_return_pct else None,
            "periodReturn": round(latest.period_return_pct, 2) if latest and latest.period_return_pct else None,
            "investedPct": round(latest.invested_pct, 2) if latest else 0,
            "cashPct": round(latest.cash_pct, 2) if latest else 0,
        } if latest else None,
    }

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Tracker</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-secondary);
            margin-bottom: 2rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-bottom: 0.25rem;
        }}

        .stat-value {{
            font-size: 1.75rem;
            font-weight: 600;
        }}

        .stat-value.positive {{
            color: var(--accent-green);
        }}

        .stat-value.negative {{
            color: var(--accent-red);
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        @media (max-width: 600px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
        }}

        .chart-card h2 {{
            font-size: 1.125rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}

        .chart-container {{
            position: relative;
            height: 300px;
        }}

        .positions-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .positions-table th,
        .positions-table td {{
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid var(--bg-card);
        }}

        .positions-table th {{
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.875rem;
        }}

        .positions-table td:last-child {{
            text-align: right;
        }}

        .bar {{
            height: 8px;
            background: var(--accent-blue);
            border-radius: 4px;
            margin-top: 0.25rem;
        }}

        footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid var(--bg-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Portfolio Tracker</h1>
        <p class="subtitle">Updated: <span id="lastUpdate"></span></p>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Index Value</div>
                <div class="stat-value" id="indexValue">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Return</div>
                <div class="stat-value" id="totalReturn">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Period Return</div>
                <div class="stat-value" id="periodReturn">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Invested</div>
                <div class="stat-value" id="investedPct">-</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h2>Portfolio Index (Baseline = 100)</h2>
                <div class="chart-container">
                    <canvas id="indexChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h2>Monthly Returns</h2>
                <div class="chart-container">
                    <canvas id="returnsChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h2>Current Allocation</h2>
                <div class="chart-container">
                    <canvas id="allocationChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h2>Allocation Over Time</h2>
                <div class="chart-container">
                    <canvas id="allocationHistoryChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h2>Regional Allocation</h2>
                <div class="chart-container">
                    <canvas id="regionChart"></canvas>
                </div>
            </div>

            <div class="chart-card">
                <h2>Regional Allocation Over Time</h2>
                <div class="chart-container">
                    <canvas id="regionHistoryChart"></canvas>
                </div>
            </div>
        </div>

        <div class="chart-card">
            <h2>Current Positions</h2>
            <table class="positions-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Allocation</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="positionsTable">
                </tbody>
            </table>
        </div>

        <footer>
            <p>Data shows percentages only. No actual values are displayed.</p>
        </footer>
    </div>

    <script>
        const data = {json.dumps(chart_data)};

        // Update stats
        if (data.latest) {{
            document.getElementById('lastUpdate').textContent = data.latest.date;
            document.getElementById('indexValue').textContent = data.latest.indexValue.toFixed(2);

            const totalReturnEl = document.getElementById('totalReturn');
            if (data.latest.totalReturn !== null) {{
                const sign = data.latest.totalReturn >= 0 ? '+' : '';
                totalReturnEl.textContent = sign + data.latest.totalReturn.toFixed(2) + '%';
                totalReturnEl.className = 'stat-value ' + (data.latest.totalReturn >= 0 ? 'positive' : 'negative');
            }}

            const periodReturnEl = document.getElementById('periodReturn');
            if (data.latest.periodReturn !== null) {{
                const sign = data.latest.periodReturn >= 0 ? '+' : '';
                periodReturnEl.textContent = sign + data.latest.periodReturn.toFixed(2) + '%';
                periodReturnEl.className = 'stat-value ' + (data.latest.periodReturn >= 0 ? 'positive' : 'negative');
            }}

            document.getElementById('investedPct').textContent = data.latest.investedPct.toFixed(1) + '%';
        }}

        // Populate positions table
        const tbody = document.getElementById('positionsTable');
        data.currentAllocation.forEach(pos => {{
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${{pos.symbol}}</td>
                <td>
                    <div>${{pos.pct.toFixed(2)}}%</div>
                    <div class="bar" style="width: ${{Math.min(pos.pct, 100)}}%"></div>
                </td>
                <td></td>
            `;
            tbody.appendChild(tr);
        }});

        // Chart.js defaults
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = '#334155';

        // Index Chart
        new Chart(document.getElementById('indexChart'), {{
            type: 'line',
            data: {{
                labels: data.dates,
                datasets: [{{
                    label: 'Index Value',
                    data: data.indexValues,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    annotation: {{
                        annotations: {{
                            baseline: {{
                                type: 'line',
                                yMin: 100,
                                yMax: 100,
                                borderColor: '#64748b',
                                borderDash: [5, 5],
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                    }}
                }}
            }}
        }});

        // Returns Chart
        new Chart(document.getElementById('returnsChart'), {{
            type: 'bar',
            data: {{
                labels: data.dates,
                datasets: [{{
                    label: 'Return %',
                    data: data.returns,
                    backgroundColor: data.returns.map(r => r >= 0 ? '#22c55e' : '#ef4444'),
                    borderRadius: 4,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                    }}
                }}
            }}
        }});

        // Allocation Pie Chart
        const pieColors = [
            '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
            '#06b6d4', '#6366f1', '#d946ef', '#f97316', '#14b8a6',
            '#64748b', '#22c55e'
        ];

        new Chart(document.getElementById('allocationChart'), {{
            type: 'doughnut',
            data: {{
                labels: data.currentAllocation.map(p => p.symbol),
                datasets: [{{
                    data: data.currentAllocation.map(p => p.pct),
                    backgroundColor: pieColors.slice(0, data.currentAllocation.length),
                    borderWidth: 0,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                    }},
                }},
            }}
        }});

        // Allocation History (Stacked Area)
        const stackedDatasets = [];
        let colorIdx = 0;

        data.topSymbols.forEach(symbol => {{
            stackedDatasets.push({{
                label: symbol,
                data: data.allocationSeries[symbol],
                backgroundColor: pieColors[colorIdx % pieColors.length],
                fill: true,
                tension: 0.3,
            }});
            colorIdx++;
        }});

        stackedDatasets.push({{
            label: 'Other Positions',
            data: data.otherPcts,
            backgroundColor: '#64748b',
            fill: true,
            tension: 0.3,
        }});

        stackedDatasets.push({{
            label: 'Cash',
            data: data.cashPcts,
            backgroundColor: '#22c55e',
            fill: true,
            tension: 0.3,
        }});

        new Chart(document.getElementById('allocationHistoryChart'), {{
            type: 'line',
            data: {{
                labels: data.dates,
                datasets: stackedDatasets,
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                    }},
                }},
                scales: {{
                    y: {{
                        stacked: true,
                        max: 100,
                    }},
                    x: {{
                        stacked: true,
                    }}
                }}
            }}
        }});

        // Regional Allocation Pie Chart
        new Chart(document.getElementById('regionChart'), {{
            type: 'doughnut',
            data: {{
                labels: data.regionalAllocation.map(r => r.region),
                datasets: [{{
                    data: data.regionalAllocation.map(r => r.pct),
                    backgroundColor: data.regionalAllocation.map(r => r.color),
                    borderWidth: 0,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                    }},
                }},
            }}
        }});

        // Regional Allocation History (Stacked Area)
        const regionDatasets = [];

        data.regions.forEach(region => {{
            regionDatasets.push({{
                label: region,
                data: data.regionalSeries[region],
                backgroundColor: data.regionColors[region],
                fill: true,
                tension: 0.3,
            }});
        }});

        regionDatasets.push({{
            label: 'Other Positions',
            data: data.otherPcts,
            backgroundColor: '#64748b',
            fill: true,
            tension: 0.3,
        }});

        regionDatasets.push({{
            label: 'Cash',
            data: data.cashPcts,
            backgroundColor: '#22c55e',
            fill: true,
            tension: 0.3,
        }});

        new Chart(document.getElementById('regionHistoryChart'), {{
            type: 'line',
            data: {{
                labels: data.dates,
                datasets: regionDatasets,
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                    }},
                }},
                scales: {{
                    y: {{
                        stacked: true,
                        max: 100,
                    }},
                    x: {{
                        stacked: true,
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

    return html


def generate_site(history: PortfolioHistory) -> Path:
    """Generate the static HTML site."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    html = _generate_html(history)

    index_path = SITE_DIR / "index.html"
    with open(index_path, "w") as f:
        f.write(html)

    # Also save the public data as JSON for potential API use
    data_path = SITE_DIR / "data.json"
    with open(data_path, "w") as f:
        json.dump(history.to_dict(), f, indent=2)

    return SITE_DIR
