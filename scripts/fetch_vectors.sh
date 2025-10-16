#!/usr/bin/env bash
set -euo pipefail

VECTORS_DIR="${VECTORS_DIR:-vectors}"
mkdir -p "$VECTORS_DIR"

OWNER="bache-archive"
REPO="chris-bache-archive"

# If RELEASE_TAG is set, we pin to it. Otherwise we pull the latest release.
TAG="${RELEASE_TAG:-}"
PARQUET_NAME="bache-talks.embeddings.parquet"
FAISS_NAME="bache-talks.index.faiss"
CHECKSUMS="checksums.sha256"

if [[ -n "$TAG" ]]; then
  BASE="https://github.com/${OWNER}/${REPO}/releases/download/${TAG}"
else
  BASE="https://github.com/${OWNER}/${REPO}/releases/latest/download"
fi

echo "Downloading vectors from: $BASE"
curl -LfS "$BASE/$PARQUET_NAME" -o "$VECTORS_DIR/$PARQUET_NAME"
curl -LfS "$BASE/$FAISS_NAME"   -o "$VECTORS_DIR/$FAISS_NAME"

# Optional but recommended: verify checksums if present
if curl -LfS "$BASE/$CHECKSUMS" -o "$VECTORS_DIR/$CHECKSUMS" ; then
  echo "Verifying checksums…"
  (cd "$VECTORS_DIR" && shasum -a 256 -c "$CHECKSUMS")
else
  echo "No checksums file found (continuing)."
fi

ls -lh "$VECTORS_DIR"/bache-talks.*
echo "✅ vectors ready"
