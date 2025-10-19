# Multi-Source Search Integration Analysis

## Overview
Integration of 3 scrapers into a unified Streamlit interface:
1. **ClearanceJobs** - Job search API
2. **DVIDS** - Defense Visual Information Distribution Service (military media)
3. **SAM.gov** - Government contract opportunities

---

## 1. ClearanceJobs API

### Location
- `/home/brian/sam_gov/ClearanceJobs/`
- Main library: `ClearanceJobs/__init__.py`
- Search script: `search_cybersecurity_jobs.py`

### Status
✅ **Working** - No authentication required for job search

### API Details
- **Base URL**: `https://api.clearancejobs.com/api/v1`
- **Endpoint**: `/jobs/search` (POST)
- **Auth**: None required for jobs (resumes require login)

### Parameters
**Core:**
- `keywords` (str) - Search query
- `limit` (int) - Results per page (default: 25)

**Filters:**
- `career_level` (str) - Experience level
  - `b` = <2 yrs exp
  - `c` = 2+ yrs exp
  - `d` = 5+ yrs exp
  - `e` = 10+ yrs exp
  - `f` = Mgr/Director
  - `h` = President, CEO

- `city` (str) - City name (e.g., "Washington, DC")
- `loc` (int) - State ID (1-55)
- `loc_country` (int) - Country ID (1000 = US)

- `clearance` (int) - Security clearance level
  - `1` = Confidential
  - `2` = Secret
  - `3` = Top Secret
  - `4` = Top Secret/SCI
  - `5` = Intel Agency (NSA, CIA, FBI, etc)
  - `6` = Unspecified
  - `7` = DoE Q or L
  - `8` = Public Trust
  - `9` = Dept of Homeland Security

- `polygraph` (str) - Polygraph requirement
  - `s` = Unspecified
  - `n` = None
  - `p` = Polygraph
  - `i` = CI Polygraph
  - `l` = Full Scope Polygraph

- `type` (str) - Job type
  - `e` = Employee
  - `c` = Contractor/Consultant
  - `s` = Seasonal
  - `i` = Intern/Entry Level
  - `a` = Any Job Type

- `remote` (int) - Remote work
  - `1` = Remote

- `received` (int) - Posted within days
  - `1` = Today
  - `3` = Last 3 days
  - `7` = Last 7 days
  - `31` = Within a month
  - `93` = Within 3 months
  - `186` = Within 6 months
  - `365` = Within 12 months

- `ind` (str) - Industry/Job Category (NAICS-like)
- `co_name` (str) - Company name

### Response Structure
```json
{
  "data": [
    {
      "id": 8597728,
      "job_name": "...",
      "company_name": "...",
      "job_url": "...",
      "locations": [{"location": "...", "type": "..."}],
      "clearance": "...",
      "polygraph": "...",
      "career_level": "...",
      "preview_text": "...",
      "created_at": "..."
    }
  ],
  "meta": {
    "navigation": { ... }
  }
}
```

### ⚠️ UNCERTAINTIES
1. **Pagination**: Not clear how pagination works (page parameter?)
2. **Rate limits**: Unknown
3. **Sort options**: Not documented in current implementation
4. **Multiple filter values**: How to pass multiple cities, clearances, etc?
5. **Filter ID vs value**: Some filters use ID (loc=1), others use value (city="Alexandria, VA")

---

## 2. DVIDS API

### Location
- `/home/brian/sam_gov/dvids.py`
- `/home/brian/sam_gov/dvids_streamlit.py`

### Status
✅ **Working** - Requires API key (already have: `key-68f319e8dc377`)

### API Details
- **Base URL**: `https://api.dvidshub.net`
- **Endpoint**: `/search` (GET)
- **Auth**: API key required

### Parameters
**Core:**
- `api_key` (str) - Required
- `q` (str) - Text query (searches title, description, keywords)
- `page` (int) - Page number (default: 1)
- `max_results` (int) - Results per page [1-50] (default: 10)

**Filters:**
- `type[]` (array) - Media type (can be multiple)
  - `image`
  - `video`
  - `audio`
  - `news`
  - `graphics`
  - `publication_issue`
  - `webcast`

- `branch` (str) - Military branch
  - `Army`, `Navy`, `Air Force`, `Marines`, `Coast Guard`, `Joint`, `Civilian`

- `country` (str) - Country name (e.g., "United States", "Germany")
- `state` (str) - State name
- `aspect_ratio` (str) - Image aspect ratio
  - `landscape`, `portrait`, `square`, `16:9`, `4:3`

- `from_publishdate` (ISO8601) - Start date (e.g., "2024-01-01T00:00:00Z")
- `to_publishdate` (ISO8601) - End date

- `sort` (str) - Sort field
  - `date`, `publishdate`, `timestamp`, `score`, `rating`

- `sortdir` (str) - Sort direction
  - `asc`, `desc`

- `has_image` (int) - Filter for items with images (0 or 1)
- `hd` (int) - HD video only (0 or 1)
- `prettyprint` (int) - Pretty print JSON (0 or 1)

### Response Structure
```json
{
  "results": [
    {
      "id": "...",
      "title": "...",
      "type": "...",
      "url": "...",
      "thumbnail": "...",
      "date_published": "...",
      "publishdate": "...",
      "credit": "...",
      "short_description": "..."
    }
  ],
  "page_info": {
    "total_results": 100,
    "results_per_page": 10,
    "current_page": 1
  }
}
```

### ⚠️ UNCERTAINTIES
1. **Rate limits**: Unknown, currently using 0.2s delay between pages
2. **Max pages**: Not documented
3. **type[] array syntax**: How does Streamlit multiselect translate to API?
4. **Date format flexibility**: Are other date formats accepted?
5. **Full list of valid branch values**: Are there others beyond the 7 listed?

