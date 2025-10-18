# Unified Multi-Source Search Application

A comprehensive Streamlit application that integrates three powerful search APIs:
- **ClearanceJobs** - Security clearance job search
- **DVIDS** - Military media and news
- **SAM.gov** - Government contract opportunities

## Features

### 🏢 ClearanceJobs
- Search by keywords, location, clearance level
- Filter by experience, polygraph requirements, job type
- Filter by company, remote work options
- Full pagination support (1000+ pages)
- CSV/JSON export

### 📸 DVIDS
- Search military photos, videos, news, and media
- Filter by branch, country, state, city
- Date range filtering
- Media type selection (image, video, audio, news, etc.)
- Advanced filters: aspect ratio, HD quality, captions
- Combatant command and unit filters
- CSV/JSON export with image thumbnails

### 📋 SAM.gov
- Search government contract opportunities
- **Required**: Posted date range (max 1 year)
- Filter by procurement type (solicitation, presolicitation, etc.)
- 18 set-aside types (Small Business, 8(a), SDVOSB, etc.)
- NAICS and PSC classification codes
- Organization, state, and ZIP code filters
- Response deadline filtering
- CSV/JSON export

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Or install individually:
   ```bash
   pip install streamlit requests pandas Pillow
   ```

2. **Install ClearanceJobs library:**
   ```bash
   cd ClearanceJobs
   pip install -e .
   cd ..
   ```

## Running the App

```bash
streamlit run unified_search_app.py
```

The app will open in your browser at `http://localhost:8501`

## API Keys

### DVIDS
- **Required**: Yes
- **Default key provided**: `key-68f319e8dc377`
- Get your own at: https://www.dvidshub.net/

### SAM.gov
- **Required**: Yes
- **Get your key**: https://sam.gov
  - Log in to your account
  - Go to Account Details
  - Request API Key

### ClearanceJobs
- **Required**: No
- Public job search works without authentication

## Usage

### Search Tips

**ClearanceJobs:**
- Use specific keywords: "cybersecurity analyst", "network engineer"
- Combine clearance filters for targeted results
- Filter by major defense hubs: Maryland, Virginia, DC, California, Colorado

**DVIDS:**
- Search is optional - leave blank to browse all recent media
- Combine media types to get photos + videos
- Use date ranges for recent operations or historical content
- HD filter works best with videos

**SAM.gov:**
- **Date range is MANDATORY** (max 1 year)
- Use NAICS codes for specific industries (e.g., 541512 = Computer Systems Design)
- Set-aside filter helps small businesses find targeted opportunities
- Response deadline filters show upcoming opportunities

### Advanced Features

**Pagination:**
- All sources support pagination
- ClearanceJobs: No limit
- DVIDS: Max 1000 results (20 pages @ 50/page)
- SAM.gov: No limit (1000/page max)

**Export Options:**
- CSV: Tabular data for Excel/analysis
- JSON: Complete API responses with all fields

**Rate Limiting:**
- Enable in sidebar to avoid hitting API limits
- 1 second delay between ClearanceJobs/SAM.gov searches
- 0.5 second delay for DVIDS

## File Structure

```
sam_gov/
├── unified_search_app.py          # Main Streamlit app
├── clearancejobs_search.py        # ClearanceJobs tab
├── dvids_search.py                # DVIDS tab
├── sam_search.py                  # SAM.gov tab
├── requirements_unified.txt       # Python dependencies
├── ClearanceJobs/                 # ClearanceJobs library
│   ├── ClearanceJobs/
│   │   └── __init__.py
│   ├── setup.py
│   └── venv/
├── INTEGRATION_ANALYSIS.md        # Technical documentation
└── UNCERTAINTIES_RESOLVED.md      # API investigation results
```

## Troubleshooting

### "No module named streamlit"
```bash
pip install streamlit
```

### "No module named ClearanceJobs"
```bash
cd ClearanceJobs
pip install -e .
```

### SAM.gov returns "PostedFrom and PostedTo are mandatory"
- Make sure both date fields are filled in the UI
- Date range cannot exceed 1 year

### DVIDS returns 403 error
- Check your API key in the sidebar
- Make sure it starts with `key-`

### ClearanceJobs returns 404
- The public API may be temporarily unavailable
- Try again in a few minutes

## API Limits

| API | Max Results/Page | Total Limit | Rate Limit |
|-----|------------------|-------------|------------|
| ClearanceJobs | 100 | None | Unknown (use 1s delay) |
| DVIDS | 50 | 1000 | Unknown (use 0.5s delay) |
| SAM.gov | 1000 | None | Unknown (use 1s delay) |

## Known Limitations

1. **ClearanceJobs**: Sort options not documented (uses relevance by default)
2. **DVIDS**: Maximum 1000 total results per search
3. **SAM.gov**: Date range limited to 1 year

## Credits

- **ClearanceJobs API**: https://www.clearancejobs.com/
- **DVIDS API**: https://api.dvidshub.net/docs
- **SAM.gov API**: https://open.gsa.gov/api/get-opportunities-public-api/

## License

This tool is for legitimate research and job searching purposes only. Respect API terms of service and rate limits.
