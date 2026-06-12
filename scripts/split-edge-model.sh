#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: $0 <input.gguf> <output-dir> <public-base-url> [chunk-size]" >&2
  echo "Example: $0 ./model.gguf ./frontend/public/models/gemma4 https://example.com/models/gemma4 256M" >&2
  exit 1
fi

INPUT_GGUF="$1"
OUTPUT_DIR="$2"
PUBLIC_BASE_URL="${3%/}"
CHUNK_SIZE="${4:-256M}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
FRONTEND_PUBLIC_DIR="$REPO_ROOT/frontend/public"

if [[ ! -f "$INPUT_GGUF" ]]; then
  echo "Input file not found: $INPUT_GGUF" >&2
  exit 1
fi

if ! command -v llama-gguf-split >/dev/null 2>&1; then
  echo "llama-gguf-split not found in PATH." >&2
  echo "Download it from llama.cpp releases or build llama.cpp locally first." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

INPUT_BASENAME="$(basename "$INPUT_GGUF")"
MODEL_PREFIX="${INPUT_BASENAME%.gguf}"
OUTPUT_PREFIX="$OUTPUT_DIR/$MODEL_PREFIX"
OUTPUT_DIR_ABS="$(cd "$OUTPUT_DIR" && pwd -P)"

if [[ "$OUTPUT_DIR_ABS" == "$FRONTEND_PUBLIC_DIR" || "$OUTPUT_DIR_ABS" == "$FRONTEND_PUBLIC_DIR/"* ]]; then
  PUBLIC_RELATIVE_PATH="${OUTPUT_DIR_ABS#"$FRONTEND_PUBLIC_DIR"}"
  PUBLIC_RELATIVE_PATH="${PUBLIC_RELATIVE_PATH#/}"
  if [[ -n "$PUBLIC_RELATIVE_PATH" && "$PUBLIC_BASE_URL" != */"$PUBLIC_RELATIVE_PATH" ]]; then
    PUBLIC_BASE_URL="${PUBLIC_BASE_URL}/${PUBLIC_RELATIVE_PATH}"
  fi
fi

llama-gguf-split --split-max-size "$CHUNK_SIZE" "$INPUT_GGUF" "$OUTPUT_PREFIX"

SHARDS=()
while IFS= read -r shard; do
  SHARDS+=("$shard")
done < <(find "$OUTPUT_DIR" -maxdepth 1 -type f -name "${MODEL_PREFIX}-*.gguf" | sort)

if [[ ${#SHARDS[@]} -eq 0 ]]; then
  echo "No shard files were created." >&2
  exit 1
fi

echo "Created ${#SHARDS[@]} shard(s):"
for shard in "${SHARDS[@]}"; do
  echo "  - $(basename "$shard")"
done

URLS=()
for shard in "${SHARDS[@]}"; do
  URLS+=("${PUBLIC_BASE_URL}/$(basename "$shard")")
done

SIZE_BYTES="$(wc -c < "$INPUT_GGUF" | tr -d ' ')"
echo
echo "Add these lines to .env:"
echo "VITE_EDGE_MODEL_SIZE_BYTES=${SIZE_BYTES}"
echo "# Public shard base: ${PUBLIC_BASE_URL}"
printf 'VITE_EDGE_MODEL_URLS='
(
  IFS=,
  printf '%s' "${URLS[*]}"
)
printf '\n'
