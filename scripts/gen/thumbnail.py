from __future__ import annotations

import glob
import json
import os
import urllib.parse
import urllib.request

from .llm import generate, is_mock
from .util import THUMBS, append_credit, log

# カテゴリ色（site.ts と対応）
_BG = {"sun": "#FFEFC9", "grape": "#EBE2FA", "coral": "#FFE1DB", "mint": "#D5F4E8", "sky": "#D6F1FA"}
_INK = {"sun": "#F0A81F", "grape": "#9678CC", "coral": "#F2624D", "mint": "#3EB587", "sky": "#2FA7CC"}
_HEAD = "#3F3A4A"
_SITE = "#7E7994"

# CJK が確実に出るフォントを探す（cairosvg は CJK フォールバックが弱く豆腐になるため Pillow で描く）
_FONT_CANDIDATES = [
    os.environ.get("KZI_CARD_FONT", ""),
    # CI (ubuntu, fonts-noto-cjk)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    # macOS
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def _font_path() -> str | None:
    for p in _FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    for pat in ("/usr/share/fonts/**/*NotoSansCJK*", "/usr/share/fonts/**/*NotoSerifCJK*"):
        hits = glob.glob(pat, recursive=True)
        if hits:
            return sorted(hits)[0]
    return None


def _font(size: int):
    from PIL import ImageFont

    p = _font_path()
    if not p:
        log("  サムネ: CJK フォントが見つからず既定フォント（豆腐の可能性）")
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(p, size)
    except Exception:  # noqa: BLE001
        return ImageFont.truetype(p, size, index=0)


# ---------------------------------------------------------------- 見出しの折り返し
def _greedy_wrap(text: str, n: int, max_lines: int = 3) -> list[str]:
    prefer = set("、。，．・！？!?」』）)")
    lines: list[str] = []
    cur = ""
    i = 0
    while i < len(text):
        cur += text[i]
        i += 1
        if len(cur) >= n and (text[i - 1] in prefer or len(cur) >= n + 2):
            lines.append(cur.strip())
            cur = ""
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur.strip())
        cur = ""
    if i < len(text):
        rest = (cur + text[i:]).strip()
        if lines:
            lines[-1] = (lines[-1] + rest)[: n - 1].rstrip() + "…"
        else:
            lines = [rest[: n - 1] + "…"]
    return [ln for ln in lines if ln]


def _balance2(text: str) -> list[str]:
    mid = len(text) // 2
    good = set("、。，・！？!?」』）)")
    particle = set("はがをにでとへやもの")
    for off in range(0, mid - 2):
        for j in (mid - off, mid + off):
            if 4 <= j <= len(text) - 4 and (text[j - 1] in good or text[j - 1] in particle):
                return [text[:j].strip(), text[j:].strip()]
    return [text[:mid].strip(), text[mid:].strip()]


def _layout(headline: str) -> tuple[list[str], int]:
    text = headline.replace("\n", " ").strip()
    for chars, fs in ((14, 66), (16, 58), (19, 52), (23, 44)):
        lines = _greedy_wrap(text, chars, max_lines=3)
        if lines and max(len(ln) for ln in lines) <= chars + 1:
            if len(lines) == 1 and len(lines[0]) >= 15:
                return _balance2(lines[0]), 58
            return lines, fs
    return _greedy_wrap(text, 23, max_lines=3), 44


# ---------------------------------------------------------------- カード描画（Pillow）
def _render_card(slug: str, headline: str, sub: str, accent: str) -> str:
    from PIL import Image, ImageDraw

    bg = _BG.get(accent, "#FFEFC9")
    ink = _INK.get(accent, "#F0A81F")
    W, H = 1200, 630

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img, "RGBA")

    d.ellipse((820, -120, 1280, 340), fill=(255, 255, 255, 115))
    d.ellipse((-40, 380, 320, 740), fill=(255, 255, 255, 100))
    d.rounded_rectangle((56, 56, 1144, 574), radius=48, fill="#FFFFFF")

    d.text((100, 120), sub.strip(), font=_font(34), fill=ink)

    lines, fs = _layout(headline)
    lh = int(fs * 1.36)
    y = 315 - lh * (len(lines) - 1) // 2 - fs // 2
    hf = _font(fs)
    for ln in lines:
        d.text((100, y), ln, font=hf, fill=_HEAD)
        y += lh

    d.rounded_rectangle((100, 500, 118, 518), radius=5, fill=ink)
    d.text((132, 496), "罪悪感ゼロ育児", font=_font(30), fill=_SITE)

    THUMBS.mkdir(parents=True, exist_ok=True)
    out = THUMBS / f"{slug}.png"
    img.save(out, "PNG")
    return f"/images/thumb/{slug}.png"


