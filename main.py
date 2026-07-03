from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.cache import SeenCache
from src.paper_filter import PaperSelector, merge_category_results
from src.pubmed_client import PubMedClient
from src.report_writer import ReportWriter
from src.summarizer import Summarizer
from src.utils import PROJECT_ROOT, ensure_directories, load_environment, load_yaml, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a daily Chinese PubMed cancer research brief.")
    parser.add_argument("--hours", type=int, default=24, help="Recent PubMed window in hours. PubMed uses day-level reldate.")
    parser.add_argument("--retmax", type=int, default=100, help="Maximum PMIDs to retrieve per category and date type.")
    parser.add_argument("--include-seen", action="store_true", help="Include papers already stored in data/seen_pmids.json.")
    parser.add_argument("--dry-run", action="store_true", help="Generate report without updating seen_pmids.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_environment()
    ensure_directories()
    logger = setup_logging()
    logger.info("Starting PubMed Cancer Research Daily Brief")

    try:
        queries = load_yaml("config/queries.yml")
        journal_config = load_yaml("config/journal_priority.yml")
        categories = queries.get("categories", {})
        if not categories:
            raise RuntimeError("No categories found in config/queries.yml")

        cache = SeenCache(PROJECT_ROOT / "data" / "seen_pmids.json")
        seen_pmids = set() if args.include_seen else cache.load()
        client = PubMedClient.from_env()

        raw_pmids: dict[str, list[str]] = {}
        all_pmids: list[str] = []
        for category_key, config in categories.items():
            query = config["query"]
            pmids = client.search_recent_pmids(query=query, hours=args.hours, retmax=args.retmax)
            raw_pmids[category_key] = pmids
            all_pmids.extend(pmids)

        unique_pmids = list(dict.fromkeys(all_pmids))
        logger.info("Fetched %s unique PMIDs before metadata retrieval", len(unique_pmids))
        papers = client.fetch_papers(unique_pmids)
        papers_by_category = merge_category_results(raw_pmids, papers)

        selector = PaperSelector(journal_config.get("priority_journals", []))
        selected = selector.assign_and_select(papers_by_category, categories, seen_pmids)

        run_time = datetime.now(ZoneInfo("Asia/Shanghai"))
        writer = ReportWriter(PROJECT_ROOT / "reports", Summarizer())
        report_path = writer.write(selected, categories, run_time)

        reported_pmids = [paper.pmid for papers_in_category in selected.values() for paper in papers_in_category]
        if not args.dry_run:
            cache.add(reported_pmids)
            logger.info("Updated seen cache with %s PMIDs", len(reported_pmids))
        else:
            logger.info("Dry run enabled; seen cache not updated")

        logger.info("Report written to %s", report_path)
        print(report_path)
        return 0
    except Exception as exc:
        logger.exception("Daily brief generation failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
