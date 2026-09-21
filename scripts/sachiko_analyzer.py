#!/usr/bin/env python3
"""Search Console データを記事(URL)単位で取得し、「改善ポテンシャルが高い記事」を判定する。

自動改善PDCAの「Plan / Check」にあたる部分。実際のリライト生成は `auto_refine.py` が担当する。

    python scripts/sachiko_analyzer.py                  # 直近30日分を取得・判定
    python scripts/sachiko_analyzer.py --days 60

判定ロジック（両方独立に判定。両方に該当することもある）:
    - フラグA（低CTR）    : 表示回数 >= --min-impressions-a（既定500） かつ CTR <= --max-ctr（既定2%）
                            → タイトル/メタディスクリプションの改善余地
    - フラグB（あと一歩）  : 平均掲載順位が --pos-low 〜 --pos-high（既定8〜20位）
                            → コンテンツ追記で上位表示が狙える可能性

`category: sango`（産後うつ、YMYL最重要）の記事は、自動リライトの対象外という
既存方針（gen/improve.py と同じ）に合わせて、ここでもフラグを立てない。

出力（すべて data/seo/ 以下、日付付き。Historyは追記型でPDCAの "Do" 用の記録に使う）:
    data/seo/pages_<end_date>.json     … 対象になった全記事の実績（フラグの有無に関わらず）
    data/seo/flagged_<end_date>.json   … フラグが立った記事の一覧（auto_refine.py の入力）
    data/seo/history.jsonl             … 1行=1記事1回分の実績（追記のみ。削除・上書きしない）

依存: pip install -r scripts/requirements-seo.txt
認証: scripts/SEO_README.md 参照（scripts/.gsc/credentials.json か client_secret.json）
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

import gsc_report  # noqa: E402
from gen.util import BLOG, DATA, today  # noqa: E402

SEO_DIR = DATA / "seo"


def _slug_from_page_url(url: str, site_url: str) -> str | None:
    """GSCが返すページURLから、/blog/<slug>/ に該当するものだけ slug を取り出す。
    それ以外（トップ・カテゴリ一覧等）は None を返して除外する。"""
    if not url.startswith(site_url.rstrip("/")):
        return None
    path = url[len(site_url.rstrip("/")):]
    m = re.match(r"^/blog/([a-zA-Z0-9\-_]+)/?$", path)
    return m.group(1) if m else None


def _local_category(slug: str) -> str | None:
    for ext in (".md", ".mdx"):
        p = BLOG / f"{slug}{ext}"
        if p.exists():
            fm = p.read_text(encoding="utf-8").split("---", 2)[1]
            m = re.search(r'^category:\s*"?([a-z]+)"?\s*$', fm, re.M)
            return m.group(1) if m else None
    return None


def fetch_page_rows(service, site_url: str, start_date: str, end_date: str, row_limit: int = 2000):
    rows = gsc_report._query(  # noqa: SLF001
        service, site_url, start_date=start_date, end_date=end_date,
        dimensions=["page"], row_limit=row_limit,
    )
    out = []
    for r in rows:
        url = r["keys"][0]
        slug = _slug_from_page_url(url, site_url)
        if not slug:
            continue
        out.append(
            {
                "slug": slug,
                "url": url,
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0),
                "position": r.get("position", 0.0),
            }
        )
    return out


def fetch_top_queries_for_page(service, site_url: str, start_date: str, end_date: str,
                                page_url: str, limit: int = 8) -> list[dict]:
    rows = gsc_report._query(  # noqa: SLF001
        service, site_url, start_date=start_date, end_date=end_date,
        dimensions=["query"], row_limit=limit,
        filters=[{"dimension": "page", "operator": "equals", "expression": page_url}],
    )
    return [
        {
            "query": r["keys"][0],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0.0),
            "position": r.get("position", 0.0),
        }
        for r in sorted(rows, key=lambda r: r.get("impressions", 0), reverse=True)
    ]


def judge(page: dict, *, min_impressions_a: int, max_ctr_a: float,
          pos_low: float, pos_high: float) -> list[str]:
    flags = []
    if page["impressions"] >= min_impressions_a and page["ctr"] <= max_ctr_a:
        flags.append("A_low_ctr")
    if pos_low <= page["position"] <= pos_high:
        flags.append("B_near_top10")
    return flags


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site-url", default=gsc_report.DEFAULT_SITE_URL)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--end-lag", type=int, default=3)
    ap.add_argument("--min-impressions-a", type=int, default=500)
    ap.add_argument("--max-ctr-a", type=float, default=0.02)
    ap.add_argument("--pos-low", type=float, default=8.0)
    ap.add_argument("--pos-high", type=float, default=20.0)
    ap.add_argument("--top-queries-per-page", type=int, default=8)
    args = ap.parse_args()

    end = dt.date.today() - dt.timedelta(days=args.end_lag)
    start = end - dt.timedelta(days=args.days)
    start_date, end_date = start.isoformat(), end.isoformat()

    print(f"対象サイト: {args.site_url}")
    print(f"期間: {start_date} 〜 {end_date}")

    service = gsc_report._build_service()  # noqa: SLF001
    pages = fetch_page_rows(service, args.site_url, start_date, end_date)
    print(f"記事URL {len(pages)} 件を取得")

    SEO_DIR.mkdir(parents=True, exist_ok=True)

    flagged = []
    history_lines = []
    for page in pages:
        category = _local_category(page["slug"])
        page["category"] = category
        flags = [] if category == "sango" else judge(
            page, min_impressions_a=args.min_impressions_a, max_ctr_a=args.max_ctr_a,
            pos_low=args.pos_low, pos_high=args.pos_high,
        )
        page["flags"] = flags
        history_lines.append(
            json.dumps({"date": end_date, **page}, ensure_ascii=False)
        )
        if flags:
            queries = fetch_top_queries_for_page(
                service, args.site_url, start_date, end_date, page["url"],
                limit=args.top_queries_per_page,
            )
            flagged.append({**page, "top_queries": queries})

    (SEO_DIR / f"pages_{end_date}.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (SEO_DIR / f"flagged_{end_date}.json").write_text(
        json.dumps(flagged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (SEO_DIR / "history.jsonl").open("a", encoding="utf-8") as f:
        for line in history_lines:
            f.write(line + "\n")

    print(f"フラグが立った記事: {len(flagged)} 件")
    for p in flagged:
        print(f"  - {p['slug']:<40s} {p['flags']} (表示{p['impressions']} / CTR {p['ctr']*100:.2f}% / 順位{p['position']:.1f})")
    print(f"\n保存: {SEO_DIR}/pages_{end_date}.json, flagged_{end_date}.json, history.jsonl（追記）")


if __name__ == "__main__":
    main()
