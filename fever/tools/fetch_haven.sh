#!/usr/bin/env bash
# Fetch the Poly Haven pool the scenes choose from, with BlenderProc's own downloader:
#   blenderproc download haven <dir> --types ... --categories/--tags ... --resolution 1k
# Downloads land in <dir>/{hdris,textures,models}/<asset_id>/. The workflow caches <dir> keyed on this
# file's hash, so Poly Haven is only asked again when these filters change.
# A filter that matches nothing is not an error: scenes fall back to procedural stand-ins.
set -uo pipefail

OUT=${1:?usage: fetch_haven.sh <output_dir>}
mkdir -p "$OUT"

fetch() {
  echo "::group::blenderproc download haven $*"
  blenderproc download haven "$OUT" --resolution 1k --threads 8 "$@" || echo "::warning::haven download failed: $*"
  echo "::endgroup::"
}

# Worlds: studio and night HDRIs, plus outdoor greenery for the lawn.
fetch --types hdris --categories studio
fetch --types hdris --categories night
fetch --types hdris --tags park garden meadow
# Surfaces: lawn, wallpaper, marble, carpet, wood floors and veneers.
fetch --types textures --tags grass wallpaper marble carpet parquet
# Models: chairs (lawn chairs, monoblocs, armchairs) and classical busts.
fetch --types models --tags chair bust sculpture statue

for kind in hdris textures models; do
  echo "$kind: $(find "$OUT/$kind" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l) assets"
done
du -sh "$OUT" || true
