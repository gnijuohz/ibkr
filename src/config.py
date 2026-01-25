"""Configuration management for IBKR Portfolio Tracker."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# IBKR Flex Web Service configuration
FLEX_TOKEN = os.getenv("IBKR_FLEX_TOKEN")
FLEX_QUERY_ID = os.getenv("IBKR_QUERY_ID")

# IBKR Flex Web Service URLs
FLEX_REQUEST_URL = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
FLEX_STATEMENT_URL = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Data file paths
HISTORY_FILE = DATA_DIR / "portfolio_history.json"


def validate_config() -> bool:
    """Validate that required configuration is present."""
    if not FLEX_TOKEN:
        print("Error: IBKR_FLEX_TOKEN not set in environment")
        return False
    if not FLEX_QUERY_ID:
        print("Error: IBKR_QUERY_ID not set in environment")
        return False
    return True
