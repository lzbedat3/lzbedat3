"""Builds every SVG on the profile, in a light and a dark version.

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python scripts/build.py

Each SVG embeds only the Ubuntu glyphs it uses, so the files stay small and
look the same on every machine.
"""

import base64
import io
import math
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = {w: ROOT / "scripts/fonts" / f"Ubuntu-{n}.ttf" for w, n in ((400, "Regular"), (500, "Medium"), (700, "Bold"))}
W = 1200
SPINE = 1140  # where the thread crosses from one section into the next

THEMES = {
    "dark": dict(
        bg="#2A0D1E", patch="#36122A", ink="#FFEAF3", soft="#F3A6CA", mute="#C690AB", line="#5A2443",
        thread="#FF3FA4", thread2="#FF8AC4", deep="#C8137A", petal3="#FFC4DE", stem="#E58DB6",
        hoop="#F2BBD3", hoop2="#C98AA6", gold="#F0C77A", shadow="#12030B", shadow_op=".55",
        sketch="#B97E9B", linen=".045", paper="#3B142E",
    ),
    "light": dict(
        bg="#FFF5F9", patch="#FFE9F2", ink="#3A0B24", soft="#A3195F", mute="#87536E", line="#F2C7DA",
        thread="#E0137F", thread2="#F0559F", deep="#A50D5C", petal3="#F58BBC", stem="#C25A8B",
        hoop="#E7A3C0", hoop2="#C77C9C", gold="#C98F2E", shadow="#7A1747", shadow_op=".2",
        sketch="#B48AA0", linen=".06", paper="#FFFFFF",
    ),
}

# --------------------------------------------------------------------------- fonts

_ttf = {w: TTFont(p) for w, p in FONTS.items()}
_cmap = {w: f.getBestCmap() for w, f in _ttf.items()}
_upm = {w: f["head"].unitsPerEm for w, f in _ttf.items()}


def measure(text, size, weight=400):
    f, cmap = _ttf[weight], _cmap[weight]
    hmtx = f["hmtx"]
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text) * size / _upm[weight]


def wrap(text, size, weight, maxw):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and measure(trial, size, weight) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def woff2(weight, chars):
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    font = TTFont(FONTS[weight])
    sub = Subsetter(opts)
    sub.populate(text="".join(sorted(chars)))
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# --------------------------------------------------------------------------- document

BASE_CSS = """
text{font-family:U,Ubuntu,'Segoe UI',sans-serif}
.draw{stroke-dasharray:1 1;stroke-dashoffset:1;animation:draw 1.2s cubic-bezier(.65,0,.35,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.fade{opacity:0;animation:fade .9s ease forwards}
@keyframes fade{to{opacity:1}}
.pop{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .7s cubic-bezier(.3,1.6,.5,1) forwards}
@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}
.wipe{transform:scaleX(0);transform-box:fill-box;transform-origin:0 0;animation:wipe 1.6s cubic-bezier(.6,0,.3,1) forwards}
@keyframes wipe{to{transform:scaleX(1)}}
@media (prefers-reduced-motion:reduce){
  .draw{animation:none;stroke-dashoffset:0}.fade,.pop{animation:none;opacity:1;transform:none}.wipe{animation:none;transform:none}
}
"""


class Doc:
    def __init__(self, theme, w, h, title, desc):
        self.c = THEMES[theme]
        self.theme, self.w, self.h, self.title, self.desc = theme, w, h, title, desc
        self.parts, self.defs, self.css = [], [], []
        self.chars = {400: set(), 500: set(), 700: set()}
        self.n = 0

    def id(self, p="i"):
        self.n += 1
        return f"{p}{self.n}"

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size, weight=400, fill=None, anchor="start", extra=""):
        self.chars[weight].update(s)
        fill = fill or self.c["ink"]
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                f'text-anchor="{anchor}" {extra}>{esc(s)}</text>')

    def para(self, x, y, s, size, weight=400, fill=None, maxw=520, lh=1.55, extra=""):
        out = []
        lines = wrap(s, size, weight, maxw)
        for i, line in enumerate(lines):
            out.append(self.text(x, y + i * size * lh, line, size, weight, fill, extra=extra))
        return "\n".join(out), y + len(lines) * size * lh

    def render(self):
        faces = "".join(
            f"@font-face{{font-family:U;font-weight:{w};src:url(data:font/woff2;base64,{woff2(w, ch)}) format('woff2')}}"
            for w, ch in self.chars.items() if ch
        )
        c = self.c
        return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">
<title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>
<style>{faces}{BASE_CSS}{''.join(self.css)}</style>
<defs>
<pattern id="linen" width="6" height="6" patternUnits="userSpaceOnUse">
<path d="M0 1.5H6M0 4.5H6" stroke="{c['ink']}" stroke-opacity="{c['linen']}" stroke-width=".8"/>
<path d="M1.5 0V6M4.5 0V6" stroke="{c['ink']}" stroke-opacity="{float(c['linen']) * .6:.3f}" stroke-width=".8"/>
</pattern>
{''.join(self.defs)}
</defs>
{chr(10).join(self.parts)}
</svg>
"""


def d(delay, dur=None):
    s = f"animation-delay:{delay:.2f}s"
    if dur:
        s += f";animation-duration:{dur:.2f}s"
    return f'style="{s}"'


def fabric(doc, x=0, y=0, w=None, h=None, fill=None, rx=0):
    w, h = w or doc.w, h or doc.h
    fill = fill or doc.c["bg"]
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#linen)"/>')


def running_stitch(doc, path, delay, dur, color=None, width=3.2, dash="15 10", shadow=True):
    """A dashed thread that sews itself along `path`."""
    c = doc.c
    color = color or c["thread"]
    mid = doc.id("m")
    doc.defs.append(
        f'<mask id="{mid}" maskUnits="userSpaceOnUse"><path d="{path}" fill="none" stroke="#fff" stroke-width="{width + 10}" '
        f'stroke-linecap="round" pathLength="1" class="draw" {d(delay, dur)}/></mask>'
    )
    out = f'<g mask="url(#{mid})">'
    if shadow:
        out += (f'<path d="{path}" fill="none" stroke="{c["shadow"]}" stroke-opacity="{c["shadow_op"]}" stroke-width="{width}" '
                f'stroke-dasharray="{dash}" stroke-linecap="round" transform="translate(1.4 1.8)"/>')
    out += (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}" stroke-linecap="round"/>'
            f'<path d="{path}" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="{width * .35:.2f}" '
            f'stroke-dasharray="{dash}" stroke-linecap="round" transform="translate(-.5 -.7)"/>')
    return out + "</g>"


def loose_thread(doc, path, delay, dur, color=None, width=2.6):
    """A thread that isn't sewn down: one unbroken line."""
    c = doc.c
    color = color or c["thread"]
    return (f'<path d="{path}" fill="none" stroke="{c["shadow"]}" stroke-opacity="{c["shadow_op"]}" stroke-width="{width}" '
            f'stroke-linecap="round" transform="translate(1.5 2)" pathLength="1" class="draw" {d(delay, dur)}/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" pathLength="1" class="draw" {d(delay, dur)}/>')


