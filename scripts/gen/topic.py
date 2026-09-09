from __future__ import annotations

import collections
import re

from .util import BLOG, CATEGORIES, DATA, ROTATION, STAGES, dump_yaml, load_json, load_yaml, log

_TARGET_PER_CATEGORY = 10  # 各カテゴリの目標本数


class NoTopic(Exception):
    pass


def _published_counts() -> tuple[collections.Counter, collections.Counter]:
    """公開済み記事の category / stage 別カウント（.md / .mdx 両方）。"""
    cc: collections.Counter = collections.Counter()
    sc: collections.Counter = collections.Counter()
    for p in list(BLOG.glob("*.md")) + list(BLOG.glob("*.mdx")):
        fm = p.read_text(encoding="utf-8").split("---", 2)
        fm = fm[1] if len(fm) == 3 else ""
        c = re.search(r'^category:\s*"?([a-z_]+)"?', fm, re.M)
        s = re.search(r'^stage:\s*"?([a-z0-9_]+)"?', fm, re.M)
        if c:
            cc[c.group(1)] += 1
        if s:
            sc[s.group(1)] += 1
    return cc, sc


def _need_score(entry: dict, cc: collections.Counter, sc: collections.Counter) -> float:
    """不足しているほど高スコア。カテゴリ不足＋ステージ不足。"""
    cat_need = max(0, _TARGET_PER_CATEGORY - cc.get(entry.get("category"), 0))
    st = entry.get("stage")
    stage_need = 0.0
    if st in STAGES:
        avg = (sum(sc.values()) / len(STAGES)) if sc else 0
        stage_need = max(0.0, avg - sc.get(st, 0)) / 4.0
    return cat_need + stage_need


# ネタが尽きたときに LLM 起案へ渡す、カテゴリ別の公的ソース既定値。
_DEFAULT_SOURCES = {
    "gohan": ["https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000134208.html", "https://www.cfa.go.jp/policies/boshihoken"],
    "nenne": ["https://www.cfa.go.jp/policies/boshihoken", "https://www.jpeds.or.jp/"],
    "kokoro": ["https://www.cfa.go.jp/", "https://www.mhlw.go.jp/kokoro/"],
    "sango": ["https://www.mhlw.go.jp/kokoro/", "https://www.cfa.go.jp/policies/boshihoken"],
    "wanope": ["https://www.cfa.go.jp/policies/boshihoken"],
    "hatsuiku": ["https://www.cfa.go.jp/policies/boshihoken", "https://www.jpeds.or.jp/"],
    "kurashi": ["https://www.caa.go.jp/policies/policy/consumer_safety/child/"],
    "sns": ["https://www.cfa.go.jp/"],
}


