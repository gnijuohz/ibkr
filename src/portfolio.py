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
    account_id: str = ""

    def to_dict(self) -> dict:
        result = {
            "symbol": self.symbol,
            "allocation_pct": round(self.allocation_pct, 2),
        }
        if self.account_id:
            result["account_id"] = self.account_id
        return result


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
    accounts: list[str] = None  # List of account IDs
    cash_by_account: dict[str, float] = None  # account_id -> cash percentage
    other_by_account: dict[str, float] = None  # account_id -> other percentage
    total_by_account: dict[str, float] = None  # account_id -> total percentage (for calculating other without exposing it)

    def __post_init__(self):
        if self.accounts is None:
            self.accounts = []
        if self.cash_by_account is None:
            self.cash_by_account = {}
        if self.other_by_account is None:
            self.other_by_account = {}
        if self.total_by_account is None:
            self.total_by_account = {}

    def to_dict(self) -> dict:
        result = {
            "date": self.date,
            "positions": [p.to_dict() for p in self.positions],
            "cash_pct": round(self.cash_pct, 2),
            "other_pct": round(self.other_pct, 2),
            "invested_pct": round(self.invested_pct, 2),
            "index_value": round(self.index_value, 2),
            "period_return_pct": round(self.period_return_pct, 2) if self.period_return_pct is not None else None,
            "total_return_pct": round(self.total_return_pct, 2) if self.total_return_pct is not None else None,
        }
        if self.accounts:
            result["accounts"] = self.accounts
            result["cash_by_account"] = {k: round(v, 2) for k, v in self.cash_by_account.items()}
            result["other_by_account"] = {k: round(v, 2) for k, v in self.other_by_account.items()}
            result["total_by_account"] = {k: round(v, 2) for k, v in self.total_by_account.items()}
        return result


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
    hidden_by_account: dict[str, float] = {}

    # Collect all account IDs
    account_ids = set()
    for pos in snapshot.positions:
        if pos.account_id:
            account_ids.add(pos.account_id)

    for pos in snapshot.positions:
        if pos.asset_category in HIDDEN_CATEGORIES:
            hidden_value += pos.market_value
            if pos.account_id:
                hidden_by_account[pos.account_id] = hidden_by_account.get(pos.account_id, 0) + pos.market_value
        else:
            pct = (pos.market_value / total_value) * 100
            if pct >= 0.1:  # Only show positions >= 0.1%
                visible_positions.append(PublicPosition(
                    symbol=pos.symbol,
                    allocation_pct=pct,
                    account_id=pos.account_id,
                ))

    # Sort by allocation (largest first)
    visible_positions.sort(key=lambda p: p.allocation_pct, reverse=True)

    # Calculate percentages
    cash_pct = (snapshot.cash_balance / total_value) * 100
    other_pct = (hidden_value / total_value) * 100
    invested_pct = 100 - cash_pct

    # Calculate per-account percentages
    cash_by_account = {}
    for acc_id, cash in snapshot.cash_by_account.items():
        cash_by_account[acc_id] = (cash / total_value) * 100
        account_ids.add(acc_id)

    other_by_account = {}
    for acc_id, hidden in hidden_by_account.items():
        other_by_account[acc_id] = (hidden / total_value) * 100

    # Calculate total per account (positions + cash + hidden)
    # This allows calculating "Other" without exposing the specific hidden amount
    total_by_account: dict[str, float] = {}
    positions_by_account: dict[str, float] = {}
    for pos in snapshot.positions:
        if pos.account_id:
            positions_by_account[pos.account_id] = positions_by_account.get(pos.account_id, 0) + pos.market_value

    for acc_id in account_ids:
        acc_positions = positions_by_account.get(acc_id, 0)
        acc_cash = snapshot.cash_by_account.get(acc_id, 0)
        acc_total = acc_positions + acc_cash
        total_by_account[acc_id] = (acc_total / total_value) * 100

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
        accounts=sorted(account_ids),
        cash_by_account=cash_by_account,
        other_by_account=other_by_account,
        total_by_account=total_by_account,
    )

    return public_snapshot, total_value
