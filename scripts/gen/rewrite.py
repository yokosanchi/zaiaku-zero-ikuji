from __future__ import annotations

import re

from .guardrails import check_banned, check_ymyl
from .llm import generate, generate_json
from .util import log, read_prompt


class YMYLBlocked(Exception):
    def __init__(self, labels: list[str]):
        super().__init__("YMYL hazard: " + ", ".join(labels))
        self.labels = labels


def concept_rewrite(draft: dict, topic: dict) -> dict:
    """2nd pass: サイトの声に「コンセプトリライト」。

    - 徹底的な共感・肯定のトーンへ
    - 決まった構成（共感→ファクト→考え方→工夫→まとめ→肯定）へ整える
    - 禁止語を deterministic に除去
    - 医療・安全の危険断定があれば公開を止める（YMYLBlocked）
    """
    prompt = (
        read_prompt("concept_rewrite")
        .replace("{{CONCEPT}}", read_prompt("_concept"))
        .replace("{{TYPE}}", draft.get("articleType", ""))
        .replace("{{TITLE}}", draft.get("title", ""))
        .replace("{{DESCRIPTION}}", draft.get("description", ""))
        .replace("{{BODY}}", draft.get("body_md", ""))
    )
    out = generate_json(prompt, temperature=0.6)
    art = dict(draft)
    for k in ("title", "description", "body_md"):
        if out.get(k):
            art[k] = out[k].strip()

    # 1) 禁止語の除去（最大2回の言い換えパス）
    for _ in range(2):
        hits = check_banned(art["title"] + "\n" + art["body_md"])
        if not hits:
            break
        log(f"  rewrite: 禁止語 {hits} → 言い換え")
        art["body_md"] = generate(
            "次の記事本文から、禁止語「" + "」「".join(hits) + "」を、"
            "意味を変えずに一切使わない表現へ全て書き換えてください。"
            "マークダウンの見出し・箇条書き構造は保ち、本文だけを返してください。\n\n"
            + art["body_md"]
        ).strip()
    if check_banned(art["title"] + "\n" + art["body_md"]):
        raise RuntimeError("禁止語を除去できませんでした")

    # 2) YMYL ハードストップ
    flags = check_ymyl(art["title"] + "\n" + art.get("description", "") + "\n" + art["body_md"])
    if flags:
        raise YMYLBlocked(flags)

    # 3) レイアウトが自動で付ける締めブロックと重複したら削る
    art["body_md"] = _strip_dupe_closing(art["body_md"])
    return art


def _strip_dupe_closing(md: str) -> str:
    md = re.sub(r"\n#{1,4}\s*(最後に、?あなたへ|さいごに、?あなたへ)[\s\S]*$", "\n", md)
    return md.rstrip() + "\n"
