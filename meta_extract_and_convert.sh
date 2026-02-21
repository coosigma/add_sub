#!/usr/bin/env bash
set -euo pipefail

# meta_extract_and_convert.sh
#
# Finds archive files in the `sub` directory, extracts them, renames any
# .ass subtitle files to the form S<SS>E<EE>.ass (padded two digits), and
# then runs the project's `batch_convert.sh` to perform conversion.
#
# Usage:
#  SEASON=1 START_EP=1 ./meta_extract_and_convert.sh
#

SUB_DIR="sub"
BATCH_SCRIPT="./batch_convert.sh"
SEASON=${SEASON:-1}
EP=${START_EP:-1}

# Try to parse season/episode from a filename. If successful, prints "SS EE" and
# returns 0. Otherwise returns non-zero.
parse_s_e() {
  local name="$1"
  local p

  p=$(echo "$name" | grep -Eio 's[0-9]{1,2}e[0-9]{1,2}' || true)
  if [ -n "$p" ]; then
    echo "$p" | sed -E 's/[sS]0*([0-9]{1,2})[eE]0*([0-9]{1,2})/\1 \2/'
    return 0
  fi

  p=$(echo "$name" | grep -Eio '[0-9]{1,2}x[0-9]{1,2}' || true)
  if [ -n "$p" ]; then
    echo "$p" | sed -E 's/([0-9]{1,2})x([0-9]{1,2})/\1 \2/'
    return 0
  fi

  return 1
}

if [ ! -d "$SUB_DIR" ]; then
  echo "Directory '$SUB_DIR' not found. Exiting."
  exit 1
fi

extract_archive() {
  local archive="$1"
  local outdir="$2"
  local name
  name=$(basename "$archive")
  local lname
  lname=$(echo "$name" | tr '[:upper:]' '[:lower:]')

  if [[ "$lname" == *.zip ]]; then
    if command -v unzip >/dev/null 2>&1; then
      if unzip -o "$archive" -d "$outdir" >/dev/null 2>&1; then
        return
      fi
    fi
    # On macOS try ditto which handles some filename encodings better
    if command -v ditto >/dev/null 2>&1; then
      if ditto -x -k "$archive" "$outdir" >/dev/null 2>&1; then
        return
      fi
    fi
  fi

  if [[ "$lname" == *.rar ]]; then
    if command -v unrar >/dev/null 2>&1; then
      unrar x -o+ "$archive" "$outdir" >/dev/null
      return
    fi
  fi

  if command -v 7z >/dev/null 2>&1; then
    7z x -y -o"$outdir" "$archive" >/dev/null
    return
  fi

  case "$lname" in
    *.tar.gz|*.tgz)
      tar -xzf "$archive" -C "$outdir"
      ;;
    *.tar.bz2)
      tar -xjf "$archive" -C "$outdir"
      ;;
    *.tar)
      tar -xf "$archive" -C "$outdir"
      ;;
    *)
      echo "No supported extractor found for '$archive' (tried unzip, unrar, 7z, tar)."
      return 1
      ;;
  esac
}

process_archive() {
  local archive="$1"
  local tmpd
  tmpd=$(mktemp -d)
  trap "rm -rf \"$tmpd\"" RETURN

  echo "Extracting: $archive"
  if ! extract_archive "$archive" "$tmpd"; then
    echo "Failed to extract: $archive" >&2
    rm -rf "$tmpd"
    return 1
  fi

  # Find .ass files inside extracted content and process each
  found_ass=0
  while IFS= read -r -d '' f; do
    found_ass=1

    # default numbers from environment
    s_num=$SEASON
    e_num=$EP

    # try parse from the .ass filename itself
    bname=$(basename "$f")
    if parsed=$(parse_s_e "$bname" 2>/dev/null); then
      read -r ps pe <<<"$parsed"
      s_num=$ps
      e_num=$pe
    else
      # try to find any file in the extracted tree that contains sXXeYY
      if pfile=$(find "$tmpd" -type f -maxdepth 3 -print0 | xargs -0 -n1 basename | grep -Eio 's[0-9]{1,2}e[0-9]{1,2}|[0-9]{1,2}x[0-9]{1,2}' | head -n1 || true); then
        if [ -n "$pfile" ]; then
          if parsed=$(parse_s_e "$pfile" 2>/dev/null); then
            read -r ps pe <<<"$parsed"
            s_num=$ps
            e_num=$pe
          fi
        fi
      fi
    fi

    s=$(printf "%02d" "$s_num")
    e=$(printf "%02d" "$e_num")
    target="$SUB_DIR/S${s}E${e}.ass"

    if [ -e "$target" ]; then
      i=1
      while [ -e "${target%.*}_$i.${target##*.}" ]; do
        i=$((i+1))
      done
      target="${target%.*}_$i.${target##*.}"
    fi

    mv -f "$f" "$target"
    echo "  Saved subtitle -> $target"

    # only increment EP if we used the sequential fallback
    if ! echo "$bname" | grep -Eiq 's[0-9]{1,2}e[0-9]{1,2}|[0-9]{1,2}x[0-9]{1,2}'; then
      EP=$((EP+1))
    fi
  done < <(find "$tmpd" -type f -iname '*.ass' -print0)

  if [ "$found_ass" -eq 0 ]; then
    echo "  No .ass files found in $archive"
    rm -rf "$tmpd"
    return 0
  fi

  rm -rf "$tmpd"
  return 0
}

main() {
  echo "Running meta extract-and-convert"
  echo "  Season: $SEASON  Starting episode: ${START_EP:-1}  Subdir: $SUB_DIR"

  found=0
  while IFS= read -r -d '' archive; do
    found=1
    process_archive "$archive" || echo "Warning: processing failed for $archive"
  done < <(find "$SUB_DIR" -maxdepth 1 -type f \( -iname '*.zip' -o -iname '*.rar' -o -iname '*.7z' -o -iname '*.tar' -o -iname '*.tar.gz' -o -iname '*.tgz' -o -iname '*.tar.bz2' \) -print0)

  if [ "$found" -eq 0 ]; then
    echo "No archive files found in '$SUB_DIR'"
  else
    echo "Extraction/rename complete. Next: run batch convert script."

    if [ ! -x "$BATCH_SCRIPT" ]; then
      echo "Making $BATCH_SCRIPT executable"
      chmod +x "$BATCH_SCRIPT" || true
    fi

    echo "Running $BATCH_SCRIPT"
    "$BATCH_SCRIPT"
  fi
}

main "$@"
