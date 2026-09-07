from __future__ import annotations

import datetime
import json
import pathlib
import re

# scripts/gen/util.py → parents[2] = リポジトリルート
ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BLOG = ROOT / "src" / "content" / "blog"
THUMBS = ROOT / "public" / "images" / "thumb"
PROMPTS = SCRIPTS / "prompts"

# src/lib/site.ts と一致させること
CATEGORIES = ["sns", "gohan", "nenne", "kokoro", "sango", "wanope", "hatsuiku", "kurashi"]
STAGES = ["ninshin", "age0", "age1_2", "age3_pre", "gakudo"]
ARTICLE_TYPES = ["trend", "basics", "service", "voice", "cheer"]
ROTATION = ["trend", "basics", "service", "voice", "cheer"]

STAGE_LABEL = {
    "ninshin": "妊娠・出産",
    "age0": "0歳",
    "age1_2": "1〜2歳",
    "age3_pre": "3歳〜未就学",
    "gakudo": "小学生〜",
}

TYPE_LABEL = {
    "trend": "SNSで話題の深掘り",
    "basics": "基本のき",
    "service": "使ってよかった",
    "voice": "リアルな声 × 事実",
    "cheer": "今日のあなたへ",
}
CATEGORY_ACCENT = {
    "sns": "sky",
    "gohan": "sun",
    "nenne": "grape",
    "kokoro": "coral",
    "sango": "grape",
    "wanope": "sky",
    "hatsuiku": "mint",
    "kurashi": "sky",
}


def today() -> str:
    return datetime.date.today().isoformat()


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


def read_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def load_yaml(path: pathlib.Path):
    import yaml

    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: pathlib.Path, data) -> None:
    import yaml

    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def load_json(path: pathlib.Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


def unique_slug(base: str) -> str:
    slug, n = base, 2
    while (BLOG / f"{slug}.md").exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def frontmatter(meta: dict) -> str:
    import yaml

    body = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{body}\n---\n"


def append_log(line: str) -> None:
    path = DATA / "improvement-log.md"
    prefix = "" if path.exists() else "# 自動更新ログ\n\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}- {today()} {line}\n")


def append_credit(line: str) -> None:
    """public/images/CREDITS.md の「自動取得分」に写真クレジットを追記。"""
    path = ROOT / "public" / "images" / "CREDITS.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# 画像クレジット\n"
    marker = "\n## 自動取得分（パイプライン）\n"
    if marker not in text:
        text += "\n" + marker
    text = text.rstrip() + f"\n- {line}\n"
    path.write_text(text, encoding="utf-8")


def write_review(slug_hint: str, issues: list[str], body: str = "") -> None:
    path = ROOT / "REVIEW.md"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"## {today()} — {slug_hint}\n\n")
        for i in issues:
            f.write(f"- [ ] {i}\n")
        if body:
            f.write("\n<details><summary>下書き</summary>\n\n```\n" + body[:6000] + "\n```\n\n</details>\n")
        f.write("\n")