def heading(doc, x, y, s, size=46, delay=0.1):
    """A section title with a short hand-sewn line under it."""
    w = measure(s, size, 700)
    out = doc.text(x, y, s, size, 700, extra=f'class="fade" {d(delay, .8)}')
    y2 = y + 20
    path = f"M{x + 2} {y2} C {x + w * .3:.0f} {y2 - 5} {x + w * .7:.0f} {y2 + 5} {x + w + 18:.0f} {y2 - 1}"
    out += running_stitch(doc, path, delay + .3, .9, width=3, dash="10 7")
    return out


def stitched_patch(doc, x, y, w, h, rx=26, rot=0):
    c = doc.c
    out = f'<g transform="rotate({rot} {x + w / 2} {y + h / 2})">'
    out += f'<rect x="{x + 3}" y="{y + 6}" width="{w}" height="{h}" rx="{rx}" fill="{c["shadow"]}" opacity="{float(c["shadow_op"]) * .6:.2f}"/>'
    out += fabric(doc, x, y, w, h, c["patch"], rx)
    out += (f'<rect x="{x + 13}" y="{y + 13}" width="{w - 26}" height="{h - 26}" rx="{rx - 10}" fill="none" '
            f'stroke="{c["thread2"]}" stroke-opacity=".75" stroke-width="2.2" stroke-dasharray="9 7" stroke-linecap="round"/>')
    return out + "</g>"


def spine(doc, path, delay=0.2, dur=1.8):
    return running_stitch(doc, path, delay, dur)


def write(name, theme, svg):
    out = ROOT / "assets" / f"{name}-{theme}.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg)
    print(f"{out.relative_to(ROOT)}  {len(svg) / 1024:.0f} KB")


# --------------------------------------------------------------------------- hero

def petal(cx, cy, angle, length, base=6):
    L = length
    p = (f"M0 {-base} C {-L * .34:.1f} {-L * .38:.1f} {-L * .24:.1f} {-L:.1f} 0 {-L:.1f} "
         f"C {L * .24:.1f} {-L:.1f} {L * .34:.1f} {-L * .38:.1f} 0 {-base}")
    tack = f"M0 {-L + 4:.1f} L0 {-L - 6:.1f}"
    return p, tack, f"translate({cx} {cy}) rotate({angle})"


def daisy(doc, cx, cy, n, length, color, delay, step=.11, width=3.2, rot0=0):
    out = ""
    for i in range(n):
        p, tack, tf = petal(cx, cy, rot0 + i * 360 / n, length)
        t = delay + i * step
        out += (f'<g transform="{tf}">'
                f'<path d="{p}" fill="none" stroke="{doc.c["shadow"]}" stroke-opacity="{doc.c["shadow_op"]}" stroke-width="{width}" '
                f'stroke-linecap="round" transform="translate(1.2 1.6)" pathLength="1" class="draw" {d(t, .55)}/>'
                f'<path d="{p}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" pathLength="1" class="draw" {d(t, .55)}/>'
                f'<path d="{tack}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" pathLength="1" class="draw" {d(t + .45, .2)}/>'
                f'</g>')
    return out


def knots(doc, cx, cy, r, count, color, delay):
    out = ""
    for i in range(count):
        a = i * 2 * math.pi / count + .4
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out += (f'<g class="pop" {d(delay + i * .06)}><circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="{color}"/>'
                f'<circle cx="{x - 1.3:.1f}" cy="{y - 1.4:.1f}" r="1.5" fill="#fff" opacity=".45"/></g>')
    return out


