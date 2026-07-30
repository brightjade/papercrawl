#!/usr/bin/env bash
# 로컬 전용 헬퍼. 원격 호스트에 ssh로 붙어 장시간 ppr 작업을 tmux 안에서 돌린다.
#
# 접속 정보는 이 파일에 두지 않는다 — 공개 저장소이기 때문이다.
# 저장소 루트의 .remote.env (gitignore됨) 또는 환경변수에서만 읽는다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_config() {
  local env_file="$REPO_ROOT/.remote.env"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  fi
  if [[ -z "${PPR_REMOTE_HOST:-}" || -z "${PPR_REMOTE_DIR:-}" ]]; then
    cat >&2 <<'EOF'
접속 정보가 없습니다. 저장소 루트에 .remote.env 를 만드세요 (gitignore됩니다):

  PPR_REMOTE_HOST=<ssh 호스트 별칭>
  PPR_REMOTE_DIR=<원격 저장소 절대경로>

환경변수로 넘겨도 됩니다.
EOF
    exit 1
  fi
}

# 원격에서 heredoc 스크립트를 실행한다. 인자는 호출부에서 %q로 인용해 넘긴다.
remote_bash() {
  ssh "$PPR_REMOTE_HOST" "bash -s -- $*"
}

cmd_sync() {
  if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    echo "경고: 로컬에 미커밋 변경이 있습니다 — 커밋해야 원격에 반영됩니다." >&2
  fi

  echo "==> 로컬 push"
  # --force 는 쓰지 않는다. non-fast-forward 로 거부되면 set -e 가 여기서 멈추는 것이
  # 의도된 동작이다 — 사람이 직접 풀어야 한다.
  git -C "$REPO_ROOT" push

  echo "==> 원격 pull + uv sync"
  remote_bash "$(printf %q "$PPR_REMOTE_DIR")" <<'REMOTE'
set -euo pipefail
cd "$1"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "원격 워킹트리가 dirty합니다. 정리한 뒤 다시 시도하세요." >&2
  exit 1
fi
git fetch origin
git pull --ff-only
uv sync
git log --oneline -1
REMOTE
}

usage() {
  cat <<'EOF'
사용법: scripts/remote.sh <명령> [인자...]

  sync                        로컬 push → 원격 pull --ff-only → uv sync
  run [--no-sync] <ppr 인자...>  원격 tmux 세션에서 `uv run ppr <인자>` detach 실행
  ps                          실행 중인 ppr-* 세션 목록
  logs [세션]                 원격 로그 tail -f (생략 시 가장 최근 로그)
  attach [세션]               tmux 세션에 붙기 (생략 시 가장 최근 세션)
  stop <세션>                 세션 종료
  pull-data [--delete]        원격 data/ → 로컬 (원격이 정본)
  push-data [--delete]        로컬 data/ → 원격 (확인 프롬프트)

접속 정보는 .remote.env 에서 읽습니다.
EOF
}

main() {
  local cmd="${1:-}"
  if [[ $# -gt 0 ]]; then shift; fi
  case "$cmd" in
    sync) load_config; cmd_sync "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "알 수 없는 명령: $cmd" >&2; usage >&2; exit 1 ;;
  esac
}

main "$@"
