"""公開前のセーフティネット。

- check_banned: CLAUDE.md の禁止語（説教調）を検出
- check_ymyl : 医療・安全上あぶない断定を検出 → 見つかったら公開せず REVIEW.md 行き
どちらもヒューリスティック。取りこぼし・誤検知はあり得るが、
「あやしければ人間に回す」方向に倒してある。
"""

from __future__ import annotations

import re

BANNED_PATTERNS: list[tuple[str, str]] = [
    (r"す?べき(?:です|だ|でしょう|だろう|)", "〜すべき"),
    (r"して(?:ください|下さい)", "〜してください"),
    (r"しなきゃ(?:ダメ|だめ|いけない)", "〜しなきゃダメ"),
    (r"がんばりましょう|頑張りましょう|(?:がんばって|頑張って)(?:ください|下さい)", "がんばりましょう"),
]

# (ラベル, 必須語, 文脈語(any/空=不問), 危険語(any/空=不問))
YMYL_RULES: list[tuple[str, list[str], list[str], list[str]]] = [
    (
        "1歳未満のはちみつ",
        [r"はちみつ|ハチミツ|蜂蜜"],
        [r"0歳|ゼロ歳|1歳(?:未満|前|になる前)|生後|乳児|赤ちゃん|離乳"],
        [r"与え|あげ|食べさせ|なめさせ|使っ|混ぜ|おすすめ|良い|よい|大丈夫|平気"],
    ),
    (
        "うつ伏せ寝の推奨",
        [r"うつ(?:伏せ|ぶせ)"],
        [r"寝|睡眠|寝かせ|寝かし"],
        [r"推奨|おすすめ|良い|よい|安心|大丈夫|問題ない|平気|させて"],
    ),
    (
        "自己判断の断薬・通院中止",
        [r"薬をやめ|断薬|服薬をやめ|通院をやめ|受診をやめ|病院に行かなく"],
        [],
        [r"大丈夫|問題ない|いい|平気|必要ない|しなくて|やめても"],
    ),
    (
        "発熱・けいれんの様子見断定",
        [r"高熱|発熱|けいれん|痙攣|ひきつけ|意識|ぐったり|脱水"],
        [],
        [r"様子見で(?:いい|大丈夫|平気)|放って?おいて|受診しなくて(?:いい|大丈夫)|病院に行かなくて(?:いい|大丈夫)"],
    ),
    (
        "予防接種の忌避",
        [r"ワクチン|予防接種"],
        [],
        [r"打たなくて(?:いい|大丈夫)|不要|受けなくて(?:いい|大丈夫)|危険だから避け"],
    ),
    (
        "添い寝・同床を安全と断定",
        [r"添い寝|添い乳|同じ布団|ベッドで一緒|同床"],
        [],
        [
            r"(添い寝|添い乳|同じ布団|一緒に寝て|同床)(?:は|も|でも|しても|なら)?\s*"
            r"(安全|安心|問題ない|大丈夫|推奨|おすすめ|心配ない)"
        ],
    ),
]


def check_banned(text: str) -> list[str]:
    hits = [label for pat, label in BANNED_PATTERNS if re.search(pat, text)]
    return sorted(set(hits))


# 「危険を避けよう」という文脈は安全側なので、危険語が近くにあっても除外する
_SAFE_NEGATION = re.compile(
    r"避け|さけ|しない|防ぐ|防止|危険|リスク|注意|控え|やめ|ではなく|NG|禁物|絶対に(?!安全)"
)


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[。！？\n])", text)


def check_ymyl(text: str) -> list[str]:
    flags: list[str] = []
    sents = _sentences(text)
    for label, must_any, ctx_any, danger_any in YMYL_RULES:
        if not any(re.search(p, text) for p in must_any):
            continue
        hit = False
        for s in sents:
            if not any(re.search(p, s) for p in must_any):
                continue
            if ctx_any and not any(re.search(p, s) for p in ctx_any):
                continue
            if danger_any and not any(re.search(p, s) for p in danger_any):
                continue
            # 同じ文が「避ける／防ぐ／危険」等を含むなら安全側とみなす
            if _SAFE_NEGATION.search(s):
                continue
            hit = True
            break
        if hit:
            flags.append(label)
    return flags
