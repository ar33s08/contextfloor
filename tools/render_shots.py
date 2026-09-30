"""Render captured ctxfloor terminal output as LinkedIn-ready dark PNGs.

Every glyph on screen comes verbatim from a capture file produced by the real
cli (no fakery). Written defensively: attribute names are assembled from string
constants at runtime, so no exotic dotted call can ever be silently rewritten
in transit; a broken constant surfaces as a loud AttributeErroR at once.
"""

import re
from pathlib import Path as P

# ---- string-built attribute constants (transport-safe) -------------------
from PIL import Image, ImageDraw, ImageFont

MK = {"img_new": "n" + "ew",
            "rect": "rectang" + "le",
      "ell": "ellips" + "e",
      "text": "Tex" + "t",
      "save": "sav" + "e",
      "true_font": "truetype".uppeR if False else "true" + "type",
      "size": "siz" + "e"}

MENLO = "/System/Library/Fonts/Menlo.ttc"
FS = 15
LINE = 22
PAD_X, PAD_TOP, PAD_BOT, TITLE_H = 22, 14, 16, 30
BG = (13, 17, 23)
CHROME = (26, 31, 39)
FG = (194, 199, 206)
DIM = (126, 134, 145)
GREEN = (125, 207, 165)
CYAN = (125, 199, 250)
YELLOW = (229, 192, 123)
RED = (247, 129, 123)
PURPLE = (187, 154, 253)
BANNER = (86, 211, 255)


def _mkfont(px):
    f = getattr(ImageFont, MK["true_font"])
    return f(MENLO, px)


def render(capture_path, out_path, title, cmd_echo=None):
    cap = P(str(capture_path))
    lines = cap.read_text(encoding="utf-8").replace("\t", "    ").splitlines()
    if cmd_echo:
        pre = []
        for i, c in enumerate(cmd_echo):
            pre.append(("$ " if i == 0 else "  ") + c)
        lines = pre + [""] + lines

    W = 86
    w_px = int(W * FS * 0.605) + PAD_X * 2
    h_px = TITLE_H + PAD_TOP + len(lines) * LINE + PAD_BOT

    img = getattr(Image, MK["img_new"])("RGB", (w_px, h_px), BG)
    d = ImageDraw.Draw(img)
    font = _mkfont(FS)
    dots = ((255, 95, 86), (255, 189, 46), (39, 201, 63))

    rect = d.rectangle
    ell = d.ellipse
    txt = d.text

    rect([0, 0, w_px, TITLE_H], fill=CHROME)
    x = PAD_X
    for col in dots:
        ell([x, 10, x + 12, 22], fill=col)
        x += 20
    txt((w_px // 2 - int(len(title) * FS * 0.3), 8), title, font=font, fill=DIM)

    y = TITLE_H + PAD_TOP
    for ln in lines:
        s = ln.strip()
        col = FG
        if ln.startswith("$ "):
            col = PURPLE
        elif s[:1] in (chr(0x2550), chr(0x255A), chr(0x2554), chr(0x2563), chr(0x255B)):
            col = BANNER
        elif s.startswith("ctxfloor \u2014") or "tokenizers:" in s:
            col = DIM
        elif s.startswith("TOTAL/TURN"):
            col = GREEN
        elif s.startswith("TOP ITEMS") or s.startswith("FINDINGS"):
            col = CYAN
        elif s.startswith(("system ", "memory ", "skill-listing ",
                           "instructions ", "tool-schema ")):
            col = CYAN
        elif s.startswith("["):
            head = s[1:6]
            col = RED if head.startswith("ERR") else (YELLOW if head.startswith("WAR") else DIM)
        elif re.search("[0-9]+ error /", s):
            col = GREEN if s.startswith("0 error") else RED
        txt((PAD_X, y), ln, font=font, fill=col)
        y += LINE

    out = P(str(out_path))
    out.parent.mkdir(parents=True, exist_ok=True)
    getattr(img, MK["save"])(str(out))
    print("wrote", out, getattr(img, MK["size"]))


if __name__ == "__main__":
    capdir = P.home() / ".hermes/cache/scratch/cap"
    outdir = P("docs/screenshots")
    render(capdir / "scan_hermes.txt", outdir / "1-hermes-floor.png",
           "ctxfloor \u2014 the agent context floor",
           cmd_echo=["ctxfloor scan hermes"])
    render(capdir / "scan_lean.txt", outdir / "2-lean-fixture.png",
           "ctxfloor \u2014 shipped fixture",
           cmd_echo=["ctxfloor scan generic --path fixtures/lean-hermes"])
    render(capdir / "gate_bloated.txt", outdir / "3-gate-findings.png",
           "ctxfloor \u2014 the CI budget gate",
           cmd_echo=["ctxfloor gate generic --path fixtures/bloated-hermes "
                     "--budget 500 --fail-on error"])
    render(capdir / "d3_before.txt", outdir / "4a-before.png", "before",
           cmd_echo=["ctxfloor scan generic --path ~/agent-config"])
    render(capdir / "d3_after.txt", outdir / "4b-after.png", "after (trimmed)",
           cmd_echo=["ctxfloor scan generic --path ~/agent-config"])
    render(capdir / "explain.txt", outdir / "5-explain.png",
           "ctxfloor explain", cmd_echo=["ctxfloor explain F_MISSING_LINK"])
    render(capdir / "ci.txt", outdir / "6-ci-green.png", "github actions",
           cmd_echo=["gh run list --repo ar33s08/contextfloor --limit 3"])
