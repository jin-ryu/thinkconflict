#!/usr/bin/env bash
set -euo pipefail

STUDY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$STUDY_DIR/data/raw"
CONFRAG_REV="529e760a78a58791d0387fe469e0732377a6d94d"
NATCONFQA_REV="71864ed8d3913b879e9032755458cd411084c6b5"

mkdir -p "$RAW_DIR"

if [[ ! -d "$RAW_DIR/confrag/.git" ]]; then
  git clone https://huggingface.co/datasets/OracleY/ConfRAG "$RAW_DIR/confrag"
fi
git -C "$RAW_DIR/confrag" fetch origin "$CONFRAG_REV"
git -C "$RAW_DIR/confrag" checkout --detach "$CONFRAG_REV"
"$STUDY_DIR/../../.venv/bin/hf" download OracleY/ConfRAG ConfRAGsuggested.jsonl \
  --repo-type dataset --revision "$CONFRAG_REV" --local-dir "$RAW_DIR/confrag"

if [[ ! -d "$RAW_DIR/natconfqa/.git" ]]; then
  git clone https://github.com/EN555/ContraQA.git "$RAW_DIR/natconfqa"
fi
git -C "$RAW_DIR/natconfqa" fetch origin "$NATCONFQA_REV"
git -C "$RAW_DIR/natconfqa" checkout --detach "$NATCONFQA_REV"

echo "Raw snapshots are ready under $RAW_DIR"
