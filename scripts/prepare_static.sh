#!/usr/bin/env bash
set -euo pipefail

echo "=== prepare_static.sh: start ==="
TMPDIR=/tmp/ignored_static
mkdir -p "$TMPDIR"

# 1) Move JS files that reference source maps to backup (avoid *.map errors)
echo "-> Moving JS files with sourceMappingURL to $TMPDIR"
grep -RIl --include='*.js' 'sourceMappingURL' . || true | while IFS= read -r jsf; do
  # skip if empty
  [ -z "$jsf" ] && continue
  mkdir -p "$TMPDIR/$(dirname "$jsf")"
  mv -v "$jsf" "$TMPDIR/$jsf" || true
done

# 2) Create tiny placeholder files for missing files referenced by CSS url(...)
echo "-> Creating placeholders for CSS url(...) references"
# For each CSS file, extract url(...) targets and create placeholder if missing
find . -type f -name '*.css' -print0 | while IFS= read -r -d '' css; do
  grep -oE "url\\([^)]*\\)" "$css" || true | sed -E "s/^url\\(['\"]?//; s/['\"]?\\)\$//" | while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    # skip absolute URLs and data URIs
    case "$ref" in
      http:*|https:*|data:*) continue ;;
    esac
    # normalize path (strip query/hash)
    path="${ref%%[?#]*}"
    # If path exists anywhere, skip
    if find . -type f -path "*/$path" -print -quit >/dev/null 2>&1; then
      continue
    fi
    target="$PWD/$path"
    mkdir -p "$(dirname "$target")"
    if [ ! -f "$target" ]; then
      # create a tiny placeholder
      printf "" > "$target"
      echo "placeholder created: $target"
    fi
  done
done

# 3) Deduplicate files under assets/ (keep first occurrence, move others to backup)
echo "-> Deduplicating files under assets/ (duplicates moved to $TMPDIR)"
# list relative paths under 'assets' and detect duplicates
find . -type f -path '*/assets/*' -printf '%P\n' | sort | uniq -d >/tmp/duplicated_asset_paths.txt || true
if [ -s /tmp/duplicated_asset_paths.txt ]; then
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    # find all file paths that end with this relative path
    find . -type f -path "*/$rel" | sort | awk 'NR>1' | while IFS= read -r dup; do
      mkdir -p "$TMPDIR/$(dirname "$dup")"
      mv -v "$dup" "$TMPDIR/$dup" || true
    done
  done < /tmp/duplicated_asset_paths.txt
fi

# 4) Strip any leftover sourceMappingURL lines from remaining JS files
echo "-> Stripping sourceMappingURL comments from remaining JS files"
find . -type f -name '*.js' -exec sed -i '/sourceMappingURL/d' {} + || true

echo "=== prepare_static.sh: done. Backup stored at $TMPDIR ==="
