#!/usr/bin/env bash
# DRAGged · QACC · RAMDocs 원본 데이터셋 일괄 다운로드 (계획서 §2 시작점 원칙).
#
# 원본 파일은 git에 넣지 않는다. 이 스크립트 + checksums.lock 만으로 전부 재현한다.
#   bash data/raw/download.sh            # 다운로드 + lock 파일 검증 (lock 없으면 생성)
#   bash data/raw/download.sh --record   # lock 파일 강제 재생성 (버전 갱신 시에만; 커밋 필수)
#
# 버전 고정: 각 소스의 git commit SHA / HF revision과 데이터 파일 sha256을
# checksums.lock에 기록·커밋해 고정한다. LICENSE 사본은 LICENSES/에 복사·커밋한다.
set -euo pipefail

RAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="$RAW_DIR/checksums.lock"
LICENSE_DIR="$RAW_DIR/LICENSES"
MODE="${1:-verify}"

# ── 원 출처 (계획서 §3.1 실측 기준) ─────────────────────────────────────────
# DRAGged  (Cattan et al., 2025; arXiv:2506.08500) — 458문항, Table 2 분포 일치 확인본
DRAGGED_REPO="https://github.com/google-research-datasets/rag_conflicts"
# QACC     (Liu et al., Findings of NAACL 2025; arXiv:2410.12311) — 1,617문항/충돌 381, CC BY-SA 3.0
QACC_REPO="https://github.com/amazon-science/qa-with-conflicting-context"
# RAMDocs  (Wang et al., COLM 2025; arXiv:2504.13079) — test 500문항
RAMDOCS_HF="HanNight/RAMDocs"

mkdir -p "$LICENSE_DIR"

locked_rev() { # $1=key → lock에 기록된 리비전 (없으면 빈 문자열)
  [[ -f "$LOCK_FILE" ]] && awk -v k="$1" '$1==k {print $2}' "$LOCK_FILE" || true
}

clone_pinned() { # $1=repo_url $2=dest_dir $3=lock_key
  local rev; rev="$(locked_rev "$3")"
  if [[ ! -d "$2/.git" ]]; then
    git clone "$1" "$2"
  fi
  if [[ -n "$rev" && "$MODE" != "--record" ]]; then
    git -C "$2" fetch --quiet origin "$rev" 2>/dev/null || true
    git -C "$2" checkout --quiet "$rev"
    echo "  pinned  $3 @ $rev"
  else
    echo "  HEAD    $3 @ $(git -C "$2" rev-parse HEAD)"
  fi
}

echo "[1/3] DRAGged → $RAW_DIR/dragged"
clone_pinned "$DRAGGED_REPO" "$RAW_DIR/dragged" "dragged_commit"
cp -f "$RAW_DIR/dragged/LICENSE"* "$LICENSE_DIR/" 2>/dev/null \
  || echo "  (LICENSE 파일명 확인 필요 — 수동 복사)"

echo "[2/3] QACC → $RAW_DIR/qacc"
clone_pinned "$QACC_REPO" "$RAW_DIR/qacc" "qacc_commit"
cp -f "$RAW_DIR/qacc/LICENSE"* "$LICENSE_DIR/" 2>/dev/null \
  || echo "  (LICENSE 파일명 확인 필요 — 수동 복사; 데이터는 CC BY-SA 3.0)"

echo "[3/3] RAMDocs → $RAW_DIR/ramdocs"
RAMDOCS_REV="$(locked_rev ramdocs_revision)"
RESOLVED_REV_FILE="$(mktemp)"
trap 'rm -f "$RESOLVED_REV_FILE"' EXIT
python3 - "$RAW_DIR/ramdocs" "$RAMDOCS_HF" "${RAMDOCS_REV:-main}" "$RESOLVED_REV_FILE" <<'PY'
import sys
from huggingface_hub import HfApi, snapshot_download
dest, repo, rev, rev_out = sys.argv[1:5]
# 브랜치명(main)은 시간에 따라 움직인다 — 실제 커밋 SHA로 해석해 기록해야 버전이 고정된다.
sha = HfApi().dataset_info(repo, revision=rev).sha
path = snapshot_download(repo_id=repo, repo_type="dataset", revision=sha, local_dir=dest)
open(rev_out, "w").write(sha)
print(f"  snapshot {repo} @ {sha} → {path}")
PY
RAMDOCS_REV="$(cat "$RESOLVED_REV_FILE")"

# ── 체크섬 lock 생성/검증 ────────────────────────────────────────────────────
hash_tree() { # 데이터 파일 sha256 (git 메타·캐시 제외)
  find "$RAW_DIR/dragged" "$RAW_DIR/qacc" "$RAW_DIR/ramdocs" -type f \
    \( -name '*.json' -o -name '*.jsonl' -o -name '*.csv' -o -name '*.tsv' -o -name '*.parquet' \) \
    -not -path '*/.git/*' -not -path '*/.cache/*' -print0 |
    sort -z | xargs -0 shasum -a 256 | sed "s|$RAW_DIR/||"
}

if [[ "$MODE" == "--record" || ! -f "$LOCK_FILE" ]]; then
  {
    echo "dragged_commit $(git -C "$RAW_DIR/dragged" rev-parse HEAD)"
    echo "qacc_commit $(git -C "$RAW_DIR/qacc" rev-parse HEAD)"
    echo "ramdocs_revision $RAMDOCS_REV"
    echo "---"
    hash_tree
  } > "$LOCK_FILE"
  echo "checksums.lock 생성 완료 — 반드시 커밋할 것 (버전 고정의 물증)"
else
  if diff <(sed -n '/^---$/,$p' "$LOCK_FILE" | tail -n +2) <(hash_tree) >/dev/null; then
    echo "체크섬 검증 통과 — lock과 일치"
  else
    echo "오류: 데이터 파일이 checksums.lock과 다름. 출처 변경 여부 확인 후 필요 시 --record로 갱신·커밋" >&2
    exit 1
  fi
fi
