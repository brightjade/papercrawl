import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from api_client import OpenReviewAPIClient, create_openreview_client
from acl_scraper import SCRAPERS
from citations import CitationFetcher
from config import CrawlConfig
from models import Paper

CONFIGS_DIR = Path(__file__).parent / "configs"
OUTPUTS_DIR = Path(__file__).parent / "outputs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _available_conferences() -> list[str]:
    from_configs = {p.stem for p in CONFIGS_DIR.glob("*.yaml")}
    return sorted(from_configs | SCRAPERS.keys())


def _resolve_input(conf_id: str) -> Path:
    return OUTPUTS_DIR / conf_id / "papers.jsonl"


def _save_papers(papers: list[Paper], conf_id: str) -> Path:
    save_path = OUTPUTS_DIR / conf_id / "papers.jsonl"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write(paper.to_json() + "\n")
    return save_path


def _add_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--username",
        default=os.environ.get("OPENREVIEW_USERNAME"),
        help="OpenReview username (default: OPENREVIEW_USERNAME env var).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("OPENREVIEW_PASSWORD"),
        help="OpenReview password (default: OPENREVIEW_PASSWORD env var).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orc",
        description="Crawl accepted papers from OpenReview conferences.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # crawl
    crawl_parser = subparsers.add_parser(
        "crawl", help="Fetch accepted papers (e.g., orc crawl iclr_2025 neurips_2025)"
    )
    crawl_parser.add_argument(
        "conferences", nargs="+",
        help="Conference IDs (e.g., iclr_2025 neurips_2025).",
    )
    _add_auth_args(crawl_parser)

    # citations
    cite_parser = subparsers.add_parser(
        "citations", help="Fetch citation counts (e.g., orc citations iclr_2025)"
    )
    cite_parser.add_argument(
        "conference", help="Conference ID (e.g., iclr_2025).",
    )
    cite_parser.add_argument(
        "--api-key", default=os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
        help="Semantic Scholar API key (optional, increases rate limits).",
    )
    cite_parser.add_argument(
        "--concurrency", type=int, default=5,
        help="Max concurrent requests (default: 5 without key, use 50 with key).",
    )

    # discover
    discover_parser = subparsers.add_parser(
        "discover", help="Discover venue IDs for a conference"
    )
    discover_parser.add_argument(
        "venue_prefix",
        help="Venue prefix to search (e.g., ICLR.cc/2025/Conference).",
    )
    _add_auth_args(discover_parser)

    return parser


def cmd_crawl(args):
    conf_ids = args.conferences

    # Split into scraped vs OpenReview conferences
    scraped = [c for c in conf_ids if c in SCRAPERS]
    openreview = [c for c in conf_ids if c not in SCRAPERS and (CONFIGS_DIR / f"{c}.yaml").exists()]
    unknown = [c for c in conf_ids if c not in scraped and c not in openreview]

    if unknown:
        available = _available_conferences()
        raise FileNotFoundError(
            f"Unknown conference(s): {', '.join(unknown)}. "
            f"Available: {', '.join(available)}"
        )

    # Scrape ACL-family conferences (no login needed)
    for conf_id in scraped:
        papers = SCRAPERS[conf_id]()
        save_path = _save_papers(papers, conf_id)
        logger.info("Done: %s (%d papers) -> %s", conf_id, len(papers), save_path)

    # Fetch OpenReview conferences (one login, reuse client)
    if openreview:
        or_client = create_openreview_client(
            username=args.username, password=args.password
        )
        for conf_id in openreview:
            config = CrawlConfig.from_yaml(CONFIGS_DIR / f"{conf_id}.yaml")
            client = OpenReviewAPIClient(config, or_client)
            papers = client.fetch_papers()
            client.save_papers(papers)
            logger.info(
                "Done: %s %s (%d papers) -> %s",
                config.name, config.year, len(papers), config.get_save_path(),
            )


def cmd_citations(args):
    input_path = _resolve_input(args.conference)
    if not input_path.exists():
        raise FileNotFoundError(
            f"No papers found at {input_path}. Run 'orc crawl {args.conference}' first."
        )

    with open(input_path, encoding="utf-8") as f:
        papers = [Paper.from_dict(json.loads(line)) for line in f if line.strip()]

    logger.info("Loaded %d papers from %s", len(papers), input_path)

    api_key = args.api_key or None
    fetcher = CitationFetcher(api_key=api_key, max_concurrency=args.concurrency)

    output_dir = input_path.parent
    tmp_path = output_dir / ".papers_with_citations.tmp.jsonl"
    final_path = output_dir / "papers_with_citations.jsonl"

    papers = asyncio.run(fetcher.fetch_and_stream(papers, tmp_path))

    sorted_papers = sorted(
        papers,
        key=lambda p: p.citation_count if p.citation_count is not None else -1,
        reverse=True,
    )
    with open(final_path, "w", encoding="utf-8") as f:
        for paper in sorted_papers:
            f.write(paper.to_json() + "\n")
    tmp_path.unlink()
    logger.info("Saved %d papers (sorted by citations) to %s", len(sorted_papers), final_path)


def cmd_discover(args):
    or_client = create_openreview_client(
        username=args.username, password=args.password
    )
    config = CrawlConfig(
        name="", year=0, venue_id="", selections={},
        conference_id="",
    )
    client = OpenReviewAPIClient(config, or_client)
    members = client.discover_venue_ids(args.venue_prefix)
    if members:
        logger.info("Found venue members for '%s':", args.venue_prefix)
        for m in members:
            print(f"  {m}")
    else:
        logger.warning("No members found for '%s'", args.venue_prefix)


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "crawl": cmd_crawl,
        "citations": cmd_citations,
        "discover": cmd_discover,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
