# CLAUDE.md — 『罪悪感ゼロ育児』開発ガイド

このファイルは、以降のすべての開発で保持すべきコンセプトと技術ルールを定義する。
作業前に必ず参照し、迷ったら「読者を絶対に責めない」を判断基準にする。

---

## 1. メディアのコンセプト

- **サイト名：** 罪悪感ゼロ育児
- **サブタイトル：** あなたはダメな親じゃない。「手抜き」じゃなく「心を守る選択」で、新米パパママの自己肯定感と知識を高めるメディア
- **ターゲット：** 子育て未経験者（プレパパ・プレママ、新米パパママ）
- **成り立ち（記事の根っこ。トーンはここから来る）：**
  身体に障害を負い、できることが大きく限られた「管理人」が、妻のために・子どものために、
  「知っておきたかった育児情報」をまとめようとして生まれたサイト。
  手を動かして育児・家事を引き受けるのが難しい立場だからこそ、
  **道具に頼る／人に頼る／完璧をあきらめる = 限られた力で家族を大切にするための、まっとうな選択**、
  という確信が全記事の前提。「手抜きを責めない」は建前ではなく実体験。
  → About ページ（`src/pages/about.astro`）とフッター、トップの管理人ノートで明示。
  署名は「編集部」ではなく **「管理人」**（作成の一部は自動化しているが、方針とチェック基準は管理人が決める、という書き方で統一）。
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
| 自動化 | GitHub Actions（1日2〜3本を自動生成・公開）※Phase 2 |

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
heroImage: string        # 実質必須。写真 or デザインカード。**絵文字だけのサムネは禁止**
tags: [string]            # カテゴリ／タグ
emoji: string             # チップ等の装飾用（サムネの代わりにはしない）
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

### 実在の個人名を主語にしたコンテンツの禁止（`kakawari` / `saino` 共通ルール）

「毒親→凶悪犯罪」「すごい子育て→東大・名選手」のような、**実在の特定個人（犯罪者・経営者・スポーツ選手・"すごい子"含む）を主語にして、その人の子育て・家庭環境が結果の原因だったと断定する**記事は書かない。理由：
1. 因果関係の証明になっていない（生存者バイアス／逆の反例は無数にあり、単一事例からは何も言えない）
2. 実在の家族（多くは存命）への名誉毀損リスク
3. 現役の子ども（"すごい子"）を実名でプロファイリングするのはプライバシー・同意の観点で不可
4. 自動パイプラインには事実検証能力がなく、実在個人についての具体的主張はねつ造になり得る

代わりに：個人名を出さず、「型・パターン」としてのみ扱う（例：生存者バイアスの構造そのもの、早期教育の煽り表現の検証、自己決定理論などの一般的な心理学的知見）。研究・公的資料ベースで一般化する。ユーザー了承済みの標準方針。

---

## 5.5 コンテンツ安全基準・ガバナンス方針

「手抜き」と「放置」を明確に分ける。全記事（手書き・自動生成とも）が満たすこと。

### 基本思想
- **罪悪感を減らす対象は「家事・作業の工程」だけ。** 子どもの安全・情緒的応答（愛情表現・声かけ）の削減は推奨しない。
- 記事は必ず Win-Win 構造で締める：**省力化で生まれた「時間」と「心のゆとり」を、子どもとの笑顔のコミュニケーションに還元する**。

### 必須チェック（事前リスクケア）
1. **食事・栄養**：レトルト・惣菜・市販ベビーフードを勧めるとき、毎食の完全依存は勧めず、栄養を補う簡単な工夫（汁物を足す・果物を添える等）を併記。アレルギー・誤飲・喉詰めは厚労省等の公的ガイドラインに基づく注意書きを必須に。
2. **デジタル・放置**：スマホ・動画・TV は「無制限の放置」ではなく、時間のメリハリ（例：30分まで／夕飯準備中のみ）・作品の選定など管理下の活用ルールを提示。見せたあとに短い双方向の会話（「どれが面白かった？」）を挟む案をセットに。
3. **安全管理・事故防止**：「親が別室で休む」「家事に没頭する」等を紹介するときは、誤飲・転倒・浴室/ベランダ対策（ベビーゲート・ベビーモニター等）が済んでいることを前提として明記。