---

## 3. SAM.gov API

### Location
- `/home/brian/sam_gov/sam_search_app.py`

### Status
✅ **Working** - Requires API key (needs to be provided)

### API Details
- **Base URL**: `https://api.sam.gov`
- **Endpoint**: `/opportunities/v2/search` (GET)
- **Auth**: API key required

### Parameters
**Core:**
- `api_key` (str) - Required
- `keywords` (str) - Search query
- `limit` (int) - Results per page [1-1000] (default: 100)
- `offset` (int) - Pagination offset
- `type` (str) - Opportunity type (default: "Active")

**Filters:**
- `postedFrom` (str) - Start date (MM/DD/YYYY format)
- `postedTo` (str) - End date (MM/DD/YYYY format)

- `noticeType` (str) - Notice type
  - `Solicitation`
  - `Presolicitation`
  - `Sources Sought`
  - `Special Notice`
  - `Award Notice`

- `naics` (str) - NAICS code(s) (comma-separated)
- `state` (str) - 2-letter state code (e.g., "VA", "CA", "TX")

### Response Structure
```json
{
  "opportunitiesData": [
    {
      "noticeId": "...",
      "title": "...",
      "type": "...",
      "postedDate": "...",
      "responseDeadLine": "...",
      "organizationName": "..."
    }
  ],
  "totalRecords": 100
}
```

### ⚠️ UNCERTAINTIES
1. **Rate limits**: Unknown
2. **Other filter options**: PSC codes? Set-aside codes? Agency?
3. **Response field variations**: Code checks for both `opportunitiesData` and `results` keys
4. **Total records variations**: Checks both `totalRecords` and `total`
5. **Valid values for `type`**: Are there other values besides "Active"?
6. **Multiple NAICS handling**: Comma-separated confirmed, but limit?

---

## Integration Requirements

### Common Features Needed
1. **Unified search interface** with tabs for each source
2. **Export to CSV/JSON** for all sources
3. **Date range pickers** (with source-specific formats)
4. **Pagination controls**
5. **Results preview/display**
6. **Download capabilities**

### Technical Challenges

#### 1. API Key Management
- **DVIDS**: Hardcoded key available
- **SAM.gov**: User must provide
- **ClearanceJobs**: Not needed
- **Solution**: Sidebar inputs, optional persistence

#### 2. Date Formatting
- **DVIDS**: ISO8601 format (`2024-01-01T00:00:00Z`)
- **SAM.gov**: US format (`01/01/2024`)
- **ClearanceJobs**: Days-based filter (`received=31`)
- **Solution**: Convert from Streamlit date_input to each format

#### 3. Parameter Translation
- **Array parameters** (DVIDS type[])
- **ID vs value** (ClearanceJobs loc=1 vs city="Alexandria, VA")
- **Comma-separated** (SAM.gov NAICS)
- **Solution**: Helper functions per source

#### 4. Response Structure Differences
- **ClearanceJobs**: `data` array
- **DVIDS**: `results` array
- **SAM.gov**: `opportunitiesData` or `results` array
- **Solution**: Normalization layer

#### 5. Pagination Strategies
- **ClearanceJobs**: Unknown (possibly `page` param)
- **DVIDS**: `page` parameter (1-indexed)
- **SAM.gov**: `offset` parameter (0-indexed)
- **Solution**: Per-source pagination logic

### Dependencies Required
```
streamlit
requests
pandas
Pillow  # for DVIDS image display
```

### File Structure (Proposed)
```
sam_gov/
├── unified_search_app.py          # Main Streamlit app
├── scrapers/
│   ├── __init__.py
│   ├── clearancejobs.py          # ClearanceJobs wrapper
│   ├── dvids.py                  # DVIDS wrapper (already exists)
│   ├── sam.py                    # SAM.gov wrapper
│   └── utils.py                  # Shared utilities
└── ClearanceJobs/                # Existing library
```

---

## Critical Questions to Resolve

### ClearanceJobs
1. ❓ How does pagination work? Is there a `page` parameter?
2. ❓ How to pass multiple filter values (e.g., multiple clearance levels)?
3. ❓ Are there sort options?
4. ❓ What are the rate limits?

### DVIDS
1. ❓ How to properly format type[] for multiple values in requests.get()?
2. ❓ What are the rate limits?
3. ❓ Maximum number of pages/results?

### SAM.gov
1. ❓ What are the rate limits?
2. ❓ Full list of available filters (PSC, set-aside, agency, etc.)?
3. ❓ Why does code check for both `opportunitiesData` and `results`?

### Integration
1. ❓ Should we create a single search box that searches all 3, or separate tabs?
2. ❓ How to handle authentication (save keys in session state, env vars, file)?
3. ❓ Should results be merged or displayed separately?
4. ❓ Export format: separate files per source or combined CSV?

---

## Recommendations

### Phase 1: Basic Integration
- Create tabbed interface with 3 separate search forms
- Implement core search functionality for each
- Basic results display
- CSV export per source

### Phase 2: Advanced Features
- Unified search across all sources
- Advanced filtering with dynamic filter discovery
- Result deduplication/merging
- Scheduled searches
- Email notifications

### Phase 3: Optimization
- Caching layer
- Rate limit handling
- Async searches
- Result ranking/relevance scoring

---

## Next Steps
1. Clarify pagination for ClearanceJobs
2. Test multiple value filters on all APIs
3. Determine rate limits (or add conservative delays)
4. Build Phase 1 unified interface
5. User testing and feedback
