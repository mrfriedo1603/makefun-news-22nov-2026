#!/usr/bin/env python3
"""Sum up 22 November 2026's world news in one image.

Pure standard-library program. No network access at runtime, no external
fonts or images. Renders a 1024x1024 newspaper-style front page as a PNG
using an embedded vector stroke font and a hand-written PNG encoder.

Output: writes entry.png into the directory named by MAKEFUN_OUTPUT_DIR
(default "out" for local testing; the sandbox sets it to /output).

Deterministic: same input always produces byte-identical output.
"""

import binascii
import os
import struct
import sys
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedded vector stroke font.
# Each glyph is a list of strokes; each stroke is a list of (x, y) points
# on a 5-wide by 13-tall grid. Baseline is y=10, cap top is y=0, the
# x-height top is y=3.5, descenders reach y=13. Advance is 6 units.
# ---------------------------------------------------------------------------

FONT = {
    "A": [[(0, 10), (2.5, 0), (5, 10)], [(1.3, 6.5), (3.7, 6.5)]],
    "B": [[(0, 0), (0, 10)],
          [(0, 0), (3, 0), (5, 1.5), (5, 3.5), (3, 5), (0, 5)],
          [(0, 5), (3, 5), (5, 6.5), (5, 8.5), (3, 10), (0, 10)]],
    "C": [[(5, 2), (3, 0), (1, 0), (0, 2), (0, 8), (1, 10), (3, 10), (5, 8)]],
    "D": [[(0, 0), (0, 10)], [(0, 0), (3, 0), (5, 2), (5, 8), (3, 10), (0, 10)]],
    "E": [[(0, 0), (0, 10)], [(0, 0), (5, 0)], [(0, 5), (3.5, 5)], [(0, 10), (5, 10)]],
    "F": [[(0, 0), (0, 10)], [(0, 0), (5, 0)], [(0, 5), (3.5, 5)]],
    "G": [[(5, 2), (3, 0), (1, 0), (0, 2), (0, 8), (1, 10), (3, 10), (5, 8), (5, 5), (2.5, 5)]],
    "H": [[(0, 0), (0, 10)], [(5, 0), (5, 10)], [(0, 5), (5, 5)]],
    "I": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 10)], [(0, 10), (5, 10)]],
    "J": [[(1, 0), (5, 0)], [(4, 0), (4, 8), (2.5, 10), (1, 10), (0, 8)]],
    "K": [[(0, 0), (0, 10)], [(5, 0), (0, 5)], [(1.5, 6), (5, 10)]],
    "L": [[(0, 0), (0, 10)], [(0, 10), (5, 10)]],
    "M": [[(0, 10), (0, 0), (2.5, 5), (5, 0), (5, 10)]],
    "N": [[(0, 10), (0, 0), (5, 10), (5, 0)]],
    "O": [[(1, 0), (4, 0), (5, 2), (5, 8), (4, 10), (1, 10), (0, 8), (0, 2), (1, 0)]],
    "P": [[(0, 0), (0, 10)], [(0, 0), (3.5, 0), (5, 2), (5, 3.5), (3.5, 5), (0, 5)]],
    "Q": [[(1, 0), (4, 0), (5, 2), (5, 8), (4, 10), (1, 10), (0, 8), (0, 2), (1, 0)],
          [(3, 7), (5.5, 10.5)]],
    "R": [[(0, 0), (0, 10)], [(0, 0), (3.5, 0), (5, 2), (5, 3.5), (3.5, 5), (0, 5)],
          [(2.5, 5), (5, 10)]],
    "S": [[(5, 2), (4, 0), (1, 0), (0, 2), (0, 4), (1, 5), (4, 5), (5, 6), (5, 8), (4, 10), (1, 10), (0, 8)]],
    "T": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 10)]],
    "U": [[(0, 0), (0, 8), (1, 10), (4, 10), (5, 8), (5, 0)]],
    "V": [[(0, 0), (2.5, 10), (5, 0)]],
    "W": [[(0, 0), (1.2, 10), (2.5, 4), (3.8, 10), (5, 0)]],
    "X": [[(0, 0), (5, 10)], [(5, 0), (0, 10)]],
    "Y": [[(0, 0), (2.5, 5)], [(5, 0), (2.5, 5)], [(2.5, 5), (2.5, 10)]],
    "Z": [[(0, 0), (5, 0), (0, 10), (5, 10)]],
    "a": [[(0.5, 5), (2, 3.5), (3.5, 3.5), (4.5, 5), (4.5, 8), (3.5, 10), (2, 10), (0.5, 8), (0.5, 5)],
          [(4.5, 3.5), (4.5, 10)]],
    "b": [[(0, 0), (0, 10)],
          [(0, 6), (1, 4), (3, 3.5), (4.5, 5), (4.5, 8), (3, 10), (1, 10), (0, 8)]],
    "c": [[(4.5, 5), (3, 3.5), (1, 3.5), (0, 5), (0, 8), (1, 10), (3, 10), (4.5, 8.5)]],
    "d": [[(0.5, 5), (2, 3.5), (3.5, 3.5), (4.5, 5), (4.5, 8), (3.5, 10), (2, 10), (0.5, 8), (0.5, 5)],
          [(4.5, 0), (4.5, 10)]],
    "e": [[(4.5, 8), (3.5, 10), (1.5, 10), (0.5, 8), (0.5, 5.5), (1.5, 3.5),
           (3.5, 3.5), (4.5, 5.5), (4.5, 6.8), (0.5, 6.8)]],
    "f": [[(3.5, 0), (1.5, 0), (0.5, 2), (0.5, 10)], [(0, 6), (3, 6)]],
    "g": [[(0.5, 5), (2, 3.5), (3.5, 3.5), (4.5, 5), (4.5, 8), (3.5, 10), (2, 10), (0.5, 8), (0.5, 5)],
          [(4.5, 3.5), (4.5, 10), (3, 13), (1, 13), (0.5, 11)]],
    "h": [[(0, 0), (0, 10)], [(0, 6), (1, 4), (3, 3.5), (4.5, 5), (4.5, 10)]],
    "i": [[(2, 3.5), (2, 10)], [(2, 0.6), (2, 1.4)]],
    "j": [[(3.5, 3.5), (3.5, 10), (2, 13), (0.5, 13)], [(3.5, 0.6), (3.5, 1.4)]],
    "k": [[(0, 0), (0, 10)], [(4.5, 3.5), (1, 6.5)], [(2, 7.5), (4.5, 10)]],
    "l": [[(2.5, 0), (2.5, 10)]],
    "m": [[(0, 3.5), (0, 10)], [(0, 5), (1, 3.5), (2.5, 3.5), (2.5, 10)],
          [(2.5, 5), (3.5, 3.5), (5, 3.5), (5, 10)]],
    "n": [[(0, 3.5), (0, 10)], [(0, 5), (1, 3.5), (3, 3.5), (4.5, 5), (4.5, 10)]],
    "o": [[(1, 4), (3, 3.5), (4.5, 5), (4.5, 8), (3, 10), (1, 10), (0, 8), (0, 5), (1, 4)]],
    "p": [[(0, 3.5), (0, 13)],
          [(0, 6), (1, 4), (3, 3.5), (4.5, 5), (4.5, 8), (3, 10), (1, 10), (0, 8)]],
    "q": [[(0.5, 5), (2, 3.5), (3.5, 3.5), (4.5, 5), (4.5, 8), (3.5, 10), (2, 10), (0.5, 8), (0.5, 5)],
          [(4.5, 3.5), (4.5, 13)]],
    "r": [[(0, 3.5), (0, 10)], [(0, 5), (1, 3.5), (3, 3.5), (4, 4.5)]],
    "s": [[(4.5, 5), (3.5, 3.5), (1.5, 3.5), (0.5, 5), (0.5, 6.5), (1.5, 7.5),
           (3.5, 7.5), (4.5, 8.5), (4.5, 9.5), (3.5, 10), (1.5, 10), (0.5, 9)]],
    "t": [[(2, 0), (2, 10)], [(1, 10), (3.5, 10)], [(0.5, 4), (3.5, 4)]],
    "u": [[(0, 3.5), (0, 8), (1, 10), (3.5, 10), (4.5, 8), (4.5, 3.5)]],
    "v": [[(0, 3.5), (2.5, 10), (5, 3.5)]],
    "w": [[(0, 3.5), (1.2, 10), (2.5, 5), (3.8, 10), (5, 3.5)]],
    "x": [[(0, 3.5), (5, 10)], [(5, 3.5), (0, 10)]],
    "y": [[(0, 3.5), (2.5, 10), (5, 3.5)], [(4, 6.5), (2.5, 10), (2.5, 13)]],
    "z": [[(0, 3.5), (5, 3.5), (0, 10), (5, 10)]],
    "0": [[(1, 0), (4, 0), (5, 2), (5, 8), (4, 10), (1, 10), (0, 8), (0, 2), (1, 0)]],
    "1": [[(1, 2), (3, 0), (3, 10)], [(0.5, 10), (4, 10)]],
    "2": [[(0.5, 2), (1.5, 0), (3.5, 0), (4.5, 2), (4.5, 4), (0.5, 10), (5, 10)]],
    "3": [[(0.5, 2), (1.5, 0), (3.5, 0), (4.5, 2), (4.5, 4), (3, 5.5)],
          [(3, 5.5), (4.5, 6.5), (4.5, 8.5), (3.5, 10), (1.5, 10), (0.5, 8.5)]],
    "4": [[(3.5, 0), (0.5, 6), (4.5, 6)], [(3.5, 0), (3.5, 10)]],
    "5": [[(5, 0), (0.5, 0), (0.5, 5), (3, 5), (4.5, 6.5), (4.5, 8.5), (3.5, 10), (1.5, 10), (0.5, 8.5)]],
    "6": [[(4.5, 1.5), (3, 0), (1, 0), (0, 2), (0, 8), (1, 10), (3, 10), (4.5, 8), (4.5, 6), (3, 5), (1, 5)]],
    "7": [[(0, 0), (5, 0), (2, 10)]],
    "8": [[(2, 0), (4, 1), (4, 4), (2, 5), (4, 6), (4, 9), (2, 10), (0, 9), (0, 6), (2, 5), (0, 4), (0, 1), (2, 0)]],
    "9": [[(0.5, 8.5), (2, 10), (4, 10), (5, 8), (5, 2), (4, 0), (2, 0), (0.5, 2), (0.5, 4), (2, 5), (4, 5)]],
    " ": [],
    ".": [[(2.3, 9.2), (2.7, 9.2)]],
    ",": [[(2.3, 9.2), (2.7, 9.2)], [(2.5, 10), (1.8, 12.5)]],
    ":": [[(2.3, 4.2), (2.7, 4.2)], [(2.3, 9.2), (2.7, 9.2)]],
    "-": [[(0.5, 6.5), (4.5, 6.5)]],
    "/": [[(4.5, 0), (0.5, 10)]],
}

