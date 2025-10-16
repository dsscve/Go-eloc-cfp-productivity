#!/usr/bin/env python3
"""
Stage 2 – Measure ELOC (Effective Lines of Code) using CLOC.

Counts code, comment, and blank lines for each repository under 'repos/'.
Requires:
  - 'cloc' CLI installed (e.g. `sudo apt-get install -y cloc`)
Outputs:
  - data/eloc_metrics.csv
"""

import os
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import pandas as pd

DATA_DIR = "data"
REPO_DIR = "repos"
OUTPUT_FILE = os.path.join(DATA_DIR, "eloc_metrics.csv")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 8))

os.makedirs(DATA_DIR, exist_ok=True)

def run_cloc(repo_path):
    """Run cloc on a repo and return Go metrics if available."""
    try:
        result = subprocess.run(
            ["cloc", "--json", "--quiet", repo_path],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)

        if "Go" in data:
            go_data = data["Go"]
            code = go_data.get("code", 0)
            comments = go_data.get("comment", 0)
            blanks = go_data.get("blank", 0)
            total = code + comments + blanks
            return {"code": code, "comments": comments, "blanks": blanks, "total_eloc": total, "error": ""}
        else:
            return {"code": 0, "comments": 0, "blanks": 0, "total_eloc": 0, "error": "no Go files detected"}
    except Exception as e:
        return {"code": 0, "comments": 0, "blanks": 0, "total_eloc": 0, "error": str(e)}

def analyze_repo(repo_folder):
    repo_path = os.path.join(REPO_DIR, repo_folder)
    if not os.path.isdir(repo_path):
        return {"repo": repo_folder, "code": 0, "comments": 0, "blanks": 0, "total_eloc": 0, "error": "not a directory"}
    result = run_cloc(repo_path)
    return {"repo": repo_folder, **result}

def main():
    if not os.path.isdir(REPO_DIR):
        raise RuntimeError(f"❌ '{REPO_DIR}' not found. Make sure Stage 1 cloned repositories.")

    repos = [r for r in os.listdir(REPO_DIR) if os.path.isdir(os.path.join(REPO_DIR, r))]
    if not repos:
        raise RuntimeError("⚠️ No repositories found to analyze.")

    print(f"📊 Measuring ELOC (via cloc) for {len(repos)} repos using {MAX_WORKERS} threads...")
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for res in tqdm(executor.map(analyze_repo, repos), total=len(repos)):
            results.append(res)

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)
    success = len(df[df['error'] == ""])
    failed = len(df) - success
    print(f"✅ ELOC metrics written to {OUTPUT_FILE} ({success} succeeded, {failed} failed)")

if __name__ == "__main__":
    main()