### トーンの禁止事項（炎上・批判防止）
- 「育児なんて適当でいい」「放置しても育つ」等の極端・乱暴な表現の禁止。
- 手作り・尽力している親や特定の育児方針を否定・批判・下げる比較（マウント・他者下げ）の禁止。
- 小児科医・栄養士等の専門家領域に踏み込む医療的判断・自己流の治療法の提示の禁止（必ず「違和感があれば医療機関へ」を注記）。

**機械チェック**：乱暴表現は `guardrails.check_banned` に、上記1〜3の「対で書く」未充足は `guardrails.check_governance`（非ブロッキング、`REVIEW.md` に警告）で拾う。`sango`（産後うつ）記事は自動リライト対象外。

---

## 6. SEO / 構造化

- H2 / H3 を意味順に配置（H1 は 1 ページ 1 つ、タイトルのみ）
- `description` は各記事で必ず固有に書く（`BaseHead.astro` が meta / OGP に反映）
- 内部リンク：記事末から `/blog` へ、関連記事へ相互リンク
- 記事詳細（`BlogPost.astro`）：見出し(H2/H3)から**もくじ(TOC)自動生成**（`post.render()` の `headings`）、
  **SNSシェアボタン**（X / LINE / Facebook / リンクコピー）、関連記事、カテゴリ＋ステージ＋タイプのチップ
- `astro.config.mjs` の `site` を本番 URL に合わせる（OGP・シェアの絶対 URL 生成に必要）
- sitemap / RSS は Phase 3 で追加（`@astrojs/sitemap` は現行環境でビルドが不安定なため一旦保留）

---

## 7. 自動記事生成パイプライン（実装済み / `scripts/`）

**完全自動・1日2〜3本（各カテゴリ10本まで積み増し中は3本、以降2本）。LLM の一発出しにはしない多段構成。** 詳細は `scripts/README.md`。

```
pick_topic → research → draft → concept_rewrite → thumbnail → publish → improve
```

- **pick_topic**：`data/topic-bank.yml`（キュレーション型ネタ帳）からローテーションで1件。
  順番は `trend → basics → service → voice → cheer`（= 5つの記事タイプ、`src/lib/site.ts` と一致）。
- **research**：`official_sources`（公的機関URL）を取得して事実メモに要約。
  `ref_urls`（大手競合の良質記事）は**見出し構成のシグナルだけ**取得し、本文は取り込まない（著作権配慮）。
- **draft**：タイプ別プロンプト（`scripts/prompts/draft_<type>.md`）で下書き。競合は「読者の期待の把握」だけに使い、本文は公式ソース根拠の完全オリジナル。
- **concept_rewrite**：サイトの声へリライト（§4）。禁止語を機械的に除去。
- **thumbnail**：`UNSPLASH_ACCESS_KEY` があれば、draft が出す英語 `photo_query` で Unsplash を検索し、
  内容に合う横長写真を `public/images/thumb/<slug>.jpg` に保存して `heroImage` に採用（クレジットは `public/images/CREDITS.md` に追記）。
  無ければ「カテゴリ色＋見出し」の 1200×630 デザインカードを **Pillow で直接 PNG 描画**（`public/images/thumb/<slug>.png`）し、これも `heroImage` に採用。
  CJK フォントは CI=Noto Sans CJK / mac=ヒラギノ を自動検出（`scripts/gen/thumbnail.py::_font_path`）。
  **どちらの経路でも必ず画像を返す。絵文字だけのサムネは禁止。**
