"""毎日の自己改善パス。

既存記事を1本ずつ点検して、サイトを少しずつ良くしていく。
- mode "links"      : 内部リンク・画像の存在チェックのみ。壊れていたら REVIEW.md に記録。
- mode "full"（既定）: さらに LLM の軽いリライト（導入をターゲットのリアルなペインに寄せて締める・
                       冗長な数文を整える）。事実・見出し・分量は保つ。
                       禁止語 / YMYL に触れたら破棄して links 相当に留める。
                       本文が変わったら frontmatter に updatedDate を入れて鮮度を出す。
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


_REWRITE_PROMPT = """\
次の記事本文を、サイト「罪悪感ゼロ育児」の声で軽くリライトしてください。

必ず守る:
- 事実・数字・出典・見出し構成（##）は一切変えない
- 全体の分量はほぼ同じ（±25%以内）
- 禁止語を使わない: 〜すべき / 〜してください / 〜しなさい / 〜しなきゃダメ / がんばりましょう / がんばって
- 医療・安全の断定をしない（「絶対大丈夫」「必ず治る」など不可）

やること:
1. 導入（最初の1〜3文）を、読者のリアルなペインに寄り添う入りに書き直す。
   読者像 = 睡眠不足で余裕のない新米の親。SNSの比較でしんどくなっている人。
   「〜という夜はありませんか？」のように、具体的な情景から始めて共感で掴む。
2. 本文中の回りくどい／固い文を2〜3か所だけ、やわらかく短くする。
3. それ以外は触らない。

本文全体をマークダウンだけで返してください（前置き・説明は書かない）。

----- 本文 -----
"""


def _set_updated_date(fm: str) -> str:
    """frontmatter 文字列に updatedDate を差し込む/更新する。"""
    line = f"updatedDate: '{today()}'"
    if re.search(r"^updatedDate:", fm, re.M):
        return re.sub(r"^updatedDate:.*$", line, fm, flags=re.M)
    # pubDate の直後に入れる（無ければ末尾）
    if re.search(r"^pubDate:.*$", fm, re.M):
        return re.sub(r"^(pubDate:.*)$", r"\1\n" + line, fm, count=1, flags=re.M)
    return fm.rstrip("\n") + "\n" + line + "\n"


def _editor_pass(text: str) -> str | None:
    if is_mock():
        return None
    head, fm, body = text.split("---", 2)
    try:
        out = generate(_REWRITE_PROMPT + body.strip(), temperature=0.5).strip()
    except Exception as e:  # noqa: BLE001
        log(f"  リライト失敗（{e}）→ スキップ")
        return None
    if out.startswith("```"):
        out = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", out).strip()
    if check_banned(out) or check_ymyl(out):
        log("  リライト結果がガードレールに抵触 → 破棄")
        return None
    if abs(len(out) - len(body.strip())) > len(body.strip()) * 0.30:
        log("  リライト結果の分量が想定外 → 破棄")
        return None
    if out == body.strip():
        return None
    return head + "---" + _set_updated_date(fm) + "---\n\n" + out + "\n"


def daily_improve(mode: str = "full") -> dict:
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
        append_log(f"🔧 点検 `{slug}` — 問題なし{'（導入を軽くリライト・updatedDate 更新）' if changed else ''}")

    return {"status": "reviewed", "slug": slug, "issues": issues, "edited": changed}
