# 自動生成を「回る」状態にする手順

現状：パイプラインのコードと設定は入っているが、**まだ自動生成は動いていない**。
下のどちらかを設定すると回り始める。

先に共通で1つ：

```bash
cp .env.example .env
# .env を開いて GEMINI_API_KEY= に値を入れる
#   → https://aistudio.google.com/apikey で無料取得
```

状態チェック：

```bash
pip install -r scripts/requirements.txt
python scripts/pipeline.py --check          # READY と出れば準備OK
python scripts/pipeline.py --daily --dry-run  # 1本ぶん生成して中身を確認（保存しない）
```

---

## 方法A：GitHub + Cloudflare Pages（推奨・完全自動）

毎朝クラウドで生成 → コミット → サイト自動デプロイ。この Mac の電源に依存しない。

### 1. GitHub にリポジトリを作って push

```bash
# github.com で空のリポジトリを作成（例：zaiaku-zero-ikuji）してから
git remote add origin https://github.com/<あなた>/zaiaku-zero-ikuji.git
git push -u origin main
```

### 2. GitHub Secrets に APIキーを登録

リポジトリ → Settings → Secrets and variables → Actions → New repository secret

- `GEMINI_API_KEY` … 必須
- `UNSPLASH_ACCESS_KEY` … 任意（記事写真を自動取得したい場合）

（`.github/workflows/daily.yml` が毎日 06:00 JST に実行される。手動テストは Actions タブ → daily-article → Run workflow）

### 3. Cloudflare Pages に接続

dash.cloudflare.com → Workers & Pages → Create → Pages → Connect to Git → このリポジトリ

- Build command: `npm run build`
- Build output directory: `dist`
- 保存で初回デプロイ。以降は push のたび自動

### 4.（任意）訪問者カウンタ

Workers & Pages → KV → 名前空間を作成 → 対象 Pages プロジェクト → Settings → Functions →
KV namespace bindings に **変数名 `HITS`** で割り当てる。

### 5. `astro.config.mjs` の `site` を本番URLに更新

---

## 方法B：この Mac で回す（GitHub なしで、まず動かしたいとき）

毎朝この Mac が起きていれば、ローカルで生成してローカルコミットまで行う（push はしない）。
あとで手動 push、または方法Aの Cloudflare 連携をあとから足せば自動デプロイになる。

```bash
sh scripts/local-schedule.sh install    # 毎日 06:15 に実行を登録
sh scripts/local-schedule.sh status     # 登録確認
sh scripts/local-schedule.sh uninstall  # 解除
```

- `.env` に `GEMINI_API_KEY` が無いと、生成はスキップされる（MOCKの記事は作らない）
- ログ：`scripts/local-run.log`
- 1回すぐ試す：`sh scripts/run-local.sh` のあと `cat scripts/local-run.log`

---

## 記事のネタを足す

`data/topic-bank.yml` に `status: queued` で追記するだけ（1日1件消費）。
`slug` は英数字ハイフンで一意、`official_sources` に公的機関URL、`ref_urls` に競合の良質記事URL
（構成の参考にするだけで本文は取り込まない）。ネタが尽きた日は何もしない。
