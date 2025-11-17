# Wiki V3 - Standalone Prototype (Isolation-First Design)

**IMPORTANT**: This is the **standalone prototype design**. For eventual integration with existing research tools, see `v3_INTEGRATED_FUTURE.md`.

**Design Philosophy**: Build and validate in isolation first, integrate later (if at all).

---

## 0. Implementation Phasing (Ultra-Minimal Approach)

**CRITICAL**: This document describes the eventual V1 system. **DO NOT build V1 directly.**

Instead, use **3-stage validation approach** to avoid building the wrong thing:

### Stage 1: Manual Proof (2 hours, ZERO code)
- Use 2-3 **public investigative reports** (Bellingcat, ProPublica, declassified docs)
- Manually extract entities to spreadsheet
- Try manual entity pivoting across reports
- **Decision Gate**: Is entity organization useful? GO/STOP
- **Location**: `./poc/stage1_manual_test.md`
- **GO if**: You can name 2-3 entities where manual grouping clearly surfaced patterns you'd have missed reading inline AND you want a faster way to do this again
- **STOP if**: Flat reading was just as effective

**Test Data**: See `./test_data/README.md` for suggested public investigative sources

### Stage 2: SQLite + CLI (4-6 hours, ~100 lines)
- **Only if Stage 1 validates value**
- 3 tables: evidence, entities, evidence_entities
- Manual data entry (CSV import from public sources)
- 2 CLI commands: list-entities, evidence-for-entity
- **Decision Gate**: Is CLI useful? GO/MAINTAIN/STOP
- **IMPORTANT**: Stage 2/3 tables must be exact prefixes of V1 schemas (use ALTER TABLE to extend, not rebuild)
- **GO if**: You reach for the CLI during investigation (not just testing) AND at least 2-3 entities become "pivot hubs" with multiple snippets that feel genuinely useful
- **MAINTAIN if**: CLI is useful but manual CSV import is acceptable
- **STOP if**: CLI doesn't help vs. spreadsheet

### Stage 3: LLM Extraction (4-6 hours, +50 lines)
- **Only if Stage 2 validates automation need**
- Add entity_extractor.py (LLM extraction)
- Eliminate manual data entry
- **Decision Gate**: Extraction quality good? GO/TUNE/STOP
- **GO if**: LLM extraction quality is good enough to replace manual CSV creation (80%+ accuracy acceptable)
- **TUNE if**: Extraction has issues but prompt adjustments can fix them
- **STOP if**: Manual CSV creation is faster/more accurate than debugging LLM extraction

### Full PoC (4-6 hours)
- **Only if Stage 3 validates**
- Add: leads, research_runs, sources tables
- Add: `poc.py run` command (full automation)
- **Expect 6-8 hours in practice** (debugging, integration)
- **Note**: At this stage, you can OPTIONALLY add a simple research adapter (web search + LLM summarizer)

### V1 (20-25 hours)
- **Only after Full PoC validates**
- Add: claims, predicates, entity_aliases tables
- Add: Multi-lead support
- Add: Web UI (Streamlit)
- **Research Layer Options**:
  - Option A: Simple web search (Brave/Tavily) + LLM summarizer (standalone)
  - Option B: Integration adapter to external research tools (see v3_INTEGRATED_FUTURE.md)

**See**: Section 7 (Phase 2 / Later) for full implementation roadmap

---

## 1. Overview

**Note**: This section describes the *end-state behavior* of standalone V1. Early stages (Stage 1-3 + Full PoC) will implement only small slices of this.

* Short description of what v1 does:

  * Takes a topic (e.g. *"psychological warfare and J-2"*).
  * Uses a **simple research layer** to gather sources:
    * Stage 1-3: Manual extraction from public investigative reports
    * Full PoC/V1: Either (a) simple web search + LLM summarizer, OR (b) pluggable adapter to external tools (future)
  * Extracts entities/claims into a simple knowledge graph.
  * Organizes everything into per-topic **Leads** (your notebooks / case files), each with its own graph, search history, and automatic filtering rules.
  * Supports **filter-based follow-up searches** with automation-first design.

---

## 1. Goals & Non-Goals (v1)

* **Goals**

  * Support *investigative journalism–style* deep dives, not just Q&A.
  * Keep **all raw text** (nothing thrown away).
  * Build a **persistent KG + leads** you can keep revisiting.
  * **Standalone first**: Build and validate without external dependencies
  * **Integration later** (Phase 2+): Optionally add adapters to external research tools after proving standalone value
  * **Automation-first**: System attaches evidence to leads automatically, runs pattern-based expansions, and builds reports without mandatory manual review steps (human review is optional enhancement, not required workflow).
* **Non-Goals**

  * No fancy NLI / truth pruning yet.
  * No enterprise auth / security.
  * No perfect ontology; "good enough" schema.
  * **No coupling to external codebases** in Stage 1-3 validation phases

