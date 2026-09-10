#!/usr/bin/env python3
"""Threads 投稿の単体チェック。パイプライン全体を回さずに確認できる。

    python scripts/threads_check.py            # 鍵の有無 + 最新記事の投稿文を表示（投稿しない）
    python scripts/threads_check.py --post     # 最新記事の投稿文を実際に投稿する（鍵が必要）
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


def _latest_meta() -> tuple[dict, str]:
    posts = sorted((_ROOT / "src/content/blog").glob("*.md"), key=lambda p: p.stat().st_mtime)
    posts += sorted((_ROOT / "src/content/blog").glob("*.mdx"), key=lambda p: p.stat().st_mtime)
    if not posts:
        raise SystemExit("記事がありません")
    p = max(posts, key=lambda x: x.stat().st_mtime)
    fm = p.read_text(encoding="utf-8").split("---", 2)[1]

    def g(k: str) -> str:
        m = re.search(rf'^{k}:\s*"?(.+?)"?\s*$', fm, re.M)
        return m.group(1) if m else ""

    return {"title": g("title"), "description": g("description"), "ogImage": g("ogImage")}, p.stem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--text")
    args = ap.parse_args()

    _load_dotenv()
    from gen.post_threads import _creds, compose_post, post

    c = _creds()
    print("鍵2つ:", "OK（そろっている）" if c else "未設定（THREADS_USER_ID / THREADS_ACCESS_TOKEN）")

    img = None
    if args.text:
        text = args.text
    else:
        meta, slug = _latest_meta()
        text = compose_post(meta, slug)
        img = meta.get("ogImage") or None
        print(f"\n--- 最新記事: {slug} ---")

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
