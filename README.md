# 罪悪感ゼロ育児

> あなたはダメな親じゃない。「手抜き」じゃなく「心を守る選択」で、新米パパママの自己肯定感と知識を高めるメディア。

Astro + Tailwind CSS で構築した完全コストゼロ構成の静的サイト。ホスティングは Cloudflare Pages。

## セットアップ

```bash
npm install
npm run dev      # http://localhost:4321
```

## コマンド

| コマンド | 内容 |
| --- | --- |
| `npm run dev` | 開発サーバを起動 |
| `npm run build` | 本番ビルド（`dist/` に出力） |
| `npm run preview` | ビルド結果をローカルで確認 |

## 記事を追加する

`src/content/blog/` に `.md` ファイルを置く。front matter のスキーマは `src/content/config.ts` を参照。

```markdown
---
title: "記事タイトル"
description: "メタディスクリプション"
pubDate: 2026-09-07
tags: ["離乳食", "心のケア"]
emoji: "🍼"                      # 画像がないときカードに出る絵文字
heroImage: "/images/xxx.jpg"     # 任意。public/images/ に置いた写真
---

本文…
```

## 写真素材

`public/images/` に配置。すべて Unsplash（帰属不要）。差し替えは同名ファイルで上書きするか
`heroImage` を変更するだけ。一覧は [`public/images/CREDITS.md`](./public/images/CREDITS.md)。

## 自動記事パイプライン

毎朝1本、5タイプ（trend / basics / service / voice / cheer）をローテーションで自動生成・公開する。
多段構成（下書き → コンセプトリライト → 記事別サムネ生成 → 公開 → 既存記事の点検）。
ネタは [`data/topic-bank.yml`](./data/topic-bank.yml) に貯める。使い方は [`scripts/README.md`](./scripts/README.md)。

```bash
PIPELINE_MOCK=1 python scripts/pipeline.py --daily   # APIキー無しで配線確認
```

GitHub Actions（`.github/workflows/daily.yml`）が毎日実行。Secret に `GEMINI_API_KEY` が要る。

## カテゴリ

トピックの受け皿は `src/lib/site.ts` の `CATEGORIES` が唯一の定義元。
ページは `/categories` と `/categories/[key]`。

## 開発ルール

コンセプト・技術スタック・トーンの禁止ワード・YMYL ガードレール・パイプライン仕様は
[`CLAUDE.md`](./CLAUDE.md) に集約。編集前に必ず参照すること。

## デプロイ（Cloudflare Pages）

- Build command: `npm run build`
- Output directory: `dist`
- `astro.config.mjs` の `site` を本番 URL に更新
