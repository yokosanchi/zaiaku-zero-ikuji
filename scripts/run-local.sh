#!/bin/sh
# ローカルで毎朝走らせる用。pipeline を回し、記事ができたらローカルコミット（push はしない）。
# launchd/cron から呼ばれる。単体でも実行可。
set -u

cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)" || exit 1
LOG="scripts/local-run.log"

{
  echo "=== $(date '+%F %T') ==="

  python3 scripts/pipeline.py --daily
  RESULT=$(cat data/last_result.json 2>/dev/null)
  echo "result: $RESULT"

  # 生成物や state に変化があればコミット（build を通してから）
  if ! git diff --quiet || ! git diff --cached --quiet; then
    if npm run build >/dev/null 2>&1; then
      git add src/content/blog public/images data REVIEW.md 2>/dev/null || true
      git commit -m "chore(content): 自動記事更新 $(date -u +%F)" >/dev/null 2>&1 \
        && echo "ローカルコミット完了（push は手動 / または Cloudflare 連携で自動デプロイ）" \
        || echo "コミットなし"
    else
      echo "npm run build 失敗 → コミットせず終了（生成物は作業ツリーに残っています）"
    fi
  else
    echo "変更なし（ネタ切れ・キー未設定・要レビュー等）"
  fi
} >> "$LOG" 2>&1
