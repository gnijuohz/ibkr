#!/usr/bin/env python3
"""Generate mock portfolio data for testing and preview."""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.portfolio import PublicSnapshot, PublicPosition, PortfolioHistory
from src.storage import save_history, HISTORY_FILE
from src.config import DATA_DIR

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Seed for reproducibility
random.seed(42)


def generate_mock_data(num_snapshots: int = 20) -> list[PublicSnapshot]:
    """Generate realistic mock portfolio data with variable intervals."""

    # Starting positions
    positions = {
        "AAPL": 18.5,
        "MSFT": 15.2,
        "GOOGL": 12.0,
        "AMZN": 8.5,
        "NVDA": 7.3,
        "META": 5.5,
    }
    cash_pct = 25.0
    other_pct = 8.0  # Options/hidden
    index_value = 100.0

    snapshots = []

    # Start date - about 6 months ago
    current_date = datetime(2024, 7, 15)

    for i in range(num_snapshots):
        # Variable interval: 5-14 days (roughly weekly, but not exact)
        if i > 0:
            days_delta = random.randint(5, 14)
            current_date += timedelta(days=days_delta)

        # Calculate returns (random walk with slight upward bias)
        if i == 0:
            period_return = None
            total_return = None
        else:
            period_return = round(random.gauss(0.8, 2.5), 2)  # Mean +0.8%, std 2.5%
            index_value = round(index_value * (1 + period_return / 100), 2)
            total_return = round((index_value - 100), 2)

        # Evolve positions slightly
        for symbol in positions:
            change = random.gauss(0, 0.8)  # Small random changes
            positions[symbol] = max(0.5, positions[symbol] + change)

        # Occasionally add/remove a position
        if i > 5 and random.random() < 0.1:
            if "TSLA" not in positions:
                positions["TSLA"] = random.uniform(2, 5)
            elif random.random() < 0.3:
                del positions["TSLA"]

        # Normalize positions
        total_pos = sum(positions.values())
        invested_target = random.uniform(70, 88)
        scale = (invested_target - other_pct) / total_pos

        normalized = {k: round(v * scale, 2) for k, v in positions.items()}

        # Adjust cash
        cash_pct = round(100 - sum(normalized.values()) - other_pct, 2)
        invested_pct = round(100 - cash_pct, 2)

        # Small drift in other_pct (options)
        other_pct = round(max(5, min(15, other_pct + random.gauss(0, 0.5))), 2)

        # Create snapshot
        snapshot = PublicSnapshot(
            date=current_date.strftime("%Y%m%d"),
            positions=[PublicPosition(k, v) for k, v in sorted(normalized.items(), key=lambda x: -x[1])],
            cash_pct=cash_pct,
            other_pct=other_pct,
            invested_pct=invested_pct,
            index_value=index_value,
            period_return_pct=period_return,
            total_return_pct=total_return,
        )
        snapshots.append(snapshot)

    return snapshots


# Generate data
mock_snapshots = generate_mock_data(25)  # ~6 months of weekly-ish data

# Create history
history = PortfolioHistory(snapshots=mock_snapshots)

# Save with mock baseline
mock_baseline = 100000.0
mock_last_value = mock_baseline * (mock_snapshots[-1].index_value / 100)

save_history(history, mock_baseline, mock_last_value)

print(f"Generated {len(mock_snapshots)} snapshots with variable intervals")
print(f"Date range: {mock_snapshots[0].date} to {mock_snapshots[-1].date}")
print(f"Saved to: {HISTORY_FILE}")
print(f"\nLatest snapshot:")
print(f"  Date: {mock_snapshots[-1].date}")
print(f"  Index: {mock_snapshots[-1].index_value}")
print(f"  Total Return: {mock_snapshots[-1].total_return_pct}%")
