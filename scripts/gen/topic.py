from __future__ import annotations

from .util import DATA, ROTATION, load_json, load_yaml, log


class NoTopic(Exception):
    pass


def pick(force_type: str | None = None) -> dict:
    """data/topic-bank.yml から今日書くトピックを1つ選ぶ。

    ローテーション（trend→basics→service→voice→cheer）で希望タイプを決め、
    そのタイプの未使用トピックを優先。無ければ他タイプから補充。
    """
    bank = load_yaml(DATA / "topic-bank.yml") or []
    state = load_json(DATA / "state.json", {})
    idx = int(state.get("rotation_index", 0))
    wanted = force_type or ROTATION[idx % len(ROTATION)]

    open_entries = [e for e in bank if e.get("status", "queued") in ("queued", "candidate")]
    if not open_entries:
        raise NoTopic("topic-bank に未使用（queued / candidate）のトピックがありません")

    preferred = [e for e in open_entries if e.get("type") == wanted]
    chosen = (preferred or open_entries)[0]
    chosen.setdefault("type", wanted)

    note = "" if chosen in preferred else "  ← 希望タイプが空につき他タイプから補充"
    log(
        f"topic: rotation={idx} 希望={wanted} → 採用 type={chosen['type']} "
        f"slug={chosen.get('slug')!r} seed={chosen.get('title_seed')!r}{note}"
    )
    return chosen
