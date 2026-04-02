import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from ppr.scrapers import SCRAPERS
from ppr.api_client import OpenReviewAPIClient, create_openreview_client, create_openreview_v1_client
from ppr.citations import CitationFetcher
from ppr.config import CrawlConfig
from ppr.models import Paper

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

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
        prog="ppr",
        description="Crawl accepted papers from OpenReview conferences.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # crawl
    crawl_parser = subparsers.add_parser(
        "crawl", help="Fetch accepted papers (e.g., ppr crawl iclr_2025 neurips_2025)"
    )
    crawl_parser.add_argument(
        "conferences", nargs="+",
        help="Conference IDs (e.g., iclr_2025 neurips_2025).",
    )
    _add_auth_args(crawl_parser)

    # enrich
    enrich_parser = subparsers.add_parser(
        "enrich", help="Enrich papers with citation counts and abstracts (e.g., ppr enrich iclr_2025)"
    )
    enrich_parser.add_argument(
        "conference", help="Conference ID (e.g., iclr_2025).",
    )
    enrich_parser.add_argument(
        "--api-key", default=os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
        help="Semantic Scholar API key (optional, increases rate limits).",
    )
    enrich_parser.add_argument(
        "--concurrency", type=int, default=1,
        help="Max concurrent requests (default: 1, matching Semantic Scholar rate limit).",
    )

    return parser


def cmd_crawl(args: argparse.Namespace) -> None:
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

    # Scrape non-OpenReview conferences (no login needed)
    for conf_id in scraped:
        papers = SCRAPERS[conf_id]()
        save_path = _save_papers(papers, conf_id)
        logger.info("Done: %s (%d papers) -> %s", conf_id, len(papers), save_path)

    # Fetch OpenReview conferences (one login per API version, reuse clients)
    if openreview:
        configs = [CrawlConfig.from_yaml(CONFIGS_DIR / f"{c}.yaml") for c in openreview]
        api_versions = {c.api_version for c in configs}

        # Create only the clients needed (avoids unnecessary logins)
        or_clients = {}
        if 1 in api_versions:
            or_clients[1] = create_openreview_v1_client(
                username=args.username, password=args.password
            )
        if 2 in api_versions:
            or_clients[2] = create_openreview_client(
                username=args.username, password=args.password
            )

        for config in configs:
            client = OpenReviewAPIClient(config, or_clients[config.api_version])
            papers = client.fetch_papers()
            client.save_papers(papers)
            logger.info(
                "Done: %s %s (%d papers) -> %s",
                config.name, config.year, len(papers), config.get_save_path(),
            )


def cmd_enrich(args: argparse.Namespace) -> None:
    input_path = _resolve_input(args.conference)
    if not input_path.exists():
        raise FileNotFoundError(
            f"No papers found at {input_path}. Run 'ppr crawl {args.conference}' first."
        )

    with open(input_path, encoding="utf-8") as f:
        papers = [Paper.from_dict(json.loads(line)) for line in f if line.strip()]

    logger.info("Loaded %d papers from %s", len(papers), input_path)

    api_key = args.api_key or None
    fetcher = CitationFetcher(api_key=api_key, max_concurrency=args.concurrency)

    output_dir = input_path.parent
    tmp_path = output_dir / ".papers_with_citations.tmp.jsonl"
    final_path = output_dir / "papers_with_citations.jsonl"

    # Resume: load already-enriched papers from tmp file
    done_papers = []
    if tmp_path.exists():
        with open(tmp_path, encoding="utf-8") as f:
            done_papers = [Paper.from_dict(json.loads(line)) for line in f if line.strip()]
        done_titles = {p.title for p in done_papers}
        remaining = [p for p in papers if p.title not in done_titles]
        logger.info("Resuming: %d already done, %d remaining", len(done_papers), len(remaining))
    else:
        remaining = papers

    if remaining:
        new_papers = asyncio.run(fetcher.fetch_and_stream(remaining, tmp_path, append=bool(done_papers)))
        all_papers = done_papers + new_papers
    else:
        all_papers = done_papers
        logger.info("All papers already enriched")

    sorted_papers = sorted(
        all_papers,
        key=lambda p: p.citation_count if p.citation_count is not None else -1,
        reverse=True,
    )
    with open(final_path, "w", encoding="utf-8") as f:
        for paper in sorted_papers:
            f.write(paper.to_json() + "\n")
    tmp_path.unlink()
    logger.info("Saved %d papers (sorted by citations) to %s", len(sorted_papers), final_path)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "crawl": cmd_crawl,
        "enrich": cmd_enrich,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
