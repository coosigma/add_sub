#!/usr/bin/env bash
# Main pipeline: extract archives in `sub/`, rename subtitle files to SxxExx.ass when possible,
# convert SRT -> ASS with forced alignment, and copy resulting .ass next to matched .mp4 files in `input/`.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# If the script was invoked with a non-bash shell (e.g. `sh run_pipeline.sh`),
# re-exec with bash so bash-specific features (shopt, [[ ) work correctly.
if [ -z "${BASH_VERSION-}" ]; then
  if command -v bash >/dev/null 2>&1; then
    exec bash "$0" "$@"
  else
    echo "This script requires bash. Please run with 'bash run_pipeline.sh' or install bash." >&2
    exit 1
  fi
fi

# ensure python venv
if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi
source "$ROOT/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# set sensible defaults if env vars not provided (can still override)
: "${RAISE_BY:=40}"
: "${H_MARGIN:=8}"
: "${H_MARGIN_PCT:=0}"
: "${PLAY_RES_X:=1920}"
: "${PLAY_RES_Y:=1080}"
: "${OUTLINE:=0.5}"
: "${SHADOW:=0.5}"

STAGING_DIR=$(mktemp -d "$ROOT/staging.XXXX")
echo "Staging dir: $STAGING_DIR"

extract_to() {
  src="$1"
  dest="$2"
  mkdir -p "$dest"
  lc_src="$(echo "$src" | tr '[:upper:]' '[:lower:]')"
  case "$lc_src" in
    *.zip)
      if command -v unzip >/dev/null 2>&1; then
        unzip -q "$src" -d "$dest"
      else
        7z x -y "$src" -o"$dest" >/dev/null
      fi
      ;;
    *.tar|*.tar.gz|*.tgz|*.tar.bz2|*.tar.xz|*.gz|*.bz2|*.xz)
      tar -xvf "$src" -C "$dest" >/dev/null 2>&1 || true
      ;;
    *.7z)
      7z x -y "$src" -o"$dest" >/dev/null
      ;;
    *.rar)
      if command -v unrar >/dev/null 2>&1; then
        unrar x -inul "$src" "$dest/"
      else
        7z x -y "$src" -o"$dest" >/dev/null
      fi
      ;;
    *)
      echo "Not an archive: $src -- copying if dir or file"
      if [ -d "$src" ]; then
        (cd "$src" && tar -cf - .) | (cd "$dest" && tar -xvf - >/dev/null 2>&1)
      else
        cp -a "$src" "$dest/"
      fi
      ;;
  esac
}

rename_subs() {
  # POSIX-compatible: find subtitle files and rename those containing SxxExx in name or parent dir
  base="$1"
  find "$base" -type f \( -iname "*.srt" -o -iname "*.ass" \) | while IFS= read -r f; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    parent="$(basename "$(dirname "$f")")"
    s=""
    e=""
    if echo "$name" | grep -qiE '[sS][0-9]{1,2}[._[:space:]-]*[eE][0-9]{1,2}'; then
      s="$(echo "$name" | sed -nE 's/.*[sS]([0-9]{1,2})[._[:space:]-]*[eE]([0-9]{1,2}).*/\1/p')"
      e="$(echo "$name" | sed -nE 's/.*[sS]([0-9]{1,2})[._[:space:]-]*[eE]([0-9]{1,2}).*/\2/p')"
    elif echo "$parent" | grep -qiE '[sS][0-9]{1,2}[._[:space:]-]*[eE][0-9]{1,2}'; then
      s="$(echo "$parent" | sed -nE 's/.*[sS]([0-9]{1,2})[._[:space:]-]*[eE]([0-9]{1,2}).*/\1/p')"
      e="$(echo "$parent" | sed -nE 's/.*[sS]([0-9]{1,2})[._[:space:]-]*[eE]([0-9]{1,2}).*/\2/p')"
    fi
    if [ -n "$s" ] && [ -n "$e" ]; then
      sxx=$(printf "s%02de%02d" "$((10#$s))" "$((10#$e))")
      newpath="$(dirname "$f")/$sxx.ass"
      if [ "$f" != "$newpath" ]; then
        echo "Renaming $f -> $newpath"
        mv -n "$f" "$newpath" || true
      fi
    fi
  done
}