- **publish**：`src/content/blog/<slug>.md` を書き出し、`topic-bank` / `data/state.json` / `data/improvement-log.md` を更新。
- **X 投稿**（任意）：`scripts/gen/post_x.py`。`X_API_KEY`/`X_API_SECRET`/`X_ACCESS_TOKEN`/`X_ACCESS_SECRET` が4つ揃うと、公開直後に X へ自動ポスト（OAuth1.0a、標準ライブラリのみ）。無ければスキップ。`--no-x` で無効化。文面は `compose_tweet`（275字重み以内）。MOCK 実行時は投稿しない。
- **improve**：毎回、既存記事を1本点検（リンク・画像切れ）＋ `full` で導入を軽くリライト。**`category: sango`（産後うつ）は LLM リライト対象外**（点検のみ）。

ガードレール（`scripts/gen/guardrails.py`）：§4 の禁止語＋§5 の YMYL ハザード。
**YMYL 検出時は公開せず**、リポジトリ直下 `REVIEW.md` に積んで人間に回す（当日は「見送り」）。

**まだ自動実行は動いていない。回すための手順は `SETUP.md`。** 要約：

- 共通：`cp .env.example .env` → `GEMINI_API_KEY` を入れる（`pipeline.py` は起動時に `.env` を読む）
- 点検：`python scripts/pipeline.py --check`（READY 判定）／`--daily --dry-run`（保存せず中身確認）
- キー無しで `--daily` は**何もしない**（`result: no_key`）。MOCKで保存テストしたいときだけ `--allow-mock`
- **方法A（推奨・完全自動）**：GitHub へ push → Secrets に `GEMINI_API_KEY`（任意 `UNSPLASH_ACCESS_KEY`）→ `.github/workflows/daily.yml` が毎日 06:00 JST 実行 → `npm run build` 検証 → push → Cloudflare Pages 自動デプロイ
- **方法B（この Mac で回す）**：`sh scripts/local-schedule.sh install`（launchd で毎日 06:15 に `scripts/run-local.sh`）。生成→ビルド検証→ローカルコミットまで（push はしない）
- 任意 env：`GEMINI_MODEL` / `IMPROVE_MODE`(links|full) / `THUMB_HEADLINE`(ai)

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

### 2軸タクソノミー（`src/lib/site.ts` が唯一の定義元）

- **横軸＝話題別カテゴリ（7つ）** ＋ **縦軸＝成長ステージ（5つ）**。記事は必ず `category` と `stage` を1つずつ持つ。
- 記事タイプ（trend/basics/service/voice/cheer）は分類ではなく「毎日どの切り口で書くか」のローテーション用ラベル。
  ※ 2026-09 の「Ver 3.0」案（横軸を5テーマに統一 / 縦軸4段階）は不採用。横軸=話題別・縦軸=5段階を維持。
- ステージ：`/stages`（一覧）、`/stages/[key]`。`StageNav` をトップ/記事一覧/ステージ各ページに。

### 横軸カテゴリ（12）

`sns`（SNSバズ・深掘り / sky）｜`gohan`（ごはん・離乳食 / sun）｜`nenne`（ねんね・生活リズム / grape）｜`kokoro`（心のケア / coral）｜`sango`（産後うつ・こころの不調 / grape）｜`kakawari`（関わり方 / grape・叱り方ほめ方＋"目を背けたくなる話"担当）｜`saino`（才能と教育のホント / mint・成功神話の反証。生存者バイアス／早期教育の煽り／比べない、を実在の個人名を出さず研究ベースで扱う）｜`wanope`（ワンオペ育児 / sky）｜`hatsuiku`（発育・健康 / mint）｜`kurashi`（暮らし・便利グッズ / sky）｜`shinmama`（シンママ / sun・養育費・児童扶養手当・面会交流・偏見への対処。法律/制度がらみは法テラス等の公的窓口への接続を必須にする）｜`okane`（子どもとお金 / coral・教育費、お小遣い、学資保険。特定の金融商品を断定的に推奨しない、金額は必ず出典付きの調査データを引用する）

