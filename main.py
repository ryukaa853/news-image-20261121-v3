#!/usr/bin/env python3
"""The World in One Day -- Saturday, 21 November 2026.

A make.fun news-image-20261121 entry (v3). Pure standard library: the
program draws a one-page newspaper front page for the day's world news
and writes it as a 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output/entry.png).

No network, no clock, no randomness: two runs write byte-identical
output. Every story on the page happened, or was first reported, on
Saturday 21 November 2026, and each one is labelled with the outlet
that reported it. Sources are listed in the page footer.

Layout (1024 x 1024), one clear newspaper front page:
  * masthead with the date in huge type
  * lead story: Iran strikes at U.S. bases in Bahrain, over a drawn
    map of the Gulf
  * second row: the missile on Kryvyi Rih / Poland, and the market
    sell-off, each with its own drawn scene
  * third row: the Chapo Isidro capture, COP31 overtime, the ship
    ablaze in the Gulf of Finland
  * a ticker band with the rest of the day, by the numbers
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)   # newsprint cream
INK = (22, 22, 22)        # headline black
RED = (178, 38, 28)       # breaking red
BLUE = (31, 78, 121)      # deep news blue
NAVY = (18, 44, 70)       # Gulf night sea
SEA = (28, 66, 102)       # lighter sea
SAND = (214, 196, 152)    # land
GOLD = (176, 141, 58)     # medal / badge gold
GREY = (112, 108, 98)     # small-print grey
LIGHT = (233, 227, 212)   # panel tint
WHITE = (255, 255, 255)
FLAME = (232, 116, 26)    # explosion orange
EMBER = (248, 196, 58)    # explosion yellow
SMOKE = (120, 122, 126)
DUSK = (52, 68, 92)       # evening sky over Kryvyi Rih
TEAL = (23, 94, 84)       # COP green-teal
SKY = (178, 208, 224)     # pale Baltic sky


# ---------------------------------------------------------------- canvas
class Canvas:
    """An RGB framebuffer with small drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x, y, w, c, t=1):
        self.fill_rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.fill_rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        """Bresenham line, thickness t (square brush)."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.fill_rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        """Filled circle."""
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d2 <= (r + 1) ** 2:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        """Filled polygon (scanline fill)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(round(xs[k]))
                xb = int(round(xs[k + 1]))
                self.fill_rect(xa, y, xb - xa + 1, 1, c)

    def star(self, cx, cy, r_out, r_in, points, c, rot=-90):
        import math
        pts = []
        for i in range(points * 2):
            r = r_out if i % 2 == 0 else r_in
            a = math.radians(rot + i * 180.0 / points)
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        self.poly(pts, c)


# ------------------------------------------------------------------- font
# A 5x7 bitmap font, drawn from scratch for this page. Each glyph is
# seven rows of five bits, '#' on and '.' off. Only capitals, digits
# and the punctuation the page needs.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00010", "00100", "00100", "00100"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "01100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '%': ("10001", "10010", "00010", "00100", "01000", "01001", "10001"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '/': ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    '(': ("00011", "00100", "01000", "01000", "01000", "00100", "00011"),
    ')': ("11000", "00100", "00010", "00010", "00010", "00100", "11000"),
    '&': ("01100", "10010", "10010", "01000", "10101", "10010", "01101"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    '+': ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    '=': ("00000", "00000", "01110", "00000", "01110", "00000", "00000"),
    '•': ("00000", "00000", "01100", "01100", "01100", "00000", "00000"),
    '—': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}


def text_width(text, scale, gap=None):
    """Pixel width of text at a scale (gap = space between glyphs)."""
    if gap is None:
        gap = 1 if scale <= 2 else 2
    if not text:
        return 0
    return len(text) * (5 * scale + gap) - gap


def draw_text(cv, x, y, text, scale, color, gap=None):
    """Draw text with the bitmap font; returns the width drawn."""
    if gap is None:
        gap = 1 if scale <= 2 else 2
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
        cx += 5 * scale + gap
    return cx - x - (gap if text else 0)