ADVANCE = 6.0      # font units per character, including spacing
CELL_HEIGHT = 13.0  # font units from cap top (0) to descender bottom (13)


def _disc_offsets(radius):
    """Integer (dx, dy) offsets inside a disc of the given radius."""
    offsets = []
    r = int(radius)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= radius * radius:
                offsets.append((dx, dy))
    return offsets


class Canvas:
    """A plain RGB raster canvas with thick-line and text drawing."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, background)
        self._discs = {}

    def _disc(self, radius):
        if radius not in self._discs:
            self._discs[radius] = _disc_offsets(radius)
        return self._discs[radius]

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i] = color[0]
            self.pixels[i + 1] = color[1]
            self.pixels[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.width, int(x + w))
        y1 = min(self.height, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        row = bytes((r, g, b)) * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * self.width + x0) * 3
            self.pixels[start:start + len(row)] = row

    def draw_disc(self, cx, cy, radius, color):
        for dx, dy in self._disc(radius):
            self.set_pixel(int(cx) + dx, int(cy) + dy, color)

    def draw_line(self, x0, y0, x1, y1, width, color):
        """Thick line from (x0, y0) to (x1, y1), round caps."""
        radius = max(0.6, width / 2.0)
        dx = x1 - x0
        dy = y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        steps = max(1, int(dist * 2) + 1)
        for i in range(steps + 1):
            t = i / steps
            self.draw_disc(x0 + dx * t, y0 + dy * t, radius, color)

    def draw_circle(self, cx, cy, radius, width, color, segments=48):
        import math
        prev = None
        for i in range(segments + 1):
            a = 2.0 * math.pi * i / segments
            px = cx + radius * math.cos(a)
            py = cy + radius * math.sin(a)
            if prev is not None:
                self.draw_line(prev[0], prev[1], px, py, width, color)
            prev = (px, py)

    # -- text ---------------------------------------------------------------

    def text_width(self, text, size, tracking=0.0):
        scale = size / CELL_HEIGHT
        width = 0.0
        for ch in text:
            if ch not in FONT:
                raise ValueError("no glyph for character: %r" % ch)
            width += ADVANCE * scale + tracking
        if text:
            width -= tracking
        return width

    def draw_text(self, x, y, text, size, color, tracking=0.0):
        """Draw text with its top at y. Returns the width drawn."""
        scale = size / CELL_HEIGHT
        stroke = max(1.4, 1.15 * scale)
        cx = float(x)
        for ch in text:
            strokes = FONT[ch]
            for stroke_pts in strokes:
                for i in range(len(stroke_pts) - 1):
                    ax, ay = stroke_pts[i]
                    bx, by = stroke_pts[i + 1]
                    self.draw_line(cx + ax * scale, y + ay * scale,
                                   cx + bx * scale, y + by * scale,
                                   stroke, color)
                if len(stroke_pts) == 1:
                    ax, ay = stroke_pts[0]
                    self.draw_disc(cx + ax * scale, y + ay * scale, stroke / 2.0, color)
            cx += ADVANCE * scale + tracking
        return cx - x - (tracking if text else 0.0)

    def draw_text_centered(self, cx, y, text, size, color, tracking=0.0):
        w = self.text_width(text, size, tracking)
        self.draw_text(cx - w / 2.0, y, text, size, color, tracking)
        return w

    def wrap_text(self, text, size, max_width, tracking=0.0):
        """Greedy word wrap. Returns a list of lines."""
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if self.text_width(trial, size, tracking) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines


def encode_png(width, height, pixels):
    """Encode RGB pixels (bytearray) as a deterministic PNG."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: None
        start = y * stride
        raw += pixels[start:start + stride]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b""))

