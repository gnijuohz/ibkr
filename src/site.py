"""Generate static HTML site with interactive Chart.js charts."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta

from .config import PROJECT_ROOT
from .portfolio import PortfolioHistory, PublicSnapshot
from .regions import get_region, get_region_color, get_region_order, REGION_CONFIG


# Use docs/ for GitHub Pages compatibility
SITE_DIR = PROJECT_ROOT / "docs"


def _fetch_benchmark_data(dates: list[str], symbols: list[str] = ["SPY", "QQQ"]) -> dict[str, list[float]]:
    """Fetch benchmark data and normalize to 100 at the first date.

    Args:
        dates: List of dates in YYYYMMDD format
        symbols: List of benchmark symbols to fetch

    Returns:
        Dict mapping symbol to list of normalized values (starting at 100)
    """
    try:
        import yfinance as yf
    except ImportError:
        return {}

    if not dates:
        return {}

    # Parse dates
    parsed_dates = []
    for d in dates:
        try:
            parsed_dates.append(datetime.strptime(d, "%Y%m%d"))
        except ValueError:
            try:
                parsed_dates.append(datetime.strptime(d, "%Y-%m-%d"))
            except ValueError:
                continue

    if not parsed_dates:
        return {}

    # Fetch data with buffer for weekends/holidays
    start_date = min(parsed_dates) - timedelta(days=7)
    end_date = max(parsed_dates) + timedelta(days=1)

    result = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                continue

            # Get closing prices for each portfolio date (use closest available)
            prices = []
            for target_date in parsed_dates:
                # Find closest date on or before target
                available_dates = hist.index[hist.index <= target_date.strftime("%Y-%m-%d %H:%M:%S%z").split()[0] + " 00:00:00-05:00"]
                if len(available_dates) == 0:
                    # Try without timezone
                    mask = hist.index.date <= target_date.date()
                    available = hist[mask]
                    if len(available) > 0:
                        prices.append(available['Close'].iloc[-1])
                    else:
                        prices.append(None)
                else:
                    prices.append(hist.loc[available_dates[-1], 'Close'])

            # Normalize to 100 at first date
            if prices and prices[0] is not None and prices[0] > 0:
                base = prices[0]
                normalized = [round((p / base) * 100, 2) if p is not None else None for p in prices]
                result[symbol] = normalized
        except Exception:
            continue

    return result


def _generate_html(history: PortfolioHistory) -> str:
    """Generate the complete HTML page with embedded data and charts."""

    # Prepare data for charts
    dates = [s.date for s in history.snapshots]
    index_values = [round(s.index_value, 2) for s in history.snapshots]

    # Fetch benchmark data (SPY and QQQ)
    benchmark_data = _fetch_benchmark_data(dates, ["SPY", "QQQ"])
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

    # Get list of all accounts and create masked names (needs to be done first)
    all_accounts_raw = sorted(set(
        acc for s in history.snapshots for acc in (s.accounts or [])
    ))
    # Create mapping: real account ID -> masked name (Account A, Account B, etc.)
    account_mask = {acc: f"Account {chr(65 + i)}" for i, acc in enumerate(all_accounts_raw)}

    # Prepare current allocation data (with masked account info)
    # Use top 6 to be consistent with Allocation Over Time chart
    current_allocation = []
    if latest:
        sorted_positions = sorted(latest.positions, key=lambda p: p.allocation_pct, reverse=True)
        top6 = sorted_positions[:6]
        remaining_pct = sum(p.allocation_pct for p in sorted_positions[6:])

        for pos in top6:
            current_allocation.append({
                "symbol": pos.symbol,
                "pct": round(pos.allocation_pct, 2),
                "account_id": account_mask.get(pos.account_id, "")
            })
        if remaining_pct > 0.1:
            current_allocation.append({"symbol": "Other Positions", "pct": round(remaining_pct, 2), "account_id": ""})
        if latest.cash_pct > 0:
            current_allocation.append({"symbol": "Cash", "pct": round(latest.cash_pct, 2), "account_id": ""})

    # Masked account list for the selector
    all_accounts = [account_mask[acc] for acc in all_accounts_raw]

    # Prepare full positions data for filtering (all positions, not just top 10)
    all_positions = []
    if latest:
        for pos in latest.positions:
            all_positions.append({
                "symbol": pos.symbol,
                "pct": round(pos.allocation_pct, 2),
                "account_id": account_mask.get(pos.account_id, "")
            })

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

        # Add Other Positions (options/derivatives) to US
        if latest.other_pct > 0:
            # Find US in the list and add to it, or create US entry
            us_entry = next((r for r in regional_allocation if r["region"] == "US"), None)
            if us_entry:
                us_entry["pct"] = round(us_entry["pct"] + latest.other_pct, 2)
            else:
                regional_allocation.insert(0, {
                    "region": "US",
                    "pct": round(latest.other_pct, 2),
                    "color": "#3b82f6"
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
        # Add other_pct (options/derivatives) to US
        if "US" in region_totals:
            region_totals["US"] += snapshot.other_pct
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
        "benchmarks": benchmark_data,
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
            "cashByAccount": {account_mask.get(k, k): v for k, v in (latest.cash_by_account or {}).items()} if latest else {},
            "totalByAccount": {account_mask.get(k, k): round(v, 2) for k, v in (latest.total_by_account or {}).items()} if latest else {},
        } if latest else None,
        "accounts": all_accounts,
        "allPositions": all_positions,
        "snapshots": [
            {
                "date": s.date,
                "positions": [
                    {"symbol": p.symbol, "pct": round(p.allocation_pct, 2), "account_id": account_mask.get(p.account_id, "")}
                    for p in s.positions
                ],
                "cash_pct": round(s.cash_pct, 2),
                "cash_by_account": {account_mask.get(k, k): round(v, 2) for k, v in (s.cash_by_account or {}).items()},
                "total_by_account": {account_mask.get(k, k): round(v, 2) for k, v in (s.total_by_account or {}).items()},
            }
            for s in history.snapshots
        ],
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

        .header-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .account-selector {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .account-btn {{
            padding: 0.5rem 1rem;
            border: 1px solid var(--bg-card);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}

        .account-btn:hover {{
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }}

        .account-btn.active {{
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-row">
            <div>
                <h1>Portfolio Tracker</h1>
                <p class="subtitle">Updated: <span id="lastUpdate"></span></p>
            </div>
            <div class="account-selector" id="accountSelector">
                <!-- Account buttons will be added by JavaScript -->
            </div>
        </div>

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
                <div class="stat-label" id="investedLabel">Invested</div>
                <div class="stat-value" id="investedPct">-</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h2>Portfolio vs Benchmarks (Baseline = 100)</h2>
                <div class="chart-container">
                    <canvas id="indexChart"></canvas>
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

        // Chart.js defaults
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = '#334155';

        const pieColors = [
            '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
            '#06b6d4', '#6366f1', '#d946ef', '#f97316', '#14b8a6',
            '#64748b', '#22c55e'
        ];

        // Region colors mapping
        const regionColorMap = {{
            'US': '#3b82f6',
            'Europe': '#8b5cf6',
            'China': '#ef4444',
            'Japan': '#f97316',
            'Taiwan': '#14b8a6',
            'Canada': '#a855f7',
            'India': '#22c55e',
            'SEAsia': '#eab308',
            'LatAm': '#ec4899',
            'Emerging': '#06b6d4',
            'Intl': '#6366f1',
            'Other': '#64748b',
            'Cash': '#22c55e'
        }};

        // Store chart instances for updates
        let indexChart, allocationChart, regionChart, allocationHistoryChart, regionHistoryChart;

        // Current selected account (null = all)
        let selectedAccount = null;

        // Initialize account selector
        function initAccountSelector() {{
            const selector = document.getElementById('accountSelector');
            if (!data.accounts || data.accounts.length <= 1) {{
                selector.style.display = 'none';
                return;
            }}

            // Add "All" button
            const allBtn = document.createElement('button');
            allBtn.className = 'account-btn active';
            allBtn.textContent = 'All';
            allBtn.onclick = () => selectAccount(null);
            selector.appendChild(allBtn);

            // Add button for each account
            data.accounts.forEach(acc => {{
                const btn = document.createElement('button');
                btn.className = 'account-btn';
                btn.textContent = acc;
                btn.onclick = () => selectAccount(acc);
                selector.appendChild(btn);
            }});
        }}

        // Select an account and update all views
        function selectAccount(account) {{
            selectedAccount = account;

            // Update button states
            document.querySelectorAll('.account-btn').forEach(btn => {{
                btn.classList.remove('active');
                if ((account === null && btn.textContent === 'All') ||
                    btn.textContent === account) {{
                    btn.classList.add('active');
                }}
            }});

            updateAllViews();
        }}

        // Get filtered positions for selected account
        function getFilteredPositions() {{
            if (!data.allPositions) return data.currentAllocation;
            if (selectedAccount === null) return data.currentAllocation;

            const filtered = data.allPositions.filter(p => p.account_id === selectedAccount);
            const cashPct = data.latest.cashByAccount?.[selectedAccount] || 0;
            // Use totalByAccount to get true account total (includes hidden options)
            const accountTotal = data.latest.totalByAccount?.[selectedAccount] || 0;

            // Sort by allocation
            const sorted = [...filtered].sort((a, b) => b.pct - a.pct);

            // Take top 6 (consistent with Allocation Over Time chart)
            const top6 = sorted.slice(0, 6);
            const top6Pct = top6.reduce((sum, p) => sum + p.pct, 0);
            const remainingPct = sorted.slice(6).reduce((sum, p) => sum + p.pct, 0);
            const visiblePositionsPct = top6Pct + remainingPct;

            // Calculate "Other Positions" = account total - visible positions - cash
            // This includes hidden options without exposing the specific amount
            const otherPct = Math.max(0, accountTotal - visiblePositionsPct - cashPct);

            // Normalize to 100%
            const result = top6.map(p => ({{
                symbol: p.symbol,
                pct: accountTotal > 0 ? (p.pct / accountTotal) * 100 : 0,
                account_id: p.account_id
            }}));

            // Add "Other Positions" (remaining stocks + hidden options)
            const totalOtherPct = remainingPct + otherPct;
            if (totalOtherPct > 0.1) {{
                result.push({{ symbol: 'Other Positions', pct: accountTotal > 0 ? (totalOtherPct / accountTotal) * 100 : 0 }});
            }}
            if (cashPct > 0.1) {{
                result.push({{ symbol: 'Cash', pct: accountTotal > 0 ? (cashPct / accountTotal) * 100 : 0 }});
            }}

            return result;
        }}

        // Calculate regional allocation for filtered positions
        function getFilteredRegionalAllocation() {{
            if (selectedAccount === null) return data.regionalAllocation;

            const positions = data.allPositions.filter(p => p.account_id === selectedAccount);
            const cashPct = data.latest.cashByAccount?.[selectedAccount] || 0;
            // Use totalByAccount to get true account total (includes hidden options)
            const total = data.latest.totalByAccount?.[selectedAccount] || 0;

            if (total === 0) return [];

            // Calculate region totals
            const regionTotals = {{}};
            positions.forEach(p => {{
                const region = getRegion(p.symbol);
                regionTotals[region] = (regionTotals[region] || 0) + p.pct;
            }});

            // Add hidden options to US region (they're US-based options)
            const visiblePct = positions.reduce((sum, p) => sum + p.pct, 0);
            const hiddenPct = Math.max(0, total - visiblePct - cashPct);
            if (hiddenPct > 0) {{
                regionTotals['US'] = (regionTotals['US'] || 0) + hiddenPct;
            }}

            // Normalize and build result
            const result = Object.entries(regionTotals)
                .map(([region, pct]) => ({{
                    region,
                    pct: (pct / total) * 100,
                    color: regionColorMap[region] || '#64748b'
                }}))
                .sort((a, b) => b.pct - a.pct);

            if (cashPct > 0.1) {{
                result.push({{
                    region: 'Cash',
                    pct: (cashPct / total) * 100,
                    color: '#22c55e'
                }});
            }}

            return result;
        }}

        // Simple region lookup (matches Python logic)
        function getRegion(symbol) {{
            const regionMap = {json.dumps({s: get_region(s) for s in set(p.symbol for p in (history.snapshots[-1].positions if history.snapshots else []))})};
            return regionMap[symbol] || 'Other';
        }}

        // Format date as "Jan 23rd, 2026"
        function formatDisplayDate(dateStr) {{
            if (!dateStr) return '';
            const year = dateStr.slice(0, 4);
            const month = dateStr.slice(4, 6);
            const day = dateStr.slice(6, 8);
            const date = new Date(year, month - 1, day);
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const d = date.getDate();
            const suffix = (d === 1 || d === 21 || d === 31) ? 'st' : (d === 2 || d === 22) ? 'nd' : (d === 3 || d === 23) ? 'rd' : 'th';
            return months[date.getMonth()] + ' ' + d + suffix + ', ' + date.getFullYear();
        }}

        // Calculate per-account index values from snapshots
        function calculateAccountIndex(account) {{
            if (!data.snapshots || data.snapshots.length === 0) return null;

            // Get account's % of total at each snapshot, multiply by portfolio index
            const accountValues = [];
            for (let i = 0; i < data.snapshots.length; i++) {{
                const snap = data.snapshots[i];
                const accountPct = snap.total_by_account?.[account] || 0;
                const portfolioIndex = data.indexValues[i];
                // Account value = (account % of total) × portfolio index / 100
                accountValues.push((accountPct / 100) * portfolioIndex);
            }}

            // Normalize to 100 at first snapshot
            const baseValue = accountValues[0];
            if (!baseValue || baseValue === 0) return null;

            const normalizedValues = accountValues.map(v => (v / baseValue) * 100);
            return normalizedValues;
        }}

        // Update stats display
        function updateStats() {{
            if (!data.latest) return;

            document.getElementById('lastUpdate').textContent = formatDisplayDate(data.latest.date);

            let indexValue = data.latest.indexValue;
            let totalReturn = data.latest.totalReturn;

            // Calculate per-account stats if an account is selected
            if (selectedAccount !== null) {{
                // Check if account has data in latest snapshot
                const latestAccountPct = data.latest.total_by_account?.[selectedAccount];
                if (!latestAccountPct || latestAccountPct === 0) {{
                    // Account has no current positions - show N/A
                    document.getElementById('indexValue').textContent = 'N/A';
                    document.getElementById('totalReturn').textContent = 'No positions';
                    document.getElementById('totalReturn').className = '';
                    return;
                }}

                const accountIndexValues = calculateAccountIndex(selectedAccount);
                if (accountIndexValues && accountIndexValues.length > 0) {{
                    indexValue = accountIndexValues[accountIndexValues.length - 1];
                    totalReturn = indexValue - 100;
                }}
            }}

            document.getElementById('indexValue').textContent = indexValue.toFixed(2);

            const totalReturnEl = document.getElementById('totalReturn');
            if (totalReturn !== null) {{
                const sign = totalReturn >= 0 ? '+' : '';
                totalReturnEl.textContent = sign + totalReturn.toFixed(2) + '%';
                totalReturnEl.className = 'stat-value ' + (totalReturn >= 0 ? 'positive' : 'negative');
            }}

            // Calculate invested % for selected account
            let investedPct = data.latest.investedPct;
            let investedLabelText = 'Invested';
            if (selectedAccount !== null) {{
                // Use totalByAccount to get true account total (includes hidden options)
                const accountTotal = data.latest.totalByAccount?.[selectedAccount] || 0;
                const cashPct = data.latest.cashByAccount?.[selectedAccount] || 0;
                // Invested = total - cash (includes visible positions + hidden options)
                investedPct = accountTotal > 0 ? ((accountTotal - cashPct) / accountTotal) * 100 : 0;
            }}
            document.getElementById('investedPct').textContent = investedPct.toFixed(1) + '%';
            document.getElementById('investedLabel').textContent = investedLabelText;
        }}

        // Update positions table
        function updatePositionsTable() {{
            const tbody = document.getElementById('positionsTable');
            tbody.innerHTML = '';

            const positions = getFilteredPositions();
            positions.forEach(pos => {{
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
        }}

        // Update allocation chart
        function updateAllocationChart() {{
            const positions = getFilteredPositions();
            allocationChart.data.labels = positions.map(p => p.symbol);
            allocationChart.data.datasets[0].data = positions.map(p => p.pct);
            allocationChart.data.datasets[0].backgroundColor = pieColors.slice(0, positions.length);
            allocationChart.update();
        }}

        // Update region chart
        function updateRegionChart() {{
            const regions = getFilteredRegionalAllocation();
            regionChart.data.labels = regions.map(r => r.region);
            regionChart.data.datasets[0].data = regions.map(r => r.pct);
            regionChart.data.datasets[0].backgroundColor = regions.map(r => r.color);
            regionChart.update();
        }}

        // Compute allocation history data for selected account
        function computeAllocationHistoryData() {{
            const snapshots = data.snapshots || [];
            if (snapshots.length === 0) return {{ topSymbols: [], series: {{}}, otherStocksPcts: [], otherPcts: [], cashPcts: [] }};

            // Get symbol totals across all snapshots (filtered by account)
            const symbolTotals = {{}};
            snapshots.forEach(snap => {{
                let positions = snap.positions;
                if (selectedAccount !== null) {{
                    positions = positions.filter(p => p.account_id === selectedAccount);
                }}
                positions.forEach(p => {{
                    symbolTotals[p.symbol] = (symbolTotals[p.symbol] || 0) + p.pct;
                }});
            }});

            // Get top 6 symbols
            const topSymbols = Object.keys(symbolTotals)
                .sort((a, b) => symbolTotals[b] - symbolTotals[a])
                .slice(0, 6);

            // Build series for each symbol
            const series = {{}};
            topSymbols.forEach(symbol => {{ series[symbol] = []; }});
            const otherPositionsPcts = [];
            const cashPcts = [];

            snapshots.forEach(snap => {{
                let positions = snap.positions;
                let cashPct = snap.cash_pct;
                let total = 100;  // Default for "All" view

                if (selectedAccount !== null) {{
                    positions = positions.filter(p => p.account_id === selectedAccount);
                    cashPct = snap.cash_by_account?.[selectedAccount] || 0;
                    // Use total_by_account to get true account total (includes hidden options)
                    total = snap.total_by_account?.[selectedAccount] || 0;
                }}

                const allPositionsPct = positions.reduce((s, p) => s + p.pct, 0);

                const posMap = {{}};
                positions.forEach(p => {{
                    posMap[p.symbol] = (posMap[p.symbol] || 0) + p.pct;
                }});

                let topSum = 0;
                topSymbols.forEach(symbol => {{
                    const pct = posMap[symbol] || 0;
                    topSum += pct;
                    series[symbol].push(total > 0 ? (pct / total) * 100 : 0);
                }});

                // Other positions = account total - top symbols - cash
                // This includes remaining visible positions + hidden options
                const otherPositionsPct = total - topSum - cashPct;
                otherPositionsPcts.push(total > 0 ? Math.max(0, (otherPositionsPct / total) * 100) : 0);
                cashPcts.push(total > 0 ? (cashPct / total) * 100 : 0);
            }});

            return {{ topSymbols, series, otherPositionsPcts, cashPcts }};
        }}

        // Compute regional history data for selected account
        function computeRegionalHistoryData() {{
            const snapshots = data.snapshots || [];
            if (snapshots.length === 0) return {{ regions: [], series: {{}}, cashPcts: [] }};

            // Get all regions
            const allRegions = new Set();
            snapshots.forEach(snap => {{
                let positions = snap.positions;
                if (selectedAccount !== null) {{
                    positions = positions.filter(p => p.account_id === selectedAccount);
                }}
                positions.forEach(p => allRegions.add(getRegion(p.symbol)));
            }});

            const regions = Array.from(allRegions).sort();
            const series = {{}};
            regions.forEach(r => {{ series[r] = []; }});
            const cashPcts = [];

            snapshots.forEach(snap => {{
                let positions = snap.positions;
                let cashPct = snap.cash_pct;
                let total = 100;  // Default for "All" view

                if (selectedAccount !== null) {{
                    positions = positions.filter(p => p.account_id === selectedAccount);
                    cashPct = snap.cash_by_account?.[selectedAccount] || 0;
                    // Use total_by_account to get true account total (includes hidden options)
                    total = snap.total_by_account?.[selectedAccount] || 0;
                }}

                // Calculate region totals
                const regionTotals = {{}};
                positions.forEach(p => {{
                    const region = getRegion(p.symbol);
                    regionTotals[region] = (regionTotals[region] || 0) + p.pct;
                }});

                // Add hidden options to US region (they're US-based options)
                const visiblePct = positions.reduce((s, p) => s + p.pct, 0);
                const hiddenPct = Math.max(0, total - visiblePct - cashPct);
                if (hiddenPct > 0) {{
                    regionTotals['US'] = (regionTotals['US'] || 0) + hiddenPct;
                }}

                regions.forEach(region => {{
                    const pct = regionTotals[region] || 0;
                    series[region].push(total > 0 ? (pct / total) * 100 : 0);
                }});
                cashPcts.push(total > 0 ? (cashPct / total) * 100 : 0);
            }});

            return {{ regions, series, cashPcts }};
        }}

        // Update allocation history chart
        function updateAllocationHistoryChart() {{
            const histData = computeAllocationHistoryData();
            const datasets = [];
            let colorIdx = 0;

            histData.topSymbols.forEach(symbol => {{
                datasets.push({{
                    label: symbol,
                    data: histData.series[symbol],
                    backgroundColor: pieColors[colorIdx % pieColors.length],
                    fill: true,
                    tension: 0.3,
                }});
                colorIdx++;
            }});
            datasets.push({{
                label: 'Other Positions',
                data: histData.otherPositionsPcts,
                backgroundColor: '#64748b',
                fill: true,
                tension: 0.3,
            }});
            datasets.push({{
                label: 'Cash',
                data: histData.cashPcts,
                backgroundColor: '#22c55e',
                fill: true,
                tension: 0.3,
            }});

            allocationHistoryChart.data.datasets = datasets;
            allocationHistoryChart.update();
        }}

        // Update regional history chart
        function updateRegionalHistoryChart() {{
            const histData = computeRegionalHistoryData();
            const datasets = [];

            histData.regions.forEach(region => {{
                datasets.push({{
                    label: region,
                    data: histData.series[region],
                    backgroundColor: regionColorMap[region] || '#64748b',
                    fill: true,
                    tension: 0.3,
                }});
            }});
            datasets.push({{
                label: 'Cash',
                data: histData.cashPcts,
                backgroundColor: '#22c55e',
                fill: true,
                tension: 0.3,
            }});

            regionHistoryChart.data.datasets = datasets;
            regionHistoryChart.update();
        }}

        // Update index chart for selected account
        function updateIndexChart() {{
            if (!indexChart) return;

            let portfolioData;
            let label;
            if (selectedAccount === null) {{
                portfolioData = data.indexValues;
                label = 'Portfolio';
            }} else {{
                const accountIndex = calculateAccountIndex(selectedAccount);
                portfolioData = accountIndex || data.indexValues;
                label = selectedAccount;
            }}

            indexChart.data.datasets[0].data = portfolioData;
            indexChart.data.datasets[0].label = label;
            indexChart.update();
        }}

        // Update all views
        function updateAllViews() {{
            updateStats();
            updatePositionsTable();
            updateIndexChart();
            updateAllocationChart();
            updateRegionChart();
            updateAllocationHistoryChart();
            updateRegionalHistoryChart();
        }}

        // Initialize charts
        function initCharts() {{
            // Index Chart with benchmark comparison
            const indexDatasets = [{{
                label: 'Portfolio',
                data: data.indexValues,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: false,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6,
                borderWidth: 3,
            }}];

            // Add SPY benchmark if available
            if (data.benchmarks && data.benchmarks.SPY) {{
                indexDatasets.push({{
                    label: 'SPY',
                    data: data.benchmarks.SPY,
                    borderColor: '#22c55e',
                    backgroundColor: 'transparent',
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    borderWidth: 2,
                    borderDash: [5, 5],
                }});
            }}

            // Add QQQ benchmark if available
            if (data.benchmarks && data.benchmarks.QQQ) {{
                indexDatasets.push({{
                    label: 'QQQ',
                    data: data.benchmarks.QQQ,
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    fill: false,
                    tension: 0.3,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    borderWidth: 2,
                    borderDash: [2, 2],
                }});
            }}

            indexChart = new Chart(document.getElementById('indexChart'), {{
                type: 'line',
                data: {{
                    labels: data.dates,
                    datasets: indexDatasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top',
                            labels: {{ usePointStyle: true }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2)
                            }}
                        }}
                    }},
                    scales: {{ y: {{ beginAtZero: false }} }}
                }}
            }});


            // Allocation Bar Chart (filtered by account)
            allocationChart = new Chart(document.getElementById('allocationChart'), {{
                type: 'bar',
                data: {{
                    labels: data.currentAllocation.map(p => p.symbol),
                    datasets: [{{
                        data: data.currentAllocation.map(p => p.pct),
                        backgroundColor: pieColors.slice(0, data.currentAllocation.length),
                        borderRadius: 4,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{ callback: v => v + '%' }}
                        }}
                    }}
                }}
            }});

            // Allocation History (filtered by account)
            allocationHistoryChart = new Chart(document.getElementById('allocationHistoryChart'), {{
                type: 'line',
                data: {{ labels: data.dates, datasets: [] }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{ position: 'bottom' }},
                        tooltip: {{
                            callbacks: {{
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{ stacked: true, max: 100, ticks: {{ callback: v => v + '%' }} }},
                        x: {{ stacked: true }}
                    }}
                }}
            }});
            updateAllocationHistoryChart();

            // Regional Allocation Bar Chart (filtered by account)
            regionChart = new Chart(document.getElementById('regionChart'), {{
                type: 'bar',
                data: {{
                    labels: data.regionalAllocation.map(r => r.region),
                    datasets: [{{
                        data: data.regionalAllocation.map(r => r.pct),
                        backgroundColor: data.regionalAllocation.map(r => r.color),
                        borderRadius: 4,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{ callback: v => v + '%' }}
                        }}
                    }}
                }}
            }});

            // Regional History (filtered by account)
            regionHistoryChart = new Chart(document.getElementById('regionHistoryChart'), {{
                type: 'line',
                data: {{ labels: data.dates, datasets: [] }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{ position: 'bottom' }},
                        tooltip: {{
                            callbacks: {{
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{ stacked: true, max: 100, ticks: {{ callback: v => v + '%' }} }},
                        x: {{ stacked: true }}
                    }}
                }}
            }});
            updateRegionalHistoryChart();
        }}

        // Initialize everything
        initAccountSelector();
        initCharts();
        updateStats();
        updatePositionsTable();
    </script>
</body>
</html>'''

    return html


def _mask_account_ids(history_dict: dict) -> dict:
    """Mask real account IDs with generic names (Account A, Account B, etc.)."""
    import copy
    result = copy.deepcopy(history_dict)

    # Collect all unique account IDs
    all_accounts = set()
    for snap in result.get("snapshots", []):
        all_accounts.update(snap.get("accounts", []))
        for pos in snap.get("positions", []):
            if pos.get("account_id"):
                all_accounts.add(pos["account_id"])

    # Create mapping
    account_mask = {acc: f"Account {chr(65 + i)}" for i, acc in enumerate(sorted(all_accounts))}

    # Apply masking
    for snap in result.get("snapshots", []):
        # Mask accounts list
        if "accounts" in snap:
            snap["accounts"] = [account_mask.get(a, a) for a in snap["accounts"]]

        # Mask position account_ids
        for pos in snap.get("positions", []):
            if pos.get("account_id"):
                pos["account_id"] = account_mask.get(pos["account_id"], pos["account_id"])

        # Mask cash_by_account keys
        if "cash_by_account" in snap:
            snap["cash_by_account"] = {
                account_mask.get(k, k): v for k, v in snap["cash_by_account"].items()
            }

        # Mask total_by_account keys (keeps total per account for calculating "Other")
        if "total_by_account" in snap:
            snap["total_by_account"] = {
                account_mask.get(k, k): v for k, v in snap["total_by_account"].items()
            }

        # Remove other_by_account to not expose options allocation
        if "other_by_account" in snap:
            del snap["other_by_account"]
        if "other_pct" in snap:
            del snap["other_pct"]

    return result


def generate_site(history: PortfolioHistory) -> Path:
    """Generate the static HTML site."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    html = _generate_html(history)

    index_path = SITE_DIR / "index.html"
    with open(index_path, "w") as f:
        f.write(html)

    # Also save the public data as JSON for potential API use (with masked account IDs)
    data_path = SITE_DIR / "data.json"
    masked_data = _mask_account_ids(history.to_dict())
    with open(data_path, "w") as f:
        json.dump(masked_data, f, indent=2)

    return SITE_DIR
