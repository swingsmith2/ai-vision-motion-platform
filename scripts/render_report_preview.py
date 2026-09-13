#!/usr/bin/env python3
"""Render report.html to a PNG preview with embedded CJK text."""
from __future__ import annotations

import argparse
import base64
import html as html_lib
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
BG = (15, 20, 28)
PANEL = (24, 34, 48)
TEXT = (232, 237, 245)
MUTED = (139, 151, 168)
CAPTION = (183, 194, 208)
TITLE = (244, 247, 251)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size, index=2)


def strip_tags(raw: str) -> str:
    text = re.sub(r"<code>(.*?)</code>", r"\1", raw, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return html_lib.unescape(re.sub(r"\s+", " ", text)).strip()


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if draw.textlength(trial, font=font) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = ch
    if current:
        lines.append(current)
    return lines or [""]


def parse_report(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    title = strip_tags(re.search(r"<h1>(.*?)</h1>", raw, re.S).group(1))
    summary = strip_tags(re.search(r'<div class="summary">(.*?)</div>', raw, re.S).group(1))
    metrics = [(strip_tags(k), strip_tags(v)) for k, v in re.findall(r"<span>(.*?)</span><strong>(.*?)</strong>", raw)]
    cards = []
    for src, caption in re.findall(r'<img src="([^"]+)"[^>]*>\s*<p>(.*?)</p>', raw, re.S):
        if src.startswith("data:"):
            payload = src.split(",", 1)[1]
            image = Image.open(io.BytesIO(base64.b64decode(payload))).convert("RGB")
        else:
            image = Image.open(path.parent / src).convert("RGB")
        cards.append((image, strip_tags(caption)))
    return {"title": title, "summary": summary, "metrics": metrics, "cards": cards}


def pick_cards(cards: list, max_cards: int | None) -> list:
    if max_cards is None or max_cards >= len(cards):
        return cards
    picked = []
    seen = set()
    for image, caption in cards:
        key = caption.split()[0] if caption else caption
        if key in seen:
            continue
        seen.add(key)
        picked.append((image, caption))
        if len(picked) >= max_cards:
            return picked
    for item in cards:
        if item not in picked:
            picked.append(item)
        if len(picked) >= max_cards:
            break
    return picked


def render(
    report: dict,
    out: Path,
    width: int = 1100,
    cols: int = 3,
    max_cards: int | None = None,
    thumb_h: int | None = None,
) -> Path:
    pad = 28
    gap = 12
    cards = pick_cards(report["cards"], max_cards)
    card_w = (width - pad * 2 - gap * (cols - 1)) // cols
    title_font = load_font(26)
    body_font = load_font(14)
    metric_label = load_font(11)
    metric_value = load_font(18)
    caption_font = load_font(12)

    probe = Image.new("RGB", (width, 200), BG)
    draw = ImageDraw.Draw(probe)
    summary_lines = wrap(draw, report["summary"], body_font, width - pad * 2 - 40)
    summary_h = 20 + len(summary_lines) * 22
    metric_h = 64 if report["metrics"] else 0
    card_heights = []
    fitted: list[tuple[Image.Image, str, int]] = []
    for image, caption in cards:
        scale = card_w / image.width
        h = max(1, int(image.height * scale))
        if thumb_h:
            h = min(h, thumb_h)
            w = max(1, int(image.width * (h / image.height)))
            image = image.resize((w, h), Image.Resampling.LANCZOS)
            canvas_img = Image.new("RGB", (card_w, h), (11, 15, 22))
            canvas_img.paste(image, ((card_w - w) // 2, 0))
            image = canvas_img
        else:
            image = image.resize((card_w, h), Image.Resampling.LANCZOS)
        fitted.append((image, caption, h))
        card_heights.append(h + 40)
    rows = [card_heights[i : i + cols] for i in range(0, len(card_heights), cols)]
    grid_h = sum(max(row) for row in rows) + gap * max(0, len(rows) - 1) if rows else 0
    height = pad + 36 + 12 + summary_h + 12 + metric_h + 12 + grid_h + pad

    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    y = pad
    draw.text((pad, y), report["title"], font=title_font, fill=TITLE)
    y += 38
    draw.rounded_rectangle((pad, y, width - pad, y + summary_h), 10, fill=PANEL)
    ty = y + 10
    for line in summary_lines:
        draw.text((pad + 16, ty), line, font=body_font, fill=TEXT)
        ty += 22
    y += summary_h + 12
    if report["metrics"]:
        n = len(report["metrics"])
        mw = (width - pad * 2 - gap * (n - 1)) // n
        for i, (key, value) in enumerate(report["metrics"]):
            x = pad + i * (mw + gap)
            draw.rounded_rectangle((x, y, x + mw, y + 56), 10, fill=PANEL)
            draw.text((x + 12, y + 8), key, font=metric_label, fill=MUTED)
            draw.text((x + 12, y + 26), value, font=metric_value, fill=TITLE)
        y += metric_h
    y += 10
    for i, (image, caption, img_h) in enumerate(fitted):
        col = i % cols
        if col == 0 and i:
            y += max(card_heights[i - cols : i]) + gap
        x = pad + col * (card_w + gap)
        card_h = img_h + 36
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), 10, fill=PANEL)
        canvas.paste(image, (x, y))
        draw.text((x + 10, y + img_h + 10), caption, font=caption_font, fill=CAPTION)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, optimize=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--max-cards", type=int, default=None)
    parser.add_argument("--thumb-h", type=int, default=None)
    args = parser.parse_args()
    path = render(
        parse_report(args.report),
        args.output,
        width=args.width,
        cols=args.cols,
        max_cards=args.max_cards,
        thumb_h=args.thumb_h,
    )
    print(path, path.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