---

## 2. Core Data Model (Concepts)

**Note**: This section describes the *end-state architecture*. Stage 1-3 will use minimal subsets of these tables.

[... rest of data model sections remain the same as they describe generic concepts ...]

### 2.1 Source

"Which document/page did this come from?"

* Fields (conceptually): `source_id`, `url`, `domain`, `search_engine`, `search_query`, `fetched_at`, etc.

### 2.2 Evidence

"Which exact text chunk did we see, from which source?"

* Fields: `evidence_id`, `source_id`, `snippet_text`, `location_in_source`, `fetched_at`, maybe `llm_notes`.

### 2.3 Entity

"People / orgs / projects / codewords / places / concepts."

* Fields: `entity_id` (local), `label`, `type`, `aliases`, `optional_wikidata_qid`.

### 2.4 Claim (Triple)

"Our structured interpretation: subject–predicate–object."

* Fields: `claim_id`, `subject_entity_id`, `predicate_id`, `object_entity_id_or_literal`, `evidence_id`, `extraction_model_version`.

### 2.5 Lead (Thread / Notebook)

"Investigation line you care about - your case file / notebook."

* Fields: `lead_id`, `title`, `description`, `status`, `created_at`, `updated_at`, `lead_filters_json` (defines which evidence auto-attaches to this lead based on entities, keywords, domains, time ranges).

### 2.6 SearchRun

"A single run of a research operation."

* Fields: `search_run_id`, `lead_id`, `input_query_or_plan`, `engine_type` (manual / web_search / external_adapter), `parameters` (depth, breadth), `started_at`, `finished_at`, `cost_estimate`.

### 2.7 SearchPatternTemplate

"Reusable search strategy patterns (your boolean tricks)."

* Fields: `pattern_id`, `name`, `description`, `template_string` (with placeholders like `{PERSON}`, `{TOPIC}`), `used_for` (people×topic / office×capability etc.).

### 2.8 LeadRelation (Optional Cross-Linking)

"Simple cross-linking between related Leads."

* Fields: `id`, `from_lead_id`, `to_lead_id`, `relation_type` ("related_to", "person_profile", "background_context"), `note` (optional short text explaining relationship).

---

## 3. Storage Layout (Technically Simple)

* One relational database (SQLite for v1, Postgres for later) with tables:

  * `sources`
  * `evidence`
  * `entities`
  * `claims`
  * `leads`
  * `lead_relations` (cross-linking between Leads)
  * `search_runs`
  * `search_pattern_templates`
* Optional: simple `tags` table for tagging entities/leads ("high priority", "psywar", etc.).

---

## 4. External Components (Research Layer)

### 4.1 Research Data Sources (Phased Approach)

**Stage 1-3**: Manual extraction from public sources
- Bellingcat investigations
- ProPublica long-form reports
- Declassified document sets (CIA FOIA, NSA archives)
- Academic investigative case studies

**Full PoC / V1 Option A (Standalone)**: Simple web search + LLM
- Define thin `ResearchClient` interface:
  ```text
  run_research(query, params) -> {
      report_md: str,
      citations: [ {url, snippet, source_title, …} ]
  }
  ```
- Implementation:
  1. Build 3-5 Brave/Tavily queries from user prompt
  2. Fetch pages
  3. Ask LLM to:
     - Summarize findings
     - List investigative leads
     - Extract key entities/claims
- **Pros**: Fully standalone, no external dependencies
- **Cons**: Simpler than specialized research frameworks

**V1 Option B (Future Integration)**: Pluggable adapter pattern
- Same `ResearchClient` interface
- Adapter to external research tools (see v3_INTEGRATED_FUTURE.md)
- **Decide after Stage 1-3 validation**

### 4.2 Search / Scraping

* For standalone v1: Brave API or Tavily API
* Log all queries and URLs for reproducibility

### 4.3 LLM for Extraction & KG

* A separate LLM call (or small script) to:

  * extract entities from snippets,
  * convert them into claims,
  * decide which entities become seeds for new Leads.

---

## 5. Core Workflows

**Note**: This section describes the *end-state workflows* of V1+. Early stages will have simplified manual versions.

### 5.1 Start New Investigation (New Lead + Initial Research)

* You type a topic (e.g. "psychological warfare and J-2").
* System:

  * creates a new `Lead`;
  * launches one `SearchRun` using the research layer (manual in Stage 1-3, automated in Full PoC/V1);
  * ingests returned sources → evidence → entities → claims;
  * attaches best evidence/entities to the Lead.

### 5.2 Expand an Existing Lead (Pattern-Driven Follow-up)

* You open a Lead and choose:

  * "Expand using pattern: Person×Topic" or "Office×Capability" etc.
