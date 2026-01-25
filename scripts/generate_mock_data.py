#!/usr/bin/env python3
"""Generate mock portfolio data for testing and preview."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.portfolio import PublicSnapshot, PublicPosition, PortfolioHistory
from src.storage import save_history, HISTORY_FILE
from src.config import DATA_DIR

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Mock data: 12 months of portfolio snapshots
mock_snapshots = [
    # Month 1 - Starting point (baseline)
    PublicSnapshot(
        date="20250101",
        positions=[
            PublicPosition("AAPL", 18.5),
            PublicPosition("MSFT", 15.2),
            PublicPosition("GOOGL", 12.0),
            PublicPosition("AMZN", 8.5),
            PublicPosition("NVDA", 7.3),
            PublicPosition("META", 5.5),
        ],
        cash_pct=25.0,
        other_pct=8.0,  # Options
        invested_pct=75.0,
        index_value=100.0,
        period_return_pct=None,
        total_return_pct=None,
    ),
    # Month 2
    PublicSnapshot(
        date="20250201",
        positions=[
            PublicPosition("AAPL", 19.2),
            PublicPosition("MSFT", 14.8),
            PublicPosition("GOOGL", 11.5),
            PublicPosition("AMZN", 9.0),
            PublicPosition("NVDA", 8.5),
            PublicPosition("META", 5.0),
        ],
        cash_pct=23.0,
        other_pct=9.0,
        invested_pct=77.0,
        index_value=103.2,
        period_return_pct=3.2,
        total_return_pct=3.2,
    ),
    # Month 3
    PublicSnapshot(
        date="20250301",
        positions=[
            PublicPosition("AAPL", 17.8),
            PublicPosition("MSFT", 15.5),
            PublicPosition("GOOGL", 10.2),
            PublicPosition("AMZN", 8.8),
            PublicPosition("NVDA", 10.2),
            PublicPosition("META", 5.5),
        ],
        cash_pct=22.0,
        other_pct=10.0,
        invested_pct=78.0,
        index_value=101.5,
        period_return_pct=-1.65,
        total_return_pct=1.5,
    ),
    # Month 4
    PublicSnapshot(
        date="20250401",
        positions=[
            PublicPosition("AAPL", 16.5),
            PublicPosition("MSFT", 16.0),
            PublicPosition("GOOGL", 9.8),
            PublicPosition("AMZN", 9.2),
            PublicPosition("NVDA", 12.5),
            PublicPosition("META", 4.5),
        ],
        cash_pct=20.0,
        other_pct=11.5,
        invested_pct=80.0,
        index_value=108.7,
        period_return_pct=7.09,
        total_return_pct=8.7,
    ),
    # Month 5
    PublicSnapshot(
        date="20250501",
        positions=[
            PublicPosition("AAPL", 15.8),
            PublicPosition("MSFT", 16.5),
            PublicPosition("GOOGL", 9.5),
            PublicPosition("AMZN", 9.8),
            PublicPosition("NVDA", 14.2),
            PublicPosition("META", 4.2),
        ],
        cash_pct=18.0,
        other_pct=12.0,
        invested_pct=82.0,
        index_value=112.3,
        period_return_pct=3.31,
        total_return_pct=12.3,
    ),
    # Month 6
    PublicSnapshot(
        date="20250601",
        positions=[
            PublicPosition("AAPL", 14.5),
            PublicPosition("MSFT", 17.2),
            PublicPosition("GOOGL", 8.8),
            PublicPosition("AMZN", 10.5),
            PublicPosition("NVDA", 15.8),
            PublicPosition("META", 3.8),
        ],
        cash_pct=17.0,
        other_pct=12.4,
        invested_pct=83.0,
        index_value=115.8,
        period_return_pct=3.12,
        total_return_pct=15.8,
    ),
    # Month 7 - Small pullback
    PublicSnapshot(
        date="20250701",
        positions=[
            PublicPosition("AAPL", 14.2),
            PublicPosition("MSFT", 16.8),
            PublicPosition("GOOGL", 9.0),
            PublicPosition("AMZN", 10.2),
            PublicPosition("NVDA", 14.5),
            PublicPosition("META", 4.0),
        ],
        cash_pct=19.0,
        other_pct=12.3,
        invested_pct=81.0,
        index_value=111.2,
        period_return_pct=-3.97,
        total_return_pct=11.2,
    ),
    # Month 8
    PublicSnapshot(
        date="20250801",
        positions=[
            PublicPosition("AAPL", 15.0),
            PublicPosition("MSFT", 17.5),
            PublicPosition("GOOGL", 9.2),
            PublicPosition("AMZN", 11.0),
            PublicPosition("NVDA", 13.8),
            PublicPosition("META", 4.5),
        ],
        cash_pct=17.0,
        other_pct=12.0,
        invested_pct=83.0,
        index_value=118.5,
        period_return_pct=6.56,
        total_return_pct=18.5,
    ),
    # Month 9
    PublicSnapshot(
        date="20250901",
        positions=[
            PublicPosition("AAPL", 14.8),
            PublicPosition("MSFT", 18.2),
            PublicPosition("GOOGL", 8.5),
            PublicPosition("AMZN", 11.5),
            PublicPosition("NVDA", 14.5),
            PublicPosition("TSLA", 3.5),
        ],
        cash_pct=16.0,
        other_pct=13.0,
        invested_pct=84.0,
        index_value=122.8,
        period_return_pct=3.63,
        total_return_pct=22.8,
    ),
    # Month 10
    PublicSnapshot(
        date="20251001",
        positions=[
            PublicPosition("AAPL", 13.5),
            PublicPosition("MSFT", 19.0),
            PublicPosition("GOOGL", 8.0),
            PublicPosition("AMZN", 12.2),
            PublicPosition("NVDA", 15.8),
            PublicPosition("TSLA", 4.0),
        ],
        cash_pct=14.0,
        other_pct=13.5,
        invested_pct=86.0,
        index_value=128.5,
        period_return_pct=4.64,
        total_return_pct=28.5,
    ),
    # Month 11 - Correction
    PublicSnapshot(
        date="20251101",
        positions=[
            PublicPosition("AAPL", 14.0),
            PublicPosition("MSFT", 18.5),
            PublicPosition("GOOGL", 8.2),
            PublicPosition("AMZN", 11.8),
            PublicPosition("NVDA", 13.5),
            PublicPosition("TSLA", 3.2),
        ],
        cash_pct=18.0,
        other_pct=12.8,
        invested_pct=82.0,
        index_value=119.2,
        period_return_pct=-7.24,
        total_return_pct=19.2,
    ),
    # Month 12 - Recovery
    PublicSnapshot(
        date="20251201",
        positions=[
            PublicPosition("AAPL", 14.5),
            PublicPosition("MSFT", 19.2),
            PublicPosition("GOOGL", 8.5),
            PublicPosition("AMZN", 12.5),
            PublicPosition("NVDA", 14.8),
            PublicPosition("TSLA", 3.5),
        ],
        cash_pct=15.0,
        other_pct=12.0,
        invested_pct=85.0,
        index_value=125.8,
        period_return_pct=5.54,
        total_return_pct=25.8,
    ),
]

# Create history
history = PortfolioHistory(snapshots=mock_snapshots)

# Save with mock baseline (we use 100000 as a fake starting value)
# This value is private and never displayed
mock_baseline = 100000.0
mock_last_value = mock_baseline * (mock_snapshots[-1].index_value / 100)

save_history(history, mock_baseline, mock_last_value)

print(f"Generated {len(mock_snapshots)} months of mock data")
print(f"Saved to: {HISTORY_FILE}")
print(f"\nLatest snapshot:")
print(f"  Date: {mock_snapshots[-1].date}")
print(f"  Index: {mock_snapshots[-1].index_value}")
print(f"  Total Return: {mock_snapshots[-1].total_return_pct}%")
