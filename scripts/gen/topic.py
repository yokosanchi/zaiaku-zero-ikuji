from __future__ import annotations

import re

from .util import BLOG, CATEGORIES, DATA, ROTATION, dump_yaml, load_json, load_yaml, log


class NoTopic(Exception):
    pass


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
    used = {e.get("slug") for e in bank} | {p.stem for p in BLOG.glob("*.md")}
    slug, n = base, 2
    while slug in used or (BLOG / f"{slug}.md").exists():
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

    prompt = (
        "あなたは育児メディア『罪悪感ゼロ育児』の編集者です。"
        "読者は睡眠不足で余裕のない新米の親で、SNSの比較でしんどくなっている層。"
        f"次の方針で、新しい記事ネタを1件だけ提案してください: {type_hint}。\n"
        "手抜きを責めない・公的情報に基づく・特定の子育て法を断定しない、というサイト方針を守ること。\n"
        "既存記事と重複しないこと。既存slug: " + ", ".join(sorted({e.get("slug", "") for e in bank})) + "\n\n"
        "次のJSONだけを返す（前置き不要）:\n"
        '{"slug": "半角英数とハイフンのみ・8〜40字・内容を表す", '
        '"title_seed": "記事タイトルの種になる日本語20〜36字", '
        '"angle": "切り口を日本語で40〜80字。/ 区切りで2〜3点", '
        f'"category": "次から1つ: {", ".join(CATEGORIES)}"}}'
    )
    try:
        d = generate_json(prompt, temperature=0.9)
    except Exception as e:  # noqa: BLE001
        raise NoTopic(f"topic-bank が空、LLM 起案も失敗: {e}") from e

    cat = d.get("category") if d.get("category") in CATEGORIES else "kokoro"
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
    chosen = (preferred or open_entries)[0]
    chosen.setdefault("type", wanted)

    note = "" if chosen in preferred else "  ← 希望タイプが空につき他タイプから補充"
    log(
        f"topic: rotation={idx} 希望={wanted} → 採用 type={chosen['type']} "
        f"slug={chosen.get('slug')!r} seed={chosen.get('title_seed')!r}{note}"
    )
    return chosen
