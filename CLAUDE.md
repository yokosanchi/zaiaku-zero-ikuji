# CLAUDE.md — 『罪悪感ゼロ育児』開発ガイド

このファイルは、以降のすべての開発で保持すべきコンセプトと技術ルールを定義する。
作業前に必ず参照し、迷ったら「読者を絶対に責めない」を判断基準にする。

---

## 1. メディアのコンセプト

- **サイト名：** 罪悪感ゼロ育児
- **サブタイトル：** あなたはダメな親じゃない。「手抜き」じゃなく「心を守る選択」で、新米パパママの自己肯定感と知識を高めるメディア
- **ターゲット：** 子育て未経験者（プレパパ・プレママ、新米パパママ）
- **コアバリュー：**
  - 「手抜き」「時短」を「心と笑顔を守るためのスマートな選択」として再定義する
  - 読者の罪悪感を消し、自己肯定感を最大化する
  - リアルな失敗談（生声）× 公的機関のファクト（根拠）で、信頼できる知識を届ける

---

## 2. 技術スタック / インフラ（完全コストゼロ構成）

| 領域 | 採用 |
| --- | --- |
| サイト本体（SSG） | Astro（TypeScript / Tailwind CSS） |
| コンテンツ | Markdown / MDX（`src/content/blog/` 配下、content collections） |
| ホスティング | Cloudflare Pages（GitHub 連携・無料枠） |
| 記事生成 AI | Gemini 1.5 Flash API（無料枠）※Phase 2 |
| 自動化 | GitHub Actions（毎朝 1 記事を自動生成）※Phase 2 |

### コマンド

```bash
npm install       # 依存関係
npm run dev       # 開発サーバ（http://localhost:4321）
npm run build     # 本番ビルド → dist/
npm run preview   # ビルド結果をローカル確認
```

### Cloudflare Pages 設定

- Build command: `npm run build`
- Build output directory: `dist`
- Node version: 20 以上

---

## 3. ディレクトリ構成

```
src/
├── components/
│   ├── BaseHead.astro      # <head> / SEO / OGP / フォント読み込み
│   ├── Header.astro        # サイトロゴ＋グローバルナビ
│   ├── Footer.astro        # 医療免責・広告表記・コピーライト
│   ├── ArticleCard.astro   # 記事カード（画像/絵文字・タグ・日付）
│   └── ArticleList.astro   # カードのグリッド
├── content/
│   ├── config.ts           # blog コレクションのスキーマ（zod）
│   └── blog/*.md           # 記事本体
├── layouts/
│   ├── BaseLayout.astro    # 全ページ共通の外枠
│   └── BlogPost.astro      # 記事詳細レイアウト（prose・免罪符ボックス）
├── pages/
│   ├── index.astro         # トップ（ファーストビュー＋新着記事）
│   ├── about.astro         # このサイトについて（運営方針・YMYL・広告）
│   └── blog/
│       ├── index.astro     # 記事一覧
│       └── [...slug].astro # 記事詳細（getStaticPaths）
└── styles/global.css       # Tailwind エントリ＋base（背景グラデ・marker-sun）

public/images/              # 写真素材（Unsplash・帰属不要）。CREDITS.md 参照
```

## デザイン方針（ポップ＆明るい）

- 配色：`cream` 地に `coral`（主役CTA）＋ `sun`/`sky`/`mint`/`grape` のパステルポップ。`ink` は黒すぎない `#3F3A4A`。
- 形：大きめ角丸（`rounded-3xl`〜`[2rem]`）、ハード影 `shadow-pop` / `shadow-pop-lg`、装飾 blob（`rounded-blob` + `animate-floaty`）。
- 文字：見出し = Zen Maru Gothic、本文 = Zen Kaku Gothic New、手書きアクセント = Yomogi（`font-hand`）。
- 記事の H2 は黄色い角丸ステッカー、ファクト枠（blockquote）は水色カード＋ `📊`。
- 写真は Unsplash 無料素材を `public/images/` に置き、記事 front matter の `heroImage: "/images/xxx.jpg"` で指定。
- モーション過敏対応：`prefers-reduced-motion` で全アニメOFF（global.css）。

### 記事の front matter スキーマ（`src/content/config.ts`）

