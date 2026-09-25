#!/usr/bin/env python3
"""Google Analytics 4（GA4）のアクセスデータを取得し、集計するツール。

Search Console（検索での実績）だけでは分からない「実際にサイトに来た人がどう動いたか」
（流入元・記事ごとの閲覧数・エンゲージメント）を見るためのもの。同じサービスアカウント・
同じ認証情報ファイル（scripts/.gsc/credentials.json）を gsc_report.py と共用する。

    python scripts/ga4_report.py --property-id 123456789
    python scripts/ga4_report.py --property-id 123456789 --days 60

やること（4つ）:
    1. 全体サマリー（セッション数・表示回数・エンゲージメント率・平均セッション時間）
    2. ページ別の閲覧数 上位（どの記事が実際に読まれているか）
    3. 流入元（session source / medium）別のセッション数
       （Threads経由は utm_source=threads を付けているので "threads / social" で確認できる）
    4. キャンペーン別（utm_campaign）のセッション数

■ 事前準備（GCP・GA4側）― 詳しくは scripts/SEO_README.md
    1. Google Cloud Console → 同じプロジェクトで「Google Analytics Data API」を有効化
    2. GA4 管理画面 → プロパティ → 「プロパティのアクセス管理」→
       gsc_report.py で使ったサービスアカウントのメールアドレス
       （...@...iam.gserviceaccount.com）を「閲覧者」として追加
    3. GA4のプロパティID（測定ID "G-XXXXXXXXXX" とは別の、数字だけのID。
       管理 → プロパティの詳細 に表示される）を --property-id で指定するか、
       DEFAULT_PROPERTY_ID に設定しておく

依存: pip install -r scripts/requirements-seo.txt
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import gsc_report  # noqa: E402  同じ認証情報(_get_credentials)を使い回す

# GA4のプロパティID（数字だけ、測定ID "G-XXXXXXXXXX" とは別物）。--property-id で上書き可。
# 罪悪感ゼロ育児（zaiaku-zero-ikuji.pages.dev）のプロパティ。
DEFAULT_PROPERTY_ID = "555905063"


def _build_client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient

    creds = gsc_report._get_credentials()  # noqa: SLF001
    return BetaAnalyticsDataClient(credentials=creds)


def _run_report(client, property_id: str, *, dimensions: list[str], metrics: list[str],
                 start_date: str, end_date: str, limit: int = 20, order_by_metric: str | None = None):
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    order_bys = []
    if order_by_metric:
        order_bys = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)
        ]

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=order_bys,
        limit=limit,
    )
    return client.run_report(request)


def fetch_summary(client, property_id: str, start_date: str, end_date: str) -> dict:
    resp = _run_report(
        client, property_id,
        dimensions=[],
        metrics=["sessions", "screenPageViews", "engagementRate", "averageSessionDuration"],
        start_date=start_date, end_date=end_date, limit=1,
    )
    if not resp.rows:
        return {"sessions": 0, "pageviews": 0, "engagement_rate": 0.0, "avg_duration": 0.0}
    v = resp.rows[0].metric_values
    return {
        "sessions": int(v[0].value or 0),
        "pageviews": int(v[1].value or 0),
        "engagement_rate": float(v[2].value or 0),
        "avg_duration": float(v[3].value or 0),
    }


def fetch_top_pages(client, property_id: str, start_date: str, end_date: str, limit: int = 15):
    resp = _run_report(
        client, property_id,
        dimensions=["pagePath"],
        metrics=["screenPageViews", "engagedSessions", "userEngagementDuration"],
        start_date=start_date, end_date=end_date, limit=limit,
        order_by_metric="screenPageViews",
    )
    rows = []
    for r in resp.rows:
        path = r.dimension_values[0].value
        pv = int(r.metric_values[0].value or 0)
        engaged = int(r.metric_values[1].value or 0)
        dur = float(r.metric_values[2].value or 0)
        rows.append({
            "path": path,
            "pageviews": pv,
            "engaged_sessions": engaged,
            "avg_engagement_sec": round(dur / pv, 1) if pv else 0.0,
        })
    return rows


def fetch_traffic_sources(client, property_id: str, start_date: str, end_date: str, limit: int = 15):
    resp = _run_report(
        client, property_id,
        dimensions=["sessionSource", "sessionMedium"],
        metrics=["sessions"],
        start_date=start_date, end_date=end_date, limit=limit,
        order_by_metric="sessions",
    )
    return [
        {
            "source": r.dimension_values[0].value,
            "medium": r.dimension_values[1].value,
            "sessions": int(r.metric_values[0].value or 0),
        }
        for r in resp.rows
    ]


def fetch_campaigns(client, property_id: str, start_date: str, end_date: str, limit: int = 15):
    resp = _run_report(
        client, property_id,
        dimensions=["sessionCampaignName"],
        metrics=["sessions"],
        start_date=start_date, end_date=end_date, limit=limit,
        order_by_metric="sessions",
    )
    return [
        {"campaign": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value or 0)}
        for r in resp.rows
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--property-id", default=DEFAULT_PROPERTY_ID, help="GA4のプロパティID（数字のみ）")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--top-n", type=int, default=15)
    args = ap.parse_args()

    if not args.property_id:
        raise SystemExit(
            "GA4のプロパティIDが必要です。--property-id で指定するか、"
            "ga4_report.py の DEFAULT_PROPERTY_ID に設定してください。"
        )

    end = dt.date.today()
    start = end - dt.timedelta(days=args.days)
    start_date, end_date = start.isoformat(), end.isoformat()

    print(f"対象プロパティ: {args.property_id}")
    print(f"期間: {start_date} 〜 {end_date}")
    print()

    client = _build_client()

    summary = fetch_summary(client, args.property_id, start_date, end_date)
    print("=" * 60)
    print("■ 全体サマリー")
    print("=" * 60)
    print(f"  セッション数　　　: {summary['sessions']:,}")
    print(f"  ページビュー数　　: {summary['pageviews']:,}")
    print(f"  エンゲージメント率: {summary['engagement_rate']*100:.1f}%")
    print(f"  平均セッション時間: {summary['avg_duration']:.0f}秒")
    print()

    pages = fetch_top_pages(client, args.property_id, start_date, end_date, args.top_n)
    print("=" * 60)
    print(f"■ ページ別 閲覧数 上位{args.top_n}")
    print("=" * 60)
    if not pages:
        print("  （データなし）")
    for i, p in enumerate(pages, 1):
        print(f"  {i:2d}. {p['path']:<50s} 表示{p['pageviews']:>5d} / "
              f"エンゲージ{p['engaged_sessions']:>4d} / 平均{p['avg_engagement_sec']:.0f}秒")
    print()

    sources = fetch_traffic_sources(client, args.property_id, start_date, end_date, args.top_n)
    print("=" * 60)
    print("■ 流入元（source / medium）別セッション数")
    print("=" * 60)
    if not sources:
        print("  （データなし）")
    for s in sources:
        print(f"  {s['source']:<30s} / {s['medium']:<15s} : {s['sessions']:>5d}")
    print()

    campaigns = fetch_campaigns(client, args.property_id, start_date, end_date, args.top_n)
    print("=" * 60)
    print("■ キャンペーン（utm_campaign）別セッション数")
    print("  ※ Threads自動投稿は utm_campaign=auto_post を付けています")
    print("=" * 60)
    if not campaigns:
        print("  （データなし）")
    for c in campaigns:
        print(f"  {c['campaign']:<30s} : {c['sessions']:>5d}")


if __name__ == "__main__":
    main()