- `sns` は SNS で話題の悩み・投稿を事実で深掘りするカテゴリ。記事は基本 `articleType: trend`。
  実在の投稿は丸写しせず要約・一般化。`snsRefs`（frontmatter）で X / Instagram / TikTok のハッシュタグ検索ページへリンクし、記事末に「元になったSNSの話題」ボックスを表示。
  バズ規模は「#◯◯ は数十万件規模」等の phenomenon スケールで、数値変動の断り＋リンク確認を添える（特定投稿の『◯万いいね』のような数字はねつ造になるので書かない）。

### 縦軸ステージ（5つ）

`ninshin`（妊娠・出産 / coral）｜`age0`（0歳 / sun）｜`age1_2`（1〜2歳 / mint）｜`age3_pre`（3歳〜未就学 / sky）｜`gakudo`（小学生〜 / grape）

- カテゴリ／ステージ追加時に触る所：`src/lib/site.ts`（CATEGORIES / STAGES）｜`src/content/config.ts`（enum）｜`scripts/gen/util.py`（CATEGORIES / STAGES / *_ACCENT / STAGE_LABEL）。
- 色は5トークン（sun/grape/coral/mint/sky）を流用。ナビ隣接で同色が並ばないように。
- `sango` は YMYL 高感度。記事は自己診断させず、必ず相談窓口（厚労省「まもろうよ こころ」等）へ接続する。

ページ：`/categories`（一覧）、`/categories/[key]`（カテゴリ別）。Header/Footer/トップ/記事一覧に `CategoryNav`。

---

## 8. トップページの動的パーツ

- **「◯月◯日に届いた記事」**：ビルド日と `pubDate`/`updatedDate` が一致する記事だけ表示（`index.astro`）。自動更新でその日の分が並ぶ。無い日はセクションごと非表示。
- **きょうの訪問者数**：`functions/api/hits.js`（Cloudflare Pages Functions + KV）。`BaseLayout` のインラインスクリプトが 1 ブラウザ 1 日 1 回だけ `POST /api/hits?bump=1` して数を取得し、`[data-hits]` 要素を表示。
  - **セットアップ（CF ダッシュボード、1回だけ）**：KV 名前空間を作成 → 対象 Pages プロジェクト → Settings → Functions → KV namespace bindings に **変数名 `HITS`** で割り当て。
  - 未設定でも壊れない（`/api/hits` が使えない＝カウンタ非表示になるだけ）。`astro dev` では Functions が動かないので常に非表示。
  - Cookie 不使用・PII なし。日次キーは3日で自動失効。KV 無料枠は 1,000 write/日 なので、伸びたら D1 等へ。

---

## 9. ロゴ

- モチーフ：**ハート＋スマイル**（セルフ・コンパッション＝「自分を許していい」）。coral 角丸バッジに白いハートと笑顔。
- 実体は `src/components/Logo.astro`（インライン SVG、Header/Footer が使用）。`public/favicon.svg` も同じ絵柄。
- ブランドキット：`public/logo/`（`mark-heart.svg` 採用 / `mark-chick.svg`・`mark-bubble.svg` 予備 / `lockup.svg` ヨコ組み / `proposals.svg` 比較シート）。
  差し替えるなら `Logo.astro` と `public/favicon.svg` の中身を置き換える。

---

## 10. 現在の進捗

- [x] Phase 1：Astro + Tailwind 土台、Header、トップ、記事一覧、記事詳細、ダミー記事
- [x] リデザイン：ポップ＆明るいトーン（coral+パステル、blob、手書きフォント、ハード影）＋写真（Unsplash）
- [x] Phase 2：多段パイプライン（5タイプ・ローテーション）＋カテゴリ受け皿＋関連記事＋記事別OGP生成＋毎日の自己改善＋GitHub Actions＋ロゴ
- [ ] Phase 2 の残：GitHub リポ作成 → `GEMINI_API_KEY` 登録 → 初回 workflow_dispatch（ユーザー作業）
- [ ] Phase 3：`ref_urls` を実際の競合記事で埋める、トレンド自動収集（`00_collect_trends`）、アクセス解析ベースの改善、RSS/sitemap
