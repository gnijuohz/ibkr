"""IBKR Flex Web Service client."""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests

from .config import FLEX_TOKEN, FLEX_QUERY_ID, FLEX_REQUEST_URL, FLEX_STATEMENT_URL


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


@dataclass
class PortfolioSnapshot:
    """Represents a complete portfolio snapshot."""
    date: str
    positions: list[Position]
    cash_balance: float
    total_value: float
    currency: str = "USD"


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

        # Step 3: Parse the XML into a PortfolioSnapshot
        return self._parse_statement(statement_xml)

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
            position = Position(
                symbol=pos.get("symbol", ""),
                description=pos.get("description", ""),
                asset_category=pos.get("assetCategory", ""),
                market_value=float(pos.get("markValue", 0) or 0),
                cost_basis=float(pos.get("costBasisMoney", 0) or 0),
                unrealized_pnl=float(pos.get("fifoPnlUnrealized", 0) or 0),
                currency=pos.get("currency", "USD"),
            )
            positions.append(position)

        # Parse cash balance
        cash_balance = 0.0
        for cash in root.findall(".//CashReportCurrency"):
            if cash.get("currency") == "BASE_SUMMARY":
                cash_balance = float(cash.get("endingCash", 0) or 0)
                break

        # Calculate total value
        total_value = sum(p.market_value for p in positions) + cash_balance

        return PortfolioSnapshot(
            date=date,
            positions=positions,
            cash_balance=cash_balance,
            total_value=total_value,
        )