* System:

  * pulls related entities from KG (e.g. J-2 heads);
  * instantiates search templates into **concrete queries**;
  * for each query: runs another `SearchRun`, ingests results, updates KG and Lead.

### 5.3 Prospector Pass (Suggest New Leads) **[Phase 1.5+]**

**Status**: Phase 1.5+ feature (not part of minimal V1 build)

* System periodically scans KG + evidence:

  * finds unusual co-occurrences (e.g. person repeatedly appearing with J-2 + psyops),
  * rare but recurring codewords,
  * bridge entities linking multiple themes.
* Suggests new Leads:

  * "Candidate Lead: Jane R. Doe as cross-program actor. Accept?"

### 5.4 Browse / Query Layer for You

* Very simple v1 UI / CLI actions:

  * list all Leads, filter by tag / status.
  * open a Lead → see:

    * hypothesis, open questions, attached evidence, entities, search runs.
  * simple queries over KG:

    * "show all claims involving J-2 and psychological warfare"
    * "list entities co-occurring with Operation FORESIGHT".

---

## 6. Search Pattern System (Your Investigator Tricks) **[Phase 1.5+]**

**Status**: Phase 1.5+ feature (not part of minimal V1 build)

* A small set of **template types**:

  * Person×Topic
  * Office×Capability
  * Codename×Org
  * Time-bounded variants
* For each:

  * define template string,
  * rules for filling placeholders from KG (which entities/terms),
  * how many concrete queries to generate per Lead.

---

## 7. Phase 2 / Later (Not in Minimal v1)

* NLI / entailment filters to down-rank conflicting / low-support claims.
* More ontology / TBox (richer types, subproperties).
* **Integration adapters** to external research frameworks (GPT-Researcher, DeerFlow, or custom tools)
* Time-aware graph views ("state of world as of 2012").
* Better UI (graph visualization, timelines).
* **Auto-wiki generation from matured Leads**: Once Leads reach sufficient depth (100+ evidence snippets, dense entity graph), generate MediaWiki/Wikibase exports automatically. Mozart-style publishing pipeline as separate layer on top of investigative notebooks - transforms mature research into shareable wiki pages without disrupting active investigation workflow.

---

[Continue with remaining sections from v3_INTEGRATED_FUTURE.md, removing references to "your existing deep_research.py" and replacing with either "manual extraction" (for Stage 1-3) or "simple research layer" (for Full PoC/V1)]

**NOTE**: For complete data model, workflows, and uncertainty sections, see remaining sections in this document. The key differences from v3_INTEGRATED_FUTURE.md are:

1. **Research Layer**: Standalone (public sources → simple web search + LLM), not integrated with external tools
2. **Stage 1-3**: Manual extraction from public investigative reports
3. **Full PoC/V1**: Optional simple research implementation OR integration adapter (user choice)
4. **Philosophy**: Prove value in isolation before considering integration

---

## Design Principles for Standalone V1

### 1. Validate Before Integrating

**Stage 1-3 proves**:
- Entity extraction adds value
- CLI tools are useful
- LLM automation works

**Only after validation**:
- Consider building simple research layer
- OR consider integration adapters to external tools

### 2. Simple Research Layer (Option A for Full PoC/V1)

If you want fully standalone system:

```python
class SimpleResearchClient:
    def run_research(self, query: str, params: dict) -> ResearchResult:
        # 1. Generate 3-5 targeted queries
        queries = generate_queries(query)

        # 2. Search via Brave/Tavily
        results = []
        for q in queries:
            results.extend(brave_search(q, limit=10))

        # 3. Fetch page content
        pages = [fetch_content(r.url) for r in results]

        # 4. LLM summarization
        report = llm_summarize(query, pages)
        entities = llm_extract_entities(pages)

        return ResearchResult(
            report_md=report,
            citations=[...],
            entities=entities
        )
```

**Advantages**:
- No external dependencies
- Full control over search strategy
- Simple to understand and debug
- Can preserve boolean logic exactly

**Disadvantages**:
- Less sophisticated than specialized frameworks
- More code to maintain
- May miss advanced features (multi-step reasoning, adaptive planning)

### 3. Integration Adapters (Option B for Phase 2+)

If Stage 1-3 validates AND you want advanced features:

See `v3_INTEGRATED_FUTURE.md` for integration architecture with existing research tools.

**Recommendation**: Build standalone first (Option A), add integration later (Option B) if needed.

---

## Appendix: Test Data Sources for Stage 1

See `./test_data/README.md` for detailed list of public investigative sources suitable for entity extraction testing.

**Recommended starting points**:
1. Bellingcat MH17 investigation
2. ProPublica "Machine Bias" series
3. CIA FOIA reading room on Operation Mockingbird
4. NYT "Penetrating the Kremlin" investigation

These provide:
- Rich entity sets (people, orgs, programs)
- Cross-document entity recurrence
- Investigative journalism depth
- Publicly accessible content