def _maybe_ai_headline(article_title: str) -> str | None:
    if os.environ.get("THUMB_HEADLINE") != "ai" or is_mock():
        return None
    try:
        h = (
            generate(
                "次の記事タイトルを、サムネイル用に12〜16字の短い惹句へ言い換えて。"
                "煽らず、やさしく、肯定的に。1案だけ、記号なしで返す。\n\n" + article_title,
                temperature=0.7,
            )
            .strip()
            .splitlines()[0][:20]
        )
        return h or None
    except Exception as e:  # noqa: BLE001
        log(f"  サムネ惹句生成失敗（{e}）→ タイトルを使用")
        return None


# ---------------------------------------------------------------- 写真（Unsplash）
_UNSPLASH_API = "https://api.unsplash.com/search/photos"
_UA = "kzi-bot/1.0 (+https://zaiaku-zero-ikuji.pages.dev)"


def _unsplash_photo(query: str) -> dict | None:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key or not query or is_mock():
        return None
    qs = urllib.parse.urlencode(
        {"query": query, "orientation": "landscape", "content_filter": "high", "per_page": "8"}
    )
    req = urllib.request.Request(
        f"{_UNSPLASH_API}?{qs}",
        headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1", "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        log(f"  Unsplash 検索失敗（{e}）→ カード生成にフォールバック")
        return None
    for res in data.get("results", []):
        raw = (res.get("urls") or {}).get("raw")
        if not raw:
            continue
        return {
            "download": raw + "&w=1200&h=630&fit=crop&crop=faces,entropy&fm=jpg&q=72",
            "credit_name": ((res.get("user") or {}).get("name")) or "Unsplash",
            "credit_link": ((res.get("links") or {}).get("html")) or "https://unsplash.com",
            "id": res.get("id", ""),
        }
    return None


def _download(url: str, dest) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read()
        if len(body) < 2000:
            return False
        dest.write_bytes(body)
        return True
    except Exception as e:  # noqa: BLE001
        log(f"  写真ダウンロード失敗（{e}）")
        return False


def render(
    slug: str,
    headline: str,
    sub: str,
    emoji: str,
    accent: str,
    *,
    photo_query: str | None = None,
) -> dict:
    """記事のメイン画像を用意する。

    1. UNSPLASH_ACCESS_KEY + photo_query があれば、内容に合う写真をDLして heroImage に
    2. 無ければ「カテゴリ色＋見出し」のデザインカード（PNG）を Pillow で描く
    戻り値: {"heroImage": <path>, "ogImage": <path>}
    ※ 絵文字だけのサムネは出さない。必ず写真かカードを返す。
    """
    THUMBS.mkdir(parents=True, exist_ok=True)

    photo = _unsplash_photo(photo_query or "")
    if photo:
        dest = THUMBS / f"{slug}.jpg"
        if _download(photo["download"], dest):
            append_credit(
                f"`{slug}` — photo by [{photo['credit_name']}]({photo['credit_link']}) on Unsplash"
                f"（query: {photo_query!r}）"
            )
            log(f"  photo: public/images/thumb/{slug}.jpg  by {photo['credit_name']} (Unsplash)")
            return {"heroImage": f"/images/thumb/{slug}.jpg", "ogImage": f"/images/thumb/{slug}.jpg"}

    headline = _maybe_ai_headline(headline) or headline
    try:
        path = _render_card(slug, headline, sub, accent)
        log(f"  thumbnail(card): public/images/thumb/{slug}.png")
        return {"heroImage": path, "ogImage": path}
    except Exception as e:  # noqa: BLE001
        log(f"  カード生成失敗（{e}）")
        raise
