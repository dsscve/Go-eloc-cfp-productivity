#!/usr/bin/env python3
"""
Stage 1 – Fetch top Go repositories from GitHub and clone them locally.
Outputs:
  - data/repos.json
  - data/repos.txt
  - repos/ directory (with cloned repos)
"""

import os
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

DATA_DIR = "data"
REPO_DIR = "repos"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPO_DIR, exist_ok=True)

GITHUB_API = "https://api.github.com/search/repositories"
HEADERS = {"Accept": "application/vnd.github+json"}

def fetch_go_repos(max_repos=400):
    """Fetch top Go repositories by stars."""
    repos = []
    page = 1
    while len(repos) < max_repos:
        params = {"q": "language:Go", "sort": "stars", "order": "desc", "per_page": 100, "page": page}
        r = requests.get(GITHUB_API, headers=HEADERS, params=params)
        r.raise_for_status()
        batch = r.json().get("items", [])
        if not batch:
            break
        for repo in batch:
            repos.append({
                "full_name": repo["full_name"],
                "clone_url": repo["clone_url"],
                "language": repo["language"],
                "stargazers_count": repo["stargazers_count"],
            })
        page += 1
    return repos[:max_repos]

def clone_repo(repo):
    name = repo["full_name"].replace("/", "_")
    dest = os.path.join(REPO_DIR, name)
    if os.path.exists(dest):
        return f"✅ Skipped {repo['full_name']} (already cloned)"
    try:
        subprocess.run(["git", "clone", "--depth", "1", repo["clone_url"], dest], check=True, capture_output=True)
        return f"✅ Cloned {repo['full_name']}"
    except subprocess.CalledProcessError as e:
        return f"❌ Failed to clone {repo['full_name']}: {e}"

def main():
    print("🔍 Fetching top Go repositories...")
    repos = fetch_go_repos()
    with open(os.path.join(DATA_DIR, "repos.json"), "w") as f:
        json.dump(repos, f, indent=2)
    with open(os.path.join(DATA_DIR, "repos.txt"), "w") as f:
        f.write("\n".join([r["full_name"] for r in repos]))
    print(f"🎯 Saved {len(repos)} repositories to data/")

    print(f"🚀 Cloning {len(repos)} repositories in parallel...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        for msg in tqdm(executor.map(clone_repo, repos), total=len(repos)):
            print(msg)
    print("✅ Stage 1 complete.")

if __name__ == "__main__":
    main()
