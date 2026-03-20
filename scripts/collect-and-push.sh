#!/bin/bash
# Collect GitHub traffic stats and push to repo
# Runs via launchd daily at 9am CST

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

REPO_DIR="/Users/vishal/code/github-stats-tracker"
LOG="/tmp/github-stats.log"

echo "=== $(date) ===" >> "$LOG"

cd "$REPO_DIR" || { echo "FAIL: can't cd to $REPO_DIR" >> "$LOG"; exit 1; }

# Use gh CLI for token
export GH_TOKEN=$(gh auth token 2>> "$LOG")
if [ -z "$GH_TOKEN" ]; then
  echo "FAIL: gh auth token returned empty" >> "$LOG"
  exit 1
fi

/opt/homebrew/bin/python3 scripts/collect.py >> "$LOG" 2>&1 || { echo "FAIL: collect.py" >> "$LOG"; exit 1; }
/opt/homebrew/bin/python3 scripts/build_dashboard.py >> "$LOG" 2>&1 || { echo "FAIL: build_dashboard.py" >> "$LOG"; exit 1; }

git add data/ docs/ >> "$LOG" 2>&1
if git diff --staged --quiet; then
  echo "No changes to commit" >> "$LOG"
else
  git commit -m "data: daily traffic snapshot $(date +%Y-%m-%d)" >> "$LOG" 2>&1
  git push >> "$LOG" 2>&1
fi

echo "=== done ===" >> "$LOG"
