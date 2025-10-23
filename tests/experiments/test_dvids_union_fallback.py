#!/usr/bin/env python3
"""
Experiment: Test DVIDS union fallback strategy without touching main code.

Given a composite OR query, run:
  1) Single-call query as-is
  2) Per-term queries split on " OR " and union results by "id"
Also optionally test with and without type[] media filters.

Requires DVIDS_API_KEY in environment, otherwise uses demo key
  (key-68f319e8dc377) which may be rate limited.

Usage:
  python tests/experiments/test_dvids_union_fallback.py "SIGINT OR signals intelligence OR ELINT OR COMINT" --types image video news
"""

import os
import sys
import argparse
import requests
from typing import List, Dict, Set

API = "https://api.dvidshub.net/search"


def fetch(q: str, api_key: str, types: List[str] = None, max_results: int = 25) -> Dict:
    params = {
        "api_key": api_key,
        "page": 1,
        "max_results": max_results,
        "q": q,
    }
    if types:
        params["type[]"] = types
    r = requests.get(API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def union_ids(result_sets: List[Dict]) -> Dict:
    seen: Set[str] = set()
    merged = []
    total = 0
    for data in result_sets:
        results = data.get("results", [])
        total += len(results)
        for item in results:
            iid = str(item.get("id") or item.get("url") or id(item))
            if iid not in seen:
                seen.add(iid)
                merged.append(item)
    return {"total": len(merged), "merged": merged, "raw_total": total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Composite OR query string")
    ap.add_argument("--types", nargs="*", help="type[] values: image video news", default=None)
    ap.add_argument("--max", type=int, default=25)
    args = ap.parse_args()

    api_key = os.getenv("DVIDS_API_KEY", "key-68f319e8dc377")
    q = args.query
    types = args.types

    print(f"API key: {'env' if os.getenv('DVIDS_API_KEY') else 'demo'} | types: {types or 'None'}")
    print(f"Query: {q}")

    try:
        single = fetch(q, api_key, types, args.max)
        total_single = single.get("page_info", {}).get("total_results", len(single.get("results", [])))
        print(f"Single-call total: {total_single}")
    except Exception as e:
        print(f"Single-call error: {e}")
        single = {"results": []}
        total_single = 0

    # Split on OR (literal) and trim
    terms = [t.strip() for t in q.split(" OR ") if t.strip()]
    per_term = []
    for t in terms:
        try:
            data = fetch(t, api_key, types, args.max)
            count = data.get("page_info", {}).get("total_results", len(data.get("results", [])))
            print(f"Term '{t}': {count}")
            per_term.append(data)
        except Exception as e:
            print(f"  Error for term '{t}': {e}")

    merged = union_ids(per_term)
    print(f"Union merged unique: {merged['total']} (raw sum: {merged['raw_total']})")

    # If single-call is zero but union > 0, demonstrate fallback benefit
    if total_single == 0 and merged["total"] > 0:
        print("Fallback helps: OR query returned 0, union per-term produced results ✅")
    else:
        print("Fallback not required or no benefit in this case.")


if __name__ == "__main__":
    main()

