import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.database import (
    authenticate_user,
    create_password_reset,
    create_user,
    get_comparison_history,
    get_latest_model_run,
    get_market_summary,
    get_stock,
    get_stock_count,
    get_stock_history,
    get_stocks,
    get_top_stocks,
    init_db,
    reset_password,
    seed_snapshot_history,
)
from src.scraper.nse_scraper import scrape_and_update_stocks


def parse_args():
    parser = argparse.ArgumentParser(description="Python DB CLI for NSE backend")
    parser.add_argument(
        "command",
        choices=["top", "list", "symbol", "history", "compare", "summary", "refresh", "train", "model", "register", "login", "forgot-password", "reset-password"],
        help="Database command",
    )
    parser.add_argument("value", nargs="?", default="", help="Optional command argument")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--search", default="")
    parser.add_argument("--sort", default="score")
    parser.add_argument("--direction", default="desc")
    parser.add_argument("--username", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--code", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    init_db()
    seed_snapshot_history()

    if args.command == "top":
        limit = int(args.value) if args.value else args.limit
        print(json.dumps(get_top_stocks(limit=limit)))
        return

    if args.command == "list":
        stocks = get_stocks(
            limit=args.limit,
            offset=args.offset,
            search=args.search or args.value,
            sort_by=args.sort,
            sort_dir=args.direction,
        )
        print(json.dumps({"items": stocks, "total": get_stock_count(args.search or args.value)}))
        return

    if args.command == "symbol":
        print(json.dumps(get_stock(args.value) or {}))
        return

    if args.command == "history":
        print(json.dumps(get_stock_history(args.value.upper(), limit=args.limit)))
        return

    if args.command == "compare":
        symbols = [item.strip().upper() for item in (args.value or "").split(",") if item.strip()]
        print(json.dumps(get_comparison_history(symbols=symbols or None, limit=args.limit)))
        return

    if args.command == "summary":
        print(json.dumps(get_market_summary(limit=args.limit)))
        return

    if args.command == "model":
        print(json.dumps(get_latest_model_run()))
        return

    if args.command == "train":
        from src.scraper.nse_scraper import train_model_only
        model_meta = train_model_only()
        print(json.dumps({"model": model_meta}))
        return

    if args.command == "refresh":
        symbols = [item.strip().upper() for item in (args.value or "").split(",") if item.strip()]
        refreshed, model_meta, market_universe = scrape_and_update_stocks(symbols=symbols or None)
        print(
            json.dumps(
                {
                    "updated": len(refreshed),
                    "stocks": refreshed,
                    "model": model_meta,
                    "universe_size": len(market_universe),
                }
            )
        )
        return

    if args.command == "register":
        print(json.dumps(create_user(args.username, args.email, args.password)))
        return

    if args.command == "login":
        print(json.dumps(authenticate_user(args.value or args.username or args.email, args.password)))
        return

    if args.command == "forgot-password":
        print(json.dumps(create_password_reset(args.value or args.username or args.email)))
        return

    if args.command == "reset-password":
        print(json.dumps(reset_password(args.value or args.username or args.email, args.code, args.password)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
