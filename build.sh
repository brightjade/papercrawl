#!/usr/bin/env bash
set -euo pipefail

uv run python -m scripts.build_data "$@"