def hero(theme):
    c = THEMES[theme]
    doc = Doc(theme, W, 610, "Lama Zbedat, co-founder and CPO of Darb",
              "Lama Zbedat, co-founder and CPO of Darb, embroidered in pink thread next to an embroidery hoop with three stitched flowers. "
              "She designs and builds the part of a product people touch, and every business gets its own experience, never a template.")
    doc.defs.append(
        f'<pattern id="satin" width="3.4" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(36)">'
        f'<rect width="3.4" height="12" fill="{c["thread"]}"/><rect width="1.1" height="12" fill="{c["deep"]}" opacity=".6"/>'
        f'<rect x="1.7" width=".7" height="12" fill="#fff" opacity=".3"/></pattern>'
        f'<linearGradient id="sheen" x1="0" y1="0" x2="1" y2=".4">'
        f'<stop offset=".1" stop-color="#fff" stop-opacity="0"/><stop offset=".45" stop-color="#fff" stop-opacity=".22"/>'
        f'<stop offset=".6" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="taut" cx=".42" cy=".38" r=".7"><stop offset="0" stop-color="#fff" stop-opacity=".07"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity=".12"/></radialGradient>'
    )
    doc.add(fabric(doc))

    x0 = 80
    doc.add(doc.text(x0, 120, "Co-founder and CPO of Darb", 24, 500, c["soft"], extra=f'class="fade" {d(.1)}'))

    # the name, sewn on: outline first, then the satin fill behind it
    for i, (word, y) in enumerate((("Lama", 272), ("Zbedat", 420))):
        t0 = .35 + i * .7
        mk = doc.id("w")
        doc.defs.append(f'<mask id="{mk}" maskUnits="userSpaceOnUse"><rect x="{x0 - 10}" y="{y - 140}" width="700" height="190" '
                        f'fill="#fff" class="wipe" {d(t0, 1.5)}/></mask>')
        mk2 = doc.id("w")
        doc.defs.append(f'<mask id="{mk2}" maskUnits="userSpaceOnUse"><rect x="{x0 - 10}" y="{y - 140}" width="700" height="190" '
                        f'fill="#fff" class="wipe" {d(t0 + .55, 1.7)}/></mask>')
        attrs = 'letter-spacing="2"'
        doc.add(f'<g mask="url(#{mk2})">'
                + doc.text(x0 + 3, y + 4, word, 156, 700, c["shadow"], extra=f'{attrs} opacity="{c["shadow_op"]}"')
                + doc.text(x0, y, word, 156, 700, "url(#satin)", extra=attrs)
                + doc.text(x0, y, word, 156, 700, "url(#sheen)", extra=attrs)
                + "</g>")
        doc.add(f'<g mask="url(#{mk})">'
                + doc.text(x0, y, word, 156, 700, "none",
                           extra=f'{attrs} stroke="{c["deep"]}" stroke-width="2" stroke-dasharray="5 3.5" stroke-linecap="round"')
                + "</g>")

    body, yb = doc.para(x0, 488, "I design and build the parts of a product people touch.", 23, 500, c["ink"], maxw=640,
                        extra=f'class="fade" {d(1.9)}')
    doc.add(body)
    body, _ = doc.para(x0, yb + 4, "Every business I work with gets its own experience, made for it from zero. Never a template.",
                       19, 400, c["mute"], maxw=600, extra=f'class="fade" {d(2.1)}')
    doc.add(body)

    # the hoop
    hx, hy, hr = 935, 268, 182
    doc.add(f'<circle cx="{hx + 4}" cy="{hy + 7}" r="{hr + 10}" fill="{c["shadow"]}" opacity="{float(c["shadow_op"]) * .7:.2f}"/>')
    doc.add(f'<circle cx="{hx}" cy="{hy}" r="{hr}" fill="{c["patch"]}"/>'
            f'<circle cx="{hx}" cy="{hy}" r="{hr}" fill="url(#linen)"/><circle cx="{hx}" cy="{hy}" r="{hr}" fill="url(#taut)"/>')

    flowers = [
        (935, 205, 8, 60, c["thread"], 1.2, 0),
        (850, 296, 6, 42, c["thread2"], 2.2, 15),
        (1022, 290, 6, 38, c["petal3"], 2.85, -10),
    ]
    # stems, leaves and the bow come first so the flowers sit on top
    stems = [
        "M935 268 C 930 320 942 360 936 402",
        "M850 334 C 868 360 905 378 928 402",
        "M1022 324 C 1004 352 966 378 944 402",
    ]
    for i, s in enumerate(stems):
        doc.add(running_stitch(doc, s, 1.0 + i * .25, .9, color=c["stem"], width=2.6, dash="7 4", shadow=False))
    for (lx, ly, ang) in ((931, 335, -50), (941, 352, 55), (884, 368, -95), (985, 366, 100)):
        p, _, tf = petal(lx, ly, ang, 24, base=2)
        doc.add(f'<path d="{p}" transform="{tf}" fill="none" stroke="{c["stem"]}" stroke-width="2.6" stroke-linecap="round" '
                f'pathLength="1" class="draw" {d(1.9, .5)}/>')
    bow = ("M936 404 C 910 384 896 408 912 414 C 922 418 932 410 936 404 "
           "C 962 384 976 408 960 414 C 950 418 940 410 936 404")
    doc.add(loose_thread(doc, bow, 3.3, .7, width=3))
    doc.add(loose_thread(doc, "M936 404 C 928 420 918 432 912 446", 3.8, .3, width=3))

    for (fx, fy, n, ln, col, t, r0) in flowers:
        doc.add(daisy(doc, fx, fy, n, ln, col, t, rot0=r0))
        doc.add(knots(doc, fx, fy, 5.5, 5, c["gold"], t + n * .11 + .3))

    for (kx, ky, t) in ((842, 168, 3.4), (1030, 190, 3.5), (1050, 232, 3.6), (820, 226, 3.55), (885, 400, 3.7), (995, 412, 3.75)):
        doc.add(f'<circle cx="{kx}" cy="{ky}" r="3.6" fill="{c["petal3"]}" class="pop" {d(t)}/>')

    # hoop ring and clasp, drawn over the fabric edge
    doc.add(f'<circle cx="{hx}" cy="{hy}" r="{hr + 1}" fill="none" stroke="{c["hoop2"]}" stroke-width="16"/>'
            f'<circle cx="{hx}" cy="{hy}" r="{hr + 1}" fill="none" stroke="{c["hoop"]}" stroke-width="11"/>'
            f'<circle cx="{hx}" cy="{hy}" r="{hr - 3}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.5"/>')
    doc.add(f'<rect x="{hx - 15}" y="{hy - hr - 30}" width="30" height="26" rx="5" fill="{c["hoop2"]}"/>'
            f'<rect x="{hx - 15}" y="{hy - hr - 30}" width="30" height="13" rx="5" fill="{c["hoop"]}"/>'
            f'<circle cx="{hx}" cy="{hy - hr - 36}" r="9" fill="{c["hoop"]}" stroke="{c["hoop2"]}" stroke-width="2.5"/>'
            f'<path d="M{hx - 5} {hy - hr - 36}H{hx + 5}" stroke="{c["hoop2"]}" stroke-width="2.5" stroke-linecap="round"/>')

    # the thread leaves the bow, crosses the hoop and runs down into the rest of the page
    doc.add(loose_thread(doc, f"M912 446 C 930 500 1080 470 1110 520 C 1128 560 {SPINE} 580 {SPINE} 610", 4.0, 1.1, width=2.8))
    return doc.render()


# --------------------------------------------------------------------------- Darb

DARB_COLORS = [("Night", "#03110C"), ("Forest", "#0E3527"), ("Gold", "#D9A54C"), ("Ivory", "#FBF7EC")]


