#!/usr/bin/env python3
"""
Script to migrate deep_research.py prompts to Jinja2 templates.

Replaces f-string prompts with render_prompt() calls for 5 remaining methods.
"""
import re

# Read the file
with open('research/deep_research.py', 'r') as f:
    content = f.read()

# 1. Migrate _decompose_question() - lines ~569-589
old_decompose = '''    async def _decompose_question(self, question: str) -> List[ResearchTask]:
        """Use LLM to break question into 3-5 initial research tasks."""
        prompt = f"""Break this complex research question into 3-5 specific, focused search tasks.

Research Question: {question}

Each task should be:
- A clear, searchable query (can be used with database search or web search)
- Focused on one aspect of the overall question
- Likely to return concrete results (not too broad, not too narrow)
- Simple keyword-based queries (avoid complex Boolean operators like OR, AND, NOT)
- No site filters (site:gov) or date ranges (2015..2025) - these reduce results
- Natural language queries work best (e.g., "government surveillance contracts Palantir" instead of "site:gov contract Palantir OR Clearview")

IMPORTANT - Query Intent:
- For definitional queries (what is X?), create subtasks that seek OFFICIAL DESCRIPTIONS and DOCUMENTATION, not examples of content
- For content queries (what content does X provide?), ask about CONTENT CATEGORIES and TYPES, not specific examples
- Example (CORRECT): "Find official documentation about DVIDS mission and purpose" → targets reference material
- Example (WRONG): "DVIDS photos videos multimedia gallery" → targets event media, not documentation

Return tasks in priority order (most important first).
"""'''

new_decompose = '''    async def _decompose_question(self, question: str) -> List[ResearchTask]:
        """Use LLM to break question into 3-5 initial research tasks."""
        prompt = render_prompt(
            "deep_research/task_decomposition.j2",
            question=question
        )'''

content = content.replace(old_decompose, new_decompose)

# 2. Migrate _select_relevant_sources() - lines ~757-790
#    Note: This one is more complex due to the options_text variable
old_select_sources = '''        prompt = f"""Select which sources should be queried for this research subtask.

Original research question: "{self.original_question}"
Task query: "{query}"

Available sources:
{options_text}

IMPORTANT: Default to exploring sources broadly. Include any source that might plausibly help answer the query. When uncertain, investigate rather than skip. Always include Brave Search unless you are very confident it won't help.

Return a JSON list of tool names (e.g., "search_dvids", "brave_search")."""'''

new_select_sources = '''        prompt = render_prompt(
            "deep_research/source_selection.j2",
            research_question=self.original_question,
            query=query,
            options_text=options_text
        )'''

content = content.replace(old_select_sources, new_select_sources)

# 3. Migrate _extract_entities() - lines ~1427-1456
old_extract_entities = '''        prompt = f"""Extract key entities (people, organizations, programs, operations) from these search results.

CONTEXT:
- Original research question: "{research_question}"
- Search query used: "{task_query}"

Use the context to disambiguate acronyms and focus on entities relevant to the research question.

Results:
{results_text}

Return a JSON list of entity names (3-10 entities). Focus on named entities that:
1. Are RELEVANT to the research question
2. Could be researched further
3. Match the domain of the research question (e.g., if researching cybersecurity contracts, focus on companies, agencies, programs in that domain)

Examples (matching the research domain):
- Research question about "JSOC operations" → ["Joint Special Operations Command", "CIA", "Operation Cyclone"]
- Research question about "NSA cybersecurity contracts" → ["National Security Agency", "Palantir", "Booz Allen Hamilton", "Leidos"]
- Research question about "FBI surveillance programs" → ["Federal Bureau of Investigation", "PRISM", "FISA Court"]

DO NOT extract generic entities unrelated to the research question.
"""'''

new_extract_entities = '''        prompt = render_prompt(
            "deep_research/entity_extraction.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )'''

content = content.replace(old_extract_entities, new_extract_entities)

# 4. Migrate _validate_result_relevance() - lines ~1524-1550
old_validate_relevance = '''        prompt = f"""Evaluate whether these search results are relevant to the research question.

Original Research Question: "{research_question}"
Search Query Used: "{task_query}"

Sample Results:
{results_text}

Score the relevance of these results on a scale of 0-10:
- 10: Highly relevant - directly answers the research question
- 7-9: Relevant - related to the topic but may be indirect
- 4-6: Somewhat relevant - mentions key terms but not focused on the topic
- 1-3: Barely relevant - only tangentially related
- 0: Completely off-topic - wrong domain or subject matter entirely

IMPORTANT:
- If the results are about a DIFFERENT entity with the same acronym (e.g., "Naval Support Activity" when asked about "National Security Agency"), score 0-2 (wrong entity).
- If the results are in the wrong domain (e.g., military logistics when asked about cybersecurity contracts), score 0-3.

Return the relevance score and a brief reason.
"""'''

