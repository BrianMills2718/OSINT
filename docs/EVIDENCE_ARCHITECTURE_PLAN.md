# Evidence Architecture Refactor Plan

**Created**: 2025-12-05
**Status**: Investigation Complete - Awaiting Approval
**Author**: Claude Code (Investigation Session)

---

## Executive Summary

This document presents a comprehensive investigation into the current Evidence/SearchResult architecture and proposes a clean refactor to properly separate raw API data from processed evidence.

**Key Finding**: The current architecture has fundamental design issues causing silent data loss. Evidence is truncated at multiple points, dates are not preserved, and rich metadata from API responses is discarded.

**Recommendation**: Implement a clean three-tier data model separating Raw Data → Processed Evidence → LLM Context.

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Problems Identified](#2-problems-identified)
3. [Proposed Architecture](#3-proposed-architecture)
4. [Implementation Plan](#4-implementation-plan)
5. [Risks and Mitigations](#5-risks-and-mitigations)
6. [Token/Cost Analysis](#6-tokencost-analysis)
7. [Backward Compatibility](#7-backward-compatibility)
8. [Open Questions](#8-open-questions)
9. [Success Criteria](#9-success-criteria)

---

## 1. Current Architecture Analysis

### 1.1 Data Model Classes

**Location**: `core/database_integration_base.py`

```
SearchResult (Pydantic BaseModel)
├── title: str
├── url: Optional[str]
├── snippet: str (Pydantic validator truncates to 500 chars!)
├── date: Optional[str]
└── metadata: Dict[str, Any] = {}

Evidence (extends SearchResult)
├── [inherits all SearchResult fields]
├── source_id: str = ""
├── relevance_score: float = 0.0
├── content: property (alias for snippet)
└── source: property (alias for source_id)
```

**Location**: `core/result_builder.py`

```
SearchResultBuilder
├── title(value, default="Untitled")
├── url(value)
├── snippet(value, max_length=500)  # Default truncation!
├── date(value)
├── metadata(dict)
└── build() -> Dict
```

### 1.2 Data Flow Through System

```
Integration API Response
        ↓
SearchResultBuilder.build() → dict {title, url, snippet, date, metadata}
        ↓                      ↑
        │                snippet truncated to 500 chars
        ↓
Evidence.from_dict(dict, source_id) → Evidence object
        ↓
_filter_results() → filters for relevance
        ↓
_summarize_evidence() → stores original in metadata["original_content"]
        ↓                replaces snippet with summary
        │
        ├─→ Entity extraction: e.content[:300] (TRUNCATED AGAIN)
        ├─→ Global index: e.content[:200] (TRUNCATED AGAIN)
        ├─→ Analysis prompts: uses e.content (already truncated)
        └─→ Report synthesis: item.content[:300] (TRUNCATED AGAIN)
        ↓
_save_result() → _result_to_dict()
        ↓
Saved JSON: {source, title, content[:500], url}
        ↑
        │ FIELDS LOST: date, metadata, relevance_score
        │ CONTENT TRUNCATED: to max_content_chars_in_synthesis (500)
        │ EVIDENCE CAPPED: to max_evidence_in_saved_result (50)
        ↓
Final Output: 50 evidence items, no dates, no metadata
```

### 1.3 Integration Patterns (23 Sources)

**Metadata Usage** (by integration type):

| Integration Type | Metadata Pattern | Example Fields |
|-----------------|------------------|----------------|
| USAspending | Stores FULL raw dict | `award` (complete API response) |
| SAM.gov | Extracts specific fields | noticeId, solicitationNumber, organizationName |
| Twitter | Complex structured | author, verified, favorites, retweets |
| Brave Search | Minimal | age, language, profile |
| FBI Vault | Simple | document_type, query, source |
| NewsAPI | Moderate | source, author, published_at, content_preview |
| CourtListener | Moderate | court, date_filed, docket_number, citation |

**Key Observation**: Only USAspending preserves full raw API response. All others extract subsets and discard the rest.

### 1.4 Storage Analysis

**Sample Output** (from 2025-11-30 research run):
```
Total evidence collected: 255
Evidence saved to result.json: 50 (80% LOSS)
Evidence with date field: 0 (100% LOSS)
Evidence with metadata field: 0 (100% LOSS)
Content truncated (495+ chars): 3 items
Average content length: 171 chars
```

**Saved Evidence Schema**:
```json
{
    "source": "brave_search",
    "title": "Pentagon taps four commercial tech firms...",
    "content": "<strong>Each company received a contract worth up to $200 million</strong>...",
    "url": "https://..."
}
```

**Missing**: date, metadata, relevance_score, original_content

---

## 2. Problems Identified

### 2.1 Critical Problems

| # | Problem | Impact | Location |
|---|---------|--------|----------|
| 1 | **Silent Truncation Chain** | Data loss without warning | Multiple (see 1.2) |
| 2 | **Dates Not Preserved** | No timeline from saved data | _result_to_dict() |
| 3 | **Metadata Discarded** | Rich API data lost | _result_to_dict() |
| 4 | **Evidence Count Capped** | 80% of evidence discarded | max_evidence_in_saved_result |
| 5 | **Overloaded snippet Field** | Raw + processed in same field | Evidence.content alias |

### 2.2 Design Flaws

1. **No Separation of Concerns**: Raw API data, processed content, and LLM-ready summaries all stored in same `snippet` field
2. **Implicit Truncation**: Pydantic validator silently truncates to 500 chars without logging
3. **Field Name Mismatch**: SearchResultBuilder outputs `snippet`, but some code reads `description` or `content`
4. **No Date Extraction from Text**: Dates only from structured API fields, never from content
5. **No Full Page Fetch**: Config exists but feature never implemented

### 2.3 Data Flow Issues

```
CURRENT:
  snippet → 500 chars → summarize → metadata["original_content"]
                                  → snippet = summary
           ↓
  Both original and summary in same Evidence object
           ↓
  Save: only snippet (the summary), original LOST

SHOULD BE:
  raw_content → unlimited storage
  processed_content → summary/extraction
  Both preserved separately
```

---

## 3. Proposed Architecture

### 3.1 New Data Model

```python
@dataclass
class RawResult:
    """Immutable raw API response data."""
    api_response: Dict[str, Any]  # Complete API response
    source_id: str
    query_params: Dict[str, Any]
    fetched_at: datetime
    response_time_ms: float

    # Extracted from raw (never truncated)
    title: str
    url: Optional[str]
    raw_content: str  # Full snippet/description from API
    structured_date: Optional[str]  # From API date field
    content_dates: List[str]  # Extracted from text


@dataclass
class ProcessedEvidence:
    """LLM-processed evidence with extracted information."""
    raw_result_id: str  # Reference to RawResult

    # Goal-specific extraction (what matters for this goal)
    extracted_facts: List[str]
    extracted_entities: List[str]
    extracted_dates: List[str]
    relevance_score: float
    relevance_reasoning: str

    # Summarized for LLM context (token-efficient)
    summary: str  # ~150 chars, goal-focused

    # Provenance
    goal: str
    extracted_by: str  # LLM model used


@dataclass
class Evidence:
    """Complete evidence with full lineage."""
    id: str  # UUID
    raw: RawResult
    processed: ProcessedEvidence

    # For LLM prompts (read-only, derived)
    @property
    def llm_context(self) -> str:
        """Token-efficient representation for prompts."""
        return self.processed.summary

    @property
    def content(self) -> str:
        """Full content for storage/analysis."""
        return self.raw.raw_content
```

### 3.2 Storage Architecture

```
data/research_v2/{timestamp}_{query}/
├── raw_responses/
│   ├── {source}_{timestamp}.json     # Complete API responses
│   └── ...
├── processed/
│   ├── evidence.json                  # ProcessedEvidence objects
│   └── extraction_log.jsonl          # LLM extraction decisions
├── output/
│   ├── result.json                    # Full result with all evidence
│   ├── result_summary.json           # LLM-context sized version
│   └── report.md                      # Synthesized report
└── execution_log.jsonl               # Existing format
```

### 3.3 Data Flow

```
Integration API Response
        ↓
RawResult (immutable, complete)
        ↓
Store to raw_responses/
        ↓
ProcessedEvidence (goal-focused extraction)
        ↓
        ├─→ LLM prompts: use .llm_context (summary)
        └─→ Storage: save complete Evidence
        ↓
Report synthesis uses summaries (token-efficient)
        ↓
Full data preserved for audit/reprocessing
```

---

## 4. Implementation Plan

### Phase 1: Data Model Refactor (4-6 hours)

**Files to Modify:**
- `core/database_integration_base.py` - New RawResult, ProcessedEvidence classes
- `core/result_builder.py` - Build RawResult instead of dict

**Tasks:**
1. Create `RawResult` dataclass with complete API storage
2. Create `ProcessedEvidence` dataclass with extraction fields
3. Create new `Evidence` class composing both
4. Add `Evidence.from_raw()` factory method
5. Maintain backward compatibility with `.content`, `.snippet` properties

### Phase 2: Integration Updates (6-8 hours)

**Files to Modify:**
- All 23 integration files

**Tasks:**
1. Update `execute_search()` to return `RawResult` objects
2. Preserve complete API response in `api_response` field
3. Extract structured dates properly
4. Remove premature truncation

**Pattern:**
```python
# Before
transformed = (SearchResultBuilder()
    .title(item.get("name"))
    .snippet(item.get("description")[:500])  # Truncation!
    .metadata({"some_field": item.get("field")})  # Partial!
    .build())

# After
raw = RawResult(
    api_response=item,  # Complete response
    source_id=self.metadata.id,
    query_params=query_params,
    fetched_at=datetime.now(),
    title=item.get("name", "Untitled"),
    url=item.get("url"),
    raw_content=item.get("description", ""),  # No truncation
    structured_date=item.get("date"),
    content_dates=[]  # Extracted later
)
```

### Phase 3: Agent Refactor (4-6 hours)

**Files to Modify:**
- `research/recursive_agent.py`

**Tasks:**
1. Update `_execute_api_call()` to create Evidence from RawResult
2. Implement `_extract_evidence()` LLM call for goal-focused extraction
3. Update `_add_to_run_index()` to store complete Evidence
4. Update `_result_to_dict()` to preserve all fields
5. Add date extraction from content (LLM-based)

### Phase 4: Prompt Updates (2-3 hours)

**Files to Modify:**
- `prompts/recursive_agent/result_filtering.j2`
- `prompts/recursive_agent/result_summarization.j2` → rename to extraction
- `prompts/deep_research/v2_report_synthesis.j2`

**Tasks:**
1. Update filtering to use `.llm_context` for decisions
2. Create new extraction prompt (facts, entities, dates)
3. Update synthesis to use structured ProcessedEvidence

### Phase 5: Storage Refactor (2-3 hours)

**Files to Modify:**
- `research/recursive_agent.py` (_save_result method)

**Tasks:**
1. Save raw responses to `raw_responses/` directory
2. Save processed evidence with full fields
3. Create both full and summary result files
4. Log data preservation metrics

### Phase 6: Testing and Validation (4-6 hours)

**Tasks:**
1. Unit tests for new data models
2. Integration tests for each source
3. E2E test verifying no data loss
4. Regression test comparing output quality

**Total Estimated Effort: 22-32 hours (3-4 days)**

---

## 5. Risks and Mitigations

### 5.1 High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing code | System crashes | Maintain backward-compatible properties |
| LLM extraction errors | Bad evidence | Fallback to raw content |
| Storage size explosion | Disk full | Configurable retention policy |

### 5.2 Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token costs increase | Higher API bills | Separate storage from LLM context |
| Date extraction fails | Missing timeline | Keep structured dates as fallback |
| Performance degradation | Slower research | Async I/O for raw storage |

### 5.3 Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Output format changes | Downstream breaks | Version output schema |
| Old results incompatible | Can't load history | Add migration script |

---

## 6. Token/Cost Analysis

### 6.1 Storage vs LLM Context

**Critical Insight**: Storage is essentially free. Token costs only matter when data is sent to LLM.

```
CURRENT APPROACH (truncated):
  Evidence saved: 50
  Chars per evidence: ~200
  Total chars: 10,000
  Estimated tokens: 2,500
  Cost/research: ~$0.025

FULL STORAGE (no truncation):
  Evidence saved: 255
  Chars per evidence: ~2,000
  Total chars: 510,000
  Disk storage: ~500KB per research
  Cost: $0.00 (local storage)

LLM CONTEXT (summaries only):
  Evidence in prompts: 30 (max_evidence_for_synthesis)
  Chars per summary: ~150
  Total chars: 4,500
  Estimated tokens: 1,125
  Cost/research: ~$0.011
```

### 6.2 Recommended Approach

```
Store EVERYTHING to disk (zero marginal cost)
     ↓
Extract summaries for LLM context (token-efficient)
     ↓
Full data available for:
  - Audit trails
  - Re-processing with different goals
  - Timeline reconstruction
  - Entity relationship discovery
```

---

## 7. Backward Compatibility

### 7.1 Properties to Maintain

```python
class Evidence:
    # Old code uses these - must keep working
    @property
    def content(self) -> str:
        return self.processed.summary if self.processed else self.raw.raw_content

    @property
    def snippet(self) -> str:
        return self.content

    @property
    def source(self) -> str:
        return self.raw.source_id

    def to_dict(self) -> Dict:
        # Return format matching old Evidence.to_dict()
        pass
```

### 7.2 Migration Path

1. **Phase 1**: Add new fields alongside old ones
2. **Phase 2**: Update writers to populate new fields
3. **Phase 3**: Update readers to prefer new fields
4. **Phase 4**: Deprecate old fields (logging when used)
5. **Phase 5**: Remove old fields (next major version)

### 7.3 Output Format Changes

```json
// OLD (result.json)
{
    "evidence": [
        {"source": "x", "title": "y", "content": "z", "url": "..."}
    ]
}

// NEW (result.json) - Backward compatible
{
    "schema_version": "2.0",
    "evidence": [
        {
            // Old fields (still present)
            "source": "x",
            "title": "y",
            "content": "z",
            "url": "...",

            // New fields
            "date": "2024-03-15",
            "raw_content": "full content here...",
            "extracted_facts": ["fact1", "fact2"],
            "extracted_entities": ["Entity1", "Entity2"],
            "relevance_score": 0.85,
            "metadata": {...}
        }
    ]
}
```

---

## 8. Open Questions

### 8.1 Architecture Decisions Needed

1. **Date Extraction Strategy**: Should we use LLM for date extraction from text, or regex patterns, or both?
   - LLM: More accurate, higher cost
   - Regex: Faster, may miss context
   - Recommendation: LLM with regex fallback

2. **Raw Storage Format**: JSON per response, or batched JSONL?
   - Per-response: Easier to debug, more files
   - Batched: Fewer files, harder to inspect
   - Recommendation: Per-response for simplicity

3. **Extraction Timing**: Extract at collection time, or on-demand?
   - At collection: Higher upfront cost, always available
   - On-demand: Lower cost, needs re-processing
   - Recommendation: At collection for complete lineage

4. **Retention Policy**: How long to keep raw data?
   - Forever: Complete audit trail, disk usage grows
   - Configurable: User decides based on needs
   - Recommendation: Configurable with default 30 days

### 8.2 Implementation Uncertainties

1. **LLM Extraction Quality**: Will extraction be reliable across sources?
   - Need: Test with diverse sources before full rollout
   - Mitigation: Fallback to raw content if extraction fails

2. **Performance Impact**: Will raw storage slow down research?
   - Need: Benchmark with async I/O
   - Mitigation: Buffer writes, compress older data

3. **Integration Compatibility**: Will all 23 integrations work with new model?
   - Need: Test each integration individually
   - Mitigation: Integration-specific adapters if needed

---

## 9. Success Criteria

### 9.1 Data Preservation

- [ ] 100% of collected evidence saved (not capped at 50)
- [ ] 100% of dates preserved (structured + extracted)
- [ ] 100% of metadata preserved (raw API responses)
- [ ] 0 silent truncations (all truncation logged with warning)

### 9.2 Backward Compatibility

- [ ] All existing tests pass
- [ ] Old code using `.content`, `.snippet` still works
- [ ] Old result.json files can still be loaded
- [ ] Report quality unchanged or improved

### 9.3 Token Efficiency

- [ ] LLM prompt sizes unchanged (use summaries)
- [ ] Storage-only data doesn't increase costs
- [ ] Extraction adds < 20% to total LLM cost

### 9.4 Quality Improvements

- [ ] Timeline generation uses extracted dates
- [ ] Entity graph uses extracted entities
- [ ] Full content available for re-analysis
- [ ] Audit trail from raw → processed → report

---

## Appendix A: File Inventory

### Files to Create
- `core/raw_result.py` - RawResult dataclass
- `core/processed_evidence.py` - ProcessedEvidence dataclass
- `prompts/recursive_agent/evidence_extraction.j2` - New extraction prompt
- `tests/test_evidence_model.py` - Unit tests for new model

### Files to Modify
- `core/database_integration_base.py` - Evidence class changes
- `core/result_builder.py` - Build RawResult
- `research/recursive_agent.py` - Agent data flow
- All 23 integration files - Return RawResult
- 4 prompt files - Use new Evidence fields

### Files to Archive
- Old truncation logic (move to deprecated module)

---

## Appendix B: Sample RawResult

```json
{
    "api_response": {
        "id": "12345",
        "title": "Pentagon Awards $200M AI Contract",
        "description": "The Defense Department announced...",
        "publishedAt": "2024-11-15T14:30:00Z",
        "author": "John Smith",
        "source": {"id": "defense-news", "name": "Defense News"},
        "urlToImage": "https://...",
        "content": "Full article content here..."
    },
    "source_id": "newsapi",
    "query_params": {"q": "Pentagon AI contract", "from": "2024-01-01"},
    "fetched_at": "2025-12-05T10:30:00Z",
    "response_time_ms": 1234.5,
    "title": "Pentagon Awards $200M AI Contract",
    "url": "https://...",
    "raw_content": "The Defense Department announced...",
    "structured_date": "2024-11-15",
    "content_dates": ["November 15, 2024", "Q1 2025"]
}
```

---

## Appendix C: Sample ProcessedEvidence

```json
{
    "raw_result_id": "abc123",
    "extracted_facts": [
        "Pentagon awarded $200M contract for AI development",
        "Four companies selected: Palantir, Anduril, Scale AI, Shield AI",
        "Contract duration: 3 years with 2 option years"
    ],
    "extracted_entities": [
        "Pentagon",
        "Palantir",
        "Anduril",
        "Scale AI",
        "Shield AI",
        "Chief Digital and AI Office"
    ],
    "extracted_dates": [
        {"date": "2024-11-15", "context": "Contract announcement date"},
        {"date": "2025-Q1", "context": "Expected work to begin"}
    ],
    "relevance_score": 0.92,
    "relevance_reasoning": "Directly addresses AI contracts to defense contractors",
    "summary": "Pentagon awarded $200M AI contracts to Palantir, Anduril, Scale AI, Shield AI for military AI workflows. 3-year base with 2 option years.",
    "goal": "Find federal AI contracts awarded in 2024",
    "extracted_by": "gemini-2.0-flash-exp"
}
```

---

**Document Status**: Ready for Review

**Next Steps**:
1. Review and approve this plan
2. Create implementation branch
3. Begin Phase 1 (Data Model Refactor)
