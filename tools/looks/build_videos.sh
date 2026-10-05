#!/usr/bin/env bash
# Turn rendered turntable frames into the v002 deliverables:
#   <stem>_luscious_48fps.mp4/.webp   - real-time turn, vanity filter
#   <stem>_crt_48fps.mp4              - half-speed slow motion through a simulated 1970s CRT
#   <stem>_crt_readme.webp            - same, lighter static, 640 px, for the README
#   <stem>_luscious_poster.png, <stem>_crt_poster.png
#
# Usage: tools/looks/build_videos.sh <frames_dir> <renders_dir> <stem> [work_dir]
# Needs: ffmpeg (libx264 + libwebp), python with numpy, pillow, scipy.
set -euo pipefail

FRAMES=$1
RENDERS=$2
STEM=$3
WORK=${4:-logs/video_work}
PY=${PYTHON:-python}
HERE=$(cd "$(dirname "$0")" && pwd)
FPS=48

mkdir -p "$RENDERS" "$WORK"/{vanity,slowmo,crt,crt_readme,seam}
N=$(ls "$FRAMES"/frame_*.png | wc -l | tr -d ' ')
echo "frames: $N"

# 1. Luscious real-time turn.
"$PY" "$HERE/vanity.py" "$FRAMES" "$WORK/vanity"
ffmpeg -y -loglevel error -framerate $FPS -i "$WORK/vanity/frame_%03d.png" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -movflags +faststart "$RENDERS/${STEM}_luscious_48fps.mp4"
ffmpeg -y -loglevel error -framerate $FPS -i "$WORK/vanity/frame_%03d.png" \
  -c:v libwebp_anim -lossless 0 -quality 82 -compression_level 6 -loop 0 "$RENDERS/${STEM}_luscious_48fps.webp"
cp "$WORK/vanity/frame_000.png" "$RENDERS/${STEM}_luscious_poster.png"

# 2. Half-speed slow motion: motion-interpolate to 2x frames. The first three frames are appended again so the
#    wrap-around (last -> first) is interpolated mid-stream; minterpolate drops frames at the very end of its input.
cp "$FRAMES/frame_000.png" "$WORK/seam/pad_0.png"
cp "$FRAMES/frame_001.png" "$WORK/seam/pad_1.png"
cp "$FRAMES/frame_002.png" "$WORK/seam/pad_2.png"
ffmpeg -y -loglevel error -framerate $FPS -i "$FRAMES/frame_%03d.png" -framerate $FPS -i "$WORK/seam/pad_%d.png" \
  -filter_complex "[0][1]concat=n=2:v=1,minterpolate=fps=$((FPS * 2)):mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
  -frames:v $((N * 2)) "$WORK/slowmo/frame_%04d.png"
GOT=$(ls "$WORK"/slowmo/frame_*.png | wc -l | tr -d ' ')
[ "$GOT" -eq $((N * 2)) ] || { echo "expected $((N * 2)) slow-motion frames, got $GOT"; exit 1; }

# 3. Through the tube: full static for the MP4, lighter static for the README WebP.
"$PY" "$HERE/crt_sim.py" "$WORK/slowmo" "$WORK/crt" --snow 0.018
"$PY" "$HERE/crt_sim.py" "$WORK/slowmo" "$WORK/crt_readme" --snow 0.006
ffmpeg -y -loglevel error -framerate $FPS -i "$WORK/crt/frame_%04d.png" \
  -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -movflags +faststart "$RENDERS/${STEM}_crt_48fps.mp4"
ffmpeg -y -loglevel error -framerate $FPS -i "$WORK/crt_readme/frame_%04d.png" -vf "scale=640:-1:flags=area" \
  -c:v libwebp_anim -lossless 0 -quality 60 -compression_level 6 -loop 0 "$RENDERS/${STEM}_crt_readme.webp"
# Poster at peak brightness (the lamp swell peaks a quarter of the way through the loop).
cp "$WORK/crt/frame_$(printf %04d $((N / 2))).png" "$RENDERS/${STEM}_crt_poster.png"

ls -la "$RENDERS"
