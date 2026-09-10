#!/usr/bin/env python3
"""デザインカードのサムネを再生成する。

対象: heroImage が /images/thumb/<slug>.png を指す記事（写真サムネは対象外）。
カードに出す文言は frontmatter の `thumbHook`（あれば）＝読み手のペイン起点のキャッチ、
無ければ `title`。

    python scripts/regen_cards.py                 # 全カード再生成
    python scripts/regen_cards.py slug1 slug2 ... # 指定スラッグだけ
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen import thumbnail as t  # noqa: E402
from gen.util import BLOG, CATEGORY_ACCENT, TYPE_LABEL  # noqa: E402


def _fm(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def _get(fm: str, key: str) -> str | None:
    m = re.search(rf'^{key}:\s*"?(.+?)"?\s*$', fm, re.M)
    return m.group(1) if m else None


def main() -> None:
    only = set(sys.argv[1:])
    files = sorted(BLOG.glob("*.md")) + sorted(BLOG.glob("*.mdx"))
    n = 0
    for p in files:
        if only and p.stem not in only:
            continue
        fm = _fm(p.read_text(encoding="utf-8"))
        hero = _get(fm, "heroImage") or ""
        if f"/images/thumb/{p.stem}.png" not in hero:
            continue  # 写真サムネはそのまま
        hook = _get(fm, "thumbHook") or _get(fm, "title") or p.stem
        cat = _get(fm, "category") or "kokoro"
        at = _get(fm, "articleType") or "voice"
        t._render_card(p.stem, hook, TYPE_LABEL.get(at, ""), CATEGORY_ACCENT.get(cat, "coral"))
        print(f"  regen {p.stem}  ← {hook!r}")
        n += 1
    print(f"再生成: {n} 枚")


if __name__ == "__main__":
    main()
