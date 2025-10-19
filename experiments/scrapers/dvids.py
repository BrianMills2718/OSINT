"""
dvids_search.py
Simple DVIDS Search API client example (Python 3.8+)

Usage:
    python dvids_search.py

Set your API key on the API_KEY variable below.
"""

import requests
import time
from typing import Dict, Any

API_KEY = "key-68f319e8dc377"   # <-- replace with your API key
BASE_URL = "https://api.dvidshub.net"
SEARCH_PATH = "/search"

def search_dvids(q: str = None, page: int = 1, max_results: int = 10, extra_params: Dict[str, Any] = None):
    """
    Perform a search. Returns parsed JSON on success, raises requests.HTTPError on HTTP error.
    - q: text query (full text search against title, description, keywords)
    - page: page number (default 1)
    - max_results: [1-50], default 10
    - extra_params: dict of additional query params (e.g. type='image', country='US', from_date=...)
    """
    url = BASE_URL + SEARCH_PATH
    params = {
        "api_key": API_KEY,
        "page": page,
        "max_results": max_results,
    }
    if q:
        params["q"] = q
    if extra_params:
        params.update(extra_params)

    # Make request
    resp = requests.get(url, params=params, timeout=15, headers={"Accept": "application/json"})
    # Raise for HTTP errors (400/403/503 etc.)
    resp.raise_for_status()
    return resp.json()

def iterate_search(q: str = None, max_results_per_page: int = 25, max_pages: int = 5, **kwargs):
    """
    Generator that yields results across pages (up to max_pages).
    """
    page = 1
    while page <= max_pages:
        data = search_dvids(q=q, page=page, max_results=max_results_per_page, extra_params=kwargs)
        # defensive checks
        if "results" not in data:
            break
        for item in data["results"]:
            yield item
        # page_info.total_results and results_per_page are in the response according to docs
        page_info = data.get("page_info") or {}
        total_results = page_info.get("total_results")
        results_per_page = page_info.get("results_per_page", max_results_per_page)
        # stop if we've reached the last page
        if not total_results or page * results_per_page >= total_results:
            break
        page += 1
        # tiny delay to be nice to API (adjust if you know permitted rate)
        time.sleep(0.2)

if __name__ == "__main__":
    # Example: search for "tank" and only return images
    try:
        print("Searching DVIDS for 'tank' (images)...")
        params = {"type": "image", "prettyprint": 1}   # add/change params as needed
        for i, result in enumerate(iterate_search(q="tank", max_results_per_page=10, max_pages=3, **params), start=1):
            # Example: print a few fields
            print(f"\nResult #{i}")
            print(" id:", result.get("id"))
            print(" title:", result.get("title"))
            print(" type:", result.get("type"))
            print(" date_published:", result.get("date_published") or result.get("publishdate"))
            print(" url:", result.get("url"))
            print(" thumbnail:", result.get("thumbnail"))
            print(" short_description:", (result.get("short_description") or "")[:140])
    except requests.HTTPError as e:
        # The API returns different status codes for invalid params / API key problems
        print("HTTP error:", e)
        if e.response is not None:
            try:
                print("Response body:", e.response.json())
            except Exception:
                print("Response text:", e.response.text)
    except Exception as e:
        print("Error:", e)