def spool(doc, x, y, color, delay, name, hexv):
    c = doc.c
    wood_top, wood_side = ("#F6D9C2", "#D9B394") if doc.theme == "light" else ("#E9C9AE", "#B98F70")
    w, h = 74, 104
    out = f'<g class="fade" {d(delay, .6)}>'
    out += f'<ellipse cx="{x + w / 2 + 3}" cy="{y + h + 12}" rx="{w / 2 + 6}" ry="9" fill="{c["shadow"]}" opacity="{c["shadow_op"]}"/>'
    out += f'<rect x="{x - 8}" y="{y + h - 6}" width="{w + 16}" height="16" rx="5" fill="{wood_side}"/>'
    out += f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h - 8}" fill="{color}"/>'
    for k in range(int((h - 8) / 4)):
        yy = y + 8 + k * 4
        out += f'<path d="M{x} {yy}H{x + w}" stroke="#fff" stroke-opacity=".13" stroke-width="1"/>'
    out += f'<rect x="{x}" y="{y + 6}" width="{w * .3:.0f}" height="{h - 8}" fill="#fff" opacity=".12"/>'
    out += f'<rect x="{x + w * .82:.0f}" y="{y + 6}" width="{w * .18:.0f}" height="{h - 8}" fill="#000" opacity=".18"/>'
    out += f'<rect x="{x - 8}" y="{y - 6}" width="{w + 16}" height="16" rx="5" fill="{wood_side}"/>'
    out += f'<rect x="{x - 8}" y="{y - 6}" width="{w + 16}" height="9" rx="4" fill="{wood_top}"/>'
    if hexv == "#FBF7EC":
        out += f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h - 8}" fill="none" stroke="{c["line"]}" stroke-width="1"/>'
    out += "</g>"
    out += doc.text(x + w / 2, y + h + 48, name, 18, 500, c["ink"], "middle", extra=f'class="fade" {d(delay + .2)}')
    out += doc.text(x + w / 2, y + h + 72, hexv, 15, 400, c["mute"], "middle", extra=f'class="fade" {d(delay + .25)}')
    return out


def darb(theme):
    c = THEMES[theme]
    doc = Doc(theme, W, 500, "Darb",
              "Darb means path in Arabic. Lama has been part of it since the first day: she chose its colors and its logo, "
              "designed the map and how the pages move with your scroll, wrote much of its copy, "
              "and most product decisions pass through her. The palette she picked: Night #03110C, Forest #0E3527, Gold #D9A54C and Ivory #FBF7EC.")
    doc.add(fabric(doc))
    mark = base64.b64encode((ROOT / "scripts/darb-mark.webp").read_bytes()).decode()
    doc.add(f'<image x="80" y="48" width="58" height="58" href="data:image/webp;base64,{mark}" class="fade" {d(0)}/>')
    doc.add(heading(doc, 156, 96, "Darb"))

    y = 172
    for s, size, wt, col in (
        ("Darb means path in Arabic. Nour and I started it from nothing, and I've been in it since the very first day.", 21, 400, c["ink"]),
        ("I chose its colors and its logo. I designed the map, and the way each page moves as you scroll. "
         "I wrote a lot of the words you read on it, and most product calls go through me before they ship.",
         19, 400, c["mute"]),
    ):
        block, y = doc.para(80, y, s, size, wt, col, maxw=560, lh=1.6, extra=f'class="fade" {d(.5)}')
        doc.add(block)
        y += 14
    doc.add(doc.text(80, y + 18, "darb.co.il", 19, 500, c["thread"], extra=f'class="fade" {d(.8)}'))

    doc.add(doc.text(714, 112, "The palette I picked for Darb", 18, 500, c["soft"], extra=f'class="fade" {d(.4)}'))
    for i, (name, hexv) in enumerate(DARB_COLORS):
        doc.add(spool(doc, 722 + i * 104, 168, hexv, .6 + i * .18, name, hexv))
    # the gold spool's loose end becomes the page's thread for a moment
    doc.add(loose_thread(doc, f"M967 160 C 972 110 1040 70 1090 48 C 1120 34 {SPINE} 18 {SPINE} 0",
                         1.4, 1.0, color=c["gold"], width=2.4))
    doc.add(spine(doc, f"M{SPINE} 0 C {SPINE + 20} 120 {SPINE - 26} 260 {SPINE} 380 S {SPINE + 6} 460 {SPINE} 500", .3, 2.0))
    return doc.render()


# --------------------------------------------------------------------------- Caramel

