#!/usr/bin/env python3
"""
Stage 3 – Enhanced COSMIC Function Points (CFP) estimation for Go repositories.

Improves CFP detection by:
  - Counting exported functions as entry points
  - Including channel sends/receives
  - Counting goroutine spawns
  - More comprehensive read/write/exit patterns
  - Optional multipliers to better reflect data movement impact

Outputs:
  - data/final_metrics.csv
"""

import os
import re
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_DIR = "repos"
DATA_DIR = "data"
INPUT_FILE = os.path.join(DATA_DIR, "eloc_metrics.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "final_metrics.csv")

# ----------------------------------------------------------
# Enhanced COSMIC Data Movement Patterns for Go
# ----------------------------------------------------------
PATTERNS = {
    "entry": [
        r"\brouter\.(GET|POST|PUT|DELETE|PATCH)",
        r"\bmux\.HandleFunc",
        r"\bapp\.(Get|Post|Put|Delete|Patch)",
        r"\bcobra\.Command",
        r"\bRegister.*Server",
        r"\bhttp\.HandleFunc",
        r"\bgrpc\.NewServer",
        r"\bchi\.NewRouter",
        r"\bfiber\.New",
        r"\bgin\.Default",
        r"\bfunc\s+[A-Z]\w*\(",  # exported functions as entry points
    ],
    "exit": [
        r"\bctx\.JSON",
        r"\bw\.Write",
        r"\bhttp\.ResponseWriter",
        r"\breturn\s+json",
        r"\breturn\s+fmt\.Sprintf",
        r"\btemplate\.Execute",
        r"\brender\.(HTML|JSON|Template)",
        r"\bfmt\.Fprintf",
    ],
    "read": [
        r"\bdb\.(Find|Select|Query|QueryRow|QueryRows|First|Where)",
        r"\bread.*File",
        r"\bios\.Open",
        r"\bjson\.Unmarshal",
        r"\bioutil\.ReadFile",
    ],
    "write": [
        r"\bdb\.(Create|Save|Exec|Update|Insert|SaveChanges)",
        r"\bwrite.*File",
        r"\bios\.Write",
        r"\bjson\.Marshal",
        r"\bioutil\.WriteFile",
    ],
    "channel": [  # treat channel communication as data movement
        r"<-chan",
        r"chan\s*<-",
    ],
    "goroutine": [  # each 'go' spawn counts
        r"\bgo\s+\w+\(",
    ]
}

# Multipliers to adjust CFP impact for specific movements
MULTIPLIERS = {
    "entry": 1,
    "exit": 1,
    "read": 1,
    "write": 1,
    "channel": 1,
    "goroutine": 1,
}

# ----------------------------------------------------------
# Functions
# ----------------------------------------------------------
def detect_movements(repo_path):
    """Scan a Go repository and count COSMIC movement types."""
    counts = {k: 0 for k in PATTERNS}
    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in ["vendor", "third_party", "generated"]):
            continue
        for f in files:
            if not f.endswith(".go") or f.endswith("_test.go"):
                continue
            try:
                with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as src:
                    text = src.read()
                    for move, patterns in PATTERNS.items():
                        for p in patterns:
                            matches = len(re.findall(p, text, re.IGNORECASE))
                            counts[move] += matches
            except Exception:
                continue
    return counts


def process_repo(row):
    """Process one repo: detect CFP movements and compute metrics."""
    repo_name = row["repo"]
    repo_path = os.path.join(REPO_DIR, repo_name)
    if not os.path.exists(repo_path):
        return None

    movements = detect_movements(repo_path)
    total_cfp = sum(movements[k] * MULTIPLIERS.get(k, 1) for k in movements)

    total_eloc = row.get("total_eloc", row.get("total", 0))
    code = row.get("code", 0)

    eloc_per_cfp = round(total_eloc / total_cfp, 2) if total_cfp else 0
    cfp_per_kloc = round(total_cfp / code * 1000, 2) if code else 0

    return {
        "repo": repo_name,
        "code": code,
        "comments": row.get("comments", 0),
        "blanks": row.get("blanks", 0),
        "total_eloc": total_eloc,
        **movements,
        "cfp_total": total_cfp,
        "eloc_per_cfp": eloc_per_cfp,
        "cfp_per_kloc": cfp_per_kloc,
    }


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
def main():
    if not os.path.exists(INPUT_FILE):
        raise RuntimeError(f"❌ Missing input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    results = []

    print(f"🔍 Estimating enhanced COSMIC Function Points for {len(df)} repositories...")

    max_workers = min(32, os.cpu_count() * 2)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_repo, row): idx for idx, row in df.iterrows()}
        for future in tqdm(as_completed(futures), total=len(futures)):
            res = future.result()
            if res:
                results.append(res)

    final_df = pd.DataFrame(results)
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Enhanced COSMIC Function Points written to {OUTPUT_FILE}")
    print(f"📊 Includes metrics: cfp_total, eloc_per_cfp, cfp_per_kloc")


if __name__ == "__main__":
    main()
