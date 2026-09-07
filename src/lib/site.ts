/**
 * サイト共通の定義（カテゴリ / 記事タイプ）。
 * ページ・コンポーネント・自動生成パイプラインが同じキーを参照する。
 */

export type CategoryKey = 'gohan' | 'nenne' | 'kokoro' | 'hatsuiku' | 'kurashi';
export type ArticleTypeKey = 'trend' | 'basics' | 'service' | 'voice' | 'cheer';

export type AccentKey = 'sun' | 'grape' | 'coral' | 'mint' | 'sky';

export interface CategoryMeta {
  key: CategoryKey;
  label: string;
  short: string;
  emoji: string;
  accent: AccentKey;
  description: string;
}

/** 読者が「トピックで」記事を探すための受け皿。5つに固定。 */
export const CATEGORIES: CategoryMeta[] = [
  {
    key: 'gohan',
    label: 'ごはん・離乳食',
    short: 'ごはん',
    emoji: '🍚',
    accent: 'sun',
    description:
      '離乳食もミルクも、市販でOK。毎日のごはんの時間を少しラクにするヒント。',
  },
  {
    key: 'nenne',
    label: 'ねんね・生活リズム',
    short: 'ねんね',
    emoji: '🌙',
    accent: 'grape',
    description: '夜泣き・寝かしつけ・生活リズム。眠れない夜をやり過ごす工夫。',
  },
  {
    key: 'kokoro',
    label: '心のケア',
    short: '心のケア',
    emoji: '💗',
    accent: 'coral',
    description:
      '罪悪感、孤独、パートナーとのこと。あなたの心をまんなかに置く話。',
  },
  {
    key: 'hatsuiku',
    label: '発育・健康',
    short: '発育・健康',
    emoji: '🌱',
    accent: 'mint',
    description: '成長のペース、健診、ちょっとした不調。ほかの子と比べなくて大丈夫。',
  },
  {
    key: 'kurashi',
    label: '暮らし・便利グッズ',
    short: '暮らし',
    emoji: '🧺',
    accent: 'sky',
    description: '家事を減らす家電やサービス。「時間を買う」という選択の話。',
  },
];

export const CATEGORY_MAP = Object.fromEntries(
  CATEGORIES.map((c) => [c.key, c])
) as Record<CategoryKey, CategoryMeta>;

/** 毎日ローテーションで書く5つの記事タイプ。 */
export interface ArticleTypeMeta {
  key: ArticleTypeKey;
  label: string;
  badge: string;
  emoji: string;
  brief: string;
}

export const ARTICLE_TYPES: Record<ArticleTypeKey, ArticleTypeMeta> = {
  trend: {
    key: 'trend',
    label: 'SNSで話題の深掘り',
    badge: '話題',
    emoji: '🔥',
    brief: 'SNSでバズった投稿の背景を、事実で深掘りする。',
  },
  basics: {
    key: 'basics',
    label: '基本のき',
    badge: '基本',
    emoji: '📖',
    brief: '子育てで必須の「基本のき」を、やさしく深掘りする。',
  },
  service: {
    key: 'service',
    label: '使ってよかった',
    badge: 'サービス',
    emoji: '🛟',
    brief: '普通に使った方がラクになるサービス・家電を紹介する。',
  },
  voice: {
    key: 'voice',
    label: 'リアルな声 × 事実',
    badge: '体験',
    emoji: '💬',
    brief: 'ブログなどのリアルな声を、正確な情報とともに伝える。',
  },
  cheer: {
    key: 'cheer',
    label: '今日のあなたへ',
    badge: '応援',
    emoji: '💛',
    brief: '「子どもを育てていて、えらい」を言葉にして手渡す。',
  },
};

export const ARTICLE_TYPE_LIST: ArticleTypeMeta[] = Object.values(ARTICLE_TYPES);

/** Tailwind の静的クラス（JIT が拾えるよう文字列リテラルで持つ）。 */
export const ACCENT: Record<
  AccentKey,
  { grad: string; softBg: string; text: string; ring: string }
> = {
  sun: {
    grad: 'from-sun-soft to-sun/50',
    softBg: 'bg-sun-soft',
    text: 'text-sun-deep',
    ring: 'ring-sun',
  },
  grape: {
    grad: 'from-grape-soft to-grape/50',
    softBg: 'bg-grape-soft',
    text: 'text-grape-deep',
    ring: 'ring-grape',
  },
  coral: {
    grad: 'from-coral-soft to-coral/40',
    softBg: 'bg-coral-soft',
    text: 'text-coral-deep',
    ring: 'ring-coral',
  },
  mint: {
    grad: 'from-mint-soft to-mint/50',
    softBg: 'bg-mint-soft',
    text: 'text-mint-deep',
    ring: 'ring-mint',
  },
  sky: {
    grad: 'from-sky-soft to-sky/50',
    softBg: 'bg-sky-soft',
    text: 'text-sky-deep',
    ring: 'ring-sky',
  },
};
