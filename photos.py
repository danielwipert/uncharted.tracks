"""The faded-polaroid photo look, baked into the image files.

build.py calls make_treated_photos() for every song that has a photo.
For each photo it saves two finished copies into the built site:
    <slug>-cover.jpg   tall crop for the song page cover
    <slug>-square.jpg  square crop for the polaroids on the home page

The look is a recreation of the design canvas, layer by layer:
    1. Fade the photo itself (sepia, lower contrast, brighter, warmer).
    2. Orange-amber color cast.
    3. A hint of yellow-green, then a light blue-violet tint.
    4. Lift the blacks to a warm brown.
    5. A pale cream haze.
    6. An orange light leak in the top-right corner.
    7. A warm dark edge (vignette).
    8. The worn layer on top: dust, scratches, crease, chewed edges.

To change the look, edit the numbers in RECIPE below and rebuild.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# The recipe. Every number here matches the design canvas.
# ---------------------------------------------------------------------------
RECIPE = {
    "sepia": 0.5,            # 0 = none, 1 = full sepia
    "contrast": 0.82,        # below 1 = more faded
    "brightness": 1.16,      # above 1 = brighter
    "saturate": 1.2,
    "hue_rotate_deg": -6,
    "orange_cast":   {"color": "#F4B55E", "opacity": 0.36},   # "color" blend
    "yellow_green":  {"color": "#DDE874", "opacity": 0.40},   # "soft light" blend
    "blue_violet":   {"color": "#7B6CE0", "opacity": 0.28},   # "soft light" blend
    "lifted_blacks": {"color": "#5C3A22", "opacity": 0.90},   # "lighten" blend
    "haze":          {"color": "#FFF1C8", "opacity": 0.15},   # plain layer
    "light_leak":    {"color": "#FF6E32", "opacity": 0.55, "x": 0.92, "y": 0.06, "reach": 0.45},
    "vignette":      {"color": "#5A320F", "opacity": 0.38, "starts_at": 0.55},
}

# Output sizes: (width, height) in pixels.
SIZES = {
    "cover": (900, 1350),    # tall, for the song page
    "square": (720, 720),    # for polaroids
}

RECIPE_VERSION = hashlib.md5(json.dumps([RECIPE, SIZES], sort_keys=True).encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return np.array([int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def apply_matrix(img, m):
    """Multiply every pixel's (r, g, b) by a 3x3 color matrix, then clip to 0..1."""
    return np.clip(img @ np.array(m, dtype=np.float32).T, 0, 1)


def mix(base, top, opacity):
    """Lay 'top' over 'base' at the given opacity (a number or a per-pixel array)."""
    return base * (1 - opacity) + top * opacity


# ---- The photo filters (same math web browsers use) ----
def sepia(img, a):
    k = 1 - a
    return apply_matrix(img, [
        [0.393 + 0.607 * k, 0.769 - 0.769 * k, 0.189 - 0.189 * k],
        [0.349 - 0.349 * k, 0.686 + 0.314 * k, 0.168 - 0.168 * k],
        [0.272 - 0.272 * k, 0.534 - 0.534 * k, 0.131 + 0.869 * k],
    ])


def contrast(img, c):
    return np.clip(img * c + (0.5 - 0.5 * c), 0, 1)


def brightness(img, b):
    return np.clip(img * b, 0, 1)


def saturate(img, s):
    return apply_matrix(img, [
        [0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s],
        [0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s],
        [0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s],
    ])


def hue_rotate(img, degrees):
    r = math.radians(degrees)
    c, s = math.cos(r), math.sin(r)
    return apply_matrix(img, [
        [0.213 + c * 0.787 - s * 0.213, 0.715 - c * 0.715 - s * 0.715, 0.072 - c * 0.072 + s * 0.928],
        [0.213 - c * 0.213 + s * 0.143, 0.715 + c * 0.285 + s * 0.140, 0.072 - c * 0.072 - s * 0.283],
        [0.213 - c * 0.213 - s * 0.787, 0.715 - c * 0.715 + s * 0.715, 0.072 + c * 0.928 + s * 0.072],
    ])


# ---- The blend modes ----
def luminosity(c):
    return c[..., 0:1] * 0.3 + c[..., 1:2] * 0.59 + c[..., 2:3] * 0.11


