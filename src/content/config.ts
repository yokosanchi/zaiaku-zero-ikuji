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
      'gohan',
      'nenne',
      'kokoro',
      'sango',
      'wanope',
      'hatsuiku',
      'kurashi',
    ]),
    /** ローテーションで書く記事タイプ */
    articleType: z
      .enum(['trend', 'basics', 'service', 'voice', 'cheer'])
      .default('voice'),
    /** タグ（自由入力） */
    tags: z.array(z.string()).default([]),
    /** 記事上部の写真（任意。無ければ絵文字ブロック） */
    heroImage: z.string().optional(),
    /** OGP/サムネ画像（1200x630。パイプラインが記事ごとに生成） */
    ogImage: z.string().optional(),
    /** カード等に出す絵文字 */
    emoji: z.string().optional(),
    /** 根拠にした公的情報など（記事末に出典として表示） */
    sources: z
      .array(z.object({ label: z.string(), url: z.string().url() }))
      .default([]),
    /** 署名 */
    author: z.string().default('編集部'),
    /** true はビルド対象外 */
    draft: z.boolean().default(false),
    /** 自動生成の透明性表示用（例: "pipeline gemini-2.5-flash / 2026-09-08"） */
    generatedBy: z.string().optional(),
  }),
});

export const collections = { blog };
