# Prompt Design Philosophy

## Core Principle: Trust the LLM

The LLM receiving these prompts is intelligent. Give it context and let it reason.

Essential elements:
1. **What the source contains** (factual description)
2. **The goal** (what we're trying to achieve)
3. **The output format** (JSON structure)

## The Key Distinction: Empirical vs Opinion

**GOOD: Empirical/factual guidance** - Based on testing or documentation
**BAD: Opinion/assumption** - Based on what you think might work

### Query Tips

**GOOD** (empirically tested):
```
USAJobs API query syntax (tested 2025-10-25):
- "cybersecurity" returns 44 results
- "cybersecurity analyst" returns 1 result
- Three+ keywords returns 0 results

The API is sensitive to query complexity.
```

**BAD** (just opinion):
```
QUERY TIPS:
- Use proper names when available
- Keep queries focused
- Avoid generic terms
```

### Examples

**GOOD** (illustrates actual API behavior):
```
Query "Northrop Grumman cybersecurity" → 0 results (company filtering broken)
Query "cybersecurity" → 200+ results
```

**BAD** (just aesthetic preference):
```
GOOD EXAMPLES:
- ["Ukraine", "Bakhmut", "Wagner"]
```

### Relevance Guidance

**GOOD** (factual disambiguation between sources):
```
SAM.gov has contracting OPPORTUNITIES (pre-award).
USAspending has awarded CONTRACTS (post-award).

If question says "contracts" without "opportunities/solicitations",
it likely means awarded contracts → USAspending is relevant.
```

**BAD** (arbitrary checklist):
```
✅ RELEVANT: Espionage, terrorism, organized crime
❌ NOT RELEVANT: Corporate matters, job listings
```

## What IS Allowed

- **Factual API constraints** - Max chars, enum values, rate limits
- **Empirically tested syntax** - Actual test results showing what works/fails
- **Source disambiguation** - Factual differences between similar sources
- **Output format** - JSON structure with field descriptions

## What is NOT Allowed

- **Made-up content inventories** - Don't list what you think a source contains
- **Opinion-based tips** - Don't tell LLM how to write queries based on assumptions
- **Arbitrary checklists** - Don't enumerate topics you think are relevant
- **Untested examples** - Don't show "good" queries you haven't verified

## Template Structure

```jinja
{# temporal_context: true #}
Generate search parameters for [Source Name].

[Source Name] provides: [Factual description]

[If empirically tested: document actual API behavior]

Research Question: {{ research_question }}

Generate [query/parameters] that would effectively find relevant results.

Return JSON:
{% raw %}
{
  "field": "description"
}
{% endraw %}
```

## Temporal Context

All prompts should include `{# temporal_context: true #}` at the top.
This tells prompt_loader.py to inject current date context.
