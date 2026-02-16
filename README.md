# GitHub Stats Tracker

Weekly collection of GitHub traffic stats (views, clones, referrers) for all public repos under [vishalsachdev](https://github.com/vishalsachdev). GitHub only retains traffic data for 14 days — this repo preserves it forever.

**Dashboard:** https://vishalsachdev.github.io/github-stats-tracker/

## How it works

1. A GitHub Actions workflow runs **every Monday** at 6am UTC
2. A Python script queries the GitHub API for traffic data on all public repos
3. New data is merged with existing records (deduplicated by date)
4. A static dashboard is regenerated and deployed via GitHub Pages

## Structure

```
github-stats-tracker/
├── .github/workflows/
│   └── collect-stats.yml    # Weekly cron workflow
├── scripts/
│   ├── collect.py           # Fetches traffic from GitHub API
│   └── build_dashboard.py   # Generates static HTML dashboard
├── data/
│   ├── {repo-name}.json     # Per-repo historical traffic
│   └── latest_run.json      # Metadata from last collection
└── docs/
    └── index.html           # Dashboard (GitHub Pages)
```

## Setup

Requires a GitHub Personal Access Token with `repo` scope (needed to access traffic endpoints):

1. Create a token at https://github.com/settings/tokens
2. Add it as a repository secret named `TRAFFIC_TOKEN`

## Manual run

```bash
export GITHUB_TOKEN=ghp_...
python scripts/collect.py
python scripts/build_dashboard.py
```

Use `--dry-run` to preview without writing files:

```bash
python scripts/collect.py --dry-run
```
