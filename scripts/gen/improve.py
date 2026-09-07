"""毎日の自己改善パス。

既存記事を1本ずつ点検して、サイトを少しずつ良くしていく。
- mode "links"（既定）: 内部リンク・画像の存在チェックのみ。壊れていたら REVIEW.md に記録。
- mode "full"        : さらに LLM の軽い推敲（導入を締める・関連リンクの言及を増やす）。
                       禁止語 / YMYL に触れたら破棄して links 相当に留める。
"""

from __future__ import annotations

import re

from .guardrails import check_banned, check_ymyl
from .llm import generate, is_mock
from .util import BLOG, CATEGORIES, DATA, ROOT, append_log, load_json, log, save_json, today, write_review


def _link_check(md: str) -> list[str]:
    issues: list[str] = []
    for m in re.finditer(r"\]\((/[^)\s]+)\)", md):
        href = m.group(1).split("#")[0].rstrip("/")
        if href in ("", "/blog", "/about", "/categories"):
            continue
        if href.startswith("/blog/"):
            if not (BLOG / (href.split("/blog/", 1)[1] + ".md")).exists():
                issues.append(f"リンク切れ {href}")
        elif href.startswith("/categories/"):
            if href.split("/categories/", 1)[1] not in CATEGORIES:
                issues.append(f"未知カテゴリ {href}")
        elif href.startswith("/images/"):
            if not (ROOT / "public" / href.lstrip("/")).exists():
                issues.append(f"画像なし {href}")
    return issues


def _editor_pass(text: str) -> str | None:
    if is_mock():
        return None
    body = text.split("---", 2)[-1]
    try:
        out = generate(
            "次の記事本文を、事実・見出し構成・意味を一切変えずに、"
            "導入1〜2文だけ少し引き締めて読みやすくしてください。"
            "禁止語（〜すべき / 〜してください / 〜しなきゃダメ / がんばりましょう）は使わないこと。"
            "本文全体をマークダウンで返してください。\n\n" + body,
            temperature=0.4,
        ).strip()
    except Exception as e:  # noqa: BLE001
        log(f"  推敲失敗（{e}）→ スキップ")
        return None
    if check_banned(out) or check_ymyl(out):
        log("  推敲結果がガードレールに抵触 → 破棄")
        return None
    if abs(len(out) - len(body)) > len(body) * 0.35:
        log("  推敲結果の分量が想定外 → 破棄")
        return None
    return text.split("---", 2)[0] + "---" + text.split("---", 2)[1] + "---\n" + out.lstrip("\n")


def daily_improve(mode: str = "links") -> dict:
    posts = sorted(BLOG.glob("*.md"))
    if not posts:
        return {"status": "skip", "reason": "no posts"}

    state = load_json(DATA / "state.json", {})
    seen = state.setdefault("improve", {})
    target = min(posts, key=lambda p: seen.get(p.stem, "1970-01-01"))
    slug = target.stem
    text = target.read_text(encoding="utf-8")

    issues = _link_check(text)
    changed = False
    if mode == "full" and not issues:
        edited = _editor_pass(text)
        if edited and edited != text:
            target.write_text(edited, encoding="utf-8")
            changed = True

    seen[slug] = today()
    save_json(DATA / "state.json", state)

    if issues:
        write_review(slug, [f"{slug}: {i}" for i in issues])
        append_log(f"🔧 点検 `{slug}` — 要確認: {'; '.join(issues)}")
    else:
        append_log(f"🔧 点検 `{slug}` — 問題なし{'（本文を推敲）' if changed else ''}")

    return {"status": "reviewed", "slug": slug, "issues": issues, "edited": changed}
