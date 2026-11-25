#!/usr/bin/env python3
"""Draw one image that sums up the world news of Tuesday 24 November 2026.

Standard library only: zlib, struct, os, sys. No network, no image library, no
font files. The type is a 5x7 bitmap alphabet carried in this file, stamped at
whole-pixel scales, and the page is an RGB byte buffer written out as a PNG.
Nothing here reads the clock or a random source, so two runs write the same
bytes.

The page is a front page: a masthead naming the day, a wireframe globe, and a
grid of eight stories, each with an eyebrow, a headline, a short deck and its
sources.
"""

import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# The day the page sums up. Nothing else on the page depends on the clock.
DAY = "TUESDAY 24 NOVEMBER 2026"

PAPER = (244, 239, 228)
INK = (21, 22, 26)
RED = (176, 42, 32)
MUTED = (110, 105, 96)
RULE = (205, 197, 183)

# ---------------------------------------------------------------- the alphabet
# Five columns by seven rows a glyph, "1" for ink. Only what the page needs.

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "01100", "01000"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
}

GLYPH_COLS = 5
GLYPH_ROWS = 7
TRACKING = 1


class Canvas(object):
    """An RGB buffer with the few primitives the page needs."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.buf = bytearray(background * (width * height))

    def rect(self, x, y, w, h, colour):
        """Fill an axis-aligned rectangle, clipped to the canvas."""
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.width, int(x + w))
        y1 = min(self.height, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        run = bytes(colour) * (x1 - x0)
        stride = self.width * 3
        for row in range(y0, y1):
            start = row * stride + x0 * 3
            self.buf[start:start + len(run)] = run

    def shape(self, x0, y0, x1, y1, inside, colour, samples=4):
        """Paint every point where inside(x, y) holds, with soft edges.

        Each pixel is tested on a samples by samples grid and given the share of
        those tests that fell inside, so curves and diagonals do not stair-step.
        """
        step = 1.0 / samples
        offset = step / 2.0
        total = float(samples * samples)
        red, green, blue = colour
        buf = self.buf
        stride = self.width * 3
        for py in range(max(0, int(y0)), min(self.height, int(y1) + 1)):
            for px in range(max(0, int(x0)), min(self.width, int(x1) + 1)):
                hit = 0
                for sy in range(samples):
                    fy = py + offset + sy * step
                    for sx in range(samples):
                        if inside(px + offset + sx * step, fy):
                            hit += 1
                if not hit:
                    continue
                index = py * stride + px * 3
                if hit == samples * samples:
                    buf[index] = red
                    buf[index + 1] = green
                    buf[index + 2] = blue
                else:
                    cover = hit / total
                    buf[index] = int(buf[index] + (red - buf[index]) * cover)
                    buf[index + 1] = int(buf[index + 1] + (green - buf[index + 1]) * cover)
                    buf[index + 2] = int(buf[index + 2] + (blue - buf[index + 2]) * cover)


def advance(scale):
    """Distance from one glyph's left edge to the next, in pixels."""
    return (GLYPH_COLS + TRACKING) * scale


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * advance(scale) - TRACKING * scale


def draw_text(canvas, x, y, text, scale, colour):
    """Draw one line of capitals; returns the x just past its last glyph."""
    step = advance(scale)
    pen = int(x)
    for character in text.upper():
        glyph = FONT.get(character) or FONT["?"]
        for row in range(GLYPH_ROWS):
            bits = glyph[row]
            col = 0
            while col < GLYPH_COLS:
                if bits[col] == "1":
                    run = 1
                    while col + run < GLYPH_COLS and bits[col + run] == "1":
                        run += 1
                    canvas.rect(pen + col * scale, y + row * scale, run * scale, scale, colour)
                    col += run
                else:
                    col += 1
        pen += step
    return pen - TRACKING * scale