# ---------------------------------------------------------------------------
# Content: the news of Sunday 22 November 2026.
# Every item below was reported on that date by the sources named in the
# footer of the image. Wording is kept factual; no speculation is stated
# as fact. Casualty figures are the figures reported on 22 November.
# ---------------------------------------------------------------------------

PAPER = (250, 246, 238)
INK = (17, 24, 39)
MUTED = (82, 88, 99)
RED = (185, 28, 28)
NAVY = (30, 58, 95)
DARK = (17, 24, 39)
RULE = (208, 202, 190)
TICKER_BG = (232, 227, 216)

LEAD = {
    "num": "1",
    "tag": "CLIMATE - LEAD STORY",
    "headline": "COP31 collapses in Antalya",
    "summary": ("UN climate talks end with no deal after the EU rejects a draft "
                "that omits fossil fuels, the main cause of warming."),
}

STORIES = [
    {
        "num": "2",
        "tag": "RUSSIA-UKRAINE WAR",
        "headline": "Warship hit at Benghazi",
        "summary": ("Suspected Ukrainian sea drones strike the Russian corvette "
                    "Merkury at a Libyan naval base, causing a blast and fire."),
    },
    {
        "num": "3",
        "tag": "MIDDLE EAST",
        "headline": "Tankers hit by mines off Hormuz",
        "summary": ("Two supertankers catch fire after hitting mines east of the "
                    "Strait of Hormuz as Iran-US tensions grip the Gulf."),
    },
    {
        "num": "4",
        "tag": "UKRAINE",
        "headline": "Strike hits flats near Kyiv",
        "summary": ("A Russian strike hits an apartment block near Kyiv, killing "
                    "at least two people and leaving others feared trapped."),
    },
    {
        "num": "5",
        "tag": "ASIA - DISASTER",
        "headline": "Factory fire in Indonesia",
        "summary": ("A fire at a candy factory in Cikande kills at least three "
                    "workers, with 36 more reported missing."),
    },
]

