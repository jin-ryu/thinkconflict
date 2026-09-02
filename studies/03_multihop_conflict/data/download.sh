#!/usr/bin/env bash
set -euo pipefail

STUDY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$STUDY_DIR/data/raw"
MAGIC_DIR="$RAW_DIR/magic"
MAGIC_REV="b96dbb2c7960ed14adc98b2feb4e693f9554df12"
PROOFWRITER_DIR="$RAW_DIR/proofwriter"
PROOFWRITER_ARCHIVE="$PROOFWRITER_DIR/proofwriter-dataset-V2020.12.3.zip"
PROOFWRITER_URL="https://aristo-data-public.s3.amazonaws.com/proofwriter/proofwriter-dataset-V2020.12.3.zip"
PROOFWRITER_SHA256="bbc5694901e8306d0bd659aa1ad53ccfd02c201864f4b320ffa3777827d1fc26"

mkdir -p "$RAW_DIR"

if [[ ! -d "$MAGIC_DIR/.git" ]]; then
  git clone https://huggingface.co/datasets/HYU-NLP/MAGIC "$MAGIC_DIR"
fi

git -C "$MAGIC_DIR" fetch origin "$MAGIC_REV"
git -C "$MAGIC_DIR" checkout --detach "$MAGIC_REV"

echo "MAGIC is ready at revision $MAGIC_REV under $MAGIC_DIR"

mkdir -p "$PROOFWRITER_DIR"
if [[ ! -f "$PROOFWRITER_ARCHIVE" ]]; then
  curl -fL --retry 3 "$PROOFWRITER_URL" -o "$PROOFWRITER_ARCHIVE"
fi

echo "$PROOFWRITER_SHA256  $PROOFWRITER_ARCHIVE" | sha256sum --check --status
echo "ProofWriter V2020.12.3 is ready under $PROOFWRITER_DIR"
