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
import pathlib
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """リポジトリ直下の .env を読み込む（既存の環境変数は上書きしない）。ローカル cron 用。"""
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

from gen import draft as draft_mod  # noqa: E402
from gen import improve as improve_mod  # noqa: E402
from gen import publish as publish_mod  # noqa: E402
from gen import research as research_mod  # noqa: E402
from gen import rewrite as rewrite_mod  # noqa: E402
from gen import thumbnail as thumb_mod  # noqa: E402
from gen import topic as topic_mod  # noqa: E402
from gen.llm import is_mock, model_label  # noqa: E402
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
    art["stage"] = d["stage"]
    art["articleType"] = d["articleType"]
    art.setdefault("tags", d.get("tags", []))
    art.setdefault("emoji", d.get("emoji", ""))
    art["sources"] = _dedupe_sources(research["facts"])

    if args.dry_run:
        preview = {k: art.get(k) for k in ("title", "description", "category", "stage", "articleType", "tags", "photo_query", "sources")}
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("\n----- BODY -----\n" + art["body_md"][:1600])
        return {"result": "dry_run", "title": art["title"]}

    th = d.get("thumb") or {}
    slug_guess = tp.get("slug") or f"{art['articleType']}-{today().replace('-', '')}"
    img = thumb_mod.render(
        slug_guess,
        th.get("headline") or art["title"],
        th.get("sub") or TYPE_LABEL.get(art["articleType"], ""),
        th.get("emoji") or art.get("emoji") or "💗",
        th.get("accent") or CATEGORY_ACCENT.get(art["category"], "coral"),
        photo_query=d.get("photo_query") or tp.get("photo_query"),
    )
    art["heroImage"] = img.get("heroImage")
    art["ogImage"] = img["ogImage"]

    slug = publish_mod.publish(art, tp, img["ogImage"], model_label=model_label())

    tweet_id = None
    if not args.no_x and not is_mock():
        from gen import post_x as x_mod

        tweet_id = x_mod.post_tweet(x_mod.compose_tweet(art, slug))

    improve = {}
    if not args.no_improve:
        improve = improve_mod.daily_improve(mode=os.environ.get("IMPROVE_MODE", "links"))

    return {
        "result": "published",
        "slug": slug,
        "type": art["articleType"],
        "tweet_id": tweet_id,
        "improve": improve,
    }


def preflight() -> dict:
    """公開はせず、動かせる状態か点検する。"""
    import importlib

    from gen.topic import pick as _pick

    checks: list[tuple[str, bool, str]] = []

    key = bool(os.environ.get("GEMINI_API_KEY"))
    checks.append(("GEMINI_API_KEY", key, "未設定：.env か環境変数に入れると本番モードになる"))

    for mod in ("yaml", "trafilatura", "cairosvg"):
        try:
            importlib.import_module(mod)
            ok = True
        except Exception:  # noqa: BLE001
            ok = False
        required = mod == "yaml"
        note = "" if ok else "pip install -r scripts/requirements.txt"
        checks.append((f"import {mod}" + ("（任意）" if not required else ""), ok or not required, note))

    try:
        tp = _pick()
        checks.append(("topic-bank に未使用トピック", True, f"次: {tp.get('slug')}"))
    except Exception as e:  # noqa: BLE001
        checks.append(("topic-bank に未使用トピック", False, str(e)))

    unsplash = bool(os.environ.get("UNSPLASH_ACCESS_KEY"))
    checks.append(("UNSPLASH_ACCESS_KEY（任意）", True, "設定すると写真アイキャッチ、無ければカード生成" if not unsplash else "OK"))

    x_keys = all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))
    checks.append(("X 投稿キー4種（任意）", True, "4つ揃うと新着記事を X へ自動投稿" if not x_keys else "OK"))

    all_ok = all(ok for _, ok, _ in checks)
    for name, ok, note in checks:
        mark = "OK " if ok and not note else ("-- " if ok else "NG ")
        log(f"  [{mark}] {name}" + (f"  — {note}" if note else ""))
    log(f"preflight: {'READY（本番モードで回せます）' if all_ok else '要確認あり'}")
    return {"result": "check", "ready": all_ok, "checks": [[n, o, m] for n, o, m in checks]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--daily", action="store_true", help="今日の1記事を生成して公開")
    ap.add_argument("--type", choices=["trend", "basics", "service", "voice", "cheer"], help="タイプを指定（ローテーション無視）")
    ap.add_argument("--dry-run", action="store_true", help="生成物を表示するだけで保存しない")
    ap.add_argument("--improve-only", action="store_true", help="既存記事の点検・改善だけ実行")
    ap.add_argument("--no-improve", action="store_true", help="改善パスをスキップ")
    ap.add_argument("--no-x", action="store_true", help="X（Twitter）への自動投稿をスキップ")
    ap.add_argument("--check", action="store_true", help="公開せず、動かせる状態か点検する")
    ap.add_argument("--allow-mock", action="store_true", help="APIキー無し(MOCK)でも --daily で保存する（テスト用）")
    args = ap.parse_args()

    # キーが無いのに --daily で本番実行 → MOCK 記事を量産しないよう止める
    if args.daily and not args.dry_run and not args.allow_mock:
        from gen.llm import is_mock

        if is_mock() and os.environ.get("PIPELINE_MOCK") != "1":
            log("GEMINI_API_KEY が無いため、記事は生成しません（--allow-mock でテスト実行は可能）。")
            save_json(DATA / "last_result.json", {"result": "no_key", "at": today()})
            print('PIPELINE_RESULT={"result": "no_key"}')
            sys.exit(0)

    try:
        if args.check:
            out = preflight()
        elif args.improve_only:
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
