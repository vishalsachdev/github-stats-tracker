# CLAUDE.md — github-stats-tracker

Weekly collection of GitHub traffic stats for all public repos under `vishalsachdev`. GitHub only retains traffic data for 14 days — this repo preserves it permanently.

**Dashboard:** https://vishalsachdev.github.io/github-stats-tracker/
**Repo:** https://github.com/vishalsachdev/github-stats-tracker

---

## Architecture

```
github-stats-tracker/
├── .github/workflows/
│   └── collect-stats.yml    # Weekly cron (Monday 6am UTC / midnight CST)
├── scripts/
│   ├── collect.py           # Fetches traffic + metadata from GitHub API
│   └── build_dashboard.py   # Generates static HTML dashboard
├── data/
│   ├── {repo-name}.json     # Per-repo historical traffic + metadata
│   └── latest_run.json      # Metadata from last collection run
└── docs/
    └── index.html           # Dashboard (GitHub Pages, auto-regenerated)
```

## Commands

```bash
# Collect fresh data (requires GITHUB_TOKEN or GH_TOKEN)
GH_TOKEN=$(gh auth token) python scripts/collect.py

# Preview without writing files
GH_TOKEN=$(gh auth token) python scripts/collect.py --dry-run

# Rebuild dashboard from existing data
python scripts/build_dashboard.py
```

## Key Design Decisions

### Metrics philosophy
- **Primary signals:** Unique visitors and stars — most reliable proxies for human interest
- **Excluded from dashboard:** Clone counts and total (non-unique) views
- **Why:** GitHub traffic is heavily inflated by automated bots that monitor the Events API and clone every public repo scanning for leaked secrets. A repo with 2 page views can show 3,700+ clones in 14 days. The methodology note on the dashboard explains this.

### Data model
Each `data/{repo}.json` stores:
- `stars`, `forks`, `description` — repo metadata (updated each run)
- `views` — daily unique visitor counts, keyed by date (deduplicated)
- `clones` — daily clone counts, keyed by date (still collected for archival, just not displayed)
- `referrers` — traffic sources (merged across runs)
- `paths` — popular pages (merged across runs)

### Automation
- Workflow runs weekly, collects data, rebuilds dashboard, commits, and pushes
- GitHub Pages auto-deploys from `docs/` on push
- `TRAFFIC_TOKEN` secret: PAT with `repo` scope (needed for traffic endpoints on other repos)
- If the token expires, update the secret at: Settings > Secrets > TRAFFIC_TOKEN

## Current Focus

Dashboard is live and collecting. Future improvements:
- Add week-over-week trend indicators
- Historical stars tracking (currently snapshot, not time-series)

## Roadmap

- [x] Centralized traffic collection for all public repos
- [x] Static dashboard on GitHub Pages
- [x] Bot-aware methodology (exclude clones/total views)
- [ ] Week-over-week trend arrows on dashboard
- [ ] Stars time-series (track star count changes over time)
- [ ] Email/Slack digest of weekly changes

## Session Log

| Date | Summary |
|------|---------|
| 2026-02-16 | Initial build: collector, dashboard, GitHub Actions workflow. Security scan of all 98 public repos with gitleaks. Redesigned dashboard to focus on unique visitors + stars after discovering bot inflation in clone data. |
