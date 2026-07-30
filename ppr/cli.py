import argparse
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from ppr.scrapers import SCRAPERS
from ppr.api_client import OpenReviewAPIClient, create_openreview_client, create_openreview_v1_client
from ppr.config import CrawlConfig
from ppr.enrich import enrich_all, format_enrich_summary
from ppr.models import Paper
from ppr.s2_client import S2Client
from ppr.venues import REGISTRY_STEM

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _available_conferences() -> list[str]:
    from ppr.discover import known_conference_ids

    return sorted(known_conference_ids())


def all_conference_ids(data_dir: Path) -> list[str]:
    """Every conference directory under data/, sorted."""
    if not data_dir.exists():
        return []
    return sorted(d.name for d in data_dir.iterdir() if d.is_dir())


def _save_papers(papers: list[Paper], conf_id: str) -> Path:
    save_path = DATA_DIR / conf_id / "papers.jsonl"
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
        "enrich", help="Enrich papers with Semantic Scholar metadata (e.g., ppr enrich iclr_2025 neurips_2025)"
    )
    enrich_parser.add_argument(
        "conferences", nargs="*", default=[],
        help="Conference IDs (e.g., iclr_2026 neurips_2026). Omit with --all.",
    )
    enrich_parser.add_argument(
        "--all", action="store_true",
        help="Enrich every conference under data/.",
    )
    enrich_parser.add_argument(
        "--full", action="store_true",
        help="Discard existing enrichment and re-run the cold path.",
    )
    enrich_parser.add_argument(
        "--retry-unmatched", action="store_true",
        help="Also retry papers that no previous run could match.",
    )
    enrich_parser.add_argument(
        "--api-key", default=os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
        help="Semantic Scholar API key (optional, increases rate limits).",
    )

    # validate
    validate_parser = subparsers.add_parser(
        "validate", help="Cross-reference paper counts against DBLP (e.g., ppr validate iclr_2025)"
    )
    validate_parser.add_argument(
        "conferences", nargs="+",
        help="Conference IDs to validate.",
    )
    validate_parser.add_argument(
        "--tolerance", type=float, default=0.1,
        help="Maximum allowed relative difference (default: 0.1 = 10%%).",
    )

    return parser


def cmd_crawl(args: argparse.Namespace) -> None:
    conf_ids = args.conferences

    # Split into scraped vs OpenReview conferences
    scraped = [c for c in conf_ids if c in SCRAPERS]
    openreview = [
        c for c in conf_ids
        if c not in SCRAPERS and c != REGISTRY_STEM and (CONFIGS_DIR / f"{c}.yaml").exists()
    ]
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
    conf_ids = all_conference_ids(DATA_DIR) if args.all else args.conferences
    if not conf_ids:
        raise SystemExit(
            "No conferences given. Pass conference IDs or use --all."
        )

    client = S2Client(api_key=args.api_key or None)
    results = asyncio.run(
        enrich_all(
            conf_ids,
            client,
            DATA_DIR,
            full=args.full,
            retry_unmatched=args.retry_unmatched,
        )
    )
    print(format_enrich_summary(results))

    # `ppr enrich --all` feeds ./build.sh and a data release, so a crashed
    # conference must not read as success to the calling shell. Guard skips are
    # a correct outcome and stay exit-0.
    failures = [r for r in results if r.status == "failed"]
    if failures:
        raise SystemExit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    from ppr.validate import validate_conference

    results = []
    for conf_id in args.conferences:
        logger.info("Validating %s...", conf_id)
        result = validate_conference(conf_id, tolerance=args.tolerance)
        results.append(result)

    # Print results table
    print(f"\n{'Conference':<28} {'Scraped':>8} {'DBLP':>8} {'Status':<10} {'Message'}")
    print("-" * 80)
    for r in results:
        scraped_str = str(r.scraped) if r.scraped else "-"
        dblp_str = str(r.dblp) if r.dblp else "-"
        print(f"{r.conf_id:<28} {scraped_str:>8} {dblp_str:>8} {r.status:<10} {r.message}")

    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        print(f"\n{len(failures)} conference(s) FAILED validation.")
        raise SystemExit(1)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "crawl": cmd_crawl,
        "enrich": cmd_enrich,
        "validate": cmd_validate,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
