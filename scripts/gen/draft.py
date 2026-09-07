from __future__ import annotations

from .guardrails import check_banned
from .llm import generate_json
from .util import CATEGORIES, STAGES, log, read_prompt

_EXTRA_NOTE = (
    "\n\n## 追加で JSON に含めるもの（必須）\n"
    "- \"stage\": 対象の成長ステージを1つ。選択肢 " + ", ".join(STAGES) + "\n"
    "  （ninshin=妊娠・出産, age0=0歳, age1_2=1〜2歳, age3_pre=3歳〜未就学, gakudo=小学生〜）。ヒント: {stage_hint}\n"
    "- \"photo_query\": 記事に合うアイキャッチ写真を探すための英語の検索語（3〜6語）。\n"
    "  温かい日常のライフスタイル写真になる語を。人物の表情が過度に悲観的にならない語で。\n"
    "  例: \"parent and toddler eating breakfast at home\", \"tired mother holding newborn softly lit\"\n"
)


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
    ) + _EXTRA_NOTE.format(stage_hint=topic.get("stage") or "（本文内容から判断）")

    d = generate_json(prompt, temperature=0.85)

    cat = d.get("category") or topic.get("category") or "kokoro"
    d["category"] = cat if cat in CATEGORIES else (topic.get("category") if topic.get("category") in CATEGORIES else "kokoro")

    stg = d.get("stage") or topic.get("stage") or "age0"
    d["stage"] = stg if stg in STAGES else (topic.get("stage") if topic.get("stage") in STAGES else "age0")

    d["articleType"] = t
    d["tags"] = (d.get("tags") or [])[:5]

    log(
        f"  draft: title={d.get('title')!r} category={d['category']} stage={d['stage']} "
        f"禁止語={check_banned(d.get('body_md', ''))}"
    )
    return d