def blend_color(base, color):
    """'Color' blend: take the hue of 'color', keep the brightness of the photo."""
    top = np.broadcast_to(color, base.shape)
    d = luminosity(base) - luminosity(top)
    c = top + d
    lum = luminosity(c)
    low = c.min(axis=-1, keepdims=True)
    high = c.max(axis=-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(low < 0, lum + (c - lum) * lum / (lum - low), c)
        c = np.where(high > 1, lum + (c - lum) * (1 - lum) / (high - lum), c)
    return np.clip(np.nan_to_num(c), 0, 1)


def blend_soft_light(base, color):
    top = np.broadcast_to(color, base.shape)
    d = np.where(base <= 0.25, ((16 * base - 12) * base + 4) * base, np.sqrt(base))
    return np.where(top <= 0.5,
                    base - (1 - 2 * top) * base * (1 - base),
                    base + (2 * top - 1) * (d - base))


def blend_lighten(base, color):
    return np.maximum(base, color)


def blend_screen(base, color):
    return base + color - base * color


# ---------------------------------------------------------------------------
# Cropping
# ---------------------------------------------------------------------------
def crop_to(img, size, focus_y):
    """Crop to the target shape (like object-fit: cover), then resize.
    focus_y: 0 = keep the top, 0.5 = middle, 1 = bottom."""
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = round((new_h - target_h) * focus_y)
    return img.crop((left, top, left + target_w, top + target_h))


# ---------------------------------------------------------------------------
# The whole look
# ---------------------------------------------------------------------------
def fade(img, wear):
    """Apply the full recipe to a cropped PIL image and return a new PIL image."""
    R = RECIPE
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255

    # 1. Fade the photo itself.
    a = sepia(a, R["sepia"])
    a = contrast(a, R["contrast"])
    a = brightness(a, R["brightness"])
    a = saturate(a, R["saturate"])
    a = hue_rotate(a, R["hue_rotate_deg"])

    # 2-5. Color layers.
    layer = R["orange_cast"]
    a = mix(a, blend_color(a, hex_to_rgb(layer["color"])), layer["opacity"])
    for key in ("yellow_green", "blue_violet"):
        layer = R[key]
        a = mix(a, blend_soft_light(a, hex_to_rgb(layer["color"])), layer["opacity"])
    layer = R["lifted_blacks"]
    a = mix(a, blend_lighten(a, hex_to_rgb(layer["color"])), layer["opacity"])
    layer = R["haze"]
    a = mix(a, hex_to_rgb(layer["color"]), layer["opacity"])

    h, w = a.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)

    # 6. Light leak: a soft circle of orange, brightest at the corner.
    leak = R["light_leak"]
    cx, cy = leak["x"] * w, leak["y"] * h
    farthest = max(math.hypot(cx - x, cy - y) for x in (0, w) for y in (0, h))
    dist = np.hypot(xs - cx, ys - cy) / (farthest * leak["reach"])
    strength = (np.clip(1 - dist, 0, 1) * leak["opacity"])[..., None]
    a = mix(a, blend_screen(a, hex_to_rgb(leak["color"])), strength)

    # 7. Vignette: darken toward the edges.
    vig = R["vignette"]
    nx = (xs - w / 2) / (w / 2 * math.sqrt(2))
    ny = (ys - h / 2) / (h / 2 * math.sqrt(2))
    t = np.sqrt(nx ** 2 + ny ** 2)
    strength = (np.clip((t - vig["starts_at"]) / (1 - vig["starts_at"]), 0, 1) * vig["opacity"])[..., None]
    a = mix(a, hex_to_rgb(vig["color"]), strength)

    # 8. Worn layer on top.
    out = Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8), "RGB").convert("RGBA")
    out.alpha_composite(crop_to(wear, (w, h), 0.5))
    return out.convert("RGB")


def make_treated_photos(src, out_dir, slug, wear_path, cache_dir, focus_y=0.25):
    """Make the cover and square copies of one photo. Returns their file names.
    Finished images are cached, so unchanged photos aren't redone on every build."""
    src = Path(src)
    out_dir = Path(out_dir)
    cache_dir = Path(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    source_hash = hashlib.md5(src.read_bytes()).hexdigest()[:10]
    names = {}
    wear = None
    original = None
    for kind, size in SIZES.items():
        name = f"{slug}-{kind}.jpg"
        cached = cache_dir / f"{slug}-{kind}-{source_hash}-{RECIPE_VERSION}-{focus_y}.jpg"
        if not cached.exists():
            if original is None:
                original = Image.open(src).convert("RGB")
                wear = Image.open(wear_path).convert("RGBA")
            treated = fade(crop_to(original, size, focus_y), wear)
            treated.save(cached, quality=82, optimize=True, progressive=True)
        (out_dir / name).write_bytes(cached.read_bytes())
        names[kind] = name
    return names
