#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run.sh <conference_id> [conference_id ...] [--citations]
#
# Examples:
#   ./run.sh iclr_2025                          # crawl only
#   ./run.sh iclr_2025 --citations              # crawl + citations
#   ./run.sh iclr_2025 neurips_2025 icml_2025   # multiple conferences
#   ./run.sh iclr_2025 neurips_2025 --citations  # multiple + citations

conferences=()
citations=false

for arg in "$@"; do
    if [[ "$arg" == "--citations" ]]; then
        citations=true
    else
        conferences+=("$arg")
    fi
done

if [[ ${#conferences[@]} -eq 0 ]]; then
    echo "Usage: ./run.sh <conference_id> [conference_id ...] [--citations]"
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
uv run orc crawl "${conferences[@]}"

if $citations; then
    for conf in "${conferences[@]}"; do
        echo ""
        echo "Fetching citations: $conf"
        uv run orc citations "$conf"
    done
fi

echo ""
echo "All done."
