#!/usr/bin/env python3
"""
IBKR Portfolio Tracker - CLI Entry Point

A privacy-focused portfolio tracker that shows only percentages,
hiding actual dollar values and sensitive positions like options.
"""

import argparse
import sys
from datetime import datetime

from .config import validate_config, OUTPUT_DIR
from .flex_client import FlexClient, FlexClientError
from .portfolio import transform_to_public, PortfolioHistory
from .storage import load_history, save_history, export_public_history
from .charts import generate_all_charts


def cmd_update(args):
    """Fetch latest portfolio data from IBKR and update history."""
    if not validate_config():
        sys.exit(1)

    print("Fetching portfolio from IBKR Flex Web Service...")

    try:
        client = FlexClient()
        snapshot = client.fetch_portfolio()
    except FlexClientError as e:
        print(f"Error fetching portfolio: {e}")
        sys.exit(1)

    print(f"Received data for: {snapshot.date}")
    print(f"Found {len(snapshot.positions)} positions")

    # Load existing history
    history, baseline_value, last_value = load_history()

    # Check for duplicate date
    existing_dates = {s.date for s in history.snapshots}
    if snapshot.date in existing_dates:
        print(f"Warning: Data for {snapshot.date} already exists. Skipping.")
        return

    # Transform to public snapshot
    public_snapshot, actual_value = transform_to_public(
        snapshot,
        baseline_value=baseline_value,
        previous_value=last_value,
    )

    # Update baseline if this is the first snapshot
    if baseline_value is None:
        baseline_value = actual_value
        print("Setting baseline value (index = 100)")

    # Add to history
    history.snapshots.append(public_snapshot)

    # Save
    save_history(history, baseline_value, actual_value)

    print(f"\nSnapshot saved!")
    print(f"  Index value: {public_snapshot.index_value:.2f}")
    print(f"  Invested: {public_snapshot.invested_pct:.1f}%")
    print(f"  Cash: {public_snapshot.cash_pct:.1f}%")
    if public_snapshot.period_return_pct is not None:
        print(f"  Period return: {public_snapshot.period_return_pct:+.2f}%")
    if public_snapshot.total_return_pct is not None:
        print(f"  Total return: {public_snapshot.total_return_pct:+.2f}%")


def cmd_show(args):
    """Show current portfolio status."""
    history, _, _ = load_history()

    if not history.snapshots:
        print("No portfolio data yet. Run 'update' first.")
        return

    latest = history.snapshots[-1]

    print(f"\n{'='*50}")
    print(f"Portfolio as of {latest.date}")
    print(f"{'='*50}")

    print(f"\nIndex Value: {latest.index_value:.2f} (baseline = 100)")

    if latest.total_return_pct is not None:
        sign = "+" if latest.total_return_pct >= 0 else ""
        print(f"Total Return: {sign}{latest.total_return_pct:.2f}%")

    if latest.period_return_pct is not None:
        sign = "+" if latest.period_return_pct >= 0 else ""
        print(f"Period Return: {sign}{latest.period_return_pct:.2f}%")

    print(f"\n{'Allocation':-^50}")
    print(f"  Invested: {latest.invested_pct:.1f}%")
    print(f"  Cash: {latest.cash_pct:.1f}%")

    if latest.positions:
        print(f"\n{'Top Positions':-^50}")
        for pos in latest.positions[:10]:
            print(f"  {pos.symbol:<10} {pos.allocation_pct:>6.2f}%")

    if latest.other_pct > 0:
        print(f"  {'Other':<10} {latest.other_pct:>6.2f}%")

    print()


def cmd_history(args):
    """Show historical portfolio data."""
    history, _, _ = load_history()

    if not history.snapshots:
        print("No portfolio data yet. Run 'update' first.")
        return

    print(f"\n{'Date':<12} {'Index':>8} {'Return':>10} {'Invested':>10} {'Cash':>8}")
    print("-" * 52)

    for snap in history.snapshots:
        ret_str = f"{snap.period_return_pct:+.2f}%" if snap.period_return_pct is not None else "N/A"
        print(f"{snap.date:<12} {snap.index_value:>8.2f} {ret_str:>10} {snap.invested_pct:>9.1f}% {snap.cash_pct:>7.1f}%")

    print()


def cmd_charts(args):
    """Generate portfolio charts."""
    history, _, _ = load_history()

    if not history.snapshots:
        print("No portfolio data yet. Run 'update' first.")
        return

    print("Generating charts...")
    paths = generate_all_charts(history)

    print(f"\nGenerated {len(paths)} chart(s):")
    for path in paths:
        print(f"  {path}")


def cmd_export(args):
    """Export public (safe to share) portfolio data."""
    output_path = export_public_history()
    print(f"Exported public portfolio data to: {output_path}")
    print("\nThis file contains only percentages and is safe to share.")
    print("It does NOT contain any actual dollar values.")


def main():
    parser = argparse.ArgumentParser(
        description="IBKR Portfolio Tracker - Track your portfolio with privacy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s update      Fetch latest data from IBKR
  %(prog)s show        Show current portfolio allocation
  %(prog)s history     Show historical data
  %(prog)s charts      Generate portfolio charts
  %(prog)s export      Export public data (safe to share)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Update command
    update_parser = subparsers.add_parser("update", help="Fetch and save latest portfolio data")
    update_parser.set_defaults(func=cmd_update)

    # Show command
    show_parser = subparsers.add_parser("show", help="Show current portfolio status")
    show_parser.set_defaults(func=cmd_show)

    # History command
    history_parser = subparsers.add_parser("history", help="Show historical data")
    history_parser.set_defaults(func=cmd_history)

    # Charts command
    charts_parser = subparsers.add_parser("charts", help="Generate portfolio charts")
    charts_parser.set_defaults(func=cmd_charts)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export public portfolio data")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