LAST = {
    "num": "6",
    "tag": "UNITED STATES",
    "headline": "Delta glitch grounds Atlanta",
    "summary": ("A weight-and-balance system failure delays more than 1,000 "
                "Delta flights at Atlanta days before Thanksgiving."),
}

BRIEFS = [
    "SPORT: Verstappen wins the Las Vegas GP by 0.639s from Norris.",
    "ASIA: Nepal PM Balendra Shah begins a two-day visit to India.",
    "ASIA: South Korea education chief quits over AI exam cheating.",
]

FOOTER = "Sources: AP / Reuters / CNN / AFP / Formula 1. Events as reported on 22 Nov 2026."


def draw_badge(canvas, x, y, num, size=30):
    canvas.fill_rect(x, y, size, size, NAVY)
    canvas.draw_text_centered(x + size / 2.0, y + 3, num, size - 6, (255, 255, 255))


def draw_story(canvas, x, y, width, story, head_size, body_size, max_body_lines=3):
    """Draw one story block. Returns the height used."""
    canvas.fill_rect(x, y, 4, 8, RED)
    canvas.draw_text(x + 12, y - 2, story["tag"], 19, RED)
    hy = y + 24
    head_lines = canvas.wrap_text(story["headline"], head_size, width)
    for line in head_lines:
        canvas.draw_text(x, hy, line, head_size, INK)
        hy += int(head_size * 1.08)
    by = hy + 2
    body_lines = canvas.wrap_text(story["summary"], body_size, width)[:max_body_lines]
    for line in body_lines:
        canvas.draw_text(x, by, line, body_size, INK)
        by += int(body_size * 1.22)
    return by - y