```yaml
title: string            # 必須。H1 / OGP
description: string       # 必須。メタディスクリプション（120〜160字目安）
pubDate: YYYY-MM-DD       # 必須
updatedDate: YYYY-MM-DD   # 任意
heroImage: string        # 任意。無ければ emoji のグラデ背景を表示
tags: [string]            # カテゴリ／タグ
emoji: string             # カード・ヒーローの絵文字
author: string            # 既定 "編集部"
draft: boolean            # true はビルド除外
```

---

## 4. トーン＆マナー（最重要・記事レビュー時に必ずチェック）

### 絶対禁止ワード（上から目線・説教調）

- 「〜すべき」
- 「〜してください」
- 「〜しなきゃダメ」
- 「がんばりましょう」

> 例外：公的機関の見解を引用する場合でも、これらの語尾は避けて言い換える
> （例：「使ってください」→「使っていいとされている」）。

### 推奨トーン

- 徹底的な共感と肯定：「〜で全然大丈夫」「〜は心を守るための素晴らしい選択」
- 読者に免罪符を与える語りかけ
- 読者の努力を認める言い方（「すでに十分やれています」）は歓迎

### 記事の基本構造

1. 悩みへの共感（具体的な情景描写で書き出す）
2. 公的ファクト（`> 📊 **見出し（出典名）**` の blockquote で提示。prose で水色カード表示）
3. 罪悪感を外す考え方
4. 現実的な工夫（箇条書き / H3）
5. （service タイプのみ）「心の余裕を守る道具として」＝アフィリエイト導線（広告表記を必ず添える）
6. `## まとめ`（箇条書き）＋ 肯定のひとこと

※ 記事末尾の「最後に、あなたへ」肯定ボックスと医療免責は `BlogPost.astro` が自動付与するので本文に書かない。

---

## 5. YMYL ガードレール（デプロイ前チェック）

医療・健康にかかわるハザード情報を厳格にチェックする。以下のような**危険な表現が本文にあればビルドを止める / 公開しない**：

- 1 歳未満へのはちみつ（乳児ボツリヌス症）
- うつぶせ寝の推奨（SIDS リスク）
- 自己判断での断薬・受診回避のすすめ
- 発熱・けいれん・脱水などに「様子見でよい」と断定する表現
- 医薬品・サプリの用量を具体的に指南する表現

判断に迷う医療トピックは「かかりつけ医・自治体の相談窓口へ」に必ず接続する。
生成パイプラインでは `scripts/gen/guardrails.py` の `check_ymyl` が検出し、
`concept_rewrite` が `YMYLBlocked` を投げて公開を止める（→ `REVIEW.md`）。手書き記事も
`python -c "...check_ymyl..."` でチェックできる（ヒューリスティックなので誤検知はあり得る）。

---

## 6. SEO / 構造化

- H2 / H3 を意味順に配置（H1 は 1 ページ 1 つ、タイトルのみ）
- `description` は各記事で必ず固有に書く（`BaseHead.astro` が meta / OGP に反映）
- 内部リンク：記事末から `/blog` へ、関連記事へ相互リンク
- `astro.config.mjs` の `site` を本番 URL に合わせる（OGP の絶対 URL 生成に必要）
- sitemap / RSS は Phase 3 で追加（`@astrojs/sitemap` は現行環境でビルドが不安定なため一旦保留）

---

## 7. 自動記事生成パイプライン（実装済み / `scripts/`）

**完全自動・毎朝1本。LLM の一発出しにはしない多段構成。** 詳細は `scripts/README.md`。

```
pick_topic → research → draft → concept_rewrite → thumbnail → publish → improve
```

- **pick_topic**：`data/topic-bank.yml`（キュレーション型ネタ帳）からローテーションで1件。
  順番は `trend → basics → service → voice → cheer`（= 5つの記事タイプ、`src/lib/site.ts` と一致）。
- **research**：`official_sources`（公的機関URL）を取得して事実メモに要約。
  `ref_urls`（大手競合の良質記事）は**見出し構成のシグナルだけ**取得し、本文は取り込まない（著作権配慮）。
- **draft**：タイプ別プロンプト（`scripts/prompts/draft_<type>.md`）で下書き。競合は「読者の期待の把握」だけに使い、本文は公式ソース根拠の完全オリジナル。
- **concept_rewrite**：サイトの声へリライト（§4）。禁止語を機械的に除去。
- **thumbnail**：記事に合わせた 1200×630 OGP 画像を生成（カテゴリ色・見出し・絵文字）→ `public/images/thumb/<slug>.png`（`cairosvg` 不在時は SVG）。
- **publish**：`src/content/blog/<slug>.md` を書き出し、`topic-bank` / `data/state.json` / `data/improvement-log.md` を更新。
- **improve**：毎回、既存記事を1本点検（リンク・画像切れ）。`IMPROVE_MODE=full` で軽い推敲も。

