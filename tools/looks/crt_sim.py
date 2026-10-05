"""Physical-ish simulation of watching footage on a 1970s colour CRT television.

Per frame, in signal order:
  1. 70s film grade           - the footage itself: faded warm stock
  2. lamp breathing           - slow studio-light swell, which is what drives the blooming
  3. composite video          - NTSC-style bandwidth: luma slightly soft, chroma smeared sideways
  4. scan conversion          - 240 visible lines, each a sample of the picture
  5. sync jitter              - lines wobble horizontally by a fraction of a pixel
  6. electron beam            - each line drawn as a Gaussian spot whose width grows with beam
                                current: dark lines are thin with black gaps, bright lines fatten and merge
  7. BLOOMING                 - high-voltage sag: as average picture level rises, the raster
                                swells and the beam defocuses (the defect described in the brief)
  8. tube geometry            - barrel deflection onto curved glass, with overscan
  9. phosphor persistence     - bright phosphors decay over a frame, leaving faint trails
 10. faceplate halation       - light scattering inside the thick glass
 11. shadow mask              - fixed on the glass: staggered RGB slot triads (the raster moves under it)
 12. hum bar + RF snow        - a soft bright band rolling up the screen, fine static
 13. glass + bezel            - window reflection on the curved glass, rounded tube face, plastic surround

Usage: python crt_sim.py <in_dir> <out_dir> [--only N]
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
RGB2YIQ = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], dtype=np.float32)
YIQ2RGB = np.linalg.inv(RGB2YIQ).astype(np.float32)

OUT_W, OUT_H = 960, 720          # delivered frame
INT_W, INT_H = 1280, 960         # internal raster resolution (4 px per scanline)
LINES = 240                      # visible scanlines


def grade(a):
    a = 0.025 + 0.86 * np.clip(a, 0, 1)
    a = a / (1 + 0.15 * a)
    a = a ** np.array([0.93, 0.98, 1.06], dtype=np.float32)
    a = a * np.array([1.04, 0.99, 0.93], dtype=np.float32)
    a = a + np.array([0.03, 0.015, 0.025], dtype=np.float32) * (1 - a)
    lum = (a @ LUMA)[..., None]
    return lum + (a - lum) * 1.3


class CRT:
    def __init__(self, n_frames, apl, snow=0.018):
        self.n = n_frames
        self.snow = snow
        # Blooming drive: normalised average picture level, -1 (darkest frame) .. +1 (brightest).
        lo, hi = float(np.min(apl)), float(np.max(apl))
        self.bloom = (2 * (np.asarray(apl) - lo) / max(hi - lo, 1e-6) - 1).astype(np.float32)

        yy, xx = np.mgrid[0:INT_H, 0:INT_W].astype(np.float32)
        self.x = (xx + 0.5) / INT_W * 2 - 1
        self.y = (yy + 0.5) / INT_H * 2 - 1
        r2 = self.x ** 2 + self.y ** 2
        self.barrel = (1 + 0.085 * r2) / 1.03           # deflection geometry, slight overscan

        # Scanline lookup: for each internal row, its position in line units.
        pos = (np.arange(INT_H, dtype=np.float32) + 0.5) * LINES / INT_H - 0.5
        self.l0 = np.floor(pos).astype(np.int32)
        self.frac = (pos - self.l0).astype(np.float32)

        # Output-space (glass) fixtures.
        oy, ox = np.mgrid[0:OUT_H, 0:OUT_W].astype(np.float32)
        gx, gy = (ox + 0.5) / OUT_W * 2 - 1, (oy + 0.5) / OUT_H * 2 - 1
        # Slot mask: RGB stripes 3 px wide, slots broken every 4 rows, staggered per triad.
        mask = np.full((OUT_H, OUT_W, 3), 0.80, dtype=np.float32)
        col = ox.astype(np.int32) % 3
        for c in range(3):
            mask[..., c] = np.where(col == c, 1.0, 0.80)
        triad = (ox.astype(np.int32) // 3) % 2
        slot_break = ((oy.astype(np.int32) + 2 * triad) % 4 == 0)
        mask[slot_break] *= 0.90
        self.mask = mask / mask.mean() * 0.98            # keep overall brightness
        # Tube face: convex rounded rectangle; plastic bezel outside it.
        ax, ay = np.abs(gx), np.abs(gy)
        q = np.maximum(np.stack([ax - 0.80, ay - 0.76]), 0)
        dist = np.sqrt((q ** 2).sum(0)) - 0.15
        dist = np.maximum(dist, np.maximum(ax - 0.95, ay - 0.95))
        self.face = np.clip(-dist / 0.012, 0, 1)[..., None]
        lip = np.exp(-((dist - 0.012) / 0.012) ** 2)[..., None]       # inner lip catches light
        self.bezel = np.array([0.075, 0.068, 0.062], dtype=np.float32) * (1 - 0.35 * np.clip(dist / 0.3, 0, 1))[..., None]
        self.bezel = self.bezel + lip * np.array([0.10, 0.09, 0.085], dtype=np.float32)
        gr2 = gx ** 2 + gy ** 2
        self.glass_vignette = (1 - 0.30 * np.clip(gr2 - 0.2, 0, None) ** 1.2)[..., None]
        # Window reflection: soft diagonal glare, upper left, as seen on the curved glass.
        streak = np.exp(-(((gx + 0.45) * 0.7 + (gy + 0.55) * 0.7) / 0.22) ** 2)
        blob = np.exp(-(((gx + 0.55) / 0.35) ** 2 + ((gy + 0.6) / 0.25) ** 2))
        self.reflection = (0.035 * streak + 0.05 * blob)[..., None] * np.array([0.95, 0.97, 1.0], dtype=np.float32)
        self.gy = gy
        self.prev = None

    def frame(self, src, t):
        phase = 2 * np.pi * t / self.n
        rng = np.random.default_rng(7000 + t)
        b = float(self.bloom[t])

        # 3. composite video bandwidth (at source resolution, 720 px wide).
        yiq = src @ RGB2YIQ.T
        yiq[..., 0] = gaussian_filter1d(yiq[..., 0], 0.7, axis=1)
        yiq[..., 1:] = gaussian_filter1d(yiq[..., 1:], 2.6, axis=1)
        sig = np.clip(yiq @ YIQ2RGB.T, 0, 1.2)

        # 4. scan conversion to 240 lines at internal width.
        lines = np.stack([
            np.asarray(Image.fromarray(np.clip(sig[..., c], 0, 1).astype(np.float32), "F")
                       .resize((INT_W, LINES), Image.BOX), dtype=np.float32) for c in range(3)], -1)

        # 5. sync jitter: smooth per-line offsets, plus defocus (7, part 1) along the line.
        jitter = gaussian_filter1d(rng.normal(0, 0.9, LINES), 3) + 0.25 * np.sin(np.arange(LINES) * 0.08 + 9 * phase)
        xs = np.arange(INT_W, dtype=np.float32)
        for i in range(LINES):
            for c in range(3):
                lines[i, :, c] = np.interp(xs + jitter[i], xs, lines[i, :, c])
        lines = gaussian_filter1d(lines, 0.8 + 1.6 * max(b, 0), axis=1)

        # 6. electron beam: Gaussian spot per line, width grows with beam current (and with blooming).
        pad = np.concatenate([lines[:1], lines, lines[-1:], lines[-1:]], 0)   # index l+1 is line l
        acc = np.zeros((INT_H, INT_W, 3), dtype=np.float32)
        for off in (-1, 0, 1, 2):
            v = pad[np.clip(self.l0 + off, -1, LINES) + 1]                    # (INT_H, INT_W, 3)
            d = (self.frac - off)[:, None, None]
            sigma = 0.20 + 0.17 * np.power(v, 0.8) + 0.05 * max(b, 0)
            acc += v * np.exp(-d * d / (2 * sigma * sigma)) / (sigma * 2.5066)
        raster = acc

        # 7 + 8. blooming swell + tube geometry, one lookup per colour gun.
        swell = 1 + 0.022 * b
        out = np.empty((INT_H, INT_W, 3), dtype=np.float32)
        convergence = {0: 1.0025, 1: 1.0, 2: 0.9975}
        for c in range(3):
            s = self.barrel * convergence[c] / swell
            sx = ((self.x * s) + 1) / 2 * INT_W - 0.5
            sy = ((self.y * s) + 1) / 2 * INT_H - 0.5
            out[..., c] = map_coordinates(raster[..., c], [sy, sx], order=1, mode="constant", cval=0.0)
        out = np.stack([np.asarray(Image.fromarray(out[..., c], "F").resize((OUT_W, OUT_H), Image.LANCZOS))
                      for c in range(3)], -1)

        # 9. phosphor persistence: only where the previous frame was brighter.
        if self.prev is not None:
            out = out + 0.22 * np.maximum(self.prev - out, 0)
        self.prev = out.copy()

        # 10. faceplate halation.
        out = out + gaussian_filter(out, (10, 10, 0)) * 0.10 + gaussian_filter(out, (40, 40, 0)) * 0.06

        # 11. shadow mask (fixed on the glass).
        out = out * self.mask * 1.12

        # 12. hum bar rolling upward twice per loop, and RF snow.
        band = ((self.gy + 1) / 2 + 2 * t / self.n) % 1.0
        hum = 1 + 0.045 * np.exp(-((band - 0.5) / 0.16) ** 2)
        out = out * hum[..., None]
        out = out + rng.normal(0, self.snow, (OUT_H, OUT_W, 1)).astype(np.float32)

        # 13. glass and bezel.
        out = out * self.glass_vignette + self.reflection
        out = out * self.face + self.bezel * (1 - self.face)
        return np.clip(out, 0, 1)


def load(path, t, n):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255
    a = grade(a)
    # 2. lamp breathing: two slow swells per loop; this is what makes the tube bloom.
    return a * (1 + 0.09 * np.sin(4 * np.pi * t / n - np.pi / 2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--only", type=int, nargs="*", help="process just these frame indices (look tests)")
    p.add_argument("--snow", type=float, default=0.018, help="RF static strength (lower = smaller files)")
    args = p.parse_args()
    frames = sorted(Path(args.src).glob("frame_*.png"))
    n = len(frames)
    # Pass 1: average picture level per frame (drives blooming), from small thumbnails.
    apl = []
    for t, path in enumerate(frames):
        thumb = Image.open(path).convert("RGB").resize((90, 68), Image.BOX)
        a = grade(np.asarray(thumb, dtype=np.float32) / 255) * (1 + 0.09 * np.sin(4 * np.pi * t / n - np.pi / 2))
        apl.append(float((a @ LUMA).mean()))
    crt = CRT(n, apl, snow=args.snow)
    dst = Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)
    order = list(range(n)) if not args.only else args.only
    if not args.only:
        # Warm up phosphor persistence on the last frames so the loop seam has trails too.
        for t in range(n - 3, n):
            crt.frame(load(frames[t], t, n), t)
    for t in order:
        if args.only:
            crt.prev = None
        out = crt.frame(load(frames[t], t, n), t)
        Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(dst / f"frame_{t:04d}.png")
        if args.only:
            print(f"bloom[{t}] = {crt.bloom[t]:+.2f}", flush=True)


if __name__ == "__main__":
    main()