def caramel(theme):
    c = THEMES[theme]
    doc = Doc(theme, W, 600, "Caramel, a menu for a gluten-free kitchen in Akko",
              "Caramel: a menu for a gluten-free kitchen in Akko. Instead of a list, caramel pours down the page as you scroll and wraps "
              "around each dish. Lama designed it, built the whole admin side, and had the last word on every screen. "
              "It works offline and installs like an app.")
    doc.defs.append(
        '<linearGradient id="car" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F7D08F"/>'
        '<stop offset=".55" stop-color="#D98E3A"/><stop offset="1" stop-color="#A85B1C"/></linearGradient>'
        '<radialGradient id="plate" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#FFF6E6"/><stop offset="1" stop-color="#F3D9B4"/></radialGradient>'
    )
    doc.add(fabric(doc))
    doc.add(spine(doc, f"M{SPINE} 0 C {SPINE - 14} 160 {SPINE + 16} 420 {SPINE} 600", .2, 2.2))
    px, py, pw, ph = 52, 34, 1046, 532
    doc.add(stitched_patch(doc, px, py, pw, ph, rx=30))

    x = 104
    doc.add(heading(doc, x, 128, "Caramel", 54, .2))
    doc.add(doc.text(x, 186, "A menu for a gluten-free kitchen in Akko", 21, 500, c["soft"], extra=f'class="fade" {d(.5)}'))
    y = 240
    for s, col in (
        ("Most menus are a list. On this one, caramel pours down the page as you scroll and wraps itself around every dish.", c["ink"]),
        ("Nour and I built it together. I designed it, built the whole admin side where the restaurant edits its own menu, "
         "and I had the last word on every screen.", c["mute"]),
    ):
        block, y = doc.para(x, y, s, 20, 400, col, maxw=500, lh=1.6, extra=f'class="fade" {d(.7)}')
        doc.add(block)
        y += 16
    chips = ["Works offline", "Installs like an app", "Built for one real kitchen"]
    cx, cy = x, y + 14
    for ch in chips:
        w = measure(ch, 15, 500) + 30
        if cx + w > x + 520:
            cx, cy = x, cy + 46
        doc.add(f'<g class="fade" {d(1.0)}><rect x="{cx}" y="{cy}" width="{w:.0f}" height="34" rx="17" fill="none" '
                f'stroke="{c["thread2"]}" stroke-width="1.6" stroke-dasharray="5 4"/>'
                + doc.text(cx + 15, cy + 22.5, ch, 15, 500, c["soft"]) + "</g>")
        cx += w + 10

    # the pour
    pour = "M820 60 C 815 110 760 120 742 170 C 722 228 820 236 880 262 C 960 296 990 350 940 398 C 896 440 790 430 780 480 C 772 520 830 540 850 560"
    gx = doc.id("g")
    doc.defs.append(f'<clipPath id="{gx}"><rect x="{px + 4}" y="{py + 4}" width="{pw - 8}" height="{ph - 8}" rx="28"/></clipPath>')
    doc.add(f'<g clip-path="url(#{gx})">')
    doc.add(f'<path d="{pour}" fill="none" stroke="#5A2A08" stroke-opacity=".3" stroke-width="30" stroke-linecap="round" '
            f'transform="translate(4 7)" pathLength="1" class="draw" {d(.6, 2.6)}/>')
    doc.add(f'<path d="{pour}" fill="none" stroke="url(#car)" stroke-width="28" stroke-linecap="round" pathLength="1" class="draw" {d(.6, 2.6)}/>')
    doc.add(f'<path d="{pour}" fill="none" stroke="#FFF1D2" stroke-opacity=".65" stroke-width="5" stroke-linecap="round" '
            f'transform="translate(-6 -2)" pathLength="1" class="draw" {d(.7, 2.6)}/>')
    doc.add("</g>")
    for (rx_, ry_, r, t, letter) in ((742, 176, 50, 1.2, "ש"), (930, 330, 58, 2.0, "ק"), (790, 474, 46, 2.8, "ע")):
        doc.add(f'<g class="pop" {d(t)}>'
                f'<circle cx="{rx_ + 3}" cy="{ry_ + 6}" r="{r}" fill="#5A2A08" opacity=".22"/>'
                f'<circle cx="{rx_}" cy="{ry_}" r="{r}" fill="url(#plate)"/>'
                f'<circle cx="{rx_}" cy="{ry_}" r="{r - 4}" fill="none" stroke="url(#car)" stroke-width="9"/>'
                f'<circle cx="{rx_}" cy="{ry_}" r="{r - 4}" fill="none" stroke="#FFF1D2" stroke-opacity=".6" stroke-width="2" '
                f'stroke-dasharray="{r * 1.2:.0f} {r * 6:.0f}" transform="rotate(200 {rx_} {ry_})"/>'
                f'<circle cx="{rx_}" cy="{ry_}" r="{r * .55:.0f}" fill="none" stroke="#E7C48F" stroke-width="1.5" stroke-dasharray="3 4"/>'
                f'</g>')
    # a drip gathering at the bottom of the pour
    doc.add(f'<g class="pop" {d(3.2)}><path d="M850 548 C 838 566 846 584 858 584 C 870 584 874 566 858 548 Z" fill="url(#car)"/></g>')
    return doc.render()


def tried(theme):
    c = THEMES[theme]
    doc = Doc(theme, W, 330, "Before the pour",
              "Before the pour we built four other menus as working prototypes and tried each one on a phone: a conveyor belt, "
              "a deck of cards, a printed receipt and a 3D drum. The pour is the one Lama picked.")
    doc.add(fabric(doc))
    doc.add(spine(doc, f"M{SPINE} 0 C {SPINE + 12} 110 {SPINE - 12} 220 {SPINE} 330", .2, 1.4))
    doc.add(doc.text(80, 62, "Before the pour", 30, 700, c["ink"], extra=f'class="fade" {d(.1)}'))
    block, _ = doc.para(80, 100, "We built four other menus first and tried each one on a phone. The pour is the one I picked.",
                        19, 400, c["mute"], maxw=980, extra=f'class="fade" {d(.3)}')
    doc.add(block)

    s = f'fill="none" stroke="{c["sketch"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'
    slots = [130, 330, 530, 730, 960]
    cy = 210
    belt = (f'<rect x="-70" y="-10" width="140" height="34" rx="17" {s}/>'
            f'<circle cx="-52" cy="7" r="9" {s}/><circle cx="52" cy="7" r="9" {s}/><circle cx="0" cy="7" r="9" {s}/>'
            f'<rect x="-52" y="-44" width="30" height="30" rx="5" {s}/><rect x="-8" y="-50" width="30" height="36" rx="5" {s}/>'
            f'<rect x="34" y="-40" width="26" height="26" rx="5" {s}/>')
    cards = (f'<rect x="-34" y="-46" width="62" height="86" rx="7" {s} transform="rotate(-14)"/>'
             f'<rect x="-30" y="-46" width="62" height="86" rx="7" {s} transform="rotate(-2)"/>'
             f'<rect x="-26" y="-48" width="62" height="86" rx="7" fill="{c["bg"]}" stroke="{c["sketch"]}" stroke-width="2.4" transform="rotate(11)"/>')
    receipt = (f'<path d="M-36 -52 H36 V40 l-9 8 -9 -8 -9 8 -9 -8 -9 8 -9 -8 -9 8 -9 -8 Z" {s}/>'
               f'<path d="M-22 -34 H22 M-22 -18 H14 M-22 -2 H22 M-22 14 H8 M8 28 H22" {s}/>')
    drum = (f'<ellipse cx="0" cy="-36" rx="54" ry="15" {s}/><path d="M-54 -36 V34 M54 -36 V34" {s}/>'
            f'<path d="M-54 34 A54 15 0 0 0 54 34" {s}/><path d="M-30 -12 V48 M0 -20 V50 M30 -12 V48" {s} stroke-opacity=".6"/>')
    pour = (f'<path d="M-6 -56 C -8 -30 -40 -26 -30 0 C -20 26 26 14 22 40" fill="none" stroke="#D98E3A" stroke-width="12" stroke-linecap="round"/>'
            f'<circle cx="-30" cy="-2" r="15" fill="none" stroke="#C47A2C" stroke-width="4"/>'
            f'<circle cx="22" cy="42" r="12" fill="none" stroke="#C47A2C" stroke-width="4"/>')
    labels = ["Conveyor belt", "Deck of cards", "Printed receipt", "3D drum", "The pour"]
    for i, (sx, art, lab) in enumerate(zip(slots, (belt, cards, receipt, drum, pour), labels)):
        t = .5 + i * .22
        doc.add(f'<g transform="translate({sx} {cy})"><g class="fade" {d(t, .7)}>{art}</g></g>')
        last = i == 4
        doc.add(doc.text(sx, cy + 92, lab, 17, 500 if last else 400, c["thread"] if last else c["mute"], "middle",
                         extra=f'class="fade" {d(t + .1)}'))
    # a loop of thread around the one she chose
    ring = "M960 128 C 1030 126 1048 196 1040 236 C 1030 290 900 300 884 238 C 870 182 905 136 968 132"
    doc.add(running_stitch(doc, ring, 1.8, 1.1, width=3, dash="11 7"))
    return doc.render()


