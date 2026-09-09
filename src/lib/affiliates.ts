/**
 * アフィリエイト提携先。ここに1回貼れば、全 service 記事から参照できる。
 * URL を差し替えたいときはこのファイルだけ直す。
 *
 * `link`  : クリック先（A8 の px.a8.net リンク）
 * `pixel` : インプレッション計測用の 1x1 gif（A8 が広告リンクとセットで渡すもの）。無ければ空文字
 * `label` : ボタンの既定文言（記事側で上書き可）
 * `note`  : 記事に添える一言（任意）
 */
export interface Affiliate {
  link: string;
  pixel?: string;
  label: string;
  note?: string;
}

export const AFFILIATES: Record<string, Affiliate> = {
  carryon: {
    link: 'https://px.a8.net/svt/ejp?a8mat=4BC4QV+FEW1CQ+3OGM+5YJRM',
    pixel: 'https://www19.a8.net/0.gif?a8mat=4BC4QV+FEW1CQ+3OGM+5YJRM',
    label: 'キャリーオンで子供服を見てみる',
    note: '子供服のUSED通販。新規会員登録で300ポイント、3,900円以上で送料無料。',
  },
  // elmo:   { link: '', pixel: '', label: 'ELMO for Family を見てみる' },
  // novakid:{ link: '', pixel: '', label: 'NovaKid の無料お試しを見る' },
};