new_validate_relevance = '''        prompt = render_prompt(
            "deep_research/relevance_evaluation.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )'''

content = content.replace(old_validate_relevance, new_validate_relevance)

# 5. Migrate _reformulate_query_simple() - lines ~1684-1727 (escaped JSON with {{)
old_reformulate_simple = '''        prompt = f"""The search query returned insufficient results. Reformulate it to be more effective.

Original Query: {original_query}
Results Found: {results_count}

Reformulate the query to:
- Be BROADER and SIMPLER to get more results
- Remove complex Boolean operators (OR, AND, NOT) if present
- Remove site filters (site:gov) or date ranges (2015..2025) if present
- Use natural language keywords instead of structured queries
- Try different terminology or synonyms
- Focus on core concepts, not specific details

Examples:
- "site:gov contract (Palantir OR Clearview)" → "government contracts Palantir Clearview surveillance"
- "investigation report lawsuit 2018..2025" → "investigation reports lawsuits surveillance privacy"

OPTIONAL - Source-Specific Parameter Adjustments:
If the query would benefit from adjusting source-specific parameters, suggest them:

Reddit parameters:
- time_filter: "hour" | "day" | "week" | "month" | "year" | "all"
  (Use "year" or "all" to get more historical results)

USAJobs parameters:
- keywords: Prefer single broad keyword over multi-word phrases
  (e.g., "analyst" gets more results than "intelligence analyst senior")

Return JSON with:
{{
  "query": "new query text (broader and simpler)",
  "param_adjustments": {{
    "reddit": {{"time_filter": "year"}},
    "usajobs": {{"keywords": "broad keyword"}}
  }}
}}
"""'''

new_reformulate_simple = '''        prompt = render_prompt(
            "deep_research/query_reformulation_simple.j2",
            original_query=original_query,
            results_count=results_count
        )'''

content = content.replace(old_reformulate_simple, new_reformulate_simple)

# 6. Migrate _synthesize_report() - lines ~1926-1965
old_synthesize_report = '''        prompt = f"""Synthesize these research findings into a comprehensive report.

Original Question: {original_question}

Research Summary:
- Tasks Executed: {len(self.completed_tasks)}
- Total Results: {len(all_results)}
- Entities Discovered: {len(self.entity_graph)}

Entity Relationships:
{chr(10).join(relationship_summary)}

Top Findings (from {len(all_results)} results):
{json.dumps(all_results[:20], indent=2)}

Create a detailed markdown report with:

# Research Report: [Title based on question]

## Executive Summary
[3-5 sentences summarizing key findings]

## Key Findings
[Bullet points of most important discoveries]

## Detailed Analysis
[2-3 paragraphs analyzing the findings, connecting entities, explaining relationships]

## Entity Network
[Description of key entities and their relationships]

## Sources
[List of unique sources consulted]

## Methodology
[Brief note on research approach - {len(self.completed_tasks)} tasks, {len(all_results)} results]

Make the report insightful and well-structured. Focus on connections and relationships, not just listing results.
"""'''

new_synthesize_report = '''        prompt = render_prompt(
            "deep_research/report_synthesis.j2",
            original_question=original_question,
            tasks_executed=len(self.completed_tasks),
            total_results=len(all_results),
            entities_discovered=len(self.entity_graph),
            relationship_summary=chr(10).join(relationship_summary),
            top_findings_json=json.dumps(all_results[:20], indent=2)
        )'''

content = content.replace(old_synthesize_report, new_synthesize_report)

# Write the updated file
with open('research/deep_research.py', 'w') as f:
    f.write(content)

print("✅ Migration complete!")
print("Migrated 5 prompts:")
print("  1. _decompose_question() → task_decomposition.j2")
print("  2. _select_relevant_sources() → source_selection.j2")
print("  3. _extract_entities() → entity_extraction.j2")
print("  4. _validate_result_relevance() → relevance_evaluation.j2")
print("  5. _reformulate_query_simple() → query_reformulation_simple.j2")
print("  6. _synthesize_report() → report_synthesis.j2")