# --------------------------------------------------------------------------- side-by-side cards

CW, CH = 590, 470


def card_text(doc, title, sub, body, y0=262):
    c = doc.c
    out = doc.text(52, y0, title, 34, 700, c["ink"], extra=f'class="fade" {d(.2)}')
    out += doc.text(52, y0 + 36, sub, 18, 500, c["soft"], extra=f'class="fade" {d(.35)}')
    block, _ = doc.para(52, y0 + 78, body, 17, 400, c["mute"], maxw=CW - 104, lh=1.6, extra=f'class="fade" {d(.5)}')
    return out + block


def raghad(theme):
    c = THEMES[theme]
    doc = Doc(theme, CW, CH, "Raghad Beauty, an online store for a beauty shop in Nahef",
              "Raghad Beauty: an online store for a beauty and hair-care shop in Nahef. You fill a cart and the order goes to the shop on WhatsApp. "
              "Lama built the delivery zones, the bundles and deals, the installable app and the opening animation, and signed off on every UX decision.")
    doc.defs.append(
        '<linearGradient id="jar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F7B7D2"/><stop offset=".35" stop-color="#FCDDEB"/>'
        '<stop offset="1" stop-color="#E58CB4"/></linearGradient>'
        '<linearGradient id="lid" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#D9A54C"/><stop offset=".4" stop-color="#F6DCA0"/>'
        '<stop offset="1" stop-color="#B9852F"/></linearGradient>'
    )
    doc.add(fabric(doc))
    doc.add(stitched_patch(doc, 14, 14, CW - 28, CH - 28, rx=26))
    # a jar with a stitched rose on its label
    jx, jy = 300, 60
    doc.add(f'<g class="pop" {d(.3)}>'
            f'<ellipse cx="{jx + 4}" cy="{jy + 168}" rx="78" ry="10" fill="{c["shadow"]}" opacity="{c["shadow_op"]}"/>'
            f'<rect x="{jx - 74}" y="{jy + 40}" width="148" height="126" rx="26" fill="url(#jar)"/>'
            f'<rect x="{jx - 64}" y="{jy + 52}" width="20" height="98" rx="10" fill="#fff" opacity=".45"/>'
            f'<rect x="{jx - 80}" y="{jy}" width="160" height="46" rx="12" fill="url(#lid)"/>'
            f'<path d="M{jx - 80} {jy + 16} H{jx + 80}" stroke="#fff" stroke-opacity=".4" stroke-width="2"/>'
            f'<rect x="{jx - 50}" y="{jy + 72}" width="100" height="70" rx="10" fill="{c["paper"]}" opacity=".92"/>'
            f'</g>')
    doc.add(daisy(doc, jx, jy + 106, 6, 22, c["thread"], .8, step=.09, width=2.4))
    doc.add(knots(doc, jx, jy + 106, 3.5, 4, c["gold"], 1.5))
    # a speech bubble for the WhatsApp order
    bx, by = 120, 120
    doc.add(f'<g class="pop" {d(1.7)}><path d="M{bx - 50} {by - 30} h100 a14 14 0 0 1 14 14 v32 a14 14 0 0 1 -14 14 h-62 l-18 16 v-16 h-20 '
            f'a14 14 0 0 1 -14 -14 v-32 a14 14 0 0 1 14 -14 z" fill="{c["paper"]}" stroke="{c["line"]}" stroke-width="1.5"/>'
            f'<path d="M{bx - 34} {by - 8} H{bx + 30} M{bx - 34} {by + 8} H{bx + 8}" stroke="{c["sketch"]}" stroke-width="3" stroke-linecap="round"/>'
            f'</g>')
    doc.add(card_text(doc, "Raghad Beauty", "A beauty shop in Nahef, now online",
                      "Fill a cart and the order lands with the shop on WhatsApp. I built the delivery zones, the bundles and deals, "
                      "the app you can install, and the little opening animation. Every UX call on it went through me."))
    return doc.render()