def build_image():
    width, height = 1024, 1024
    c = Canvas(width, height, PAPER)
    margin = 44
    content = width - 2 * margin  # 936

    # Masthead.
    y = 22
    c.draw_text_centered(width / 2.0, y, "THE WORLD IN ONE PAGE", 64, INK, tracking=5.0)
    y += 68
    c.draw_text_centered(width / 2.0, y, "SUNDAY EDITION - ONE DAY, ONE PAGE", 21, RED, tracking=2.0)
    y += 26
    c.fill_rect(margin, y, content, 3, RED)
    y += 6
    c.fill_rect(margin, y, content, 1, RULE)
    y += 12

    # Date band: the single most important element.
    band_h = 72
    c.fill_rect(margin, y, content, band_h, NAVY)
    c.draw_text_centered(width / 2.0, y + 10, "SUNDAY, 22 NOVEMBER 2026", 52, (255, 255, 255), tracking=1.0)
    y += band_h + 10
    c.draw_text_centered(width / 2.0, y, "Six stories that defined the day - from Antalya to Atlanta",
                         25, INK)
    y += 34

    # Lead story, full width.
    draw_badge(c, margin, y, LEAD["num"])
    c.draw_text(margin + 40, y + 2, LEAD["tag"], 20, RED)
    hy = y + 28
    c.draw_text(margin, hy, LEAD["headline"], 42, INK)
    hy += 48
    lead_lines = c.wrap_text(LEAD["summary"], 26, content)
    for line in lead_lines:
        c.draw_text(margin, hy, line, 26, INK)
        hy += 32
    y = hy + 10
    c.fill_rect(margin, y, content, 1, RULE)
    y += 14

    # Stories 2-5 in a two-column grid.
    col_w = (content - 32) // 2
    row_h = 152
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        sx = margin + col * (col_w + 32)
        sy = y + row * row_h
        if col == 1:
            c.fill_rect(sx - 16, sy, 1, row_h - 12, RULE)
        draw_badge(c, sx, sy, story["num"], size=28)
        c.draw_text(sx + 36, sy + 2, story["tag"], 18, RED)
        hy2 = sy + 30
        head_lines = c.wrap_text(story["headline"], 31, col_w)
        for line in head_lines:
            c.draw_text(sx, hy2, line, 31, INK)
            hy2 += 36
        by = hy2 + 2
        body_lines = c.wrap_text(story["summary"], 23, col_w)[:3]
        for line in body_lines:
            c.draw_text(sx, by, line, 23, INK)
            by += 28
    y += 2 * row_h + 6
    c.fill_rect(margin, y, content, 1, RULE)
    y += 12

    # Story 6, full width.
    draw_badge(c, margin, y, LAST["num"])
    c.draw_text(margin + 40, y + 2, LAST["tag"], 20, RED)
    hy = y + 28
    c.draw_text(margin, hy, LAST["headline"], 32, INK)
    hy += 38
    last_lines = c.wrap_text(LAST["summary"], 24, content)
    for line in last_lines:
        c.draw_text(margin, hy, line, 24, INK)
        hy += 29
    y = hy + 10

    # Ticker band: three more stories from the same day.
    tick_h = 92
    c.fill_rect(margin, y, content, tick_h, TICKER_BG)
    c.fill_rect(margin, y, content, 3, RED)
    c.draw_text(margin + 16, y + 8, "ALSO ON 22 NOVEMBER", 19, RED)
    ty = y + 30
    for brief in BRIEFS:
        c.draw_text(margin + 16, ty, brief, 19, INK)
        ty += 21
    y += tick_h + 6

    # Footer with sources.
    c.draw_text_centered(width / 2.0, y, FOOTER, 17, MUTED)
    y += 20
    if y > height - 20:
        raise RuntimeError("layout overflow: final y=%d" % y)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    out_path = Path(out_dir) / "entry.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = build_image()
    data = encode_png(canvas.width, canvas.height, canvas.pixels)
    out_path.write_bytes(data)
    print("wrote %s (%d bytes, %dx%d)" % (out_path, len(data), canvas.width, canvas.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
