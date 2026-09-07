from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request

from .llm import generate, is_mock
from .util import THUMBS, append_credit, log

_BG = {"sun": "#FFEFC9", "grape": "#EBE2FA", "coral": "#FFE1DB", "mint": "#D5F4E8", "sky": "#D6F1FA"}
_INK = {"sun": "#F0A81F", "grape": "#9678CC", "coral": "#F2624D", "mint": "#3EB587", "sky": "#2FA7CC"}
_FONT = "'Zen Maru Gothic','Noto Sans CJK JP','Hiragino Maru Gothic ProN',sans-serif"


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
    if i < len(text):  # 行数が足りない → 最終行を省略記号で締める
        rest = (cur + text[i:]).strip()
        if lines:
            lines[-1] = (lines[-1] + rest)[: n - 1].rstrip() + "…"
        else:
            lines = [rest[: n - 1] + "…"]
    return [ln for ln in lines if ln]


def _balance2(text: str) -> list[str]:
    """長い1行を、中央付近の切れ目で2行に割る。"""
    mid = len(text) // 2
    good = set("、。，・！？!?」』）)")
    particle = set("はがをにでとへやもの")
    for off in range(0, mid - 2):
        for j in (mid - off, mid + off):
            if 4 <= j <= len(text) - 4 and (text[j - 1] in good or text[j - 1] in particle):
                return [text[:j].strip(), text[j:].strip()]
    return [text[:mid].strip(), text[mid:].strip()]


def _layout(headline: str) -> tuple[list[str], int]:
    """カード幅に収まる行数・フォントサイズを選ぶ。"""
    text = headline.replace("\n", " ").strip()
    for chars, fs in ((14, 66), (16, 58), (19, 52), (23, 44)):
        lines = _greedy_wrap(text, chars, max_lines=3)
        if lines and max(len(ln) for ln in lines) <= chars + 1:
            if len(lines) == 1 and len(lines[0]) >= 15:
                lines = _balance2(lines[0])
                fs = 58
            return lines, fs
    return _greedy_wrap(text, 23, max_lines=3), 44


def build_svg(headline: str, sub: str, emoji: str, accent: str, site: str = "罪悪感ゼロ育児") -> str:
    bg = _BG.get(accent, "#FFEFC9")
    ink = _INK.get(accent, "#F0A81F")
    lines, fs = _layout(headline)
    lh = int(fs * 1.34)
    block_h = lh * (len(lines) - 1)
    y0 = 330 - block_h // 2
    tspans = "".join(
        f'<tspan x="100" y="{y0 + i * lh}">{html.escape(ln)}</tspan>' for i, ln in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="{bg}"/>
  <circle cx="1040" cy="110" r="230" fill="#ffffff" opacity="0.45"/>
  <circle cx="140" cy="560" r="170" fill="#ffffff" opacity="0.4"/>
  <rect x="56" y="56" width="1088" height="518" rx="48" fill="#ffffff"/>
  <text x="100" y="156" font-family="{_FONT}" font-size="34" fill="{ink}">{html.escape((emoji + '  ' + sub).strip())}</text>
  <text font-family="{_FONT}" font-size="{fs}" font-weight="700" fill="#3F3A4A">{tspans}</text>
  <rect x="100" y="500" width="18" height="18" rx="5" fill="{ink}"/>
  <text x="130" y="516" font-family="{_FONT}" font-size="30" fill="#7E7994">{html.escape(site)}</text>
</svg>"""


def _maybe_ai_headline(article_title: str) -> str | None:
    """THUMB_HEADLINE=ai のとき、サムネ用に短い惹句を作る（任意）。"""
    if os.environ.get("THUMB_HEADLINE") != "ai" or is_mock():
        return None
    try:
        h = generate(
            "次の記事タイトルを、サムネイル用に12〜16字の短い惹句へ言い換えて。"
            "煽らず、やさしく、肯定的に。1案だけ、記号なしで返す。\n\n" + article_title,
            temperature=0.7,
        ).strip().splitlines()[0][:20]
        return h or None
    except Exception as e:  # noqa: BLE001
        log(f"  サムネ惹句生成失敗（{e}）→ タイトルを使用")
        return None


_UNSPLASH_API = "https://api.unsplash.com/search/photos"
_UA = "kzi-bot/1.0 (+https://zaiaku-zero-ikuji.pages.dev)"


def _unsplash_photo(query: str) -> dict | None:
    """UNSPLASH_ACCESS_KEY があれば、クエリに合う横長写真を1枚返す。"""
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key or not query or is_mock():
        return None
    qs = urllib.parse.urlencode(
        {
            "query": query,
            "orientation": "landscape",
            "content_filter": "high",
            "per_page": "8",
        }
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
    2. 無ければ、カテゴリ色＋見出しの SVG カードを生成して OGP 画像に
    戻り値: {"heroImage": <path|None>, "ogImage": <path>}
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

    # フォールバック：SVG カード
    headline = _maybe_ai_headline(headline) or headline
    svg = build_svg(headline, sub, emoji, accent)
    (THUMBS / f"{slug}.svg").write_text(svg, encoding="utf-8")
    try:
        import cairosvg

        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=str(THUMBS / f"{slug}.png"),
            output_width=1200,
            output_height=630,
        )
        log(f"  thumbnail(card): public/images/thumb/{slug}.png")
        return {"heroImage": None, "ogImage": f"/images/thumb/{slug}.png"}
    except Exception as e:  # noqa: BLE001
        log(f"  cairosvg 未導入/失敗（{e}）→ SVG を OGP に使用")
        return {"heroImage": None, "ogImage": f"/images/thumb/{slug}.svg"}
