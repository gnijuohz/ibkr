"""Chart generation for portfolio visualization."""

from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .config import OUTPUT_DIR
from .portfolio import PortfolioHistory, PublicSnapshot


def _parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    # Handle common IBKR date formats
    for fmt in ["%Y%m%d", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")


def generate_index_chart(history: PortfolioHistory, output_path: Path | None = None) -> Path:
    """
    Generate a chart showing portfolio value as an index (baseline 100).

    This chart shows portfolio performance over time without revealing actual values.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "portfolio_index.png"

    if len(history.snapshots) < 1:
        raise ValueError("Need at least 1 snapshot to generate chart")

    dates = [_parse_date(s.date) for s in history.snapshots]
    values = [s.index_value for s in history.snapshots]

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(dates, values, marker="o", linewidth=2, markersize=6, color="#2563eb")
    ax.axhline(y=100, color="#94a3b8", linestyle="--", linewidth=1, label="Baseline (100)")

    # Fill above/below baseline
    ax.fill_between(dates, values, 100, where=[v >= 100 for v in values],
                    alpha=0.3, color="#22c55e", interpolate=True)
    ax.fill_between(dates, values, 100, where=[v < 100 for v in values],
                    alpha=0.3, color="#ef4444", interpolate=True)

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Index Value (Baseline = 100)", fontsize=12)
    ax.set_title("Portfolio Performance Index", fontsize=14, fontweight="bold")

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45, ha="right")

    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def generate_allocation_chart(snapshot: PublicSnapshot, output_path: Path | None = None) -> Path:
    """
    Generate a pie chart showing current portfolio allocation.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / f"allocation_{snapshot.date}.png"

    # Prepare data
    labels = []
    sizes = []
    colors = []

    # Color palette
    position_colors = plt.cm.Blues(range(50, 250, 25))
    color_idx = 0

    # Add positions
    for pos in snapshot.positions[:10]:  # Top 10 positions
        labels.append(pos.symbol)
        sizes.append(pos.allocation_pct)
        colors.append(position_colors[color_idx % len(position_colors)])
        color_idx += 1

    # Add "Other Positions" if exists
    if snapshot.other_pct > 0:
        labels.append("Other Positions")
        sizes.append(snapshot.other_pct)
        colors.append("#94a3b8")

    # Add remaining small positions
    shown_pct = sum(sizes)
    remaining = snapshot.invested_pct - shown_pct
    if remaining > 0.5:
        labels.append("Other Stocks")
        sizes.append(remaining)
        colors.append("#cbd5e1")

    # Add cash
    if snapshot.cash_pct > 0:
        labels.append("Cash")
        sizes.append(snapshot.cash_pct)
        colors.append("#22c55e")

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 2 else "",
        colors=colors,
        startangle=90,
        pctdistance=0.75,
    )

    # Style
    for autotext in autotexts:
        autotext.set_fontsize(9)

    ax.set_title(f"Portfolio Allocation - {snapshot.date}", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def generate_allocation_history_chart(history: PortfolioHistory, output_path: Path | None = None) -> Path:
    """
    Generate a stacked area chart showing allocation changes over time.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "allocation_history.png"

    if len(history.snapshots) < 2:
        raise ValueError("Need at least 2 snapshots for allocation history")

    dates = [_parse_date(s.date) for s in history.snapshots]

    # Track top symbols across all snapshots
    symbol_totals: dict[str, float] = {}
    for snapshot in history.snapshots:
        for pos in snapshot.positions:
            symbol_totals[pos.symbol] = symbol_totals.get(pos.symbol, 0) + pos.allocation_pct

    # Get top 5 symbols by total allocation over time
    top_symbols = sorted(symbol_totals.keys(), key=lambda s: symbol_totals[s], reverse=True)[:5]

    # Build data series
    series_data: dict[str, list[float]] = {symbol: [] for symbol in top_symbols}
    series_data["Other Stocks"] = []
    series_data["Other Positions"] = []
    series_data["Cash"] = []

    for snapshot in history.snapshots:
        symbol_map = {p.symbol: p.allocation_pct for p in snapshot.positions}

        for symbol in top_symbols:
            series_data[symbol].append(symbol_map.get(symbol, 0))

        # Calculate "Other Stocks"
        top_pct = sum(symbol_map.get(s, 0) for s in top_symbols)
        other_stocks = snapshot.invested_pct - top_pct - snapshot.other_pct
        series_data["Other Stocks"].append(max(0, other_stocks))
        series_data["Other Positions"].append(snapshot.other_pct)
        series_data["Cash"].append(snapshot.cash_pct)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Create stacked area chart
    labels = top_symbols + ["Other Stocks", "Other Positions", "Cash"]
    colors = list(plt.cm.Blues(range(50, 200, 30))[:len(top_symbols)]) + ["#cbd5e1", "#94a3b8", "#22c55e"]

    ax.stackplot(
        dates,
        [series_data[label] for label in labels],
        labels=labels,
        colors=colors,
        alpha=0.8,
    )

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Allocation (%)", fontsize=12)
    ax.set_title("Portfolio Allocation Over Time", fontsize=14, fontweight="bold")

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45, ha="right")

    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    return output_path


def generate_returns_chart(history: PortfolioHistory, output_path: Path | None = None) -> Path:
    """
    Generate a bar chart showing monthly returns.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "monthly_returns.png"

    # Skip first snapshot (no return data)
    snapshots_with_returns = [s for s in history.snapshots if s.period_return_pct is not None]

    if len(snapshots_with_returns) < 1:
        raise ValueError("Need at least 1 snapshot with return data")

    dates = [_parse_date(s.date) for s in snapshots_with_returns]
    returns = [s.period_return_pct for s in snapshots_with_returns]

    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#22c55e" if r >= 0 else "#ef4444" for r in returns]
    bars = ax.bar(dates, returns, color=colors, width=20, alpha=0.8)

    ax.axhline(y=0, color="#1e293b", linewidth=1)

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Return (%)", fontsize=12)
    ax.set_title("Monthly Returns", fontsize=14, fontweight="bold")

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45, ha="right")

    ax.grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for bar, ret in zip(bars, returns):
        height = bar.get_height()
        ax.annotate(
            f"{ret:+.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3 if height >= 0 else -12),
            textcoords="offset points",
            ha="center",
            va="bottom" if height >= 0 else "top",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def generate_all_charts(history: PortfolioHistory) -> list[Path]:
    """Generate all available charts and return paths."""
    paths = []

    try:
        paths.append(generate_index_chart(history))
    except ValueError as e:
        print(f"Skipping index chart: {e}")

    if history.snapshots:
        paths.append(generate_allocation_chart(history.snapshots[-1]))

    try:
        paths.append(generate_allocation_history_chart(history))
    except ValueError as e:
        print(f"Skipping allocation history: {e}")

    try:
        paths.append(generate_returns_chart(history))
    except ValueError as e:
        print(f"Skipping returns chart: {e}")

    return paths
