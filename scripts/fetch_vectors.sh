#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------
# Config
# ---------------------------------------
VECTORS_DIR="${VECTORS_DIR:-vectors}"
OWNER="${OWNER:-bache-archive}"
REPO="${REPO:-chris-bache-archive}"
TAG="${RELEASE_TAG:-}"  # if empty → latest
PARQUET_NAME="${PARQUET_NAME:-bache-talks.embeddings.parquet}"
FAISS_NAME="${FAISS_NAME:-bache-talks.index.faiss}"
CHECKSUMS_BASENAME="${CHECKSUMS_BASENAME:-checksums.sha256}"

mkdir -p "$VECTORS_DIR"

if [[ -n "$TAG" ]]; then
  BASE="https://github.com/${OWNER}/${REPO}/releases/download/${TAG}"
else
  BASE="https://github.com/${OWNER}/${REPO}/releases/latest/download"
fi

# ---------------------------------------
# Helpers
# ---------------------------------------
has_cmd() { command -v "$1" >/dev/null 2>&1; }

sha_check() {
  # Use sha256sum if present (Linux), else fall back to shasum (macOS)
  if has_cmd sha256sum; then
    sha256sum -c "$1"
  else
    shasum -a 256 -c "$1"
  fi
}

download() {
  local url="$1" out="$2"
  # -L follow redirects, -f fail on HTTP errors, -S show errors, --retry for flakiness
  curl -LfsS --retry 3 --retry-delay 2 "$url" -o "$out"
}

normalize_checksums() {
  # Normalize any "vectors/<file>" prefixes to bare filenames,
  # and strip CRLF if present.
  local in="$1" out="$2"
  # 1) remove leading "vectors/" after hash+two spaces
  # 2) remove CR characters
  sed -E 's#(^[0-9a-fA-F]{64})  vectors/#\1  #g' "$in" | tr -d '\r' > "$out"
}

# ---------------------------------------
# Download vectors
# ---------------------------------------
echo "Downloading vectors from: $BASE"
download "$BASE/$PARQUET_NAME" "$VECTORS_DIR/$PARQUET_NAME"
download "$BASE/$FAISS_NAME"   "$VECTORS_DIR/$FAISS_NAME"

# ---------------------------------------
# Verify checksums (if present)
# ---------------------------------------
if download "$BASE/$CHECKSUMS_BASENAME" "$VECTORS_DIR/$CHECKSUMS_BASENAME" 2>/dev/null; then
  echo "Verifying checksums…"
  # Create normalized checksum list in case entries are prefixed with 'vectors/'
  normalize_checksums "$VECTORS_DIR/$CHECKSUMS_BASENAME" "$VECTORS_DIR/${CHECKSUMS_BASENAME}.norm"

  # Run verification from inside the vectors directory
  ( cd "$VECTORS_DIR" && sha_check "${CHECKSUMS_BASENAME}.norm" )
  echo "✅ checksums verified"
else
  echo "ℹ️  No checksums file found at $BASE/$CHECKSUMS_BASENAME — continuing without verification."
fi

# ---------------------------------------
# Done
# ---------------------------------------
echo "Files in $VECTORS_DIR:"
ls -lh "$VECTORS_DIR/$PARQUET_NAME" "$VECTORS_DIR/$FAISS_NAME" || true
echo "✅ vectors ready"