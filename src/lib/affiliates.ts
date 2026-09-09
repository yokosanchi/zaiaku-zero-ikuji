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
  novakid: {
    link: 'https://px.a8.net/svt/ejp?a8mat=4BC4QV+FRZKNU+4KYW+65U41',
    pixel: 'https://www11.a8.net/0.gif?a8mat=4BC4QV+FRZKNU+4KYW+65U41',
    label: 'NovaKid の無料お試しレッスンを見てみる',
    note: '4〜12歳向けのオンライン英会話。自宅から、都合のいい時間に。まずは無料で1回試せます。',
  },
  magicalsherry: {
    link: 'https://px.a8.net/svt/ejp?a8mat=4BC6AW+218CYI+43OO+15P77L',
    pixel: 'https://www16.a8.net/0.gif?a8mat=4BC6AW+218CYI+43OO+15P77L',
    label: 'マジカルシェリーを見てみる',
    note: '産後・子育て世代向けの着圧インナー（骨盤まわりをサポートするタイプ）。医療器具ではなく、体の負担をやわらげる道具のひとつです。',
  },
  hariti: {
    link: 'https://px.a8.net/svt/ejp?a8mat=4BC6AW+1ZG256+5EV0+5ZEMP',
    pixel: 'https://www18.a8.net/0.gif?a8mat=4BC6AW+1ZG256+5EV0+5ZEMP',
    label: 'Hariti でベビーグッズを見てみる',
    note: '子どもの安全グッズや親の負担を減らすアイテムのショップ。高価な育児用品はレンタルでも試せます。2週間返品保証あり（利用すると成果対象外）。',
  },
  // elmo: { link: '', pixel: '', label: 'ELMO for Family を見てみる' },
};
