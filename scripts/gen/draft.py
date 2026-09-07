from __future__ import annotations

from .guardrails import check_banned
from .llm import generate_json
from .util import CATEGORIES, log, read_prompt


def make(topic: dict, research: dict) -> dict:
    """1st pass: 事実メモ＋競合の構成シグナルをもとに、下書きを作る。

    競合の見出しは「読者が何を期待しているか」の把握だけに使う。
    文章は公式ソースを根拠にした完全オリジナル。
    """
    t = topic["type"]
    tmpl = read_prompt(f"draft_{t}")
    concept = read_prompt("_concept")

    facts_block = "\n".join(
        f"- {f.get('claim', '').strip()}  〔出典: {f.get('source_label', '')} {f.get('source_url', '')}〕"
        for f in research["facts"]
    ) or "（公式ソースが取得できなかった。断定を避け、一般論・気持ちに寄せて書く。医療的判断は書かない）"

    signals_block = "\n".join(f"- {s}" for s in research["outline_signals"][:30]) or "（なし）"

    prompt = (
        tmpl.replace("{{CONCEPT}}", concept)
        .replace("{{TITLE_SEED}}", topic.get("title_seed", ""))
        .replace("{{ANGLE}}", topic.get("angle", ""))
        .replace("{{CATEGORY_HINT}}", topic.get("category", "") or "（本文内容から適切に選ぶ）")
        .replace("{{FACTS}}", facts_block)
        .replace("{{OUTLINE_SIGNALS}}", signals_block)
        .replace("{{CATEGORIES}}", ", ".join(CATEGORIES))
    )

    d = generate_json(prompt, temperature=0.85)

    cat = d.get("category") or topic.get("category") or "kokoro"
    d["category"] = cat if cat in CATEGORIES else (topic.get("category") if topic.get("category") in CATEGORIES else "kokoro")
    d["articleType"] = t
    d["tags"] = (d.get("tags") or [])[:5]

    log(f"  draft: title={d.get('title')!r} category={d['category']} 禁止語={check_banned(d.get('body_md', ''))}")
    return d
