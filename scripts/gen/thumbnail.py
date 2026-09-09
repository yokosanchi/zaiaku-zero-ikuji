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


# ---------------------------------------------------------------- 見出しの折り返し（実測ベース）
# 折り返してよい区切り（この直後で改行できる）。句読点・助詞・閉じ括弧など。
_BREAK_AFTER = set("、。，．・！？!?」』）)】〕〉》")
_BREAK_BEFORE = set("「『（(【〔〈《")


def _wrap_measured(draw, text: str, font, max_w: int, max_lines: int) -> list[str] | None:
    """font で描いたとき各行が max_w 以内に収まるよう折り返す。
    max_lines を超える／1文字も入らない場合は None。"""
    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
            continue
        # cur が現在行。区切りの良い位置まで戻して改行する
        cut = cur
        if cur and cur[-1] not in _BREAK_AFTER and ch not in _BREAK_BEFORE:
            for k in range(len(cur) - 1, max(0, len(cur) - 8), -1):
                if cur[k - 1] in _BREAK_AFTER or cur[k] in _BREAK_BEFORE:
                    cut = cur[:k]
                    break
        rest = cur[len(cut):] + ch
        if not cut:  # 1文字も入らない
            return None
        lines.append(cut)
        cur = rest
        if len(lines) >= max_lines:
            # まだ文字が残る → 最終行を省略記号で締める
            remaining = cur + text[text.index(ch) + 1:] if ch in text else cur
            last = lines[-1]
            while last and draw.textlength(last + "…", font=font) > max_w:
                last = last[:-1]
            lines[-1] = (last + "…") if remaining.strip() else last
            return lines
    if cur:
        lines.append(cur)
    return lines[:max_lines] if lines else None


def _layout_card(draw, headline: str, max_w: int, max_h: int):
    """収まる中で最大のフォントサイズと行を返す。必ず max_w×max_h に収める。"""
    text = " ".join(headline.split())
    for fs in (66, 60, 54, 48, 44, 40, 36, 32):
        font = _font(fs)
        lines = _wrap_measured(draw, text, font, max_w, max_lines=3)
        if not lines:
            continue
        lh = int(fs * 1.34)
        if lh * len(lines) <= max_h and all(draw.textlength(ln, font=font) <= max_w for ln in lines):
            return lines, fs, lh
    # 最小でも収まらない（極端に長い）→ 32px で3行に強制詰め
    font = _font(32)
    lines = _wrap_measured(draw, text, font, max_w, max_lines=3) or [text[:20] + "…"]
    return lines, 32, 43


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

    # レイアウト定数（白パネル内の描画可能域）
    PAD_L = 104
    TEXT_W = 992  # 104 〜 1096
    SUB_Y = 118
    SITE_Y = 498
    HEAD_TOP = SUB_Y + 66
    HEAD_BOTTOM = SITE_Y - 24  # 見出しはこの範囲に必ず収める

    # サブ（タイプ名）— 長すぎたら縮める
    sub = " ".join((sub or "").split())
    sf = _font(32)
    while sub and d.textlength(sub, font=sf) > TEXT_W:
        sub = sub[:-1]
    d.text((PAD_L, SUB_Y), sub, font=sf, fill=ink)

    # 見出し — 実測で必ず枠内に収める
    lines, fs, lh = _layout_card(d, headline, TEXT_W, HEAD_BOTTOM - HEAD_TOP)
    hf = _font(fs)
    block_h = lh * len(lines)
    y = HEAD_TOP + max(0, (HEAD_BOTTOM - HEAD_TOP - block_h) // 2)
    for ln in lines:
        d.text((PAD_L, y), ln, font=hf, fill=_HEAD)
        y += lh

    d.rounded_rectangle((PAD_L, SITE_Y + 2, PAD_L + 18, SITE_Y + 20), radius=5, fill=ink)
    d.text((PAD_L + 32, SITE_Y - 2), "罪悪感ゼロ育児", font=_font(30), fill=_SITE)

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
