/**
 * サイト共通の定義（カテゴリ / 記事タイプ）。
 * ページ・コンポーネント・自動生成パイプラインが同じキーを参照する。
 */

export type CategoryKey =
  | 'sns'
  | 'gohan'
  | 'nenne'
  | 'kokoro'
  | 'sango'
  | 'kakawari'
  | 'saino'
  | 'wanope'
  | 'hatsuiku'
  | 'kurashi'
  | 'shinmama';
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

/** 読者が「トピックで」記事を探すための受け皿。 */
export const CATEGORIES: CategoryMeta[] = [
  {
    key: 'sns',
    label: 'SNSバズ・深掘り',
    short: 'SNSバズ',
    emoji: '📱',
    accent: 'sky',
    description:
      'X・Instagram・TikTokで話題の悩みや投稿を、「わかる」で終わらせず事実で深掘り。',
  },
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
    key: 'sango',
    label: '産後うつ・こころの不調',
    short: '産後うつ',
    emoji: '⛅',
    accent: 'grape',
    description:
      '涙が止まらない、眠れない、笑えない。それは甘えではなく、相談していいサイン。',
  },
  {
    key: 'kakawari',
    label: '関わり方',
    short: '関わり方',
    emoji: '🫂',
    accent: 'grape',
    description:
      '叱り方・ほめ方、そして親から受け継いだもの。目を背けたくなる話も、根拠をもって扱います。',
  },
  {
    key: 'saino',
    label: '才能と教育のホント',
    short: '才能・教育',
    emoji: '🔍',
    accent: 'mint',
    description:
      '「東大に入った子の子育て法」を鵜呑みにしなくていい理由。成功の物語の裏側を、研究ベースで検証します。',
  },
  {
    key: 'wanope',
    label: 'ワンオペ育児',
    short: 'ワンオペ',
    emoji: '🤹',
    accent: 'sky',
    description:
      'ひとりで全部を回す毎日に。「最低ライン」の決め方と、頼っていい先。',
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
  {
    key: 'shinmama',
    label: 'シンママ',
    short: 'シンママ',
    emoji: '🌻',
    accent: 'sun',
    description:
      '養育費、児童扶養手当、面会交流、「かわいそう」という視線。ひとりで抱えなくていい情報と、頼っていい窓口をまとめます。',
  },
];

export const CATEGORY_MAP = Object.fromEntries(
  CATEGORIES.map((c) => [c.key, c])
) as Record<CategoryKey, CategoryMeta>;

/** もう1つの軸：子どもの成長ステージ（時系列。カテゴリと直交）。 */
export type StageKey = 'ninshin' | 'age0' | 'age1_2' | 'age3_pre' | 'gakudo';

export interface StageMeta {
  key: StageKey;
  label: string;
  short: string;
  emoji: string;
  accent: AccentKey;
  description: string;
}

export const STAGES: StageMeta[] = [
  {
    key: 'ninshin',
    label: '妊娠・出産',
    short: '妊娠・出産',
    emoji: '🤰',
    accent: 'coral',
    description: '妊娠中の不安、出産準備、産後すぐの体と心。買いすぎない・がんばりすぎない準備。',
  },
  {
    key: 'age0',
    label: '0歳',
    short: '0歳',
    emoji: '👶',
    accent: 'sun',
    description: '授乳・離乳食・夜泣き・ワンオペ。眠れない毎日を、最低ラインでやり過ごす。',
  },
  {
    key: 'age1_2',
    label: '1〜2歳',
    short: '1〜2歳',
    emoji: '🧸',
    accent: 'mint',
    description: 'イヤイヤ期、手づかみ食べ、行きしぶり。正面から勝とうとしなくて大丈夫。',
  },
  {
    key: 'age3_pre',
    label: '3歳〜未就学',
    short: '3歳〜',
    emoji: '🖍️',
    accent: 'sky',
    description: 'トイレトレーニング、登園しぶり、集団生活。その子のタイミングを待っていい。',
  },
  {
    key: 'gakudo',
    label: '小学生〜',
    short: '小学生〜',
    emoji: '🎒',
    accent: 'grape',
    description: '小1の壁、学童、宿題。全部を完璧に整えなくても、親失格じゃない。',
  },
];

export const STAGE_MAP = Object.fromEntries(
  STAGES.map((s) => [s.key, s])
) as Record<StageKey, StageMeta>;

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
