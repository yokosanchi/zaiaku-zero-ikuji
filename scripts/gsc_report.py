#!/usr/bin/env python3
"""Google Search Console（サチコ）の検索パフォーマンスデータを自動取得し、集計するツール。

    python scripts/gsc_report.py                       # 直近30日分（既定）
    python scripts/gsc_report.py --days 60              # 直近60日分
    python scripts/gsc_report.py --site-url "https://example.com/"
    python scripts/gsc_report.py --out-dir data/seo-reports  # CSVも保存する

やること（4つ）:
    1. 全体サマリー（合計クリック数・表示回数・CTR・平均掲載順位）
    2. クリック数が多い上位クエリ
    3. 「表示回数は多いのにCTRが低い」改善候補クエリ
    4. 指名検索（サイト名・ブランド名を含むクエリ）の日別推移

■ 重要な限界（誤解しないでほしいこと）
    Search Console API が返すのは「Google検索経由の実績」だけです。Threadsやその他SNSからの
    直接流入・参照元は、この仕組みでは一切分かりません（Googleの管轄外のため）。
    「Threads発信による指名検索」という観点は、あくまで
    「ブランド名・サイト名で検索する人が増えたかどうか」という“間接的な兆候”を見ているだけで、
    それがThreads経由だと断定する術はこのAPIにはありません。
    Threadsからの実際の流入を直接見たい場合は、投稿リンクに付けてある
    `utm_source=threads` を、Cloudflare PagesプロジェクトのAnalyticsタブ（Referrer別）で
    確認してください（そちらは実際のアクセスログなので、こちらより直接的です）。

■ 事前準備（GCP側）― 詳しくは scripts/SEO_README.md
    1. https://console.cloud.google.com でプロジェクトを作成（または既存のものを選択）
    2. 「APIとサービス」→「ライブラリ」で "Search Console API" を有効化
    3-A. サービスアカウントを使う場合：
         IAMと管理 → サービスアカウント → 作成 → キーを作成(JSON) →
         ダウンロードしたファイルを scripts/.gsc/credentials.json として保存
         → Search Console の「設定」→「ユーザーとアクセス権限」で、
           サービスアカウントのメールアドレス（...@...iam.gserviceaccount.com）を
           「フル」または「制限付き」ユーザーとして追加（読み取りだけなら「制限付き」で十分）
    3-B. OAuth（自分のGoogleアカウントで毎回同意する方式）を使う場合：
         APIとサービス → 認証情報 → 認証情報を作成 → OAuthクライアントID →
         アプリケーションの種類「デスクトップアプリ」→ 作成 →
         ダウンロードしたファイルを scripts/.gsc/client_secret.json として保存
         （初回実行時にブラウザが開き、Googleアカウントでログイン・同意すると
           scripts/.gsc/token.json に認証情報がキャッシュされ、以後は自動で使われる）

    scripts/.gsc/ は .gitignore 済み。認証情報ファイルをコミットしないこと。

依存: pip install -r scripts/requirements-seo.txt
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CRED_DIR = pathlib.Path(__file__).resolve().parent / ".gsc"
_SERVICE_ACCOUNT_FILE = _CRED_DIR / "credentials.json"
_OAUTH_CLIENT_FILE = _CRED_DIR / "client_secret.json"
_OAUTH_TOKEN_FILE = _CRED_DIR / "token.json"

# Search ConsoleとGA4(Analytics Data API)を同じサービスアカウント・同じ認証情報ファイルで
# 使い回せるよう、両方のスコープをまとめて要求する（scripts/ga4_report.py もこれを import して使う）。
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

# 対象ドメイン（Search Console に登録した「プロパティ」の文字列と完全一致させること。
# URLプレフィックス型なら末尾スラッシュ込みの完全なURL）。--site-url で上書き可。
DEFAULT_SITE_URL = "https://zaiaku-zero-ikuji.pages.dev/"

# 「指名検索」とみなすキーワード（クエリにこの文字列が含まれていれば対象）。
# サイト名・略称などを足したければ --brand-keywords で上書き/追加できる。
DEFAULT_BRAND_KEYWORDS = ["罪悪感ゼロ育児"]


def _get_credentials():
    """scripts/.gsc/ にある認証ファイルから Credentials を組み立てる。
    サービスアカウント(credentials.json)を優先、無ければOAuth(client_secret.json)。"""
    if _SERVICE_ACCOUNT_FILE.exists():
        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_file(
            str(_SERVICE_ACCOUNT_FILE), scopes=SCOPES
        )

    if _OAUTH_CLIENT_FILE.exists():
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if _OAUTH_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(_OAUTH_TOKEN_FILE), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(_OAUTH_CLIENT_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            _OAUTH_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            _OAUTH_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds

    raise SystemExit(
        f"認証情報が見つかりません。{_CRED_DIR} に\n"
        f"  - credentials.json（サービスアカウントキー）か\n"
        f"  - client_secret.json（OAuthクライアント）\n"
        f"のどちらかを置いてください。手順は scripts/SEO_README.md を参照。"
    )


def _build_service():
    from googleapiclient.discovery import build

    creds = _get_credentials()
    return build("searchconsole", "v1", credentials=creds)


def _query(service, site_url: str, *, start_date: str, end_date: str,
           dimensions: list[str], row_limit: int = 1000,
           filters: list[dict] | None = None) -> list[dict]:
    body: dict = {
        "startDate": start_date,
        "endDate": end_date,
        "rowLimit": row_limit,
    }
    if dimensions:
        body["dimensions"] = dimensions
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    return resp.get("rows", [])


def fetch_summary(service, site_url: str, start_date: str, end_date: str) -> dict:
    """ディメンション無しで問い合わせると、サイト全体の集計1行が返る（一番正確な合計）。"""
    rows = _query(service, site_url, start_date=start_date, end_date=end_date, dimensions=[])
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
    r = rows[0]
    return {
        "clicks": r.get("clicks", 0),
        "impressions": r.get("impressions", 0),
        "ctr": r.get("ctr", 0.0),
        "position": r.get("position", 0.0),
    }


def fetch_query_rows(service, site_url: str, start_date: str, end_date: str, row_limit: int = 1000):
    import pandas as pd

    rows = _query(service, site_url, start_date=start_date, end_date=end_date,
                  dimensions=["query"], row_limit=row_limit)
    if not rows:
        return pd.DataFrame(columns=["query", "clicks", "impressions", "ctr", "position"])
    df = pd.DataFrame(
        [
            {
                "query": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0),
                "position": r.get("position", 0.0),
            }
            for r in rows
        ]
    )
    return df


def top_queries(df, n: int = 10):
    return df.sort_values("clicks", ascending=False).head(n).reset_index(drop=True)


def improvement_candidates(df, min_impressions: int = 50, max_ctr: float = 0.02):
    """表示回数は十分あるのにCTRが低い＝タイトル/説明文を見直す価値がありそうなクエリ。"""
    cand = df[(df["impressions"] >= min_impressions) & (df["ctr"] <= max_ctr)]
    return cand.sort_values("impressions", ascending=False).reset_index(drop=True)


def branded_trend(service, site_url: str, start_date: str, end_date: str, brand_keywords: list[str]):
    """指名検索（ブランド名を含むクエリ）の日別推移。
    ※ これはGoogle検索での指名検索の動きであり、Threads等SNS経由の流入そのものではない
      （上のモジュールdocstring参照）。"""
    import pandas as pd

    filters = [
        {"dimension": "query", "operator": "contains", "expression": kw} for kw in brand_keywords
    ]
    # dimensionFilterGroups内のfiltersはAND条件になるため、複数キーワードのOR検索がしたい場合は
    # 本来グループを分けるべきだが、ブランドキーワードは通常1つなのでここでは先頭のみ使う。
    # 複数キーワードを本当にORで見たい場合は、キーワードごとに個別に呼び出すこと。
    rows = _query(
        service, site_url, start_date=start_date, end_date=end_date,
        dimensions=["date"], row_limit=1000, filters=filters[:1],
    )
    if not rows:
        return pd.DataFrame(columns=["date", "clicks", "impressions", "ctr", "position"])
    df = pd.DataFrame(
        [
            {
                "date": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0),
                "position": r.get("position", 0.0),
            }
            for r in rows
        ]
    ).sort_values("date")
    return df


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site-url", default=DEFAULT_SITE_URL)
    ap.add_argument("--days", type=int, default=30, help="何日分さかのぼるか（既定30）")
    ap.add_argument("--end-lag", type=int, default=3,
                     help="Search Consoleのデータ反映には数日のラグがあるため、"
                          "今日からこの日数分さかのぼった日を終了日にする（既定3）")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--min-impressions", type=int, default=50,
                     help="改善候補クエリの最低表示回数（既定50）")
    ap.add_argument("--max-ctr", type=float, default=0.02,
                     help="改善候補クエリの最大CTR（既定0.02=2%）")
    ap.add_argument("--brand-keywords", default=",".join(DEFAULT_BRAND_KEYWORDS),
                     help="指名検索とみなすキーワード（カンマ区切り）")
    ap.add_argument("--row-limit", type=int, default=1000, help="クエリ内訳の取得上限行数")
    ap.add_argument("--out-dir", help="指定するとCSVも保存する（例: data/seo-reports）")
    args = ap.parse_args()

    end = dt.date.today() - dt.timedelta(days=args.end_lag)
    start = end - dt.timedelta(days=args.days)
    start_date, end_date = start.isoformat(), end.isoformat()
    brand_keywords = [k.strip() for k in args.brand_keywords.split(",") if k.strip()]

    print(f"対象サイト: {args.site_url}")
    print(f"期間: {start_date} 〜 {end_date}（{args.days}日分、データ反映ラグ考慮で{args.end_lag}日前まで）")
    print()

    service = _build_service()

    # 1) 全体サマリー
    summary = fetch_summary(service, args.site_url, start_date, end_date)
    print("=" * 60)
    print("■ 全体サマリー")
    print("=" * 60)
    print(f"  合計クリック数　: {summary['clicks']:,}")
    print(f"  合計表示回数　　: {summary['impressions']:,}")
    print(f"  CTR　　　　　　 : {_fmt_pct(summary['ctr'])}")
    print(f"  平均掲載順位　　: {summary['position']:.1f}")
    print()

    df = fetch_query_rows(service, args.site_url, start_date, end_date, row_limit=args.row_limit)

    # 2) 上位クエリ
    top = top_queries(df, args.top_n)
    print("=" * 60)
    print(f"■ クリック数 上位{args.top_n}クエリ")
    print("=" * 60)
    if top.empty:
        print("  （データなし）")
    else:
        for i, row in top.iterrows():
            print(f"  {i + 1:2d}. {row['query']:<30s} クリック{row['clicks']:>4d} / "
                  f"表示{row['impressions']:>5d} / CTR {_fmt_pct(row['ctr'])} / 順位{row['position']:.1f}")
    print()

    # 3) 改善候補クエリ
    cand = improvement_candidates(df, args.min_impressions, args.max_ctr)
    print("=" * 60)
    print(f"■ 改善候補クエリ（表示回数≥{args.min_impressions} かつ CTR≤{_fmt_pct(args.max_ctr)}）")
    print("=" * 60)
    if cand.empty:
        print("  （該当なし）")
    else:
        for i, row in cand.head(20).iterrows():
            print(f"  - {row['query']:<30s} 表示{row['impressions']:>5d} / "
                  f"CTR {_fmt_pct(row['ctr'])} / 順位{row['position']:.1f}")
    print()

    # 4) 指名検索の推移
    trend = branded_trend(service, args.site_url, start_date, end_date, brand_keywords)
    print("=" * 60)
    print(f"■ 指名検索の日別推移（クエリに「{brand_keywords[0]}」を含むもの）")
    print("  ※ Google検索での指名検索の動きです。Threads等SNS経由の流入そのものではありません")
    print("    （Threadsからの実流入は utm_source=threads を Cloudflare Pages の Analytics で確認）")
    print("=" * 60)
    if trend.empty:
        print("  （該当なし）")
    else:
        for _, row in trend.iterrows():
            print(f"  {row['date']}: クリック{row['clicks']:>3d} / 表示{row['impressions']:>4d}")
    print()

    if args.out_dir:
        import pandas as pd

        out = pathlib.Path(args.out_dir)
        if not out.is_absolute():
            out = _ROOT / out
        out = out / end_date
        out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([summary]).to_csv(out / "summary.csv", index=False)
        top.to_csv(out / "top_queries.csv", index=False)
        cand.to_csv(out / "improvement_candidates.csv", index=False)
        trend.to_csv(out / "branded_trend.csv", index=False)
        print(f"CSVを保存しました: {out}")


if __name__ == "__main__":
    main()
