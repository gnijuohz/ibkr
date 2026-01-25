# IBKR Portfolio Tracker

A privacy-focused portfolio tracker for Interactive Brokers that shows only percentages, hiding actual dollar values and sensitive positions.

## Features

- **Privacy First**: Only stores and displays percentages, never actual dollar values
- **Options Hidden**: Options and other derivatives are aggregated as "Other Positions"
- **Portfolio Index**: Track performance using a baseline of 100 (like an index fund)
- **Monthly Tracking**: Store historical snapshots for trend analysis
- **Charts**: Generate visual charts of allocation and performance
- **Safe Export**: Export data that's safe to share publicly

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure IBKR Flex Query

1. Log into IBKR Account Management
2. Go to **Reports → Flex Queries → Create New**
3. Configure the query with these sections:
   - **Open Positions**: symbol, description, assetCategory, markValue, costBasisMoney, fifoPnlUnrealized, currency
   - **Cash Report**: endingCash, currency
4. Set format to **XML**
5. Save and note your **Query ID**

### 3. Get Flex Web Service Token

1. In Account Management, go to **Settings → Flex Web Service**
2. Generate or note your **Token**

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
IBKR_FLEX_TOKEN=your_token_here
IBKR_QUERY_ID=your_query_id_here
```

## Usage

### Update Portfolio Data

Fetch the latest data from IBKR (run monthly):

```bash
python -m src.main update
```

### View Current Portfolio

```bash
python -m src.main show
```

Output:
```
==================================================
Portfolio as of 20240115
==================================================

Index Value: 112.50 (baseline = 100)
Total Return: +12.50%
Period Return: +2.30%

---------------------Allocation--------------------
  Invested: 75.0%
  Cash: 25.0%

--------------------Top Positions------------------
  AAPL           15.20%
  MSFT           12.50%
  GOOGL           8.30%
  Other           5.00%
```

### View History

```bash
python -m src.main history
```

### Generate Charts

```bash
python -m src.main charts
```

Generates:
- `output/portfolio_index.png` - Portfolio value as index (baseline 100)
- `output/allocation_YYYYMMDD.png` - Current allocation pie chart
- `output/allocation_history.png` - Allocation changes over time
- `output/monthly_returns.png` - Monthly return bar chart

### Export Public Data

```bash
python -m src.main export
```

This exports `data/portfolio_public.json` which contains only percentages and is safe to share.

## Data Privacy

| Data Type | Stored | Displayed | Exported |
|-----------|--------|-----------|----------|
| Dollar values | Never* | Never | Never |
| Position % | Yes | Yes | Yes |
| Options details | Never | Never | Never |
| Account ID | Never | Never | Never |
| Index value | Yes | Yes | Yes |
| Returns % | Yes | Yes | Yes |

*Baseline value stored locally in `.private_values.json` for index calculation only

## File Structure

```
ibkr/
├── .env                 # Your secrets (never commit!)
├── .env.example         # Template for secrets
├── requirements.txt     # Python dependencies
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   ├── flex_client.py   # IBKR Flex API client
│   ├── portfolio.py     # Data models & transformations
│   ├── storage.py       # Historical data storage
│   ├── charts.py        # Chart generation
│   └── main.py          # CLI entry point
├── data/                # Portfolio data (gitignored)
│   ├── portfolio_history.json
│   └── .private_values.json
└── output/              # Generated charts (gitignored)
```

## Monthly Update Reminder

Set up a monthly reminder to run:
```bash
python -m src.main update && python -m src.main charts
```

Or add a cron job:
```bash
# Run on the 1st of each month at 9am
0 9 1 * * cd /path/to/ibkr && python -m src.main update
```