ガードレール（`scripts/gen/guardrails.py`）：§4 の禁止語＋§5 の YMYL ハザード。
**YMYL 検出時は公開せず**、リポジトリ直下 `REVIEW.md` に積んで人間に回す（当日は「見送り」）。

自動実行：`.github/workflows/daily.yml`（毎日 06:00 JST）→ 生成 → `npm run build` で検証 → 通れば push → Cloudflare Pages が自動デプロイ。
必要な Secret：`GEMINI_API_KEY`（未設定なら MOCK モードで空回り）。任意の Variables：`GEMINI_MODEL` / `IMPROVE_MODE` / `THUMB_HEADLINE`。

ネタの足し方：`data/topic-bank.yml` に `status: queued` で1行追加するだけ。`slug` は ASCII で一意、
`official_sources` に公的URL、`ref_urls` に競合の良質記事URL（構成参考のみ・複製しない）。ネタ切れの日は何もしない。

### 記事タイプ（ローテーション）

| key | 内容 |
| --- | --- |
| `trend` | SNSで話題の投稿の深掘り |
| `basics` | 子育て必須の「基本のき」の深掘り |
| `service` | 普通に使った方がよいサービス・家電の紹介（広告表記＋安全注意を必須） |
| `voice` | ブログ等のリアルな声 × 正確な情報での補正 |
| `cheer` | 「子どもを育てていて、えらい」を手渡す応援メッセージ |

### カテゴリ（受け皿。`src/lib/site.ts` が唯一の定義元。7つ）

`gohan`（ごはん・離乳食 / sun）｜`nenne`（ねんね・生活リズム / grape）｜`kokoro`（心のケア / coral）｜`sango`（産後うつ・こころの不調 / grape）｜`wanope`（ワンオペ育児 / sky）｜`hatsuiku`（発育・健康 / mint）｜`kurashi`（暮らし・便利グッズ / sky）

- カテゴリ追加時に触る4か所：`src/lib/site.ts`（CATEGORIES）｜`src/content/config.ts`（category enum）｜`scripts/gen/util.py`（CATEGORIES / CATEGORY_ACCENT）｜色は5トークン（sun/grape/coral/mint/sky）から流用可、ナビ隣接で同色が並ばないようにする。
- `sango` は YMYL 高感度。記事は自己診断させず、必ず相談窓口（厚労省「まもろうよ こころ」等）へ接続する。

ページ：`/categories`（一覧）、`/categories/[key]`（カテゴリ別）。Header/Footer/トップ/記事一覧に `CategoryNav`。

---

## 8. ロゴ

- モチーフ：**ハート＋スマイル**（セルフ・コンパッション＝「自分を許していい」）。coral 角丸バッジに白いハートと笑顔。
- 実体は `src/components/Logo.astro`（インライン SVG、Header/Footer が使用）。`public/favicon.svg` も同じ絵柄。
- ブランドキット：`public/logo/`（`mark-heart.svg` 採用 / `mark-chick.svg`・`mark-bubble.svg` 予備 / `lockup.svg` ヨコ組み / `proposals.svg` 比較シート）。
  差し替えるなら `Logo.astro` と `public/favicon.svg` の中身を置き換える。

---

## 9. 現在の進捗

- [x] Phase 1：Astro + Tailwind 土台、Header、トップ、記事一覧、記事詳細、ダミー記事
- [x] リデザイン：ポップ＆明るいトーン（coral+パステル、blob、手書きフォント、ハード影）＋写真（Unsplash）
- [x] Phase 2：多段パイプライン（5タイプ・ローテーション）＋カテゴリ受け皿＋関連記事＋記事別OGP生成＋毎日の自己改善＋GitHub Actions＋ロゴ
- [ ] Phase 2 の残：GitHub リポ作成 → `GEMINI_API_KEY` 登録 → 初回 workflow_dispatch（ユーザー作業）
- [ ] Phase 3：`ref_urls` を実際の競合記事で埋める、トレンド自動収集（`00_collect_trends`）、アクセス解析ベースの改善、RSS/sitemap
