#!/usr/bin/env python3
"""Threads 投稿の単体チェック・実投稿に使う。パイプライン全体を回さずに確認できる。

    python scripts/threads_check.py                    # 鍵の有無 + 最新記事(mtime基準)の投稿文を表示（投稿しない）
    python scripts/threads_check.py --post              # 最新記事の投稿文を実際に投稿する（鍵が必要）
    python scripts/threads_check.py --slug foo --post   # slugを明示指定（daily.ymlのデプロイ後投稿で使用。
                                                          # mtime基準だとimproveパスが触った既存記事を誤って
                                                          # 拾うことがあるため、確実にこちらを使う）
    python scripts/threads_check.py --text "..." --post
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load_dotenv() -> None:
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _meta_from_path(p: pathlib.Path) -> dict:
    fm = p.read_text(encoding="utf-8").split("---", 2)[1]

    def g(k: str) -> str:
        m = re.search(rf'^{k}:\s*"?(.+?)"?\s*$', fm, re.M)
        return m.group(1) if m else ""

    def g_list(k: str) -> list[str]:
        m = re.search(rf'^{k}:\s*\[(.*?)\]\s*$', fm, re.M)
        if not m:
            return []
        return [s.strip().strip('"').strip("'") for s in m.group(1).split(",") if s.strip()]

    return {
        "title": g("title"),
        "description": g("description"),
        "ogImage": g("ogImage"),
        "thumbHook": g("thumbHook"),
        "category": g("category"),
        "tags": g_list("tags"),
    }


def _meta_by_slug(slug: str) -> tuple[dict, str]:
    for ext in (".md", ".mdx"):
        p = _ROOT / "src/content/blog" / f"{slug}{ext}"
        if p.exists():
            return _meta_from_path(p), p.stem
    raise SystemExit(f"記事が見つかりません: {slug}")


def _latest_meta() -> tuple[dict, str]:
    """mtime基準で最新の記事を拾う。improveパスが既存記事を触ると
    そちらのmtimeが新しくなり得るため、確実性が必要な場面（daily.ymlの
    デプロイ後投稿）では --slug を使うこと。"""
    posts = sorted((_ROOT / "src/content/blog").glob("*.md"), key=lambda p: p.stat().st_mtime)
    posts += sorted((_ROOT / "src/content/blog").glob("*.mdx"), key=lambda p: p.stat().st_mtime)
    if not posts:
        raise SystemExit("記事がありません")
    p = max(posts, key=lambda x: x.stat().st_mtime)
    return _meta_from_path(p), p.stem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--text")
    ap.add_argument("--slug", help="この slug の記事を明示的に使う（mtime基準の推測をしない）")
    args = ap.parse_args()

    _load_dotenv()
    from gen.post_threads import _creds, compose_post, post

    c = _creds()
    print("鍵2つ:", "OK（そろっている）" if c else "未設定（THREADS_USER_ID / THREADS_ACCESS_TOKEN）")

    img = None
    if args.text:
        text = args.text
    else:
        meta, slug = _meta_by_slug(args.slug) if args.slug else _latest_meta()
        text = compose_post(meta, slug)
        img = meta.get("ogImage") or None
        print(f"\n--- 対象記事: {slug} ---")

    print("\n----- 投稿予定の本文 -----")
    print(text)
    print(f"（{len(text)}字 / 上限500）")
    print("-------------------------")

    if not args.post:
        print("\n(--post を付けると実際に投稿します)")
        return
    if not c:
        raise SystemExit("\n鍵が未設定なので投稿できません。")
    pid = post(text, image_url=img)
    if pid:
        print(f"\n✅ 投稿成功: id={pid}")
    else:
        raise SystemExit("\n❌ 投稿失敗（上のログを確認）")


if __name__ == "__main__":
    main()
