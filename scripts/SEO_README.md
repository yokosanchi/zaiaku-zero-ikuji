# Search Console レポート（`gsc_report.py`）

Google Search Console（サチコ）の検索パフォーマンスデータを取得して、サマリー・上位クエリ・
改善候補クエリ・指名検索の推移を出すツール。

**限界の注意**：これはGoogle検索での実績しか見られません。Threadsなど他SNSからの流入は
このAPIの管轄外なので分かりません。「指名検索の推移」は"ブランド名で検索する人が増えたか"
という間接的な兆候を見ているだけで、Threadsが原因だと断定はできません。Threadsからの実流入は
投稿リンクに付けた `utm_source=threads` を、Cloudflare Pagesプロジェクトの Analytics タブ
（Referrer別）で見るほうが直接的です。

## 1. GCP側の準備

1. [console.cloud.google.com](https://console.cloud.google.com) を開き、プロジェクトを作成（または既存のものを使う）
2. 左メニュー「APIとサービス」→「ライブラリ」を開き、**"Search Console API"** を検索して有効化

## 2. 認証方法を選ぶ（どちらか一方でよい）

### 方法A：サービスアカウント（おすすめ・毎回のログイン不要）

1. 「APIとサービス」→「認証情報」→「認証情報を作成」→ **「サービスアカウント」**
2. 名前を適当に付けて作成（ロールの割り当てはスキップしてよい）
3. 作成したサービスアカウントを開き、「キー」タブ → 「鍵を追加」→「新しい鍵を作成」→ **JSON** を選択
4. ダウンロードされたファイルを、このリポジトリの
   ```
   scripts/.gsc/credentials.json
   ```
   として保存する（`.gsc/` フォルダが無ければ作成してよい。**Gitには絶対にコミットしない** — `.gitignore` 済み）
5. ダウンロードしたJSONファイルの中の `"client_email"` の値（`xxxxx@xxxxx.iam.gserviceaccount.com` のようなメールアドレス）をコピー
6. [Google Search Console](https://search.google.com/search-console) → 対象プロパティ → 左メニュー「設定」→「ユーザーとアクセス権限」→「ユーザーを追加」
7. 5でコピーしたメールアドレスを入力、権限は **「制限付き」**（読み取りだけなら十分）で追加

### 方法B：OAuth（自分のGoogleアカウントでその都度認可）

1. 「APIとサービス」→「認証情報」→「認証情報を作成」→ **「OAuthクライアントID」**
2. 同意画面の設定を求められたら「外部」で作成し、自分のメールアドレスをテストユーザーに追加
3. アプリケーションの種類は **「デスクトップアプリ」** を選択して作成
4. ダウンロードされたファイルを
   ```
   scripts/.gsc/client_secret.json
   ```
   として保存する
5. 初回実行時にブラウザが自動で開き、Googleアカウントでログイン・同意する
6. 認証結果は `scripts/.gsc/token.json` に自動キャッシュされ、以後は再ログイン不要（期限切れ時は自動更新）

## 3. インストール・実行

```bash
pip install -r scripts/requirements-seo.txt

# 直近30日分（既定）
python scripts/gsc_report.py

# 期間や対象サイトを変える
python scripts/gsc_report.py --days 60 --site-url "https://zaiaku-zero-ikuji.pages.dev/"

# CSVも保存する（data/seo-reports/<終了日>/ 以下に4ファイル）
python scripts/gsc_report.py --out-dir data/seo-reports
```

主なオプション（`python scripts/gsc_report.py --help` で一覧）：

| オプション | 既定値 | 意味 |
| --- | --- | --- |
| `--site-url` | `https://zaiaku-zero-ikuji.pages.dev/` | Search Consoleに登録したプロパティのURL（完全一致が必要） |
| `--days` | 30 | 何日分さかのぼるか |
| `--end-lag` | 3 | データ反映ラグを考慮し、今日から何日前を終了日にするか |
| `--top-n` | 10 | 上位クエリの表示件数 |
| `--min-impressions` | 50 | 改善候補クエリの最低表示回数 |
| `--max-ctr` | 0.02 | 改善候補クエリの最大CTR（2%） |
| `--brand-keywords` | `罪悪感ゼロ育児` | 指名検索とみなすキーワード（カンマ区切り） |
| `--out-dir` | （指定時のみ） | CSV保存先ディレクトリ |

## トラブルシューティング

- `認証情報が見つかりません` → `scripts/.gsc/` に `credentials.json` か `client_secret.json` を置き忘れていないか確認
- API呼び出しで 403 が出る → サービスアカウントのメールアドレスを Search Console の「ユーザーとアクセス権限」に追加し忘れていないか確認
- 全部の数字が0になる → `--site-url` がSearch Console上のプロパティ文字列と完全一致しているか確認（末尾スラッシュの有無も含めて）

---

## 自動改善PDCAパイプライン（`sachiko_analyzer.py` + `auto_refine.py`）

Search Consoleデータを元に、改善ポテンシャルが高い記事を見つけて、Geminiでタイトル/メタ
ディスクリプション・追記セクションの改善案を自動生成する仕組み。

```
sachiko_analyzer.py（Plan/Check: データ取得・フラグ判定）
        ↓
data/seo/flagged_<date>.json
        ↓
auto_refine.py（Act: Geminiで改善案を生成。--apply で記事ファイルに反映）
        ↓
data/seo/proposals/<date>/<slug>.json（判断結果の記録）
```

### 判定ロジック

- **フラグA（低CTR）**：表示回数500以上・CTR2%以下 → タイトル/メタディスクリプションの改善案を生成
- **フラグB（あと一歩）**：平均掲載順位が8〜20位 → 追記セクション（見出し+本文）の改善案も生成

しきい値は `sachiko_analyzer.py --min-impressions-a` `--max-ctr-a` `--pos-low` `--pos-high` で変更できる。

### 安全設計（これが一番重要）

- **既定は提案のみ**。`--apply` を付けない限り、記事ファイルは一切書き換わらない
- `--apply` で反映する場合も、生成結果は毎回 `gen/guardrails.py`（禁止語・YMYL）を通し、
  引っかかれば反映しない（`gen/improve.py` の既存パスと同じ考え方）
- `category: sango`（産後うつ）の記事は最初から対象外
- GitHub Actions（`seo-pdca.yml`）では、記事本体（`src/content/blog/`）の変更は
  **必ずPRになる**。`main` への直接pushはしない。マージするまで公開サイトには反映されない。
  データ集計ファイル（`data/seo/` 以下、記事の内容ではない）だけは追跡用にmainへ直接コミットされる

### ローカルでの実行

```bash
pip install -r scripts/requirements.txt -r scripts/requirements-seo.txt

npm run auto-pdca          # 分析→提案生成まで（記事ファイルは変更しない）

# 提案を確認して問題なければ、実際に反映する
python scripts/auto_refine.py --apply --limit 3
```

提案の中身は `data/seo/proposals/<日付>/<slug>.json` に保存される
（`verdict`: accepted/rejected/skipped/error と、変更前後のtitle/description、追記セクション案）。

### GitHub Actionsで自動化する場合の追加設定

1. 上の「方法A：サービスアカウント」の手順で `scripts/.gsc/credentials.json` を作成
2. そのJSONファイルの**中身をそのまま**、リポジトリの Secret `GSC_SERVICE_ACCOUNT_JSON` に登録
   （`Settings → Secrets and variables → Actions → New repository secret`）
3. `.github/workflows/seo-pdca.yml` が毎週月曜7:30 JSTに自動実行される
   （`workflow_dispatch` で手動実行も可能。`apply: false` にすると提案生成だけで止められる）
4. 記事の変更があれば `seo-refine/YYYYMMDD-HHMMSS` というブランチでPRが作られるので、
   内容を確認してからマージする（マージ後、通常の `deploy.yml` の push トリガーで公開される）
