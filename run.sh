#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run.sh <conference_id> [conference_id ...] [--enrich]
#
# Examples:
#   ./run.sh iclr_2025                          # crawl only
#   ./run.sh iclr_2025 --enrich                 # crawl + enrich (citations & abstracts)
#   ./run.sh iclr_2025 neurips_2025 icml_2025   # multiple conferences
#   ./run.sh iclr_2025 neurips_2025 --enrich     # multiple + enrich

conferences=()
enrich=false

for arg in "$@"; do
    if [[ "$arg" == "--enrich" ]]; then
        enrich=true
    else
        conferences+=("$arg")
    fi
done

if [[ ${#conferences[@]} -eq 0 ]]; then
    echo "Usage: ./run.sh <conference_id> [conference_id ...] [--enrich]"
    echo ""
    echo "Available conferences:"
    for f in configs/*.yaml; do
        echo "  $(basename "$f" .yaml)"
    done
    echo "  emnlp_2025"
    echo "  acl_2025"
    echo "  naacl_2025"
    exit 1
fi

echo "Crawling: ${conferences[*]}"
uv run ppr crawl "${conferences[@]}"

if $enrich; then
    for conf in "${conferences[@]}"; do
        echo ""
        echo "Enriching: $conf"
        uv run ppr enrich "$conf"
    done
fi

echo ""
echo "All done."
