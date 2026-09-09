from __future__ import annotations

from .util import (
    BLOG,
    DATA,
    append_log,
    dump_yaml,
    frontmatter,
    load_json,
    load_yaml,
    log,
    save_json,
    slugify,
    today,
    unique_slug,
)


def publish(article: dict, topic: dict, og_image: str, *, model_label: str) -> str:
    base = (
        topic.get("slug")
        or slugify(article.get("slug_hint", ""), "")
        or f"{article['articleType']}-{today().replace('-', '')}"
    )
    slug = unique_slug(base)

    affiliate = (topic.get("affiliate") or "").strip()

    meta = {
        "title": article["title"],
        "description": article["description"],
        "pubDate": today(),
        "category": article["category"],
        "stage": article["stage"],
        "articleType": article["articleType"],
        "tags": article.get("tags", [])[:5],
        "emoji": article.get("emoji", "") or "",
        "heroImage": article.get("heroImage") or "",
        "ogImage": og_image,
        "sources": article.get("sources", []),
        "author": "管理人",
        "generatedBy": f"pipeline {model_label} / {today()}",
    }
    if affiliate:
        meta["sponsored"] = True  # BlogPost がファーストビュー付近に PR 表示を出す
    if not meta["sources"]:
        meta.pop("sources")
    if not meta["emoji"]:
        meta.pop("emoji")
    if not meta["heroImage"]:
        meta.pop("heroImage")

    body = article["body_md"].strip()
    if affiliate:
        # .mdx で書き出し、CTA コンポーネントを本文へ差し込む（まとめの直前 / 無ければ末尾）
        ext = "mdx"
        cta = f'<AffiliateCTA name="{affiliate}" />'
        imp = "import AffiliateCTA from '../../components/AffiliateCTA.astro';"
        marker = "\n## まとめ"
        if marker in body:
            body = body.replace(marker, f"\n{cta}\n{marker}", 1)
        else:
            body = f"{body}\n\n{cta}"
        body = f"{imp}\n\n{body}"
    else:
        ext = "md"

    md = frontmatter(meta) + "\n" + body + "\n"
    (BLOG / f"{slug}.{ext}").write_text(md, encoding="utf-8")
    log(f"  publish: src/content/blog/{slug}.{ext}" + ("  [PR/affiliate]" if affiliate else ""))

    # topic-bank を published に
    bank = load_yaml(DATA / "topic-bank.yml") or []
    for e in bank:
        same = e is topic or (
            e.get("slug") == topic.get("slug")
            and e.get("title_seed") == topic.get("title_seed")
        )
        if same and e.get("status", "queued") in ("queued", "candidate"):
            e["status"] = "published"
            e["published_slug"] = slug
            e["published"] = today()
            break
    dump_yaml(DATA / "topic-bank.yml", bank)

    # state を更新（ローテーションを1つ進める）
    state = load_json(DATA / "state.json", {})
    state["rotation_index"] = int(state.get("rotation_index", 0)) + 1
    state["last_run"] = today()
    state.setdefault("published", []).append(
        {
            "slug": slug,
            "type": article["articleType"],
            "category": article["category"],
            "date": today(),
        }
    )
    save_json(DATA / "state.json", state)

    append_log(f"➕ 新規 `{slug}` ({article['articleType']} / {article['category']}) — {article['title']}")
    return slug
