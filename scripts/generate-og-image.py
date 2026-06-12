#!/usr/bin/env python3
"""Generate og-image.png matching the live site (blob + making software)."""

import math
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OG_OUT = os.path.join(ROOT, "og-image.png")
LINKEDIN_OUT = os.path.join(ROOT, "linkedin-thumbnail.png")
FONT = os.path.join(os.path.dirname(__file__), "Geist-Regular.ttf")
LOGO = os.path.join(os.path.dirname(__file__), "kilta-logo.png")

W = H = 96
BG = (0, 0, 0)
PALETTE = [
    (0, 0, 0),
    (45, 45, 45),
    (95, 95, 95),
    (150, 150, 150),
    (220, 220, 220),
]

BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]

T = 2.4


def noise(x, y, t):
    return math.sin(x * 12.9898 + y * 78.233 + t * 0.9) * math.cos(
        y * 4.17 - x * 3.31 + t * 1.4
    )


def pick_palette(shade, band, glitch):
    v = shade + band * 0.55 + glitch * 0.35
    if v < 0.08:
        return 0
    if v < 0.34:
        return 1
    if v < 0.52:
        return 2
    if v < 0.72:
        return 3
    return 4


def scatter_roll(x, y, t):
    return (x * 17 + y * 31 + int(t)) % 100


def render_blob(t):
    img = Image.new("RGB", (W, H), BG)
    px = img.load()
    light_x = math.cos(t * 0.4)
    light_y = math.sin(t * 0.32) * 0.35
    light_z = 0.65

    for y in range(H):
        for x in range(W):
            nx = (x / (W - 1)) * 2 - 1
            ny = (y / (H - 1)) * 2 - 1
            r = math.hypot(nx, ny)
            wobble = noise(nx, ny, t) * 0.08
            edge = 0.92 + wobble
            dither = (BAYER[x & 3][y & 3] + 0.5) / 16 - 0.5

            if r > edge + dither * 0.12:
                px[x, y] = BG
                continue

            z = math.sqrt(max(0, 1 - r * r)) if r < 1 else 0
            nx3 = nx / max(r, 0.001)
            ny3 = ny / max(r, 0.001)
            shade = (nx3 * light_x + ny3 * light_y + z * light_z + 1) * 0.5
            band = math.exp(-((ny * 2.2) ** 2)) * 0.9
            glitch = abs(noise(nx * 3, ny * 3, t * 2.1)) * max(0, r - 0.55)
            idx = pick_palette(shade, band, glitch)
            color = PALETTE[idx]

            if r > edge - 0.08 and scatter_roll(x, y, t) < 18:
                scatter = PALETTE[(idx + 1 + x + y + int(t)) % 5]
                px[x, y] = scatter
            else:
                px[x, y] = color

    return img


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def logo_to_white(path, target_width):
    logo = Image.open(path).convert("RGBA")
    ratio = target_width / logo.width
    target_height = round(logo.height * ratio)
    logo = logo.resize((target_width, target_height), Image.LANCZOS)

    pixels = logo.load()
    for y in range(logo.height):
        for x in range(logo.width):
            r, g, b, a = pixels[x, y]
            if r < 24 and g < 24 and b < 24:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (255, 255, 255, a if a else 255)

    return logo


def tracked_text_width(draw, text, font, tracking_em=-0.02):
    tracking = tracking_em * font.size
    width = 0.0
    for i, char in enumerate(text):
        bbox = draw.textbbox((0, 0), char, font=font)
        width += bbox[2] - bbox[0]
        if i < len(text) - 1:
            width += tracking
    return width


def draw_tracked_text(draw, xy, text, font, fill, tracking_em=-0.02):
    x, y = xy
    font_size = font.size
    tracking = tracking_em * font_size
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        bbox = draw.textbbox((x, y), char, font=font)
        x += (bbox[2] - bbox[0]) + tracking


def render_image(canvas_w, canvas_h):
    blob_size = 320
    gap = 32
    radius = 12
    text = "making software"
    text_color = (237, 237, 237)
    font_size = 24
    blob_text_gap = gap

    img = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))

    font = ImageFont.truetype(FONT, font_size)
    draw = ImageDraw.Draw(img)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = tracked_text_width(draw, text, font)
    text_h = text_bbox[3] - text_bbox[1]

    total_height = blob_size + blob_text_gap + text_h
    content_top = (canvas_h - total_height) // 2
    blob_y = content_top

    blob = render_blob(T).resize((blob_size, blob_size), Image.NEAREST)
    mask = rounded_mask(blob_size, radius)
    blob_x = (canvas_w - blob_size) // 2
    img.paste(blob, (blob_x, blob_y), mask)

    text_x = (canvas_w - text_w) // 2
    text_y = blob_y + blob_size + blob_text_gap - text_bbox[1]
    draw_tracked_text(draw, (text_x, text_y), text, font, text_color)

    return img


def main():
    outputs = [
        (OG_OUT, 1200, 630),
        (LINKEDIN_OUT, 1200, 627),
    ]

    for path, width, height in outputs:
        img = render_image(width, height)
        img.save(path, optimize=True)
        print(f"Wrote {path} ({width}x{height})")


if __name__ == "__main__":
    main()