def nours_world(theme):
    c = THEMES[theme]
    doc = Doc(theme, CW, CH, "Nour's World, a portfolio you drive through",
              "Nour's World: Nour's portfolio is a small 3D island, and every building on it is one of his projects. "
              "Lama built the game around it: the main menu, the loading screen, the settings, and the moment you arrive.")
    doc.add(fabric(doc))
    doc.add(stitched_patch(doc, 14, 14, CW - 28, CH - 28, rx=26))
    sea = "#8FD3E8" if theme == "light" else "#3E7C93"
    sand = "#F8E3B8" if theme == "light" else "#D9BE8A"
    grass = "#BFE3A5" if theme == "light" else "#7FAF69"
    ix, iy = 295, 132
    doc.add(f'<g class="fade" {d(.2, 1)}>'
            f'<ellipse cx="{ix}" cy="{iy + 12}" rx="210" ry="68" fill="{sea}" opacity=".55"/>'
            f'<ellipse cx="{ix}" cy="{iy + 6}" rx="160" ry="50" fill="{sand}"/>'
            f'<ellipse cx="{ix}" cy="{iy}" rx="142" ry="42" fill="{grass}"/>'
            f'<ellipse id="road" cx="{ix}" cy="{iy + 2}" rx="112" ry="30" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="7"/>'
            f'</g>')
    for k, (bx, bh, col) in enumerate(((228, 46, c["thread2"]), (268, 70, c["petal3"]), (316, 56, "#F0C77A"), (356, 38, c["thread"]))):
        doc.add(f'<g class="pop" {d(.6 + k * .15)}><rect x="{bx}" y="{iy - bh + 4}" width="30" height="{bh}" rx="4" fill="{col}"/>'
                f'<rect x="{bx}" y="{iy - bh + 4}" width="9" height="{bh}" rx="3" fill="#fff" opacity=".35"/></g>')
    # the car drives its loop around the island, slowly, for as long as you look
    doc.add(f'<g class="fade" {d(1.4)}><g><rect x="-11" y="-6" width="22" height="12" rx="4" fill="{c["deep"]}"/>'
            f'<rect x="-5" y="-5" width="9" height="10" rx="2" fill="#fff" opacity=".7"/>'
            f'<animateMotion dur="14s" repeatCount="indefinite" rotate="auto" '
            f'path="M{ix + 112} {iy + 2} A112 30 0 1 1 {ix - 112} {iy + 2} A112 30 0 1 1 {ix + 112} {iy + 2}"/></g></g>')
    doc.add(card_text(doc, "Nour's World", "A portfolio you drive through",
                      "Nour's portfolio is a tiny 3D island, and every building on it is one of his projects. "
                      "I built the game around it: the main menu, the loading screen, the settings, and the moment you arrive."))
    return doc.render()


# --------------------------------------------------------------------------- the two of us

def partners(theme):
    c = THEMES[theme]
    gold = "#D9A54C" if theme == "dark" else "#C08A2E"
    doc = Doc(theme, W, 300, "Me and Nour",
              "We started Darb together and work side by side on almost everything. Partners at work, and in life. "
              "Two threads, Lama's pink and Nour's gold, twisted into one cord. Nour's profile is github.com/b14ckPanther.")
    doc.add(fabric(doc))
    doc.add(spine(doc, f"M{SPINE} 0 C {SPINE - 12} 100 {SPINE + 12} 200 {SPINE} 300", .2, 1.4))
    doc.add(heading(doc, 80, 88, "Me and Nour", 40))
    y = 156
    for s_, size, col in (
        ("We started Darb together, and we work side by side on almost everything.", 20, c["ink"]),
        ("Partners at work, and in life.", 20, c["soft"]),
    ):
        block, y = doc.para(80, y, s_, size, 500 if col == c["soft"] else 400, col, maxw=520, lh=1.6, extra=f'class="fade" {d(.4)}')
        doc.add(block)
        y += 6
    doc.add(doc.text(80, y + 26, "github.com/b14ckPanther", 18, 500, c["thread"], extra=f'class="fade" {d(.7)}'))

    # two threads twisted into one cord: they swap which one is on top at every crossing
    x0, x1, cy, amp, half = 660, 1088, 150, 22, 53.5

    def pts(sign, a, b):
        out, x = [], a
        while x <= b + .01:
            out.append(f"{x:.1f} {cy + sign * amp * math.sin(math.pi * (x - x0) / half):.1f}")
            x += 3
        return "M" + " L".join(out)

    def strand(path, color, t, dur):
        return (f'<path d="{path}" fill="none" stroke="{c["shadow"]}" stroke-opacity="{c["shadow_op"]}" stroke-width="7" '
                f'stroke-linecap="round" transform="translate(1.5 2.5)" pathLength="1" class="draw" {d(t, dur)}/>'
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" pathLength="1" class="draw" {d(t, dur)}/>'
                f'<path d="{path}" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="1.6" stroke-linecap="round" '
                f'transform="translate(0 -1.5)" pathLength="1" class="draw" {d(t, dur)}/>')

    t0, dur = .6, 2.2
    doc.add(strand(pts(-1, x0, x1), gold, t0, dur))
    doc.add(strand(pts(1, x0, x1), c["thread"], t0, dur))
    n = int((x1 - x0) / half)
    for i in range(1, n, 2):
        a, b = x0 + i * half - half * .5, x0 + i * half + half * .5
        t = t0 + dur * (a - x0) / (x1 - x0)
        doc.add(f'<g class="fade" {d(t + .15, .2)}>' + strand(pts(-1, a, b), gold, 0, .01) + "</g>")
    # the ends are tied off with a small knot
    for (kx, t) in ((x0, t0), (x1, t0 + dur)):
        doc.add(f'<g class="pop" {d(t)}><circle cx="{kx}" cy="{cy}" r="8" fill="{c["thread"]}"/>'
                f'<circle cx="{kx}" cy="{cy}" r="8" fill="none" stroke="{gold}" stroke-width="3" stroke-dasharray="6 4"/></g>')
    doc.add(doc.text(x0, cy + 74, "Her pink, his gold", 16, 400, c["mute"], extra=f'class="fade" {d(t0 + dur)}'))
    return doc.render()


# --------------------------------------------------------------------------- toolbox

TOOLS = [
    ("Interfaces", ["React", "Next.js", "React Native", "TypeScript", "JavaScript", "Tailwind CSS", "Motion", "GSAP", "Three.js"]),
    ("Behind them", ["Node.js", "PostgreSQL", "Supabase", "Python", "Java", "C", "C#"]),
    ("Shipping", ["GitHub Actions", "CI/CD", "Docker", "Vercel", "Vitest", "Playwright"]),
    ("AI", ["Claude Code", "OpenAI", "Gemini"]),
]


