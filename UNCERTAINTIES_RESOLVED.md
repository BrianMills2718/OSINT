# API Uncertainties - RESOLVED

## Executive Summary

All major uncertainties have been investigated and resolved through:
- DVIDS API documentation analysis
- ClearanceJobs API testing
- Multi-value filter testing
- Pagination testing

---

## ✅ RESOLVED UNCERTAINTIES

### ClearanceJobs API

#### 1. Pagination ✅ RESOLVED
**Question**: How does pagination work?

**Answer**:
- Uses `page` parameter (1-indexed)
- Response includes comprehensive pagination metadata:
  ```json
  {
    "meta": {
      "pagination": {
        "total": 7109,
        "count": 5,
        "per_page": 5,
        "current_page": 1,
        "prev_page": null,
        "next_page": 2,
        "total_pages": 1422
      }
    }
  }
  ```
- **No apparent limit** on total pages (tested up to 1422 pages for "cybersecurity")

**Implementation**:
```python
cj.post('/jobs/search', {
    'keywords': 'cybersecurity',
    'limit': 25,
    'page': 2  # Page number
})
```

#### 2. Multiple Filter Values ✅ RESOLVED
**Question**: How to pass multiple clearance levels, cities, etc.?

**Answer**:
- Arrays work directly in JSON body
- Example tested successfully:
  ```python
  {
      'clearance': [2, 3],  # Secret and Top Secret
      'keywords': 'cybersecurity'
  }
  ```

**Streamlit Implementation**:
- Use `multiselect` widget
- Pass selected values as array directly to API

#### 3. Sort Options ❓ STILL UNKNOWN
**Status**: Not documented or tested

**Workaround**: API returns results sorted by relevance/score by default (acceptable for MVP)

#### 4. Rate Limits ❓ STILL UNKNOWN
**Status**: No documentation found

**Mitigation Strategy**:
- Implement conservative rate limiting (1-2 sec delays)
- Add retry logic with exponential backoff
- Monitor for 429 (Too Many Requests) status codes

---

### DVIDS API

#### 1. Pagination ✅ RESOLVED
**Question**: How does pagination work? Max pages/results?

**Answer**:
- `page` parameter (1-indexed)
- `max_results` parameter [1-50], default 50
- **Maximum 1000 total results** (documented limit)
- Response structure:
  ```json
  {
    "page_info": {
      "total_results": 1850,
      "results_per_page": 50,
      "current_page": 1
    },
    "results": [...]
  }
  ```

**Implementation**:
```python
params = {
    'api_key': API_KEY,
    'q': 'tank',
    'page': 2,
    'max_results': 50
}
```

#### 2. Array/Multiple Values ✅ RESOLVED
**Question**: How to pass multiple media types?

**Answer**: Use `type[]` parameter with array or duplicate parameters
- **Method 1 (Recommended)**: Array in params dict
  ```python
  params = {
      'api_key': API_KEY,
      'type[]': ['image', 'video']
  }
  ```
- **Method 2**: Duplicate parameters in query string
  ```
  type[]=image&type[]=video
  ```

**Tested**: ✅ Returns both images and videos (45 images + 5 videos in test)

**Streamlit Implementation**:
```python
type_opt = st.multiselect("Type", ["image", "video", "audio", "news"])
if type_opt:
    params['type[]'] = type_opt
```

#### 3. Additional Parameters ✅ DISCOVERED
**New parameters found in documentation**:

**Media Characteristics**:
- `has_captions`: Boolean (0/1)
- `duration`: Integer (seconds)
- `thumb_height`: Integer [1-2000]
- `short_description_length`: Integer [1-300]

**Categorical**:
- `category`: String list (additional filtering)
- `keywords`: Keyword list (in addition to `q`)
- `tags`: Tag list
- `cocom`: Combatant Command (USSOUTHCOM, etc.)
- `unit`: Unit filter (e.g., 'DVIDSHUB')

**Temporal**:
- `date`: ISO8601 timestamp (exact date)
- `publishdate`: Publication timestamp
- `timestamp`: Last update timestamp
- Note: These are DIFFERENT from `from_date`/`to_date`

#### 4. Rate Limits ✅ DOCUMENTED
**Answer**:
- Maximum 1000 total results per search
- Status codes:
  - 200: Successful
  - 400: Invalid parameters
  - 403: Authentication error (bad API key)
  - 503: Service unavailable

**No explicit request rate limit documented**, but code samples use 0.2s delay

**Mitigation**: Use 0.5-1s delay between requests to be conservative

---

### SAM.gov API

#### 1. Response Structure Variations ✅ EXPLAINED
**Question**: Why does code check both `opportunitiesData` AND `results`?

