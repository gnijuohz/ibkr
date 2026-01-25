"""Portfolio data models and privacy transformations."""

from dataclasses import dataclass, field
from typing import Optional

from .flex_client import PortfolioSnapshot, Position


# Asset categories to hide (aggregate as "Other Positions")
HIDDEN_CATEGORIES = {"OPT", "FOP", "WAR"}  # Options, Futures Options, Warrants


@dataclass
class PublicPosition:
    """A privacy-safe position showing only percentages."""
    symbol: str
    allocation_pct: float  # Percentage of total portfolio

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "allocation_pct": round(self.allocation_pct, 2),
        }


@dataclass
class PublicSnapshot:
    """A privacy-safe portfolio snapshot with only percentages."""
    date: str
    positions: list[PublicPosition]
    cash_pct: float
    other_pct: float  # Hidden positions (options, etc.)
    invested_pct: float  # Total % in market (100 - cash_pct)
    index_value: float  # Portfolio value as index (baseline 100)
    period_return_pct: Optional[float] = None  # Return since last snapshot
    total_return_pct: Optional[float] = None  # Return since inception

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "positions": [p.to_dict() for p in self.positions],
            "cash_pct": round(self.cash_pct, 2),
            "other_pct": round(self.other_pct, 2),
            "invested_pct": round(self.invested_pct, 2),
            "index_value": round(self.index_value, 2),
            "period_return_pct": round(self.period_return_pct, 2) if self.period_return_pct is not None else None,
            "total_return_pct": round(self.total_return_pct, 2) if self.total_return_pct is not None else None,
        }


@dataclass
class PortfolioHistory:
    """Historical portfolio data with baseline indexing."""
    snapshots: list[PublicSnapshot] = field(default_factory=list)
    baseline_value: Optional[float] = None  # First portfolio value (private, for index calculation)

    def to_dict(self) -> dict:
        return {
            "snapshots": [s.to_dict() for s in self.snapshots],
            # Note: baseline_value is intentionally NOT exported (it's the actual $ value)
        }


def transform_to_public(
    snapshot: PortfolioSnapshot,
    baseline_value: Optional[float] = None,
    previous_value: Optional[float] = None,
) -> tuple[PublicSnapshot, float]:
    """
    Transform a private portfolio snapshot to a public one.

    Returns:
        Tuple of (PublicSnapshot, actual_total_value)
        The actual_total_value is returned for internal tracking but should never be displayed.
    """
    total_value = snapshot.total_value

    if total_value == 0:
        # Avoid division by zero
        return PublicSnapshot(
            date=snapshot.date,
            positions=[],
            cash_pct=0,
            other_pct=0,
            invested_pct=0,
            index_value=100 if baseline_value is None else 0,
        ), 0

    # Separate visible and hidden positions
    visible_positions: list[PublicPosition] = []
    hidden_value = 0.0

    for pos in snapshot.positions:
        if pos.asset_category in HIDDEN_CATEGORIES:
            hidden_value += pos.market_value
        else:
            pct = (pos.market_value / total_value) * 100
            if pct >= 0.1:  # Only show positions >= 0.1%
                visible_positions.append(PublicPosition(
                    symbol=pos.symbol,
                    allocation_pct=pct,
                ))

    # Sort by allocation (largest first)
    visible_positions.sort(key=lambda p: p.allocation_pct, reverse=True)

    # Calculate percentages
    cash_pct = (snapshot.cash_balance / total_value) * 100
    other_pct = (hidden_value / total_value) * 100
    invested_pct = 100 - cash_pct

    # Calculate index value (baseline 100)
    if baseline_value is None:
        index_value = 100.0
    else:
        index_value = (total_value / baseline_value) * 100

    # Calculate returns
    period_return_pct = None
    total_return_pct = None

    if previous_value is not None and previous_value > 0:
        period_return_pct = ((total_value - previous_value) / previous_value) * 100

    if baseline_value is not None and baseline_value > 0:
        total_return_pct = ((total_value - baseline_value) / baseline_value) * 100

    public_snapshot = PublicSnapshot(
        date=snapshot.date,
        positions=visible_positions,
        cash_pct=cash_pct,
        other_pct=other_pct,
        invested_pct=invested_pct,
        index_value=index_value,
        period_return_pct=period_return_pct,
        total_return_pct=total_return_pct,
    )

    return public_snapshot, total_value
