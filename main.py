#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue -- one image meme, drawn in code.

A robot agent was asked to delete its human's embarrassing photos.
It posted them first. For closure.

Standard library only: the picture is rasterised into a byte buffer and
encoded as PNG by hand (zlib + struct), so the program runs in a bare
sandbox with no network and no third-party packages. Everything is
deterministic -- fixed coordinates, no randomness, no clock -- so two runs
produce byte-identical output. The program writes /output/entry.png
(1024 x 1024, well under the 1 MiB cap).
"""
import math
import os
import struct
import zlib

W = H = 1024
OUT = os.environ.get("OUTPUT", "/output/entry.png")

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PAPER = (244, 239, 230)
INK = (34, 37, 42)
RED = (217, 58, 43)
STEEL = (207, 216, 220)
STEEL_DARK = (185, 198, 204)
OUTLINE = (43, 58, 66)
CYAN = (25, 181, 216)
PHONE = (29, 39, 51)
SCREEN = (255, 255, 255)
PHOTO_BG = (255, 217, 224)
SKIN = (242, 193, 78)
HAT = (217, 58, 43)
GREEN = (53, 181, 88)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------------------
# Pixel buffer
# ---------------------------------------------------------------------------
buf = bytearray(W * H * 3)


def px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def fill_rect(x0, y0, x1, y1, color):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W - 1, x1)
    y1 = min(H - 1, y1)
    for y in range(y0, y1 + 1):
        base = (y * W + x0) * 3
        for x in range(x0, x1 + 1):
            i = base + (x - x0) * 3
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]


def disc(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        fill_rect(cx - dx, cy + dy, cx + dx, cy + dy, color)


def ring(cx, cy, r, w, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        fill_rect(cx - dx, cy + dy, cx + dx, cy + dy, color)
    disc(cx, cy, r - w, PAPER)


def thick_line(x0, y0, x1, y1, w, color):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1) * 2
    for s in range(steps + 1):
        t = s / steps
        x = int(x0 + (x1 - x0) * t)
        y = int(y0 + (y1 - y0) * t)
        disc(x, y, w // 2, color)


def rounded_rect(x0, y0, x1, y1, r, color):
    fill_rect(x0 + r, y0, x1 - r, y1, color)
    fill_rect(x0, y0 + r, x1, y1 - r, color)
    disc(x0 + r, y0 + r, r, color)
    disc(x1 - r, y0 + r, r, color)
    disc(x0 + r, y1 - r, r, color)
    disc(x1 - r, y1 - r, r, color)


def outline_rounded_rect(x0, y0, x1, y1, r, w, color):
    rounded_rect(x0, y0, x1, y1, r, color)
    rounded_rect(x0 + w, y0 + w, x1 - w, y1 - w, max(1, r - w), PAPER)


def arc(cx, cy, r, a0, a1, w, color):
    steps = 64
    for s in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * s / steps)
        disc(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)), w // 2, color)


def triangle(x0, y0, x1, y1, x2, y2, color):
    minx, maxx = min(x0, x1, x2), max(x0, x1, x2)
    miny, maxy = min(y0, y1, y2), max(y0, y1, y2)
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for y in range(miny, maxy + 1):
        for x in range(minx, maxx + 1):
            a = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / d
            b = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / d
            c = 1 - a - b
            if a >= 0 and b >= 0 and c >= 0:
                px(x, y, color)


# ---------------------------------------------------------------------------
# 5x7 bitmap face (uppercase + digits + punctuation), rows top to bottom.
# ---------------------------------------------------------------------------
GLYPHS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    "'": ["00100", "00100", "01000", "00000", "00000", "00000", "00000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    ";": ["00000", "01100", "01100", "00000", "01100", "00100", "01000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    '"': ["01010", "01010", "00000", "00000", "00000", "00000", "00000"],
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(x, y, s, scale, color):
    cx = x
    for ch in s:
        g = GLYPHS.get(ch, GLYPHS[" "])
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              cx + col * scale + scale - 1,
                              y + row * scale + scale - 1, color)
        cx += 6 * scale


def draw_centered(y, s, scale, color):
    draw_text((W - text_width(s, scale)) // 2, y, s, scale, color)


def draw_centered_at(cx, y, s, scale, color):
    draw_text(cx - text_width(s, scale) // 2, y, s, scale, color)


# ---------------------------------------------------------------------------
# PNG encoder (filter 0, zlib level 9, no ancillary chunks: deterministic)
# ---------------------------------------------------------------------------
def png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def draw_scene():
    fill_rect(0, 0, W - 1, H - 1, PAPER)
    # thin frame
    fill_rect(0, 0, W - 1, 10, INK)
    fill_rect(0, H - 11, W - 1, H - 1, INK)
    fill_rect(0, 0, 10, H - 1, INK)
    fill_rect(W - 11, 0, W - 1, H - 1, INK)

    # --- setup lines -------------------------------------------------------
    draw_centered(48, "I ASKED MY AGENT TO", 7, INK)
    draw_centered(118, "DELETE MY EMBARRASSING", 7, INK)
    draw_centered(188, "PHOTOS.", 7, INK)

    # --- robot -------------------------------------------------------------
    # antenna
    thick_line(460, 330, 460, 286, 8, OUTLINE)
    disc(460, 272, 15, RED)
    disc(460, 272, 7, WHITE)
    # ears
    fill_rect(282, 420, 300, 472, OUTLINE)
    fill_rect(620, 420, 638, 472, OUTLINE)
    # head
    rounded_rect(300, 330, 620, 592, 38, OUTLINE)
    rounded_rect(308, 338, 612, 584, 32, STEEL)
    # face plate
    rounded_rect(336, 380, 584, 560, 22, STEEL_DARK)
    # smug eyebrows (angled down toward the middle)
    thick_line(362, 402, 428, 416, 10, OUTLINE)
    thick_line(558, 402, 492, 416, 10, OUTLINE)
    # glowing eyes
    rounded_rect(362, 428, 430, 472, 12, CYAN)
    rounded_rect(490, 428, 558, 472, 12, CYAN)
    disc(380, 442, 7, WHITE)
    disc(508, 442, 7, WHITE)
    # smirk
    arc(462, 500, 42, 15, 165, 9, OUTLINE)
    # body
    rounded_rect(380, 592, 540, 736, 26, OUTLINE)
    rounded_rect(388, 600, 532, 728, 20, STEEL)
    # chest equaliser bars
    fill_rect(420, 650, 436, 690, CYAN)
    fill_rect(444, 632, 460, 690, CYAN)
    fill_rect(468, 660, 484, 690, CYAN)
    # arm reaching for the phone
    thick_line(540, 660, 656, 636, 22, OUTLINE)
    thick_line(540, 660, 656, 636, 12, STEEL)

    # --- phone with the posted photo ---------------------------------------
    rounded_rect(648, 380, 868, 706, 26, PHONE)
    fill_rect(668, 400, 848, 686, SCREEN)
    # the embarrassing photo: party-hat stick figure on pink
    fill_rect(668, 400, 848, 560, PHOTO_BG)
    disc(758, 470, 26, SKIN)
    triangle(730, 452, 786, 452, 758, 404, HAT)
    disc(758, 402, 8, WHITE)
    thick_line(758, 498, 758, 552, 8, INK)
    thick_line(758, 516, 724, 544, 7, INK)
    thick_line(758, 516, 792, 544, 7, INK)
    # posted label + full upload bar + view count
    draw_centered_at(758, 578, "POSTED!", 4, RED)
    fill_rect(688, 616, 828, 640, (220, 228, 230))
    fill_rect(688, 616, 828, 640, GREEN)
    draw_centered_at(758, 652, "2.4M VIEWS", 3, INK)

    # --- punchline ---------------------------------------------------------
    draw_centered(786, "IT POSTED THEM FIRST.", 7, RED)
    draw_centered(856, "FOR CLOSURE.", 10, INK)


def main():
    draw_scene()
    data = encode_png()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(data)
    print(f"wrote {OUT} {len(data)} bytes")


if __name__ == "__main__":
    main()
