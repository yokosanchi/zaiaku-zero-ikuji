#!/usr/bin/env python3
"""`sachiko_analyzer.py` がフラグを立てた記事に対して、Gemini でタイトル/メタディスクリプションの
改善案と、追記セクション（H2見出し+本文）を生成する。自動改善PDCAの「Act」にあたる。

既定は **提案のみ**（記事ファイルは一切書き換えない）。実際に反映するには `--apply` が必要。

    python scripts/auto_refine.py                    # 提案を生成して data/seo/proposals/ に保存するだけ
    python scripts/auto_refine.py --apply             # さらに元記事ファイルに反映する（ガードレール通過時のみ）
    python scripts/auto_refine.py --limit 5

■ 安全策（既存の gen/improve.py と同じ方針を踏襲）
    - `category: sango`（産後うつ・YMYL最重要）の記事は最初から対象外（analyzer側で既にフラグを立てていないが、念のためここでも二重チェック）
    - 生成結果は必ず `gen/guardrails.py` の禁止語・YMYLチェックを通す。引っかかったら --apply でも反映しない
    - 追記セクションは本文の分量に対して極端に長すぎないか（+80%まで）をチェック
    - すべての判断（採用/却下とその理由）は data/seo/proposals/<date>/<slug>.json に記録される。
      黙って消える提案は無い

依存: pip install -r scripts/requirements-seo.txt （sachiko_analyzer.pyと共通）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from gen.guardrails import check_banned, check_ymyl  # noqa: E402
from gen.improve import _set_updated_date  # noqa: E402
from gen.llm import generate, is_mock  # noqa: E402
from gen.util import BLOG, DATA, append_log, log, today  # noqa: E402

SEO_DIR = DATA / "seo"

_PROMPT = """\
あなたは「罪悪感ゼロ育児」というサイトの編集者です。以下の記事について、検索での見つかりやすさ・
クリックされやすさを改善する提案を作ってください。

# サイトのトーン（必ず守る）
- 読者を絶対に責めない。「〜すべき」「〜してください」「〜しなきゃダメ」「がんばりましょう」は禁止語
- 医療・安全断定はしない（「絶対大丈夫」「必ず治る」など不可）
- 数字やデータは記事内に実在する根拠しか使わない。新しい統計・数字をでっち上げない
- 読者への共感から入り、罪悪感を外す考え方を示す、という記事全体の構成を尊重する

# 現在の記事情報
- 現在のタイトル: {title}
- 現在のメタディスクリプション: {description}
- カテゴリ: {category}
- 判定フラグ: {flags}
- 既存の見出し(H2)一覧: {headings}

# この記事が獲得している検索クエリ（表示回数の多い順）
{queries_table}

# やってほしいこと
1. タイトル改善案: 上記の検索クエリの検索意図により合致するよう、現在のタイトルを改善する。
   煽り・誇張はしない。サイトのトーンを保つ。変える必要がなければ現在のタイトルをそのまま返してよい。
2. メタディスクリプション改善案: 120〜160字程度。検索結果でクリックしたくなる、かつ内容を正確に表す説明文。
3. {section_instruction}

