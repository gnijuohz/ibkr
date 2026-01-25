"""Historical data storage for portfolio snapshots."""

import json
from pathlib import Path
from typing import Optional

from .config import HISTORY_FILE, DATA_DIR
from .portfolio import PublicSnapshot, PublicPosition, PortfolioHistory


# Private file storing actual values (for index calculation)
PRIVATE_DATA_FILE = DATA_DIR / ".private_values.json"


def load_history() -> tuple[PortfolioHistory, Optional[float], Optional[float]]:
    """
    Load portfolio history from storage.

    Returns:
        Tuple of (PortfolioHistory, baseline_value, last_value)
        baseline_value and last_value are the actual $ values (private)
    """
    history = PortfolioHistory()
    baseline_value = None
    last_value = None

    # Load public history
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
            for snap_data in data.get("snapshots", []):
                positions = [
                    PublicPosition(
                        symbol=p["symbol"],
                        allocation_pct=p["allocation_pct"],
                    )
                    for p in snap_data.get("positions", [])
                ]
                snapshot = PublicSnapshot(
                    date=snap_data["date"],
                    positions=positions,
                    cash_pct=snap_data["cash_pct"],
                    other_pct=snap_data["other_pct"],
                    invested_pct=snap_data["invested_pct"],
                    index_value=snap_data["index_value"],
                    period_return_pct=snap_data.get("period_return_pct"),
                    total_return_pct=snap_data.get("total_return_pct"),
                )
                history.snapshots.append(snapshot)

    # Load private values (only stored locally, never shared)
    if PRIVATE_DATA_FILE.exists():
        with open(PRIVATE_DATA_FILE, "r") as f:
            private_data = json.load(f)
            baseline_value = private_data.get("baseline_value")
            last_value = private_data.get("last_value")

    return history, baseline_value, last_value


def save_history(
    history: PortfolioHistory,
    baseline_value: float,
    last_value: float,
) -> None:
    """Save portfolio history to storage."""
    # Save public history (safe to share)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history.to_dict(), f, indent=2)

    # Save private values (never share!)
    with open(PRIVATE_DATA_FILE, "w") as f:
        json.dump({
            "baseline_value": baseline_value,
            "last_value": last_value,
        }, f, indent=2)


def export_public_history(output_path: Optional[Path] = None) -> Path:
    """
    Export only the public (safe to share) portfolio history.

    This file contains only percentages and index values, no actual dollar amounts.
    """
    if output_path is None:
        output_path = DATA_DIR / "portfolio_public.json"

    history, _, _ = load_history()

    with open(output_path, "w") as f:
        json.dump(history.to_dict(), f, indent=2)

    return output_path