def draw_text_centered(cv, cx, y, text, scale, color):
    w = text_width(text, scale)
    draw_text(cv, cx - w // 2, y, text, scale, color)


def wrap_lines(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            if not cur:
                cur = wd
            elif len(cur) + 1 + len(wd) <= max_chars:
                cur += " " + wd
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
    return lines


def draw_para(cv, x, y, text, scale, color, max_chars, leading=None):
    """Draw a wrapped paragraph; returns the y just below the last line."""
    if leading is None:
        leading = 7 * scale + (3 if scale <= 2 else 5)
    for ln in wrap_lines(text, max_chars):
        draw_text(cv, x, y, ln, scale, color)
        y += leading
    return y


def rule(cv, x, y, w, color=INK, t=2):
    cv.hline(x, y, w, color, t)


# --------------------------------------------------------------------- png
def encode_png(cv):
    """Encode the framebuffer as a deterministic RGB PNG (filter 0)."""
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------- scene: gulf
def draw_gulf(cv, x, y, w, h):
    """The Gulf on Saturday night: Bahrain, two U.S. bases, the Strait."""
    cv.fill_rect(x, y, w, h, NAVY)
    # lighter sea band along the bottom (the Gulf)
    cv.fill_rect(x, y + h - 58, w, 58, SEA)
    # Arabian land mass, lower left
    cv.poly([(x, y + h), (x, y + h - 150), (x + 150, y + h - 120),
             (x + 230, y + h - 70), (x + 190, y + h), ], SAND)
    # Qatar / far shore hint, top right
    cv.poly([(x + w - 150, y), (x + w, y), (x + w, y + 46),
             (x + w - 190, y + 30)], SAND)
    # Bahrain island, centre-left, with a red ring
    bx, by = x + 205, y + 128
    cv.poly([(bx - 16, by - 8), (bx + 6, by - 22), (bx + 22, by - 4),
             (bx + 12, by + 18), (bx - 12, by + 14)], SAND)
    cv.ring(bx, by, 30, RED, 3)
    # the two bases, marked as crosses
    for (mx, my) in ((bx - 52, by - 44), (bx + 46, by + 34)):
        cv.line(mx - 8, my, mx + 8, my, WHITE, 3)
        cv.line(mx, my - 8, mx, my + 8, WHITE, 3)
    # missile arcs arcing in from the east (Iran, top right)
    import math
    for (sx, sy, ex, ey, col) in (
            (x + w - 30, y + 26, bx + 8, by - 6, EMBER),
            (x + w - 70, y + 12, bx - 40, by - 38, FLAME),
            (x + w - 12, y + 70, bx + 40, by + 30, EMBER)):
        steps = 26
        px, py = sx, sy
        for i in range(1, steps + 1):
            t = i / steps
            qx = sx + (ex - sx) * t
            qy = sy + (ey - sy) * t - 46 * math.sin(math.pi * t)
            cv.line(int(px), int(py), int(qx), int(qy), col, 3)
            px, py = qx, qy
        cv.disc(int(ex), int(ey), 5, col)
    # explosion starburst over Bahrain
    cv.star(bx, by, 34, 14, 8, EMBER)
    cv.star(bx, by, 20, 8, 8, FLAME)
    cv.disc(bx, by, 8, RED)
    # ships in the Strait, bottom right
    for (sx, sy) in ((x + w - 190, y + h - 30), (x + w - 120, y + h - 24),
                     (x + w - 60, y + h - 32)):
        cv.poly([(sx - 14, sy), (sx + 14, sy), (sx + 10, sy + 8),
                 (sx - 10, sy + 8)], WHITE)
        cv.fill_rect(sx - 3, sy - 10, 6, 10, WHITE)
    # labels
    draw_text(cv, x + 14, y + 12, "THE GULF", 2, WHITE)
    draw_text(cv, bx - 34, by + 44, "BAHRAIN", 2, WHITE)
    draw_text(cv, x + w - 208, y + h - 58, "STRAIT OF HORMUZ", 2, WHITE)
    draw_text(cv, x + 14, y + h - 26, "U.S. FIFTH FLEET", 2, EMBER)
    # small compass rose, top left corner
    cx, cy = x + 26, y + 52
    cv.line(cx, cy - 12, cx, cy + 12, WHITE, 2)
    cv.line(cx - 12, cy, cx + 12, cy, WHITE, 2)
    draw_text(cv, cx - 4, cy - 24, "N", 2, WHITE)


# ------------------------------------------------------------ scene: chart
def draw_chart(cv, x, y, w, h):
    """The sell-off: a red line plunging across a gridded panel."""
    cv.fill_rect(x, y, w, h, WHITE)
    cv.fill_rect(x, y, w, h, LIGHT)
    # grid
    for gx in range(x + 24, x + w, 34):
        cv.vline(gx, y + 12, h - 24, (210, 203, 186), 1)
    for gy in range(y + 12, y + h - 12, 26):
        cv.hline(x + 12, gy, w - 24, (210, 203, 186), 1)
    # the plunge: high left, low right, with a dead-cat bounce mid-way.
    # Points are kept inside the panel (offsets stay below h - 16).
    pts = [(x + 16, y + 14), (x + 70, y + 18), (x + 120, y + 16),
           (x + 170, y + 34), (x + 215, y + 30), (x + 265, y + 52),
           (x + 315, y + 68), (x + 365, y + 64), (x + w - 64, y + h - 22)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 4)
    # arrowhead at the end
    ex, ey = pts[-1]
    cv.line(ex, ey, ex - 16, ey - 2, RED, 4)
    cv.line(ex, ey, ex - 4, ey - 16, RED, 4)
    # axis labels
    draw_text(cv, x + 12, y + h - 20, "MON", 1, GREY)
    draw_text(cv, x + w - 34, y + h - 20, "FRI", 1, RED)
    draw_text(cv, x + w - 96, y + 6, "NASDAQ", 2, INK)


# ------------------------------------------------------------- scene: city
def draw_city(cv, x, y, w, h):
    """Kryvyi Rih at dusk: skyline, a missile streak, smoke. Panel 476x104."""
    cv.fill_rect(x, y, w, h, DUSK)
    # ground band
    cv.fill_rect(x, y + h - 24, w, 24, (38, 50, 70))
    # skyline silhouettes; base sits on the ground band
    import random
    rng = random.Random(21112026)
    base = y + h - 24
    bx = x + 8
    heights = (34, 48, 40, 56, 36, 50, 42, 38, 46)
    widths = (46, 30, 52, 36, 48, 34, 56, 30, 44)
    flag_top = None
    for bw, bh in zip(widths, heights):
        cv.fill_rect(bx, base - bh, bw, bh, (24, 30, 44))
        # lit windows
        for wy in range(base - bh + 8, base - 8, 14):
            for wx in range(bx + 6, bx + bw - 6, 12):
                if rng.random() < 0.4:
                    cv.fill_rect(wx, wy, 5, 6, EMBER)
        if bh == 56:
            flag_top = (bx + 8, base - bh)
        bx += bw + 6
    # Ukrainian colours: a small flag on the tallest block
    if flag_top is not None:
        fx, ft = flag_top
        cv.vline(fx, ft - 14, 14, WHITE, 2)
        cv.fill_rect(fx + 2, ft - 14, 22, 7, (0, 91, 187))
        cv.fill_rect(fx + 2, ft - 7, 22, 7, (255, 213, 0))
    # missile streaking down from the top right
    cv.line(x + w - 16, y + 6, x + 250, y + 70, EMBER, 4)
    cv.line(x + w - 16, y + 6, x + 268, y + 64, FLAME, 3)
    # impact flash + smoke plume over the centre
    ix, iy = x + 250, y + 74
    cv.star(ix, iy, 16, 7, 8, EMBER)
    cv.disc(ix, iy, 6, FLAME)
    for (sx, sy, r) in ((ix - 22, iy - 14, 9), (ix + 2, iy - 22, 11),
                        (ix + 18, iy - 12, 8)):
        cv.disc(sx, sy, r, SMOKE)
    draw_text(cv, x + 12, y + 8, "KRYVYI RIH", 2, WHITE)
    draw_text(cv, x + 12, y + 26, "UKRAINE", 2, EMBER)


# ------------------------------------------------------------ scene: badge
def draw_badge(cv, x, y, w, h):
    """The capture: a gold FBI star over a Sinaloa dusk. Panel 312x78."""
    cv.fill_rect(x, y, w, h, (44, 44, 58))
    # desert horizon
    cv.fill_rect(x, y + h - 20, w, 20, (92, 66, 44))
    cv.poly([(x, y + h - 20), (x + 60, y + h - 38), (x + 130, y + h - 20)],
            (70, 52, 38))
    cv.poly([(x + w - 140, y + h - 20), (x + w - 80, y + h - 36),
             (x + w - 10, y + h - 20)], (70, 52, 38))
    # the star, centred left-of-middle so the cuffs fit at the right
    cx, cy = x + w // 2 - 24, y + 38
    cv.star(cx, cy, 30, 13, 5, GOLD)
    cv.disc(cx, cy, 15, (214, 178, 84))
    cv.disc(cx, cy, 13, GOLD)
    draw_text_centered(cv, cx, cy - 4, "FBI", 1, INK)
    # handcuffs: two linked rings, bottom right
    hx, hy = x + w - 26, y + h - 16
    cv.ring(hx, hy, 7, WHITE, 2)
    cv.ring(hx - 16, hy, 7, WHITE, 2)
    cv.line(hx - 9, hy, hx - 7, hy, WHITE, 2)


# ----------------------------------------------------------- scene: summit
def draw_summit(cv, x, y, w, h):
    """COP31 in Antalya: a warming globe under a low sun. Panel 312x78."""
    cv.fill_rect(x, y, w, h, (214, 232, 228))
    # low sun with rays, top right
    sx, sy = x + w - 40, y + 26
    cv.disc(sx, sy, 12, FLAME)
    for a in range(0, 360, 30):
        import math
        ax = int(sx + 16 * math.cos(math.radians(a)))
        ay = int(sy + 16 * math.sin(math.radians(a)))
        bx = int(sx + 24 * math.cos(math.radians(a)))
        by = int(sy + 24 * math.sin(math.radians(a)))
        cv.line(ax, ay, bx, by, FLAME, 2)
    # the globe
    gx, gy, gr = x + 108, y + 46, 30
    cv.disc(gx, gy, gr, (34, 122, 108))
    # abstract continents
    cv.poly([(gx - 20, gy - 16), (gx - 6, gy - 20), (gx - 1, gy - 9),
             (gx - 12, gy - 3), (gx - 21, gy - 7)], (86, 168, 92))
    cv.poly([(gx + 4, gy + 2), (gx + 18, gy - 3), (gx + 21, gy + 8),
             (gx + 9, gy + 14), (gx + 2, gy + 9)], (86, 168, 92))
    cv.poly([(gx - 16, gy + 12), (gx - 4, gy + 9), (gx - 7, gy + 20),
             (gx - 18, gy + 19)], (86, 168, 92))
    # meridian lines
    cv.ring(gx, gy, gr, (200, 225, 220), 1)
    cv.line(gx - gr, gy, gx + gr, gy, (200, 225, 220), 1)
    draw_text(cv, x + 10, y + 6, "ANTALYA", 2, TEAL)
    draw_text(cv, x + 10, y + 22, "TURKEY", 2, TEAL)


# ------------------------------------------------------------- scene: ship
def draw_ship(cv, x, y, w, h):
    """A sanctioned cargo ship ablaze in the Gulf of Finland. Panel 312x78."""
    cv.fill_rect(x, y, w, h, SKY)
    # pale sun, low, top right
    cv.disc(x + w - 34, y + 18, 10, (240, 222, 160))
    # sea
    cv.fill_rect(x, y + 52, w, h - 52, (46, 88, 122))
    cv.fill_rect(x, y + 52, w, 3, (120, 160, 190))
    # the ship: hull + containers + bridge
    hx, hy = x + 30, y + 38
    cv.poly([(hx, hy), (hx + 200, hy), (hx + 186, hy + 16),
             (hx + 14, hy + 16)], (52, 52, 60))
    for i, col in enumerate(((178, 38, 28), (31, 78, 121), (176, 141, 58))):
        cv.fill_rect(hx + 26 + i * 40, hy - 14, 36, 14, col)
    cv.fill_rect(hx + 152, hy - 26, 30, 26, (230, 230, 225))
    cv.fill_rect(hx + 158, hy - 32, 16, 6, (230, 230, 225))
    # flames licking from the containers
    for (fx, fy, s) in ((hx + 44, hy - 14, 12), (hx + 84, hy - 14, 15),
                        (hx + 124, hy - 14, 11)):
        cv.poly([(fx - s // 2, fy), (fx, fy - s), (fx + s // 2, fy)],
                FLAME)
        cv.poly([(fx - s // 4, fy), (fx, fy - s // 2), (fx + s // 4, fy)],
                EMBER)
    # smoke drifting up, kept inside the panel
    for (sx, sy, r) in ((hx + 52, hy - 30, 6), (hx + 88, hy - 34, 7),
                        (hx + 118, hy - 28, 6)):
        cv.disc(sx, sy, r, SMOKE)
    # waves
    for wx in range(x + 10, x + w - 10, 36):
        cv.line(wx, y + h - 12, wx + 18, y + h - 7, WHITE, 2)


# ------------------------------------------------------------------- layout
def build_page():
    cv = Canvas(W, H, PAPER)
    # top band
    cv.fill_rect(0, 0, W, 8, RED)

    # ---- masthead
    draw_text_centered(cv, W // 2, 18, "THE WORLD IN ONE DAY", 8, INK)
    draw_text_centered(cv, W // 2, 82, "SATURDAY, 21 NOVEMBER 2026", 4, RED)
    rule(cv, 24, 118, W - 48, INK, 2)
    rule(cv, 24, 123, W - 48, INK, 1)

    # ---- lead story: Iran strikes at U.S. bases in Bahrain
    draw_gulf(cv, 24, 130, 524, 258)
    draw_text_centered(cv, 24 + 524 // 2, 396, "MISSILES OVER BAHRAIN, SATURDAY NIGHT",
                       2, GREY)
    draw_text(cv, 572, 130, "THE GULF • LEAD STORY", 2, RED)
    draw_text(cv, 572, 156, "IRAN STRIKES", 4, INK)
    draw_text(cv, 572, 192, "AT U.S. BASES", 4, INK)
    draw_text(cv, 572, 228, "IN BAHRAIN", 4, INK)
    rule(cv, 572, 266, 428, INK, 2)
    draw_para(cv, 572, 278,
              "TEHRAN SAYS ITS MISSILES AND DRONES HIT TWO PATRIOT "
              "RADARS AT AL-RIFFA AND AWALI. BAHRAIN SAYS A CIVILIAN "
              "PLANT BURNED AND ITS DEFENCES STOPPED THE REST. "
              "WASHINGTON DENIES ANY DAMAGE.",
              2, INK, 35, leading=18)
    draw_text(cv, 572, 396, "FIRE ON SITRA ISLAND", 2, RED)
    draw_text(cv, 572, 416, "NO U.S. DAMAGE, SAYS U.S.", 2, INK)
    # Gulf strip, full width
    draw_text_centered(cv, W // 2, 436,
                       "ALSO IN THE GULF: OIL THROUGH HORMUZ DOWN 15%.",
                       2, INK)
    draw_text_centered(cv, W // 2, 454,
                       "TWO PROJECTILE STRIKES NEAR THE STRAIT, UKMTO SAYS.",
                       2, INK)
    rule(cv, 24, 474, W - 48, INK, 2)

    # ---- second row: Kryvyi Rih and the markets
    draw_city(cv, 24, 482, 476, 104)
    draw_text(cv, 24, 592, "RUSSIAN MISSILE", 3, INK)
    draw_text(cv, 24, 618, "HITS KRYVYI RIH", 3, INK)
    draw_para(cv, 24, 646,
              "A BALLISTIC MISSILE KILLED A PARAMEDIC AND A 7-YEAR-OLD "
              "BOY. DEBRIS ALSO LANDED IN POLAND.",
              2, INK, 38, leading=17)
    cv.vline(512, 482, 214, INK, 1)
    draw_chart(cv, 524, 482, 476, 104)
    draw_text(cv, 524, 592, "NASDAQ PLUNGES 5.3%", 3, INK)
    draw_text(cv, 524, 622, "IN A DAY", 3, RED)
    draw_para(cv, 524, 652,
              "S&P 500 INTO CORRECTION. WORST WEEK SINCE 2020.",
              2, INK, 38, leading=17)
    rule(cv, 24, 702, W - 48, INK, 2)

    # ---- third row: capture, climate, ship
    panels = [
        (24, draw_badge, "CHAPO ISIDRO", "CAUGHT IN SINALOA",
         "MEXICO SEIZED THE FBI MOST-WANTED BOSS. AT LEAST 11 DIED "
         "IN THE BACKLASH."),
        (356, draw_summit, "COP31 RUNS PAST", "DEADLINE",
         "TALKS IN ANTALYA DEADLOCKED OVER FOSSIL FUELS. NO DEAL "
         "IN OVERTIME."),
        (688, draw_ship, "SHIP ABLAZE IN", "THE BALTIC",
         "DRONES SET A RUSSIAN SHIP ABLAZE. IT DRIFTED INTO FINNISH "
         "WATERS."),
    ]
    for (px, scene, h1, h2, deck) in panels:
        scene(cv, px, 708, 312, 78)
        draw_text(cv, px, 792, h1, 2, INK)
        draw_text(cv, px, 809, h2, 2, INK)
        draw_para(cv, px, 830, deck, 2, INK, 28, leading=17)
    cv.vline(344, 708, 176, INK, 1)
    cv.vline(676, 708, 176, INK, 1)
    rule(cv, 24, 890, W - 48, INK, 2)

    # ---- ticker band: the rest of the day, by the numbers
    cv.fill_rect(24, 896, W - 48, 76, INK)
    line1 = ("ALSO TODAY: GTA VI $2.36BN ON DAY ONE • HOUTHI MISSILES "
             "AT RIYADH STOPPED")
    draw_text_centered(cv, W // 2, 906, line1, 2, WHITE)
    draw_text_centered(cv, W // 2, 926,
                       "TRUMP SIGNS PENNY LAW • TRUMP DEFENDS PUTIN TIES "
                       "AFTER SHENZHEN SUMMIT", 2, WHITE)
    draw_text_centered(cv, W // 2, 946,
                       "NASA HALTS MARS SCIENCE • PERU QUAKE • CANADA: "
                       "4 MEDALS IN SEOUL", 2, WHITE)

    # ---- footer: sources
    draw_text_centered(cv, W // 2, 984,
                       "SOURCES: REUTERS • XINHUA • IRNA • AP • AFP • CBS "
                       "NEWS • DEADLINE / SENSOR TOWER • UKMTO",
                       1, GREY)
    draw_text_centered(cv, W // 2, 998,
                       "EVERY EVENT ON THIS PAGE HAPPENED, OR WAS FIRST "
                       "REPORTED, ON SATURDAY 21 NOVEMBER 2026",
                       1, GREY)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    png = encode_png(build_page())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))


if __name__ == "__main__":
    main()
