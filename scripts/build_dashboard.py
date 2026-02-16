#!/usr/bin/env python3
"""Build a static HTML dashboard from collected traffic data.

Reads per-repo JSON files from data/ and generates docs/index.html
for GitHub Pages hosting.
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
    """Compute total views and clones from daily data."""
    total_views = sum(d["count"] for d in repo.get("views", {}).values())
    unique_views = sum(d["uniques"] for d in repo.get("views", {}).values())
    total_clones = sum(d["count"] for d in repo.get("clones", {}).values())
    unique_clones = sum(d["uniques"] for d in repo.get("clones", {}).values())
    days_tracked = len(repo.get("views", {}))
    return {
        "name": repo.get("repo", "unknown"),
        "total_views": total_views,
        "unique_views": unique_views,
        "total_clones": total_clones,
        "unique_clones": unique_clones,
        "days_tracked": days_tracked,
        "last_updated": repo.get("last_updated", ""),
        "referrers": repo.get("referrers", []),
        "paths": repo.get("paths", []),
        "views": repo.get("views", {}),
        "clones": repo.get("clones", {}),
    }


def generate_html(repos: list[dict]) -> str:
    """Generate the dashboard HTML."""
    summaries = [compute_totals(r) for r in repos]
    summaries.sort(key=lambda x: x["total_views"], reverse=True)

    # Aggregate stats
    grand_views = sum(s["total_views"] for s in summaries)
    grand_uniques = sum(s["unique_views"] for s in summaries)
    grand_clones = sum(s["total_clones"] for s in summaries)

    # Load run metadata
    run_file = DATA_DIR / "latest_run.json"
    last_run = ""
    if run_file.exists():
        with open(run_file) as f:
            meta = json.load(f)
            last_run = meta.get("collected_at", "")[:10]

    # Build repo rows
    repo_rows = ""
    for s in summaries:
        repo_rows += f"""
        <tr class="repo-row" data-repo="{s['name']}">
          <td><a href="https://github.com/vishalsachdev/{s['name']}" target="_blank">{s['name']}</a></td>
          <td class="num">{s['total_views']:,}</td>
          <td class="num">{s['unique_views']:,}</td>
          <td class="num">{s['total_clones']:,}</td>
          <td class="num">{s['unique_clones']:,}</td>
          <td class="num">{s['days_tracked']}</td>
        </tr>"""

    # Prepare chart data (top 10 repos by views, daily timeseries)
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
        values = [s["views"].get(d, {}).get("count", 0) for d in all_dates]
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
    .subtitle {{ color: var(--text-dim); margin-bottom: 2rem; font-size: 0.9rem; }}
    .cards {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem; margin-bottom: 2rem;
    }}
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 1.25rem;
    }}
    .card .label {{ color: var(--text-dim); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card .value {{ font-size: 1.75rem; font-weight: 600; margin-top: 0.25rem; }}
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
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
    @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    footer {{ color: var(--text-dim); font-size: 0.8rem; margin-top: 3rem; text-align: center; }}
  </style>
</head>
<body>
  <h1>GitHub Traffic Dashboard</h1>
  <p class="subtitle">vishalsachdev &middot; {len(summaries)} repos tracked &middot; Last collection: {last_run or now}</p>

  <div class="cards">
    <div class="card">
      <div class="label">Total Views</div>
      <div class="value">{grand_views:,}</div>
    </div>
    <div class="card">
      <div class="label">Unique Visitors</div>
      <div class="value">{grand_uniques:,}</div>
    </div>
    <div class="card">
      <div class="label">Total Clones</div>
      <div class="value">{grand_clones:,}</div>
    </div>
    <div class="card">
      <div class="label">Repos Tracked</div>
      <div class="value">{len(summaries)}</div>
    </div>
  </div>

  <div class="chart-container">
    <h2>Daily Views — Top 10 Repos</h2>
    <canvas id="viewsChart" height="100"></canvas>
  </div>

  <div class="two-col">
    <div class="section">
      <h2>Top Referrers</h2>
      <table>
        <thead><tr><th>Source</th><th class="num">Views</th></tr></thead>
        <tbody>{referrer_rows if referrer_rows else '<tr><td colspan="2">No data yet</td></tr>'}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Collection Info</h2>
      <table>
        <tbody>
          <tr><td>Last run</td><td>{last_run or 'Not yet'}</td></tr>
          <tr><td>Schedule</td><td>Every Monday 6am UTC</td></tr>
          <tr><td>Data retention</td><td>Forever (GitHub keeps 14 days)</td></tr>
          <tr><td>Dashboard built</td><td>{now}</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>All Repos</h2>
    <table>
      <thead>
        <tr>
          <th>Repository</th>
          <th class="num">Views</th>
          <th class="num">Unique</th>
          <th class="num">Clones</th>
          <th class="num">Unique</th>
          <th class="num">Days</th>
        </tr>
      </thead>
      <tbody>{repo_rows if repo_rows else '<tr><td colspan="6">No data yet — run the collector first</td></tr>'}</tbody>
    </table>
  </div>

  <footer>
    Data collected weekly via GitHub Actions. Traffic stats are preserved forever since GitHub only keeps 14 days.
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