def wrap(text, scale, max_width):
    """Greedy word wrap, measured in whole glyph advances."""
    limit = int((max_width + TRACKING * scale) // advance(scale))
    lines = []
    line = ""
    for word in text.upper().split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= limit:
            line = line + " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# --------------------------------------------------------------- the day's news
# Each story's headline is set by hand in two lines, so the page keeps a shape
# no automatic wrap would give it. The deck runs to three lines at most.

STORIES = [
    {
        "eyebrow": "TECHNOLOGY / LAW",
        "headline": ("HUAWEI GUILTY", "IN U.S. TRIAL"),
        "deck": "Jury convicts the telecom giant of trade-secret conspiracy and bank fraud.",
        "source": "AP / REUTERS",
    },
    {
        "eyebrow": "EUROPE / SECURITY",
        "headline": ("RUSSIAN DRONE", "OVER POLAND"),
        "deck": "Warsaw says a Russian drone crossed its airspace during strikes on Ukraine.",
        "source": "REUTERS",
    },
    {
        "eyebrow": "MIDDLE EAST / ENERGY",
        "headline": ("HORMUZ OIL", "UNDER STRAIN"),
        "deck": "Fresh attacks on vessels threaten oil flows through the strategic strait.",
        "source": "AL JAZEERA / WSJ",
    },
    {
        "eyebrow": "AFRICA / HEALTH",
        "headline": ("EBOLA TEAMS", "TRAPPED IN DRC"),
        "deck": "WHO says medical teams are trapped by fighting in the Ituri region.",
        "source": "WHO / UN",
    },
    {
        "eyebrow": "ASIA / SPACE",
        "headline": ("SHENZHOU-24", "CREW NAMED"),
        "deck": "Muhammad Zeeshan Ali of Pakistan to be Tiangong's first foreign astronaut.",
        "source": "AP / REUTERS",
    },
    {
        "eyebrow": "LATIN AMERICA",
        "headline": ("BOMBING HITS", "VILLAVICENCIO"),
        "deck": "Injuries reported as a bombing hits the city amid rising urban violence.",
        "source": "AP / EFE",
    },
    {
        "eyebrow": "SPORT / AFRICA",
        "headline": ("SENEGAL REGAINS", "AFCON TITLE"),
        "deck": "Court restores Senegal as 2025 Africa Cup of Nations champion on appeal.",
        "source": "AFP / EURONEWS",
    },
    {
        "eyebrow": "CLIMATE",
        "headline": ("NO CLIMATE PACT", "AFTER COP31"),
        "deck": "Analysis on 24 November cites splits over fossil fuels and finance.",
        "source": "REUTERS",
    },
]


def draw_globe(canvas, cx, cy, radius, colour=INK):
    """A wireframe globe: outline, equator and two meridians."""
    stroke = 3.2
    canvas.shape(
        cx - radius - stroke, cy - radius - stroke,
        cx + radius + stroke, cy + radius + stroke,
        lambda x, y: abs(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 - radius) <= stroke / 2.0,
        colour,
    )

    band = stroke * 0.62
    canvas.shape(
        cx - radius, cy - band, cx + radius, cy + band,
        lambda x, y: abs(y - cy) <= band and abs(x - cx) <= radius,
        colour,
    )

    for spread in (0.46, 0.78):
        rx = radius * spread
        ry = float(radius)
        half = stroke * 0.52
        canvas.shape(
            cx - rx - half, cy - ry - half, cx + rx + half, cy + ry + half,
            lambda x, y, rx=rx, ry=ry, half=half: _ellipse_edge(x - cx, y - cy, rx, ry) <= half,
            colour,
        )


def _ellipse_edge(dx, dy, rx, ry):
    """Distance from a point to the ellipse dx^2/rx^2 + dy^2/ry^2 = 1, near it."""
    value = (dx / rx) ** 2 + (dy / ry) ** 2
    gradient = 2.0 * (((dx / (rx * rx)) ** 2 + (dy / (ry * ry)) ** 2) ** 0.5)
    if gradient == 0.0:
        return abs(dy) - ry
    return abs(value - 1.0) / gradient


def build_page(warnings=None):
    canvas = Canvas(WIDTH, HEIGHT, PAPER)
    margin = 32

    draw_text(canvas, margin, 30, "WORLD NEWS", 11, INK)
    draw_globe(canvas, 902, 68, 46)

    bar_top = 118
    bar_height = 58
    canvas.rect(margin, bar_top, WIDTH - 2 * margin, bar_height, RED)
    date_scale = 6
    draw_text(canvas, margin + 16, bar_top + 8, DAY, date_scale, PAPER)

    canvas.rect(margin, 190, WIDTH - 2 * margin, 6, INK)
    canvas.rect(margin, 202, WIDTH - 2 * margin, 1, RULE)

    body_top = 218
    body_bottom = 1002
    rows = 4
    row_height = (body_bottom - body_top) // rows
    gutter = 24
    column_width = (WIDTH - 2 * margin - gutter) // 2
    lefts = (margin, margin + column_width + gutter)

    eyebrow_scale = 3
    headline_scale = 5
    deck_scale = 3

    for index, story in enumerate(STORIES):
        row = index // 2
        column = index % 2
        left = lefts[column]
        top = body_top + row * row_height
        y = top + 2

        draw_text(canvas, left, y, story["eyebrow"], eyebrow_scale, RED)
        number = "%02d" % (index + 1)
        draw_text(canvas, left + column_width - text_width(number, eyebrow_scale), y,
                  number, eyebrow_scale, RED)
        y += GLYPH_ROWS * eyebrow_scale + 7

        for line in story["headline"]:
            if text_width(line, headline_scale) > column_width:
                warnings.append("headline too wide: %s" % line)
            draw_text(canvas, left, y, line, headline_scale, INK)
            y += 34
        if len(story["headline"]) > 2:
            warnings.append("headline over two lines: %s" % story["headline"][0])

        y += 6
        deck_lines = wrap(story["deck"], deck_scale, column_width)
        if len(deck_lines) > 3:
            warnings.append("deck over three lines: %s" % story["deck"])
        for line in deck_lines:
            draw_text(canvas, left, y, line, deck_scale, INK)
            y += 21

        y += 4
        if text_width(story["source"], deck_scale) > column_width:
            warnings.append("source too wide: %s" % story["source"])
        draw_text(canvas, left, y, story["source"], deck_scale, MUTED)

        if y + GLYPH_ROWS * deck_scale > top + row_height - 4:
            warnings.append("story overflows its cell: %s" % story["source"])

    for row in range(1, rows):
        y = body_top + row * row_height
        canvas.rect(margin, y - 7, WIDTH - 2 * margin, 1, RULE)

    canvas.rect(margin + column_width + gutter // 2, body_top, 1,
                body_bottom - body_top - 2, RULE)
    return canvas


def write_png(path, canvas):
    raw = bytearray()
    stride = canvas.width * 3
    for row in range(canvas.height):
        raw.append(0)
        raw.extend(canvas.buf[row * stride:(row + 1) * stride])

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)
    return len(png)


def output_path():
    directory = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "entry.png")


def main():
    warnings = []
    canvas = build_page(warnings)
    path = output_path()
    size = write_png(path, canvas)
    sys.stdout.write("wrote %s (%d x %d, %d bytes)\n" % (path, WIDTH, HEIGHT, size))
    for warning in warnings:
        sys.stdout.write("warning: %s\n" % warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