echo "Scanning sub/ and extracting to staging..."
mkdir -p "$STAGING_DIR"
for item in sub/*; do
  [ -e "$item" ] || continue
  bname="$(basename "$item")"
  dest="$STAGING_DIR/${bname%.*}"
  extract_to "$item" "$dest"
done

echo "Renaming possible subtitle files in staging..."
rename_subs "$STAGING_DIR"

echo "Running subtitle conversion & integration..."
# call existing python processor: it will convert srt->ass and copy .ass next to matched mp4 in input/
PY_RAISE_ARG=""
if [ ! -z "${RAISE_BY-}" ] && [ "${RAISE_BY}" -gt 0 ] 2>/dev/null; then
  PY_RAISE_ARG="--raise-by ${RAISE_BY}"
fi
PY_HM_ARG=""
if [ ! -z "${H_MARGIN-}" ] && [ "${H_MARGIN}" -ge 0 ] 2>/dev/null; then
  PY_HM_ARG="--h-margin ${H_MARGIN}"
fi
PY_HM_PCT_ARG=""
if [ ! -z "${H_MARGIN_PCT-}" ] && [ "${H_MARGIN_PCT}" -ge 0 ] 2>/dev/null; then
  PY_HM_PCT_ARG="--h-margin-pct ${H_MARGIN_PCT}"
fi
PY_RES_ARG=""
if [ ! -z "${PLAY_RES_X-}" ] && [ "${PLAY_RES_X}" -gt 0 ] 2>/dev/null; then
  PY_RES_ARG="--play-res-x ${PLAY_RES_X}"
fi
PY_RES_Y_ARG=""
if [ ! -z "${PLAY_RES_Y-}" ] && [ "${PLAY_RES_Y}" -gt 0 ] 2>/dev/null; then
  PY_RES_Y_ARG="--play-res-y ${PLAY_RES_Y}"
fi
PY_OUTLINE_ARG=""
if [ ! -z "${OUTLINE-}" ] && [ "$(echo "${OUTLINE} > 0" | bc 2>/dev/null)" -eq 1 ] 2>/dev/null; then
  PY_OUTLINE_ARG="--outline ${OUTLINE}"
fi
PY_SHADOW_ARG=""
if [ ! -z "${SHADOW-}" ] && [ "$(echo "${SHADOW} > 0" | bc 2>/dev/null)" -eq 1 ] 2>/dev/null; then
  PY_SHADOW_ARG="--shadow ${SHADOW}"
fi
"$ROOT/.venv/bin/python" "$ROOT/process_sub_archives.py" --subdir "$STAGING_DIR" --outdir output --inputdir input --align bottom-center --mux $PY_RAISE_ARG $PY_HM_ARG $PY_HM_PCT_ARG $PY_RES_ARG $PY_RES_Y_ARG $PY_OUTLINE_ARG $PY_SHADOW_ARG

echo "Packaging output (optional)..."
# Allow skipping packaging if SKIP_ZIP=1 is set in the environment
if [ "${SKIP_ZIP-0}" = "1" ]; then
  echo "SKIP_ZIP=1 set; skipping creation of output.zip"
else
  if command -v zip >/dev/null 2>&1; then
    echo "Creating output.zip (this may take a while for large files)..."
    zip -r output.zip output
    echo "Created output.zip"
  else
    echo "zip not found; skipping packaging"
  fi
fi

echo "Cleaning staging: $STAGING_DIR"
rm -rf "$STAGING_DIR"

echo "Done. Converted subtitles and generated MKV files are under ./output/."
