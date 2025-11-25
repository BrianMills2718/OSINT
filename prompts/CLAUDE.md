# Prompt Design Philosophy

## Core Principle: Trust the LLM

**Do NOT hardcode heuristics, rules, or prescriptive guidance.**

The LLM receiving these prompts is intelligent. Give it:
1. **What the source contains** (factual description)
2. **The goal** (what we're trying to achieve)
3. **The output format** (JSON structure)

Let it reason about the best approach.

## Anti-Patterns (FORBIDDEN)

```
❌ QUERY TIPS:
   - Use proper names when available
   - Keep queries focused - 1-3 terms work best
   - Avoid generic terms

❌ GOOD EXAMPLES:
   - ["Ukraine", "Bakhmut", "Wagner"]

❌ RELEVANCE CRITERIA:
   ✅ RELEVANT: Topic A, Topic B
   ❌ NOT RELEVANT: Topic C, Topic D

❌ AVOID:
   - Generic terms
   - Overly complex queries
```

These hardcode assumptions and prevent intelligent reasoning.

## Correct Pattern

```jinja
{# temporal_context: true #}
Generate search parameters for [Source Name].

[Source Name] provides: [Factual description of what the source contains]

Research Question: {{ research_question }}

Generate [query/parameters] that would effectively find relevant [documents/results].

Return JSON:
{% raw %}
{
  "field1": "description",
  "field2": "description"
}
{% endraw %}
```

## What IS Allowed

- **Factual API documentation** - If the API has specific parameter constraints (e.g., max 200 chars, specific enum values), document those
- **Empirically tested syntax** - If testing revealed that certain query syntax returns 0 results, that's factual (see reddit_query_generation.j2)
- **Output format specification** - JSON structure with field names

## What is NOT Allowed

- **Made-up content inventories** - Don't list what you think a source contains unless you've verified it
- **Prescriptive query tips** - Don't tell the LLM how to write queries
- **Relevance checklists** - Don't enumerate what is/isn't relevant
- **Examples of "good" queries** - Let the LLM figure out what works

## Temporal Context

All prompts should include `{# temporal_context: true #}` at the top.
This tells prompt_loader.py to inject current date context.