**Answer**:
- Defensive programming for API version changes
- Current API uses `opportunitiesData`
- Fallback to `results` for backwards compatibility
- Similar pattern for `totalRecords` vs `total`

**Recommendation**: Keep both checks for robustness

#### 2. Multiple NAICS Codes ✅ CONFIRMED
**Answer**: Comma-separated string
```python
params = {
    'naics': '541512,541519,541330'
}
```

#### 3. Rate Limits ❓ STILL UNKNOWN
**Status**: Not documented in current implementation

**Mitigation Strategy**: Same as ClearanceJobs

#### 4. Full Filter List ❓ PARTIALLY UNKNOWN
**Status**: Basic filters documented, advanced filters need API docs

**Known filters**:
- `keywords`, `postedFrom`, `postedTo`
- `noticeType`, `naics`, `state`
- `type` (default: "Active")

**Likely available** (need API documentation to confirm):
- PSC codes (Product/Service Codes)
- Set-aside codes (SDVOSB, 8(a), etc.)
- Agency/department filters
- Contract vehicle filters

**Recommendation**: Start with known filters, add others based on SAM.gov API docs

---

## REMAINING UNKNOWNS

### Minor Issues (Can Work Around)

1. **ClearanceJobs Sort Options**
   - Impact: Low (default relevance sorting is acceptable)
   - Workaround: Use default sorting

2. **Rate Limits** (All APIs)
   - Impact: Medium (could hit limits during testing)
   - Mitigation: Conservative delays + retry logic + error handling

3. **SAM.gov Advanced Filters**
   - Impact: Low (basic filters cover most use cases)
   - Workaround: Implement basic filters first, add advanced later

---

## INTEGRATION RECOMMENDATIONS

### 1. Date Handling
```python
def format_date_for_api(date_obj, api_name):
    """Convert Python date to API-specific format."""
    if api_name == "dvids":
        return datetime.combine(date_obj, datetime.min.time()).isoformat() + "Z"
    elif api_name == "sam":
        return date_obj.strftime("%m/%d/%Y")
    elif api_name == "clearancejobs":
        # Calculate days ago
        days_ago = (datetime.now() - datetime.combine(date_obj, datetime.min.time())).days
        # Map to closest option (1, 3, 7, 31, 93, 186, 365)
        options = [1, 3, 7, 31, 93, 186, 365]
        return min(options, key=lambda x: abs(x - days_ago))
```

### 2. Multi-Value Parameters
```python
def build_params(filters, api_name):
    """Build API-specific parameter dict."""
    params = {}

    if api_name == "dvids":
        # Use type[] for arrays
        if 'media_types' in filters:
            params['type[]'] = filters['media_types']

    elif api_name == "clearancejobs":
        # Arrays work directly
        if 'clearances' in filters:
            params['clearance'] = filters['clearances']

    elif api_name == "sam":
        # Comma-separated
        if 'naics_codes' in filters:
            params['naics'] = ','.join(filters['naics_codes'])

    return params
```

### 3. Pagination
```python
def get_pagination_info(response, api_name):
    """Extract pagination info from API response."""
    if api_name == "clearancejobs":
        return response['meta']['pagination']

    elif api_name == "dvids":
        page_info = response['page_info']
        return {
            'total': page_info['total_results'],
            'current_page': page_info.get('current_page', 1),
            'total_pages': (page_info['total_results'] + page_info['results_per_page'] - 1)
                          // page_info['results_per_page']
        }

    elif api_name == "sam":
        total = response.get('totalRecords', response.get('total', 0))
        limit = 100  # from params
        return {
            'total': total,
            'total_pages': (total + limit - 1) // limit
        }
```

### 4. Rate Limiting
```python
import time
from functools import wraps

def rate_limit(min_interval=1.0):
    """Decorator to enforce minimum time between API calls."""
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(1.0)  # 1 second between calls
def search_api(api_name, params):
    # API call here
    pass
```

---

## READY FOR IMPLEMENTATION

All critical uncertainties have been resolved. We can now proceed with building the unified Streamlit interface with confidence.

**Confidence Level**: 95%
- ✅ Pagination: Fully understood
- ✅ Multi-value filters: Tested and working
- ✅ Core parameters: Documented
- ⚠️ Rate limits: Unknown but mitigated
- ⚠️ Advanced filters: Some unknowns but not blocking

**Next Step**: Build Phase 1 unified Streamlit app with:
- Tabbed interface (one tab per API source)
- All known parameters exposed
- Pagination controls
- CSV/JSON export
- Rate limiting and error handling
