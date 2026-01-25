# IBKR Portfolio Tracker

A privacy-focused portfolio tracker for Interactive Brokers that shows only percentages, hiding actual dollar values and sensitive positions. Generates an interactive website for GitHub Pages.

## Features

- **Privacy First**: Only stores and displays percentages, never actual dollar values
- **Options Hidden**: Options and other derivatives are aggregated as "Other Positions"
- **Portfolio Index**: Track performance using a baseline of 100 (like an index fund)
- **Monthly Tracking**: Store historical snapshots for trend analysis
- **Interactive Charts**: Beautiful Chart.js visualizations (no static images)
- **GitHub Pages Ready**: One command to generate a deployable site
- **Safe Export**: All published data contains only percentages

## Quick Start

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
```bash
IBKR_FLEX_TOKEN=your_token_here
IBKR_QUERY_ID=your_query_id_here
```

## Usage

### Monthly Workflow

```bash
# 1. Fetch latest data from IBKR
python -m src.main update

# 2. Generate the website
python -m src.main site

# 3. Commit and push to deploy
git add docs/
git commit -m "Update portfolio data"
git push
```

### All Commands

| Command | Description |
|---------|-------------|
| `python -m src.main update` | Fetch latest data from IBKR |
| `python -m src.main show` | Show current portfolio in terminal |
| `python -m src.main history` | Show historical data table |
| `python -m src.main site` | Generate interactive HTML site |
| `python -m src.main export` | Export public JSON data |

### View Portfolio in Terminal

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

## GitHub Pages Deployment

### Option 1: Automatic (GitHub Actions)

1. Push to the `main` branch
2. Go to repo **Settings → Pages**
3. Set source to **GitHub Actions**
4. The site auto-deploys when `docs/` changes

### Option 2: Manual (docs folder)

1. Go to repo **Settings → Pages**
2. Set source to **Deploy from a branch**
3. Select **main** branch and **/docs** folder
4. Click Save

Your site will be live at: `https://yourusername.github.io/your-repo-name/`

### Preview Locally

```bash
python -m src.main site
cd docs && python -m http.server 8000
# Open http://localhost:8000
```

## Interactive Charts

The generated site includes:

1. **Portfolio Index** - Line chart showing value relative to baseline (100)
2. **Monthly Returns** - Bar chart of period-over-period returns
3. **Current Allocation** - Doughnut chart of position weights
4. **Allocation History** - Stacked area chart showing changes over time
5. **Positions Table** - Sortable table with allocation bars

All charts are interactive with hover tooltips and responsive design.

## Data Privacy

| Data Type | Stored Locally | Published to Site |
|-----------|----------------|-------------------|
| Dollar values | Encrypted* | **Never** |
| Position percentages | Yes | Yes |
| Options details | Never | Never |
| Account ID | Never | Never |
| Index value | Yes | Yes |
| Return percentages | Yes | Yes |

*Baseline value stored in `data/.private_values.json` for index calculation only

## File Structure

```
ibkr/
├── .env                    # Your secrets (never commit!)
├── .env.example            # Template for secrets
├── requirements.txt        # Python dependencies
├── src/
│   ├── config.py           # Configuration
│   ├── flex_client.py      # IBKR Flex API client
│   ├── portfolio.py        # Data models & privacy transforms
│   ├── storage.py          # Historical data storage
│   ├── site.py             # HTML site generator
│   └── main.py             # CLI entry point
├── data/                   # Private data (gitignored)
│   ├── portfolio_history.json
│   └── .private_values.json
├── docs/                   # GitHub Pages site (committed)
│   ├── index.html
│   └── data.json
└── .github/
    └── workflows/
        └── deploy.yml      # Auto-deploy workflow
```

## Cron Job (Optional)

Set up automatic monthly updates:

```bash
# Run on the 1st of each month at 9am
0 9 1 * * cd /path/to/ibkr && python -m src.main update && python -m src.main site && git add docs/ && git commit -m "Monthly update" && git push
```

## Security Notes

- Never commit `.env` file
- The `data/` folder contains private values and is gitignored
- Only `docs/` is published, containing only percentages
- Options positions are automatically hidden as "Other Positions"
