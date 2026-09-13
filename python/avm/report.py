from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path

_FONT_PATH = Path(__file__).resolve().parents[2] / "docs" / "fonts" / "noto-sans-sc-report.ttf"
_CJK_STACK = '"Noto Sans SC Report", "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif'


def _font_face() -> str:
    if not _FONT_PATH.exists():
        return ""
    payload = base64.b64encode(_FONT_PATH.read_bytes()).decode("ascii")
    return (
        "@font-face { font-family: 'Noto Sans SC Report'; "
        f"src: url('data:font/ttf;base64,{payload}') format('truetype'); "
        "font-weight: 400; font-style: normal; font-display: swap; }"
    )


def _inline_images(html: str, base_dir: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
            return match.group(0)
        path = (base_dir / src).resolve()
        if not path.exists():
            return match.group(0)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{payload}"'

    return re.sub(r'src="([^"]+)"', repl, html)


def write_html(
    path: Path,
    title: str,
    summary: str,
    cards: list[str],
    metrics: list[tuple[str, str]] | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_html = ""
    if metrics:
        items = "".join(f'<div class="metric"><span>{k}</span><strong>{v}</strong></div>' for k, v in metrics)
        metric_html = f'<div class="metrics">{items}</div>'
    body = "\n".join(cards)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <style>
    {_font_face()}
    body {{ font-family: {_CJK_STACK}; margin: 32px; background: #0f141c; color: #e8edf5; }}
    h1,h2 {{ color: #f4f7fb; }}
    .summary {{ background: #182230; padding: 16px 20px; border-radius: 12px; line-height: 1.6; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin: 18px 0 8px; }}
    .metric {{ background: #182230; border-radius: 10px; padding: 12px 14px; }}
    .metric span {{ display: block; color: #8b97a8; font-size: 12px; }}
    .metric strong {{ font-size: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 24px; }}
    .card {{ background: #182230; border-radius: 12px; overflow: hidden; }}
    .card img {{ width: 100%; display: block; background: #0b0f16; }}
    .card p {{ margin: 10px 14px 14px; color: #b7c2d0; font-size: 14px; }}
    code {{ color: #9ad1ff; }}
    a {{ color: #8fd0ff; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="summary">{summary}</div>
  {metric_html}
  <div class="grid">
    {body}
  </div>
</body>
</html>
"""
    html = _inline_images(html, path.parent)
    path.write_text(html, encoding="utf-8")
    return path


def card(image_rel: str, caption: str) -> str:
    return f'<article class="card"><img src="{image_rel}" alt=""/><p>{caption}</p></article>'