以下のJSON形式だけを出力してください（前置き・説明は書かない）:
{{"title": "...", "description": "...", "additional_section_markdown": "..." または null}}
"""


def _load_article(slug: str) -> tuple[pathlib.Path, str, str, str, str] | None:
    for ext in (".md", ".mdx"):
        p = BLOG / f"{slug}{ext}"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            head, fm, body = text.split("---", 2)
            return p, text, fm, body, ext
    return None


def _fm_value(fm: str, key: str) -> str:
    m = re.search(rf'^{key}:\s*"?(.+?)"?\s*$', fm, re.M)
    return m.group(1) if m else ""


def _headings(body: str) -> list[str]:
    return re.findall(r"^##\s+(.+)$", body, re.M)


def _latest_flagged_file() -> pathlib.Path | None:
    files = sorted(SEO_DIR.glob("flagged_*.json"))
    return files[-1] if files else None


def _build_prompt(article: dict, title: str, description: str, category: str, headings: list[str]) -> str:
    flags = article["flags"]
    queries_table = "\n".join(
        f"  - 「{q['query']}」 表示{q['impressions']} / クリック{q['clicks']} / "
        f"CTR{q['ctr']*100:.1f}% / 順位{q['position']:.1f}"
        for q in article.get("top_queries", [])
    ) or "  （データなし）"

    if "B_near_top10" in flags:
        section_instruction = (
            "追記セクション: 上記クエリが示す「まだ本文でカバーしきれていない疑問・悩み」を1つ選び、"
            "## 見出し + 本文（400〜700字程度）の新しいセクションを作る。"
            "既存の見出しと内容が重複しないこと（重複するなら null を返す）。"
            "サイトのトーンと事実に忠実な内容にする。本文はMarkdownで、見出しは`##`から始める"
        )
    else:
        section_instruction = "追記セクション: 今回は不要。additional_section_markdown は null を返す"

    return _PROMPT.format(
        title=title,
        description=description,
        category=category,
        flags=", ".join(flags),
        headings="、".join(headings) if headings else "（なし）",
        queries_table=queries_table,
        section_instruction=section_instruction,
    )


def _parse_llm_json(raw: str) -> dict | None:
    out = raw.strip()
    if out.startswith("```"):
        out = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", out).strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", out, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def refine_one(article: dict, *, apply: bool) -> dict:
    slug = article["slug"]
    loaded = _load_article(slug)
    if not loaded:
        return {"slug": slug, "verdict": "skipped", "reason": "記事ファイルが見つからない"}
    path, text, fm, body, ext = loaded

    category = _fm_value(fm, "category")
    if category == "sango":
        return {"slug": slug, "verdict": "skipped", "reason": "sango(YMYL)は対象外"}

    title = _fm_value(fm, "title")
    description = _fm_value(fm, "description")
    headings = _headings(body)

    if is_mock():
        return {"slug": slug, "verdict": "skipped", "reason": "PIPELINE_MOCK中はLLM呼び出しをしない"}

    prompt = _build_prompt(article, title, description, category, headings)
    try:
        raw = generate(prompt, json_mode=True, temperature=0.5)
    except Exception as e:  # noqa: BLE001
        return {"slug": slug, "verdict": "error", "reason": f"LLM呼び出し失敗: {e}"}

    parsed = _parse_llm_json(raw)
    if not parsed or "title" not in parsed or "description" not in parsed:
        return {"slug": slug, "verdict": "rejected", "reason": "LLM応答のJSON解析に失敗", "raw": raw[:500]}

    new_title = str(parsed.get("title") or title).strip()
    new_description = str(parsed.get("description") or description).strip()
    new_section = parsed.get("additional_section_markdown")
    new_section = str(new_section).strip() if new_section else ""

    check_text = new_title + "\n" + new_description + "\n" + new_section
    if check_banned(check_text) or check_ymyl(check_text):
        return {
            "slug": slug, "verdict": "rejected", "reason": "ガードレール抵触",
            "proposed": {"title": new_title, "description": new_description, "section": new_section},
        }
    if new_section and len(new_section) > len(body) * 0.8:
        return {
            "slug": slug, "verdict": "rejected", "reason": "追記セクションが長すぎる",
            "proposed": {"title": new_title, "description": new_description, "section": new_section},
        }

    result = {
        "slug": slug,
        "verdict": "accepted",
        "baseline": {k: article[k] for k in ("clicks", "impressions", "ctr", "position")},
        "flags": article["flags"],
        "before": {"title": title, "description": description},
        "after": {"title": new_title, "description": new_description},
        "additional_section": new_section or None,
        "applied": False,
    }

    if apply:
        new_fm = fm
        if new_title and new_title != title:
            new_fm = re.sub(r'^title:.*$', f'title: "{new_title}"', new_fm, count=1, flags=re.M)
        if new_description and new_description != description:
            new_fm = re.sub(r'^description:.*$', f'description: "{new_description}"', new_fm, count=1, flags=re.M)
        new_fm = _set_updated_date(new_fm)

        new_body = body
        if new_section:
            if re.search(r"^## まとめ", new_body, re.M):
                new_body = re.sub(r"(^## まとめ)", new_section.rstrip() + "\n\n" + r"\1", new_body, count=1, flags=re.M)
            else:
                new_body = new_body.rstrip() + "\n\n" + new_section.rstrip() + "\n"

        path.write_text(text.split("---", 2)[0] + "---" + new_fm + "---" + new_body, encoding="utf-8")
        result["applied"] = True
        append_log(f"🔎 SEO改善 `{slug}` — タイトル/説明文を更新"
                    + ("・セクション追記" if new_section else ""))

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flagged-file", help="対象のflagged_*.jsonのパス（省略時は最新のものを自動で使う）")
    ap.add_argument("--limit", type=int, default=3, help="1回の実行で処理する記事数の上限（既定3）")
    ap.add_argument("--apply", action="store_true", help="実際に記事ファイルへ反映する（既定は提案のみ）")
    args = ap.parse_args()

    flagged_path = pathlib.Path(args.flagged_file) if args.flagged_file else _latest_flagged_file()
    if not flagged_path or not flagged_path.exists():
        raise SystemExit("flagged_*.json が見つかりません。先に sachiko_analyzer.py を実行してください。")

    flagged = json.loads(flagged_path.read_text(encoding="utf-8"))
    print(f"入力: {flagged_path}（{len(flagged)}件中、上限{args.limit}件を処理）")
    if not args.apply:
        print("※ --apply が無いので、記事ファイルへの反映はしません（提案の生成のみ）")

    results = []
    for article in flagged[: args.limit]:
        log(f"  {article['slug']} を処理中…")
        r = refine_one(article, apply=args.apply)
        results.append(r)
        print(f"  - {article['slug']}: {r['verdict']}" + (f"（{r['reason']}）" if r.get("reason") else ""))

    out_dir = SEO_DIR / "proposals" / today()
    out_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        (out_dir / f"{r['slug']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.apply:
        log_path = SEO_DIR / "refined_log.json"
        history = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
        history.extend(
            {"date": today(), **r} for r in results if r.get("applied")
        )
        log_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n提案を保存: {out_dir}/")


if __name__ == "__main__":
    main()