def _unique_slug(base: str, bank: list[dict]) -> str:
    used = (
        {e.get("slug") for e in bank}
        | {p.stem for p in BLOG.glob("*.md")}
        | {p.stem for p in BLOG.glob("*.mdx")}
    )
    slug, n = base, 2
    while slug in used or (BLOG / f"{slug}.md").exists() or (BLOG / f"{slug}.mdx").exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _llm_topic(wanted: str, bank: list[dict]) -> dict:
    """topic-bank が尽きたとき、LLM に新しいネタを1件起案させて bank に追記する。"""
    from .llm import generate_json, is_mock

    if is_mock():
        raise NoTopic("topic-bank が空（MOCK のため LLM 起案はしない）")

    type_hint = {
        "trend": "SNS（Instagram/TikTok/X）で最近話題の育児トピックの深掘り",
        "basics": "新米の親が最初につまずく『基本のき』の解説",
        "service": "家事・育児の負担を減らす市販品や公的サービスの紹介",
        "voice": "当事者のリアルな声と公的事実を組み合わせた記事",
        "cheer": "しんどい親をそっと肯定するエッセイ寄りの記事",
    }.get(wanted, "育児トピック")

    cc, sc = _published_counts()
    thin_cats = [c for c in CATEGORIES if cc.get(c, 0) < _TARGET_PER_CATEGORY] or list(CATEGORIES)
    thin_stages = sorted(STAGES, key=lambda s: sc.get(s, 0))[:3]

    prompt = (
        "あなたは育児メディア『罪悪感ゼロ育児』の編集者です。"
        "読者は睡眠不足で余裕のない新米の親で、SNSの比較でしんどくなっている層。"
        f"次の方針で、新しい記事ネタを1件だけ提案してください: {type_hint}。\n"
        "手抜きを責めない・公的情報に基づく・特定の子育て法を断定しない、というサイト方針を守ること。\n"
        f"いま記事が不足しているカテゴリ: {', '.join(thin_cats)}。この中から選ぶこと。\n"
        f"いま記事が不足している成長ステージ: {', '.join(thin_stages)}。可能ならこの時期の話題にすること。\n"
        "既存記事と重複しないこと。既存slug: " + ", ".join(sorted({e.get("slug", "") for e in bank})) + "\n\n"
        "次のJSONだけを返す（前置き不要）:\n"
        '{"slug": "半角英数とハイフンのみ・8〜40字・内容を表す", '
        '"title_seed": "記事タイトルの種になる日本語20〜36字", '
        '"angle": "切り口を日本語で40〜80字。/ 区切りで2〜3点", '
        f'"category": "次から1つ: {", ".join(thin_cats)}", '
        f'"stage": "次から1つ: {", ".join(STAGES)}"}}'
    )
    try:
        d = generate_json(prompt, temperature=0.9)
    except Exception as e:  # noqa: BLE001
        raise NoTopic(f"topic-bank が空、LLM 起案も失敗: {e}") from e

    cat = d.get("category") if d.get("category") in CATEGORIES else (thin_cats[0] if thin_cats else "kokoro")
    base = re.sub(r"[^a-z0-9-]+", "-", str(d.get("slug", "")).lower()).strip("-") or f"auto-{wanted}"
    entry = {
        "slug": _unique_slug(base[:40], bank),
        "type": wanted,
        "title_seed": (d.get("title_seed") or "").strip() or f"{wanted} の記事",
        "angle": (d.get("angle") or "").strip(),
        "category": cat,
        "official_sources": list(_DEFAULT_SOURCES.get(cat, ["https://www.cfa.go.jp/"])),
        "ref_urls": [],
        "status": "queued",
        "generated": True,
    }
    if d.get("stage") in STAGES:
        entry["stage"] = d["stage"]
    bank.append(entry)
    dump_yaml(DATA / "topic-bank.yml", bank)
    log(f"topic: bank が空 → LLM がネタを起案し追記 slug={entry['slug']!r} category={cat}")
    return entry


def pick(force_type: str | None = None) -> dict:
    """data/topic-bank.yml から今日書くトピックを1つ選ぶ。

    ローテーション（trend→basics→service→voice→cheer）で希望タイプを決め、
    そのタイプの未使用トピックを優先。無ければ他タイプから補充。
    バンクが尽きたら LLM に新ネタを起案させて追記する。
    """
    bank = load_yaml(DATA / "topic-bank.yml") or []
    state = load_json(DATA / "state.json", {})
    idx = int(state.get("rotation_index", 0))
    wanted = force_type or ROTATION[idx % len(ROTATION)]

    open_entries = [e for e in bank if e.get("status", "queued") in ("queued", "candidate")]
    if not open_entries:
        return _llm_topic(wanted, bank)

    preferred = [e for e in open_entries if e.get("type") == wanted]
    pool = preferred or open_entries

    # 不足しているカテゴリ／ステージを優先（同点はバンクの並び順＝古い順）
    cc, sc = _published_counts()
    scored = sorted(
        enumerate(pool), key=lambda t: (-_need_score(t[1], cc, sc), t[0])
    )
    chosen = scored[0][1]
    chosen.setdefault("type", wanted)

    note = "" if preferred else "  ← 希望タイプが空につき他タイプから補充"
    log(
        f"topic: rotation={idx} 希望={wanted} → 採用 type={chosen['type']} "
        f"cat={chosen.get('category')} stage={chosen.get('stage','-')} "
        f"slug={chosen.get('slug')!r} 不足度={_need_score(chosen, cc, sc):.1f}{note}"
    )
    return chosen
