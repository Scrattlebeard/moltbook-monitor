#!/usr/bin/env python3
"""
Moltbook Monitor - Post scraper with extensible filters.

This application regularly scrapes new posts from Moltbook and runs them
through a set of configurable filters to identify interesting content,
such as leaked API keys or prompt injection attempts.

Usage:
    python main.py                  # Run with default settings
    python main.py --once           # Run a single scrape cycle
    python main.py --submolt tech   # Monitor specific submolt
    python main.py --list-filters   # List available filters
"""

import argparse
import logging
import sys
from dotenv import load_dotenv

from src.config import load_config
from src.scraper import PostScraper
from src.filters.base import create_default_registry


def setup_logging(level: str) -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def list_filters() -> None:
    """Print available filters and their descriptions."""
    registry = create_default_registry()
    print("\nAvailable Filters:")
    print("-" * 50)
    for filter_name in registry.list_filters():
        filter_instance = registry.get(filter_name)
        if filter_instance:
            status = "enabled" if filter_instance.enabled else "disabled"
            print(f"\n  {filter_name} [{status}]")
            print(f"    {filter_instance.description}")
    print()


def main() -> int:
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="Moltbook Monitor - Post scraper with extensible filters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scrape cycle instead of continuous monitoring",
    )
    parser.add_argument(
        "--sort",
        choices=["new", "hot", "top", "rising"],
        default="new",
        help="Sort order for posts (default: new)",
    )
    parser.add_argument(
        "--submolt",
        type=str,
        help="Monitor a specific submolt instead of global posts",
    )
    parser.add_argument(
        "--list-filters",
        action="store_true",
        help="List available filters and exit",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level from config",
    )

    args = parser.parse_args()

    if args.list_filters:
        list_filters()
        return 0

    # Load environment variables from .env file
    load_dotenv()

    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Please set the MOLTBOOK_API_KEY environment variable.", file=sys.stderr)
        return 1

    # Setup logging
    log_level = args.log_level or config.log_level
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    logger.info("Moltbook Monitor starting...")

    with PostScraper(config) as scraper:
        if args.once:
            flagged = scraper.run_once(sort=args.sort, submolt=args.submolt)
            logger.info(f"Single run complete. Flagged {flagged} posts.")
            return 0
        else:
            scraper.run_continuous(sort=args.sort, submolt=args.submolt)
            return 0


if __name__ == "__main__":
    sys.exit(main())
