#!/usr/bin/env python3
"""罪悪感ゼロ育児 — 毎日1記事の自動生成パイプライン（多段 / LLM一発出しではない）。

    pick_topic → research → draft → concept_rewrite → thumbnail → publish → improve

使い方:
    python scripts/pipeline.py --daily            # 本番（GitHub Actions もこれ）
    python scripts/pipeline.py --daily --dry-run  # 生成して表示するだけ（保存しない）
    python scripts/pipeline.py --daily --type cheer
    PIPELINE_MOCK=1 python scripts/pipeline.py --daily   # APIキー無しで配線確認
    python scripts/pipeline.py --improve-only     # 既存記事の点検だけ

環境変数:
    GEMINI_API_KEY   必須（未設定なら自動で MOCK モード）
    GEMINI_MODEL     既定 gemini-2.5-flash
    IMPROVE_MODE     links(既定) | full
    THUMB_HEADLINE   ai を指定するとサムネ惹句を LLM で作る
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen import draft as draft_mod  # noqa: E402
from gen import improve as improve_mod  # noqa: E402
from gen import publish as publish_mod  # noqa: E402
from gen import research as research_mod  # noqa: E402
from gen import rewrite as rewrite_mod  # noqa: E402
from gen import thumbnail as thumb_mod  # noqa: E402
from gen import topic as topic_mod  # noqa: E402
from gen.llm import model_label  # noqa: E402
from gen.util import CATEGORY_ACCENT, DATA, TYPE_LABEL, log, save_json, today, write_review  # noqa: E402


def _dedupe_sources(facts: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in facts:
        url = f.get("source_url")
        if url and url not in seen:
            seen.add(url)
            out.append({"label": f.get("source_label") or url, "url": url})
    return out[:4]


def run_daily(args) -> dict:
    try:
        tp = topic_mod.pick(force_type=args.type)
    except topic_mod.NoTopic as e:
        log(str(e))
        return {"result": "no_topic", "detail": str(e)}

    research = research_mod.gather(tp)
    d = draft_mod.make(tp, research)

    try:
        art = rewrite_mod.concept_rewrite(d, tp)
    except rewrite_mod.YMYLBlocked as e:
        log(f"YMYL ブロック: {e.labels} → 公開せず REVIEW.md へ")
        write_review(
            tp.get("slug", d.get("title", "draft")),
            [f"YMYL 疑い: {x}" for x in e.labels],
            body=d.get("body_md", ""),
        )
        return {"result": "needs_review", "labels": e.labels}

    art["category"] = d["category"]
    art["articleType"] = d["articleType"]
    art.setdefault("tags", d.get("tags", []))
    art.setdefault("emoji", d.get("emoji", ""))
    art["sources"] = _dedupe_sources(research["facts"])

    if args.dry_run:
        preview = {k: art.get(k) for k in ("title", "description", "category", "articleType", "tags", "sources")}
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("\n----- BODY -----\n" + art["body_md"][:1600])
        return {"result": "dry_run", "title": art["title"]}

    th = d.get("thumb") or {}
    slug_guess = tp.get("slug") or f"{art['articleType']}-{today().replace('-', '')}"
    og = thumb_mod.render(
        slug_guess,
        th.get("headline") or art["title"],
        th.get("sub") or TYPE_LABEL.get(art["articleType"], ""),
        th.get("emoji") or art.get("emoji") or "💗",
        th.get("accent") or CATEGORY_ACCENT.get(art["category"], "coral"),
    )

    slug = publish_mod.publish(art, tp, og, model_label=model_label())

    improve = {}
    if not args.no_improve:
        improve = improve_mod.daily_improve(mode=os.environ.get("IMPROVE_MODE", "links"))

    return {"result": "published", "slug": slug, "type": art["articleType"], "improve": improve}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--daily", action="store_true", help="今日の1記事を生成して公開")
    ap.add_argument("--type", choices=["trend", "basics", "service", "voice", "cheer"], help="タイプを指定（ローテーション無視）")
    ap.add_argument("--dry-run", action="store_true", help="生成物を表示するだけで保存しない")
    ap.add_argument("--improve-only", action="store_true", help="既存記事の点検・改善だけ実行")
    ap.add_argument("--no-improve", action="store_true", help="改善パスをスキップ")
    args = ap.parse_args()

    try:
        if args.improve_only:
            out = {"result": "improve", "improve": improve_mod.daily_improve(mode=os.environ.get("IMPROVE_MODE", "links"))}
        else:
            out = run_daily(args)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        out = {"result": "error", "error": str(e)}

    save_json(DATA / "last_result.json", {**out, "model": model_label(), "at": today()})
    print("PIPELINE_RESULT=" + json.dumps(out, ensure_ascii=False))
    sys.exit(1 if out.get("result") == "error" else 0)


if __name__ == "__main__":
    main()
