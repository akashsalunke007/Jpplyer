"""Project entry point — run from the project root: python main.py"""
import sys
import os

# Ensure the project root is on the path so 'src' is importable
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Jpplyer — Automated Job Application Pipeline")
    parser.add_argument(
        "--phase",
        choices=["scrape", "score", "resume", "apply"],
        default=None,
        help="Run only a specific phase (default: run all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape + tailor resumes but do NOT submit applications or send emails",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    from src.orchestrator import main
    asyncio.run(main(args.phase, args.dry_run))
