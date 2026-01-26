"""Region mapping for stock symbols."""

# Map stock symbols to regions
# Users can extend this mapping as needed
SYMBOL_REGIONS: dict[str, str] = {
    # US - Large Tech
    "AAPL": "US",
    "MSFT": "US",
    "GOOGL": "US",
    "GOOG": "US",
    "AMZN": "US",
    "META": "US",
    "NVDA": "US",
    "TSLA": "US",
    "AMD": "US",
    "INTC": "US",
    "NFLX": "US",
    "CRM": "US",
    "ORCL": "US",
    "ADBE": "US",
    "CSCO": "US",
    "AVGO": "US",
    "QCOM": "US",
    "TXN": "US",

    # US - Finance
    "JPM": "US",
    "BAC": "US",
    "WFC": "US",
    "GS": "US",
    "MS": "US",
    "V": "US",
    "MA": "US",
    "AXP": "US",
    "BRK.A": "US",
    "BRK.B": "US",
    "BLK": "US",

    # US - Healthcare
    "JNJ": "US",
    "UNH": "US",
    "PFE": "US",
    "MRK": "US",
    "ABBV": "US",
    "LLY": "US",
    "TMO": "US",
    "ABT": "US",

    # US - Consumer
    "WMT": "US",
    "PG": "US",
    "KO": "US",
    "PEP": "US",
    "COST": "US",
    "HD": "US",
    "MCD": "US",
    "NKE": "US",
    "SBUX": "US",
    "DIS": "US",

    # US - Industrial/Energy
    "XOM": "US",
    "CVX": "US",
    "BA": "US",
    "CAT": "US",
    "GE": "US",
    "UPS": "US",
    "LMT": "US",
    "RTX": "US",

    # US - ETFs
    "SPY": "US",
    "QQQ": "US",
    "IWM": "US",
    "DIA": "US",
    "VOO": "US",
    "VTI": "US",

    # Europe
    "ASML": "Europe",  # Netherlands
    "SAP": "Europe",   # Germany
    "NVO": "Europe",   # Denmark (Novo Nordisk)
    "SHEL": "Europe",  # UK (Shell)
    "AZN": "Europe",   # UK (AstraZeneca)
    "TM": "Japan",     # Toyota (listed as ADR)
    "UL": "Europe",    # UK (Unilever)
    "HSBC": "Europe",  # UK
    "BP": "Europe",    # UK
    "GSK": "Europe",   # UK
    "SNY": "Europe",   # France (Sanofi)
    "DEO": "Europe",   # UK (Diageo)
    "RIO": "Europe",   # UK/Australia
    "BHP": "Europe",   # Australia (but London listed)
    "LVMUY": "Europe", # France (LVMH)
    "NSRGY": "Europe", # Switzerland (Nestle)

    # China / Hong Kong
    "BABA": "China",   # Alibaba
    "JD": "China",     # JD.com
    "PDD": "China",    # Pinduoduo
    "BIDU": "China",   # Baidu
    "NIO": "China",    # NIO
    "XPEV": "China",   # XPeng
    "LI": "China",     # Li Auto
    "TCEHY": "China",  # Tencent
    "BILI": "China",   # Bilibili
    "TME": "China",    # Tencent Music
    "NTES": "China",   # NetEase
    "YUMC": "China",   # Yum China

    # Japan
    "SONY": "Japan",
    "HMC": "Japan",    # Honda
    "MUFG": "Japan",   # Mitsubishi UFJ
    "SMFG": "Japan",   # Sumitomo Mitsui

    # Other Asia
    "TSM": "Taiwan",   # TSMC
    "UMC": "Taiwan",
    "GRAB": "SEAsia",  # Southeast Asia
    "SE": "SEAsia",    # Sea Limited (Singapore)

    # India
    "INFY": "India",   # Infosys
    "WIT": "India",    # Wipro
    "HDB": "India",    # HDFC Bank

    # Latin America
    "NU": "LatAm",     # Nubank (Brazil)
    "MELI": "LatAm",   # MercadoLibre
    "VALE": "LatAm",   # Vale (Brazil)
    "PBR": "LatAm",    # Petrobras (Brazil)

    # International ETFs
    "VEA": "Intl",     # Developed Markets
    "VWO": "Emerging", # Emerging Markets
    "EFA": "Intl",     # EAFE
    "EEM": "Emerging", # Emerging Markets
    "IEMG": "Emerging",
    "IXUS": "Intl",
    "VXUS": "Intl",
    "FXI": "China",    # China Large Cap ETF
    "MCHI": "China",   # China ETF
    "EWJ": "Japan",    # Japan ETF
    "EWG": "Europe",   # Germany ETF
    "EWU": "Europe",   # UK ETF
}

# Default region for unknown symbols
DEFAULT_REGION = "Other"

# Region display order and colors
REGION_CONFIG = {
    "US": {"order": 1, "color": "#3b82f6"},      # Blue
    "Europe": {"order": 2, "color": "#8b5cf6"},  # Purple
    "China": {"order": 3, "color": "#ef4444"},   # Red
    "Japan": {"order": 4, "color": "#f97316"},   # Orange
    "Taiwan": {"order": 5, "color": "#14b8a6"},  # Teal
    "India": {"order": 6, "color": "#22c55e"},   # Green
    "SEAsia": {"order": 7, "color": "#eab308"},  # Yellow
    "LatAm": {"order": 8, "color": "#ec4899"},   # Pink
    "Emerging": {"order": 9, "color": "#06b6d4"},# Cyan
    "Intl": {"order": 10, "color": "#6366f1"},   # Indigo
    "Other": {"order": 99, "color": "#64748b"},  # Gray
}


def get_region(symbol: str) -> str:
    """Get the region for a stock symbol."""
    # Clean up symbol (remove suffixes like .L, .HK, etc.)
    clean_symbol = symbol.split(".")[0].upper()
    return SYMBOL_REGIONS.get(clean_symbol, DEFAULT_REGION)


def get_region_color(region: str) -> str:
    """Get the display color for a region."""
    return REGION_CONFIG.get(region, REGION_CONFIG["Other"])["color"]


def get_region_order(region: str) -> int:
    """Get the sort order for a region."""
    return REGION_CONFIG.get(region, REGION_CONFIG["Other"])["order"]
