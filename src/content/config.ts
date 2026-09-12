import { defineCollection, z } from 'astro:content';

// 記事コレクション（src/content/blog/*.md | *.mdx）
const blog = defineCollection({
  type: 'content',
  schema: z.object({
    /** 記事タイトル（H1・OGP に使用） */
    title: z.string(),
    /** メタディスクリプション（120〜160文字目安） */
    description: z.string(),
    /** 公開日 */
    pubDate: z.coerce.date(),
    /** 更新日（自動改善パスが更新する） */
    updatedDate: z.coerce.date().optional(),
    /** トピックの受け皿カテゴリ（src/lib/site.ts と一致） */
    category: z.enum([
      'sns',
      'gohan',
      'nenne',
      'kokoro',
      'sango',
      'kakawari',
      'saino',
      'wanope',
      'hatsuiku',
      'kurashi',
      'shinmama',
      'okane',
    ]),
    /** 子どもの成長ステージ（src/lib/site.ts と一致・カテゴリと直交） */
    stage: z.enum(['ninshin', 'age0', 'age1_2', 'age3_pre', 'gakudo']),
    /** ローテーションで書く記事タイプ */
    articleType: z
      .enum(['trend', 'basics', 'service', 'voice', 'cheer'])
      .default('voice'),
    /** タグ（自由入力） */
    tags: z.array(z.string()).default([]),
    /** 記事上部の写真（任意。無ければ絵文字ブロック） */
    heroImage: z.string().optional(),
    /** デザインカードのサムネに出す1行。読み手のペイン起点のキャッチ（無ければタイトルを使う） */
    thumbHook: z.string().optional(),
    /** OGP/サムネ画像（1200x630。パイプラインが記事ごとに生成） */
    ogImage: z.string().optional(),
    /** カード等に出す絵文字 */
    emoji: z.string().optional(),
    /** 根拠にした公的情報など（記事末に出典として表示） */
    sources: z
      .array(z.object({ label: z.string(), url: z.string().url() }))
      .default([]),
    /** 元になったSNSの話題（ハッシュタグ検索ページ等へのリンク） */
    snsRefs: z
      .array(
        z.object({
          platform: z.string(),
          label: z.string(),
          url: z.string().url(),
        })
      )
      .default([]),
    /** 署名 */
    author: z.string().default('編集部'),
    /** 広告（アフィリエイト）を含む記事。true で記事上部に PR 表示を出す（ステマ規制・ASP要件） */
    sponsored: z.boolean().default(false),
    /** true はビルド対象外 */
    draft: z.boolean().default(false),
    /** 自動生成の透明性表示用（例: "pipeline gemini-2.5-flash / 2026-09-08"） */
    generatedBy: z.string().optional(),
  }),
});

export const collections = { blog };
