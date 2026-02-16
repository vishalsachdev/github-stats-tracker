#!/usr/bin/env python3
"""Collect GitHub traffic stats for all public repos under a user.

GitHub only retains traffic data for 14 days, so this runs weekly
to capture it before it expires. Data is deduplicated by date.

Usage:
    python scripts/collect.py                    # uses GITHUB_OWNER env or defaults
    python scripts/collect.py --owner myuser
    python scripts/collect.py --dry-run          # preview without writing
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GITHUB_API = "https://api.github.com"


def gh_request(path: str, token: str) -> dict | list | None:
    """Make an authenticated GitHub API request."""
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "github-stats-tracker")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403 and "rate limit" in e.read().decode().lower():
            print(f"  Rate limited on {path}", file=sys.stderr)
        elif e.code == 404:
            # Traffic endpoints return 404 for repos with zero traffic
            return None
        else:
            print(f"  HTTP {e.code} on {path}", file=sys.stderr)
        return None


def get_public_repos(owner: str, token: str) -> list[str]:
    """Get all public repo names for a user."""
    repos = []
    page = 1
    while True:
        data = gh_request(
            f"/users/{owner}/repos?type=public&per_page=100&page={page}", token
        )
        if not data:
            break
        repos.extend(r["name"] for r in data if not r.get("fork"))
        if len(data) < 100:
            break
        page += 1
    return sorted(repos)


def collect_repo_traffic(owner: str, repo: str, token: str) -> dict:
    """Collect all traffic data for a single repo."""
    views = gh_request(f"/repos/{owner}/{repo}/traffic/views", token)
    clones = gh_request(f"/repos/{owner}/{repo}/traffic/clones", token)
    referrers = gh_request(f"/repos/{owner}/{repo}/traffic/popular/referrers", token)
    paths = gh_request(f"/repos/{owner}/{repo}/traffic/popular/paths", token)

    return {
        "views": views or {"count": 0, "uniques": 0, "views": []},
        "clones": clones or {"count": 0, "uniques": 0, "clones": []},
        "referrers": referrers or [],
        "paths": paths or [],
    }


def load_existing_data(filepath: Path) -> dict:
    """Load existing repo data file, or return empty structure."""
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {"views": {}, "clones": {}, "referrers": [], "paths": []}


def merge_daily_data(existing: dict, key: str, new_entries: list) -> dict:
    """Merge new daily entries into existing data, deduplicating by date."""
    date_map = dict(existing.get(key, {}))
    for entry in new_entries:
        ts = entry["timestamp"][:10]  # YYYY-MM-DD
        date_map[ts] = {
            "count": entry["count"],
            "uniques": entry["uniques"],
        }
    return dict(sorted(date_map.items()))


def merge_referrers(existing: list, new: list) -> list:
    """Merge referrer data, keeping latest counts."""
    ref_map = {r["referrer"]: r for r in existing}
    for r in new:
        ref_map[r["referrer"]] = r
    return sorted(ref_map.values(), key=lambda x: x.get("count", 0), reverse=True)


def merge_paths(existing: list, new: list) -> list:
    """Merge popular paths, keeping latest counts."""
    path_map = {p["path"]: p for p in existing}
    for p in new:
        path_map[p["path"]] = p
    return sorted(path_map.values(), key=lambda x: x.get("count", 0), reverse=True)


def save_repo_data(filepath: Path, data: dict):
    """Save repo data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def collect_all(owner: str, token: str, dry_run: bool = False):
    """Main collection loop."""
    print(f"Collecting traffic stats for {owner}...")
    repos = get_public_repos(owner, token)
    print(f"Found {len(repos)} public repos (excluding forks)")

    collected_at = datetime.now(timezone.utc).isoformat()
    summary = {"collected_at": collected_at, "repos_checked": len(repos), "repos_with_traffic": 0}
    repos_with_data = []

    for i, repo in enumerate(repos, 1):
        traffic = collect_repo_traffic(owner, repo, token)

        has_views = len(traffic["views"].get("views", [])) > 0
        has_clones = len(traffic["clones"].get("clones", [])) > 0

        if has_views or has_clones:
            summary["repos_with_traffic"] += 1
            repos_with_data.append(repo)
            print(f"  [{i}/{len(repos)}] {repo} - views: {traffic['views'].get('count', 0)}, clones: {traffic['clones'].get('count', 0)}")

            if not dry_run:
                filepath = DATA_DIR / f"{repo}.json"
                existing = load_existing_data(filepath)

                merged = {
                    "repo": repo,
                    "owner": owner,
                    "last_updated": collected_at,
                    "views": merge_daily_data(existing, "views", traffic["views"].get("views", [])),
                    "clones": merge_daily_data(existing, "clones", traffic["clones"].get("clones", [])),
                    "referrers": merge_referrers(existing.get("referrers", []), traffic.get("referrers", [])),
                    "paths": merge_paths(existing.get("paths", []), traffic.get("paths", [])),
                }
                save_repo_data(filepath, merged)
        else:
            print(f"  [{i}/{len(repos)}] {repo} - no traffic")

    # Save collection summary
    if not dry_run:
        summary["repos_with_traffic_names"] = repos_with_data
        summary_path = DATA_DIR / "latest_run.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")

    print(f"\nDone. {summary['repos_with_traffic']}/{len(repos)} repos had traffic.")
    if dry_run:
        print("(dry run - no files written)")


def main():
    parser = argparse.ArgumentParser(description="Collect GitHub traffic stats")
    parser.add_argument("--owner", default=os.environ.get("GITHUB_OWNER", "vishalsachdev"))
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Error: Set GITHUB_TOKEN or GH_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)

    collect_all(args.owner, token, args.dry_run)


if __name__ == "__main__":
    main()
