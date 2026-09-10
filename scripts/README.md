# 自動記事パイプライン

毎日1本、記事を作って公開する多段パイプライン。**LLMの一発出しにはしない**。

```
pick_topic → research → draft → concept_rewrite → thumbnail → publish → improve
```

| 段 | ファイル | やること |
| --- | --- | --- |
| pick_topic | `gen/topic.py` | ローテーション（trend→basics→service→voice→cheer）でタイプを決め、その中から**記事が不足しているカテゴリ／ステージを優先**して1件選ぶ。バンクが尽きたら不足枠を狙って LLM が起案 |
| research | `gen/research.py` | `official_sources` を取得して「事実メモ」に要約。`ref_urls`(競合)は**見出し構成だけ**取得（本文は取らない） |
| draft | `gen/draft.py` + `prompts/draft_<type>.md` | タイプ別プロンプトで下書き（本文は事実メモ根拠の完全オリジナル） |
| concept_rewrite | `gen/rewrite.py` + `prompts/concept_rewrite.md` | サイトの声へリライト＋**禁止語を機械的に除去**＋**YMYL 危険表現を検出したら公開中止** |
| thumbnail | `gen/thumbnail.py` | 記事に合わせた 1200×630 の OGP 画像を生成（カテゴリ色・見出し・絵文字）。`public/images/thumb/<slug>.png` |
| publish | `gen/publish.py` | `src/content/blog/<slug>.md` を書き出し、`topic-bank` と `state.json` を更新、ログ追記 |
| improve | `gen/improve.py` | 既存記事を1本、点検（リンク・画像切れ）＋**軽いリライト**（導入をペインに寄せて締める・`updatedDate` 更新）。`IMPROVE_MODE=links` で点検のみに |

ガードレールは `gen/guardrails.py`（禁止語＝CLAUDE.md準拠、YMYL＝はちみつ/うつ伏せ寝/断薬 等）。
検出時は公開せず、リポジトリ直下の `REVIEW.md` に積まれる。

## 使い方（手元）

```bash
pip install -r scripts/requirements.txt

# APIキー無しで配線だけ確認（MOCK。ダミー記事が1本できる）
PIPELINE_MOCK=1 python scripts/pipeline.py --daily

# 本番と同じ（GEMINI_API_KEY が要る）
export GEMINI_API_KEY=xxxx
python scripts/pipeline.py --daily              # ローテーションで1本
python scripts/pipeline.py --daily --type cheer # タイプ指定
python scripts/pipeline.py --daily --dry-run    # 生成して表示、保存しない
python scripts/pipeline.py --improve-only       # 既存記事の点検だけ
```

## 環境変数

| 変数 | 既定 | 説明 |
| --- | --- | --- |
| `GEMINI_API_KEY` | （必須） | 未設定なら自動で MOCK モード |
| `GEMINI_MODEL` | `gemini-3.6-flash` | 生成モデル |
| `IMPROVE_MODE` | `full` | `links` にすると improve は点検のみ（リライトしない） |
| `THUMB_HEADLINE` | （なし） | `ai` でサムネの惹句を LLM 生成 |
| `PIPELINE_MOCK` | （なし） | `1` で LLM を呼ばずダミー出力 |

## ネタの足し方

`data/topic-bank.yml` にエントリを追加するだけ（`status: queued`）。
`slug` は ASCII で一意、`official_sources` に公的機関のURL、`ref_urls` に競合の良質記事URL
（※構成の参考にするだけ。本文は複製しない）。
バンクが尽きたら `gen/topic.py` が LLM に新ネタを1件起案させて `topic-bank.yml` に追記する
（`generated: true` が付く）。止まらないが、手で良質な種を足しておく方が精度は高い。

## 自動実行

`.github/workflows/daily.yml` が毎日 **06:00 と 18:00 JST（1日2本）** に実行 → 生成 → `npm run build` で検証 →
`main` に push → **その場で `wrangler pages deploy` して Cloudflare Pages に直接公開**。
（Cloudflare の GitHub 連携には依存しない。連携が切れても確実に出る）

GitHub の **Settings → Secrets and variables → Actions → Secrets** に登録するもの:

| Secret | 取得元 |
| --- | --- |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com → My Profile → API Tokens → テンプレート「Edit Cloudflare Workers」 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare ダッシュボード右サイドの Account ID |
| `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | X Developer Portal（App 権限 Read and write）※未設定なら X 投稿だけスキップ |
| `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN` | Meta（Threads API）。長期トークンは約60日で要リフレッシュ。未設定なら Threads 投稿だけスキップ |

`CLOUDFLARE_*` が未設定なら Deploy 段はスキップされる（生成とコミットは実行される）。
