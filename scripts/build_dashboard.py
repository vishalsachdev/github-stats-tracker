#!/usr/bin/env python3
"""Build a static HTML dashboard from collected traffic data.

Reads per-repo JSON files from data/ and generates docs/index.html
for GitHub Pages hosting. Focuses on unique views and stars as
primary signals — clones and total views are excluded because
GitHub traffic data is heavily inflated by automated bot scrapers.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def load_all_repos() -> list[dict]:
    """Load all repo data files."""
    repos = []
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name == "latest_run.json":
            continue
        with open(f) as fh:
            data = json.load(fh)
            repos.append(data)
    return repos


def compute_totals(repo: dict) -> dict:
    """Compute totals from daily data."""
    unique_views = sum(d["uniques"] for d in repo.get("views", {}).values())
    days_tracked = len(repo.get("views", {}))
    return {
        "name": repo.get("repo", "unknown"),
        "description": repo.get("description", ""),
        "stars": repo.get("stars", 0),
        "forks": repo.get("forks", 0),
        "unique_views": unique_views,
        "days_tracked": days_tracked,
        "last_updated": repo.get("last_updated", ""),
        "referrers": repo.get("referrers", []),
        "paths": repo.get("paths", []),
        "views": repo.get("views", {}),
    }


def generate_html(repos: list[dict]) -> str:
    """Generate the dashboard HTML."""
    summaries = [compute_totals(r) for r in repos]
    summaries.sort(key=lambda x: x["unique_views"], reverse=True)

    # Aggregate stats
    grand_uniques = sum(s["unique_views"] for s in summaries)
    grand_stars = sum(s["stars"] for s in summaries)
    grand_forks = sum(s["forks"] for s in summaries)
    repos_with_views = sum(1 for s in summaries if s["unique_views"] > 0)

    # Load run metadata
    run_file = DATA_DIR / "latest_run.json"
    last_run = ""
    if run_file.exists():
        with open(run_file) as f:
            meta = json.load(f)
            last_run = meta.get("collected_at", "")[:10]

    # Build repo rows — sorted by unique views
    repo_rows = ""
    for s in summaries:
        star_badge = f'<span class="star-badge">{s["stars"]}</span>' if s["stars"] > 0 else '<span class="star-zero">0</span>'
        repo_rows += f"""
        <tr class="repo-row">
          <td>
            <a href="https://github.com/vishalsachdev/{s['name']}" target="_blank">{s['name']}</a>
            {f'<div class="repo-desc">{s["description"][:80]}</div>' if s['description'] else ''}
          </td>
          <td class="num">{s['unique_views']:,}</td>
          <td class="num">{star_badge}</td>
          <td class="num">{s['forks']}</td>
          <td class="num">{s['days_tracked']}</td>
        </tr>"""

    # Prepare chart data — unique visitors for top 10 repos
    chart_repos = summaries[:10]
    all_dates = set()
    for s in chart_repos:
        all_dates.update(s["views"].keys())
    all_dates = sorted(all_dates)

    chart_labels = json.dumps(all_dates)
    datasets = []
    colors = [
        "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
        "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
    ]
    for i, s in enumerate(chart_repos):
        values = [s["views"].get(d, {}).get("uniques", 0) for d in all_dates]
        datasets.append({
            "label": s["name"],
            "data": values,
            "borderColor": colors[i % len(colors)],
            "fill": False,
            "tension": 0.3,
        })
    chart_datasets = json.dumps(datasets)

    # Top referrers across all repos
    all_referrers: dict[str, int] = {}
    for s in summaries:
        for ref in s["referrers"]:
            name = ref.get("referrer", "unknown")
            all_referrers[name] = all_referrers.get(name, 0) + ref.get("count", 0)
    top_referrers = sorted(all_referrers.items(), key=lambda x: x[1], reverse=True)[:10]
    referrer_rows = ""
    for name, count in top_referrers:
        referrer_rows += f"<tr><td>{name}</td><td class='num'>{count:,}</td></tr>\n"

    # Top repos by stars (separate ranking)
    by_stars = sorted(summaries, key=lambda x: x["stars"], reverse=True)[:10]
    star_rows = ""
    for s in by_stars:
        if s["stars"] == 0:
            break
        star_rows += f"""<tr>
          <td><a href="https://github.com/vishalsachdev/{s['name']}" target="_blank">{s['name']}</a></td>
          <td class="num">{s['stars']}</td>
          <td class="num">{s['forks']}</td>
        </tr>"""

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub Traffic Dashboard — vishalsachdev</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <style>
    :root {{
      --bg: #0d1117; --surface: #161b22; --border: #30363d;
      --text: #e6edf3; --text-dim: #8b949e; --accent: #58a6ff;
      --green: #3fb950; --red: #f85149; --yellow: #d29922;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: var(--bg); color: var(--text); line-height: 1.5;
      padding: 2rem; max-width: 1200px; margin: 0 auto;
    }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: var(--text-dim); margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .methodology {{
      background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--yellow);
      border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 2rem; font-size: 0.85rem;
      color: var(--text-dim); line-height: 1.6;
    }}
    .methodology strong {{ color: var(--text); }}
    .cards {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem; margin-bottom: 2rem;
    }}
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 1.25rem;
    }}
    .card.primary {{ border-color: var(--accent); }}
    .card .label {{ color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card .value {{ font-size: 1.75rem; font-weight: 600; margin-top: 0.25rem; }}
    .card.primary .value {{ color: var(--accent); }}
    .chart-container {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem;
    }}
    .chart-container h2 {{ font-size: 1rem; margin-bottom: 1rem; }}
    .section {{ margin-bottom: 2rem; }}
    .section h2 {{ font-size: 1rem; margin-bottom: 0.75rem; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.875rem; }}
    th {{ color: var(--text-dim); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    td a {{ color: var(--accent); text-decoration: none; }}
    td a:hover {{ text-decoration: underline; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .repo-row:hover {{ background: rgba(88, 166, 255, 0.05); }}
    .repo-desc {{ color: var(--text-dim); font-size: 0.75rem; margin-top: 0.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 350px; }}
    .star-badge {{ color: var(--yellow); font-weight: 600; }}
    .star-zero {{ color: var(--text-dim); }}
    .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
    @media (max-width: 900px) {{ .three-col {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    footer {{ color: var(--text-dim); font-size: 0.8rem; margin-top: 3rem; text-align: center; }}
  </style>
</head>
<body>
  <h1>GitHub Traffic Dashboard</h1>
  <p class="subtitle">vishalsachdev &middot; {len(summaries)} repos tracked &middot; Last collection: {last_run or now}</p>

  <div class="methodology">
    <strong>Methodology note:</strong> This dashboard intentionally excludes clone counts and total (non-unique) views.
    GitHub traffic data is heavily inflated by automated bots that monitor the Events API and clone every public
    repo looking for leaked secrets. For example, a repo with 2 page views can show 3,700+ clones in 14 days.
    <strong>Unique visitors</strong> and <strong>stars</strong> are the most reliable proxies for genuine human interest.
  </div>

  <div class="cards">
    <div class="card primary">
      <div class="label">Unique Visitors</div>
      <div class="value">{grand_uniques:,}</div>
    </div>
    <div class="card">
      <div class="label">Total Stars</div>
      <div class="value">{grand_stars:,}</div>
    </div>
    <div class="card">
      <div class="label">Total Forks</div>
      <div class="value">{grand_forks:,}</div>
    </div>
    <div class="card">
      <div class="label">Repos with Visitors</div>
      <div class="value">{repos_with_views}</div>
    </div>
  </div>

  <div class="chart-container">
    <h2>Daily Unique Visitors — Top 10 Repos</h2>
    <canvas id="viewsChart" height="100"></canvas>
  </div>

  <div class="two-col">
    <div class="section">
      <h2>Top Repos by Stars</h2>
      <table>
        <thead><tr><th>Repository</th><th class="num">Stars</th><th class="num">Forks</th></tr></thead>
        <tbody>{star_rows if star_rows else '<tr><td colspan="3">No stars yet</td></tr>'}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Top Referrers</h2>
      <table>
        <thead><tr><th>Source</th><th class="num">Views</th></tr></thead>
        <tbody>{referrer_rows if referrer_rows else '<tr><td colspan="2">No data yet</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>All Repos — Sorted by Unique Visitors</h2>
    <table>
      <thead>
        <tr>
          <th>Repository</th>
          <th class="num">Unique Visitors</th>
          <th class="num">Stars</th>
          <th class="num">Forks</th>
          <th class="num">Days Tracked</th>
        </tr>
      </thead>
      <tbody>{repo_rows if repo_rows else '<tr><td colspan="5">No data yet — run the collector first</td></tr>'}</tbody>
    </table>
  </div>

  <footer>
    Data collected weekly via GitHub Actions. GitHub only retains traffic data for 14 days — this dashboard preserves it permanently.
    <br>Clones and total views excluded due to bot inflation. See methodology note above.
  </footer>

  <script>
    const ctx = document.getElementById('viewsChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: {chart_labels},
        datasets: {chart_datasets}
      }},
      options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ color: '#8b949e', boxWidth: 12, padding: 16 }} }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#8b949e', maxTicksLimit: 12 }}, grid: {{ color: '#21262d' }} }},
          y: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }}, beginAtZero: true }}
        }}
      }}
    }});
  </script>
</body>
</html>"""


def main():
    repos = load_all_repos()
    html = generate_html(repos)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out = DOCS_DIR / "index.html"
    out.write_text(html)
    print(f"Dashboard written to {out} ({len(repos)} repos)")


if __name__ == "__main__":
    main()
