"""USAJobs search execution for AI Research - temporary helper until integrated into ai_research.py"""

import requests
from datetime import datetime, timedelta


def execute_usajobs_search(query_params, api_key, limit=10):
    """Execute USAJobs search based on AI-generated parameters."""
    from core.api_request_tracker import log_request

    start_time = datetime.now()
    url = "https://data.usajobs.gov/api/search"

    try:
        if not api_key:
            return {
                "success": False,
                "error": "USAJobs API key required",
                "source": "USAJobs"
            }

        # Build headers (USAJobs requires specific format)
        headers = {
            "User-Agent": api_key,  # USAJobs uses User-Agent for auth
            "Authorization-Key": api_key
        }

        # Build params
        params = {
            "Keyword": query_params.get("keywords", ""),
            "ResultsPerPage": min(limit, 500)  # USAJobs max is 500
        }

        # Add date filters if specified
        date_from = query_params.get("date_from", "")
        date_to = query_params.get("date_to", "")

        if date_from and date_to:
            params["DatePosted"] = f"{date_from} to {date_to}"

        # Add pay grade if specified
        pay_grade = query_params.get("pay_grade_low", "")
        if pay_grade and pay_grade.strip():
            params["PayGradeLow"] = pay_grade

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log request
        log_request("USAJobs", url, response.status_code, response_time_ms, None, params)

        actual_url = response.url
        response.raise_for_status()
        data = response.json()

        # USAJobs returns SearchResult -> SearchResultItems
        search_result = data.get('SearchResult', {})
        jobs = search_result.get('SearchResultItems', [])
        total = search_result.get('SearchResultCount', 0)

        return {
            "success": True,
            "total": total,
            "results": jobs[:limit],
            "source": "USAJobs",
            "debug_query": {
                "endpoint": "GET " + url,
                "params": params,
                "actual_url": actual_url
            }
        }

    except Exception as e:
        # Log failed request
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(e, 'response', None) and e.response.status_code or 0
        log_request("USAJobs", url, status_code, response_time_ms, str(e), params if 'params' in locals() else query_params)

        return {
            "success": False,
            "error": str(e),
            "source": "USAJobs",
            "debug_query": {
                "endpoint": "GET https://data.usajobs.gov/api/search",
                "attempted_params": params if 'params' in locals() else query_params,
                "actual_url": response.url if 'response' in locals() else "N/A"
            }
        }