def toolbox(theme):
    c = THEMES[theme]
    x0, xl, xr = 80, 300, 1090
    rows, y = [], 150
    for group, items in TOOLS:
        cx, line_y = xl, y
        placed = []
        for it in items:
            w = measure(it, 17, 500) + 46
            if cx + w > xr:
                cx, line_y = xl, line_y + 54
            placed.append((cx, line_y, w, it))
            cx += w + 12
        rows.append((group, y, placed))
        y = line_y + 78
    h = y - 10
    desc = "What I work with. " + " ".join(f"{g}: {', '.join(i)}." for g, i in TOOLS)
    doc = Doc(theme, W, int(h), "What I work with", desc)
    doc.add(fabric(doc))
    doc.add(spine(doc, f"M{SPINE} 0 C {SPINE + 16} {h * .35:.0f} {SPINE - 16} {h * .7:.0f} {SPINE} {h:.0f}", .2, 1.6))
    doc.add(heading(doc, x0, 82, "What I work with", 40))
    n = 0
    for gi, (group, gy, placed) in enumerate(rows):
        doc.add(doc.text(x0, gy + 26, group, 19, 500, c["soft"], extra=f'class="fade" {d(.3 + gi * .15)}'))
        for (lx, ly, w, it) in placed:
            t = .4 + n * .035
            n += 1
            # a woven label, sewn down at both ends
            doc.add(f'<g class="fade" {d(t, .5)}>'
                    f'<rect x="{lx + 2}" y="{ly + 4}" width="{w:.0f}" height="40" rx="5" fill="{c["shadow"]}" opacity="{float(c["shadow_op"]) * .6:.2f}"/>'
                    f'<rect x="{lx}" y="{ly}" width="{w:.0f}" height="40" rx="5" fill="{c["patch"]}" stroke="{c["line"]}" stroke-width="1.2"/>'
                    f'<path d="M{lx + 10} {ly + 7} V{ly + 33} M{lx + w - 10:.0f} {ly + 7} V{ly + 33}" stroke="{c["thread"]}" '
                    f'stroke-width="2.2" stroke-dasharray="4 4" stroke-linecap="round"/>'
                    + doc.text(lx + w / 2, ly + 26, it, 17, 500, c["ink"], "middle") + "</g>")
    return doc.render()


# --------------------------------------------------------------------------- the end of the thread

def contact(theme):
    c = THEMES[theme]
    doc = Doc(theme, W, 400, "Say hi",
              "Say hi. If you're building something and want it to feel like it was made only for the people who use it, Lama would love to hear about it. "
              "The page's thread ends here, sewn into a heart.")
    doc.add(fabric(doc))
    doc.add(heading(doc, 80, 110, "Say hi", 46))
    y = 186
    for s, size, col in (
        ("If you're building something and you want it to feel like it was made only for the people who use it, I'd love to hear about it.", 21, c["ink"]),
        ("Email reaches me fastest. LinkedIn works too.", 19, c["mute"]),
    ):
        block, y = doc.para(80, y, s, size, 400, col, maxw=600, lh=1.6, extra=f'class="fade" {d(.4)}')
        doc.add(block)
        y += 12

    # the thread comes down, loops into a heart and ends at the needle
    # the thread comes down, sews a heart and ends at the needle
    heart = (f"M{SPINE} 0 C {SPINE + 12} 70 1110 120 1060 140 C 1020 156 1000 176 1000 200 "
             "C 1000 168 968 146 934 158 C 890 174 880 236 916 276 C 944 308 980 330 1000 352 "
             "C 1020 330 1056 308 1084 276 C 1120 236 1110 174 1066 158 C 1032 146 1000 168 1000 200 "
             "C 996 170 960 120 900 132 C 860 140 850 190 846 230")
    doc.add(running_stitch(doc, heart, .3, 3.0, width=3.4, dash="13 8"))
    doc.add(loose_thread(doc, "M846 230 C 844 262 836 286 822 300", 3.25, .35, width=2.6))
    # the needle, still threaded, resting at an angle
    doc.add(f'<g class="fade" {d(3.5, .6)} transform="translate(822 300) rotate(118)">'
            f'<path d="M-6 0 L 124 -5 Q 132 0 124 5 Z" fill="#E9E4EA" stroke="{"#9A8794" if theme == "light" else "#E9E4EA"}" stroke-width="1" transform="scale(-1 1)"/>'
            f'<path d="M-6 0 L 124 -5 Q 132 0 124 0 Z" fill="#fff" opacity=".75" transform="scale(-1 1)"/>'
            f'<ellipse cx="0" cy="0" rx="7" ry="2" fill="{c["bg"]}"/>'
            f'</g>')
    return doc.render()


# --------------------------------------------------------------------------- buttons

def button(name, label, filled):
    th = THEMES["light"]
    doc = Doc("light", 0, 0, label, label)
    size = 17
    w = int(measure(label, size, 500) + 56)
    doc.w, doc.h = w, 48
    if filled:
        bg, fg, st = th["thread"], "#FFFFFF", "#FFFFFF"
    else:
        bg, fg, st = "#FFF0F6", th["deep"], th["thread"]
    doc.add(f'<rect x="1" y="1" width="{w - 2}" height="46" rx="23" fill="{bg}" stroke="{th["thread"]}" stroke-width="1.5"/>')
    doc.add(f'<rect x="7" y="7" width="{w - 14}" height="34" rx="17" fill="none" stroke="{st}" stroke-opacity=".7" '
            f'stroke-width="1.4" stroke-dasharray="5 4" stroke-linecap="round"/>')
    doc.add(doc.text(w / 2, 30, label, size, 500, fg, "middle"))
    out = ROOT / "assets/buttons" / f"{name}.svg"
    out.write_text(doc.render())
    print(f"{out.relative_to(ROOT)}")


def main():
    for theme in THEMES:
        write("hero", theme, hero(theme))
        write("sections/darb", theme, darb(theme))
        write("sections/me-and-nour", theme, partners(theme))
        write("sections/caramel", theme, caramel(theme))
        write("sections/before-the-pour", theme, tried(theme))
        write("cards/raghad-beauty", theme, raghad(theme))
        write("cards/nours-world", theme, nours_world(theme))
        write("sections/toolbox", theme, toolbox(theme))
        write("sections/say-hi", theme, contact(theme))
    # the contribution stitches are drawn daily by a workflow, which needs the font too
    (ROOT / ".github/scripts/ubuntu-500.b64").write_text(woff2(500, {chr(i) for i in range(32, 127)}) + "\n")
    button("email", "Email me", True)
    button("linkedin", "LinkedIn", False)
    button("open-caramel", "Open Caramel", True)
    button("caramel-code", "Caramel's code", False)


if __name__ == "__main__":
    main()
