# 画像クレジット

すべて [Unsplash ライセンス](https://unsplash.com/ja/license)（商用可・帰属不要）の無料素材。
差し替えるときは同じファイル名で上書きするか、記事の front matter の `heroImage` を変更する。
取得元 URL 形式: `https://images.unsplash.com/<photo id>?w=1200&h=675&fit=crop&fm=jpg`

| ファイル | 用途 | Unsplash photo id |
| --- | --- | --- |
| `hero-laugh.jpg` | トップページ ヒーロー | `photo-1629822937307-ce27f951e385` |
| `eating.jpg` | 離乳食は市販のベビーフードで100点満点 | `photo-1646314951096-ed41d80638b6` |
| `bath.jpg` | ワンオペのお風呂、入れられない日があってもいい | `photo-1609220361664-a5cd02bc7345` |
| `sleep.jpg` | 夜泣きがつらい。でも「ネントレしない」 | `photo-1546015720-b8b30df5aa27` |
| `kenshin.jpg` | 乳幼児健診は「気になること」を話す場 | `photo-1632053002928-1919605ee6f7` |
| `tired-parent.jpg` | 今日、何もできなかったと思っている人へ | `photo-1583710457367-47de0ea21fef` |
| `wanope.jpg` | ワンオペの1日を乗り切る「最低ライン」 | `photo-1590467590164-c75b94a98575` |
| `dishwasher.jpg` | 食洗機は「甘え」じゃない | `photo-1758631130778-42d518bf13aa` |
| `window-calm.jpg` | 産後、涙が止まらない・眠れない | `photo-1696299437505-ceb0fa8bfb38` |
| `pregnancy.jpg` | 出産準備は「買いすぎない」がいちばんラク | `photo-1568043625493-2b0633c7c491` |
| `tantrum.jpg` | イヤイヤ期は「成長のサイン」 | `photo-1622364678783-37af307d91be` |
| `messy-eating.jpg` | 手づかみ食べで部屋がぐちゃぐちゃ | `photo-1633306002639-c9d74c129347` |
| `toddler-home.jpg` | トイレトレーニングが進まない（※差し替え候補） | `photo-1693467301038-79af2da1e40b` |
| `school-walk.jpg` | 登園しぶりで毎朝バトル | `photo-1776351546386-7cfff8fd519d` |
| `schoolyard.jpg` | 小1の壁（※差し替え候補） | `photo-1549522757-8d50c0f9c224` |
| `homework.jpg` | 宿題を見てあげられない日があっても | `photo-1758612898701-e2f2958f219d` |
| `tabenai.jpg` | 「離乳食、全然食べない」の投稿がバズるたびに | `photo-1544632561-0f8a895a2b08` |

## 自動取得分（パイプライン）

パイプラインは `UNSPLASH_ACCESS_KEY` があるとき、記事内容に合う写真を検索して
`public/images/thumb/<slug>.jpg` に保存し、ここへ追記する。
