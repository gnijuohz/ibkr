"""IBKR Flex Web Service client."""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from .config import FLEX_TOKEN, FLEX_QUERY_ID, FLEX_REQUEST_URL, FLEX_STATEMENT_URL, DATA_DIR


@dataclass
class Position:
    """Represents a single position in the portfolio."""
    symbol: str
    description: str
    asset_category: str  # STK, OPT, FUT, CASH, BOND, etc.
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    currency: str = "USD"
    account_id: str = ""


@dataclass
class PortfolioSnapshot:
    """Represents a complete portfolio snapshot."""
    date: str
    positions: list[Position]
    cash_balance: float
    total_value: float
    currency: str = "USD"
    cash_by_account: dict[str, float] = None  # account_id -> cash balance

    def __post_init__(self):
        if self.cash_by_account is None:
            self.cash_by_account = {}


class FlexClientError(Exception):
    """Error from IBKR Flex Web Service."""
    pass


class FlexClient:
    """Client for IBKR Flex Web Service."""

    def __init__(self, token: Optional[str] = None, query_id: Optional[str] = None):
        self.token = token or FLEX_TOKEN
        self.query_id = query_id or FLEX_QUERY_ID

    def fetch_portfolio(self) -> PortfolioSnapshot:
        """Fetch current portfolio from IBKR Flex Web Service."""
        # Step 1: Request the report
        reference_code = self._request_report()

        # Step 2: Wait and fetch the statement
        statement_xml = self._fetch_statement(reference_code)

        # Step 3: Save raw XML for debugging
        self._save_raw_xml(statement_xml)

        # Step 4: Parse the XML into a PortfolioSnapshot
        return self._parse_statement(statement_xml)

    def _save_raw_xml(self, xml_text: str):
        """Save raw XML response to data/raw/ for future inspection."""
        raw_dir = DATA_DIR / "raw"
        raw_dir.mkdir(exist_ok=True)

        # Extract date from the XML to use as filename
        try:
            root = ET.fromstring(xml_text)
            stmt = root.find(".//FlexStatement")
            date = stmt.get("toDate", "unknown") if stmt is not None else "unknown"
        except Exception:
            date = "unknown"

        path = raw_dir / f"flex_{date}.xml"
        path.write_text(xml_text)
        print(f"Raw XML saved to: {path}")

    def _request_report(self) -> str:
        """Request a Flex report and return the reference code."""
        params = {
            "t": self.token,
            "q": self.query_id,
            "v": "3"
        }

        response = requests.get(FLEX_REQUEST_URL, params=params)
        response.raise_for_status()

        # Parse XML response
        root = ET.fromstring(response.text)

        # Check for errors
        status = root.find(".//Status")
        if status is not None and status.text != "Success":
            error_msg = root.find(".//ErrorMessage")
            raise FlexClientError(f"Flex request failed: {error_msg.text if error_msg is not None else 'Unknown error'}")

        # Get reference code
        reference_code = root.find(".//ReferenceCode")
        if reference_code is None:
            raise FlexClientError("No reference code in response")

        return reference_code.text

    def _fetch_statement(self, reference_code: str, max_attempts: int = 10) -> str:
        """Fetch the statement using the reference code."""
        params = {
            "t": self.token,
            "q": reference_code,
            "v": "3"
        }

        for attempt in range(max_attempts):
            response = requests.get(FLEX_STATEMENT_URL, params=params)
            response.raise_for_status()

            # Check if still processing
            if "<Status>Warn</Status>" in response.text and "Statement generation in progress" in response.text:
                time.sleep(2)  # Wait before retry
                continue

            # Check for errors
            if "<Status>Fail</Status>" in response.text:
                root = ET.fromstring(response.text)
                error_msg = root.find(".//ErrorMessage")
                raise FlexClientError(f"Statement fetch failed: {error_msg.text if error_msg is not None else 'Unknown error'}")

            return response.text

        raise FlexClientError("Timeout waiting for statement generation")

    def _parse_statement(self, xml_text: str) -> PortfolioSnapshot:
        """Parse Flex statement XML into a PortfolioSnapshot."""
        root = ET.fromstring(xml_text)

        # Get statement date
        stmt = root.find(".//FlexStatement")
        date = stmt.get("toDate") if stmt is not None else ""

        # Parse positions
        positions = []
        for pos in root.findall(".//OpenPosition"):
            # Try multiple possible attribute names for market value
            # IBKR uses different names depending on query configuration
            market_value = 0.0
            for attr in ["positionValue", "markValue", "marketValue", "value"]:
                val = pos.get(attr)
                if val:
                    market_value = float(val)
                    break

            # If still 0, try calculating from quantity * markPrice
            if market_value == 0:
                quantity = float(pos.get("position", 0) or pos.get("quantity", 0) or 0)
                mark_price = float(pos.get("markPrice", 0) or 0)
                if quantity and mark_price:
                    market_value = quantity * mark_price

            position = Position(
                symbol=pos.get("symbol", ""),
                description=pos.get("description", ""),
                asset_category=pos.get("assetCategory", ""),
                market_value=market_value,
                cost_basis=float(pos.get("costBasisMoney", 0) or pos.get("costBasis", 0) or 0),
                unrealized_pnl=float(pos.get("fifoPnlUnrealized", 0) or pos.get("unrealizedPnl", 0) or 0),
                currency=pos.get("currency", "USD"),
                account_id=pos.get("accountId", ""),
            )
            positions.append(position)

        # Parse cash balance (total and per account)
        # Cash is nested under FlexStatement elements, each with its own accountId
        cash_balance = 0.0
        cash_by_account: dict[str, float] = {}

        for stmt in root.findall(".//FlexStatement"):
            account_id = stmt.get("accountId", "")
            for cash in stmt.findall(".//CashReportCurrency"):
                if cash.get("currency") == "BASE_SUMMARY":
                    ending_cash = float(cash.get("endingCash", 0) or 0)
                    if account_id:
                        cash_by_account[account_id] = ending_cash
                    cash_balance += ending_cash

        # If not found, try EquitySummaryInBase
        if cash_balance == 0:
            equity = root.find(".//EquitySummaryInBase")
            if equity is not None:
                cash_balance = float(equity.get("cash", 0) or 0)

        # Calculate total value
        total_value = sum(p.market_value for p in positions) + cash_balance

        # If total is still 0, try getting from NAV/equity summary
        if total_value == 0:
            equity = root.find(".//EquitySummaryInBase")
            if equity is not None:
                total_value = float(equity.get("total", 0) or equity.get("totalLong", 0) or 0)

        return PortfolioSnapshot(
            date=date,
            positions=positions,
            cash_balance=cash_balance,
            total_value=total_value,
            cash_by_account=cash_by_account,
        )
