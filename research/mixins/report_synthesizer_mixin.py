#!/usr/bin/env python3
"""
Report synthesis mixin for deep research.

Provides report generation and formatting capabilities.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion
from integrations.registry import registry

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class ReportSynthesizerMixin:
    """
    Mixin providing report synthesis and formatting.

    Requires host class to have:
        - self.results_by_task: Dict[int, Dict]
        - self.completed_tasks: List[ResearchTask]
        - self.failed_tasks: List[ResearchTask]
        - self.entity_graph: Dict[str, List[str]]
        - self.original_question: str
        - self.integrations: List[str]
        - self.hypothesis_branching_enabled: bool
        - self.critical_source_failures: List[str]
    """

    def _format_synthesis_json_to_markdown(self: "SimpleDeepResearch", json_data: Dict) -> str:
        """
        Convert structured synthesis JSON to markdown report.

        NO DECISION LOGIC - just formatting/templating.
        All intelligence decisions (grouping, reliability assessment, etc.) come from LLM.
        """
        try:
            report_data = json_data.get("report", {})
        except (AttributeError, TypeError):
            # If json_data is malformed, return error
            return "# Error: Invalid synthesis JSON structure\n\nThe synthesis LLM returned malformed JSON."

        md = []

        # Title
        title = report_data.get("title", "Research Report")
        md.append(f"# {title}\n\n")

        # Executive Summary
        exec_summary = report_data.get("executive_summary", {})
        md.append("## Executive Summary\n\n")
        md.append(f"{exec_summary.get('text', 'No summary provided.')}\n\n")

        if exec_summary.get("key_points"):
            md.append("**Key Points:**\n\n")
            for kp in exec_summary["key_points"]:
                point = kp.get("point", "")
                citations = kp.get("inline_citations", [])
                citation_links = []
                for c in citations:
                    title_str = c.get("title", "Source")
                    url_str = c.get("url", "")
                    date_str = c.get("date")
                    link = f"[{title_str}]({url_str})"
                    if date_str:
                        link += f" ({date_str})"
                    citation_links.append(link)

                citations_str = ", ".join(citation_links) if citation_links else "No citations"
                md.append(f"- {point} — {citations_str}\n")
            md.append("\n")

        # Source Groups (Key Findings)
        source_groups = report_data.get("source_groups", [])
        if source_groups:
            md.append("## Key Findings\n\n")
            for group in source_groups:
                group_name = group.get("group_name", "Unknown Group")
                group_desc = group.get("group_description", "")
                reliability = group.get("reliability_context", "")

                md.append(f"### {group_name}\n\n")
                if reliability:
                    md.append(f"*{reliability}*\n\n")

                findings = group.get("findings", [])
                for finding in findings:
                    claim = finding.get("claim", "")
                    citations = finding.get("inline_citations", [])
                    supporting = finding.get("supporting_detail")

                    citation_links = []
                    for c in citations:
                        title_str = c.get("title", "Source")
                        url_str = c.get("url", "")
                        date_str = c.get("date")
                        source_str = c.get("source", "")
                        link = f"[{title_str}]({url_str})"
                        if date_str:
                            link += f", {date_str}"
                        citation_links.append(link)

                    citations_str = "; ".join(citation_links) if citation_links else "No citations"
                    md.append(f"- {claim} ({citations_str})\n")

                    if supporting:
                        md.append(f"  > {supporting}\n")

                md.append("\n")

        # Entity Network
        entity_network = report_data.get("entity_network", {})
        if entity_network:
            md.append("## Entity Network\n\n")
            md.append(f"{entity_network.get('description', 'No entity description provided.')}\n\n")

            key_entities = entity_network.get("key_entities", [])
            if key_entities:
                for entity in key_entities:
                    name = entity.get("name", "Unknown Entity")
                    context = entity.get("context", "")
                    relationships = entity.get("relationships", [])

                    md.append(f"**{name}**: {context}\n")
                    for rel in relationships:
                        md.append(f"  - {rel}\n")
                    md.append("\n")

        # Timeline
        timeline = report_data.get("timeline", [])
        if timeline:
            md.append("## Timeline\n\n")
            for item in timeline:
                date = item.get("date", "Unknown date")
                event = item.get("event", "")
                sources = item.get("sources", [])

                source_links = []
                for s in sources:
                    s_title = s.get("title", "Source")
                    s_url = s.get("url", "")
                    source_links.append(f"[{s_title}]({s_url})")

                sources_str = ", ".join(source_links) if source_links else ""
                md.append(f"- **{date}**: {event}")
                if sources_str:
                    md.append(f" ({sources_str})")
                md.append("\n")
            md.append("\n")

        # Methodology
        methodology = report_data.get("methodology", {})
        if methodology:
            md.append("## Methodology\n\n")
            approach = methodology.get("approach", "No methodology description provided.")
            md.append(f"{approach}\n\n")

            tasks_exec = methodology.get("tasks_executed", 0)
            total_res = methodology.get("total_results", 0)
            entities_disc = methodology.get("entities_discovered", 0)
            integrations = methodology.get("integrations_used", [])
            coverage = methodology.get("coverage_summary", {})

            md.append(f"- **Tasks executed**: {tasks_exec}\n")
            md.append(f"- **Total results**: {total_res}\n")
            md.append(f"- **Entities discovered**: {entities_disc}\n")
            md.append(f"- **Integrations used**: {', '.join(integrations) if integrations else 'None'}\n\n")

            if coverage:
                md.append("**Coverage Summary:**\n\n")
                for source, count in coverage.items():
                    md.append(f"- {source}: {count} results\n")
                md.append("\n")

        # Quality Check (optional footer)
        quality_check = report_data.get("synthesis_quality_check", {})
        if quality_check:
            limitations = quality_check.get("limitations_noted")
            if limitations:
                md.append("## Research Limitations\n\n")
                md.append(f"{limitations}\n\n")

        return "".join(md)

    async def _synthesize_report(self: "SimpleDeepResearch", original_question: str) -> str:
        """Synthesize all findings into comprehensive report."""
        # Collect all results
        all_results = []
        for task_id, result in self.results_by_task.items():
            task = next((t for t in self.completed_tasks if t.id == task_id), None)
            if task:
                for r in result.get('results', []):  # Send ALL results to synthesis (no sampling)
                    all_results.append({
                        'task_query': task.query,
                        'title': r.get('title', ''),
                        'source': r.get('source', ''),
                        'snippet': r.get('snippet', r.get('description', ''))[:300],
                        'url': r.get('url', '')
                    })

        # Global cross-task deduplication by URL
        original_count = len(all_results)
        deduplicated_results = []
        seen_urls = set()

        for result in all_results:
            url = result.get('url', '').strip()
            if not url:
                # No URL - keep result as-is (can't deduplicate)
                deduplicated_results.append(result)
                continue

            if url not in seen_urls:
                seen_urls.add(url)
                deduplicated_results.append(result)
            # else: skip duplicate

        duplicate_count = original_count - len(deduplicated_results)
        if duplicate_count > 0:
            print(f"🔗 Global deduplication: {original_count} → {len(deduplicated_results)} results ({duplicate_count} cross-task duplicates removed)")

        all_results = deduplicated_results

        # Task 2: LLM-based entity filtering (replaces Python blacklist)
        # Count entity occurrences across tasks for filtering
        entity_task_counts = {}
        for task in self.completed_tasks:
            task_entities = set(e.strip().lower() for e in task.entities_found if e.strip())
            for entity in task_entities:
                entity_task_counts[entity] = entity_task_counts.get(entity, 0) + 1

        # Format entities with counts for LLM filtering
        entities_with_counts = "\n".join([
            f"- {entity} (appeared in {count} task{'s' if count > 1 else ''})"
            for entity, count in sorted(entity_task_counts.items(), key=lambda x: x[1], reverse=True)
        ])

        # Call LLM to filter entities
        all_entities_list = list(self.entity_graph.keys())
        if all_entities_list:
            try:
                print(f"🔍 Filtering {len(all_entities_list)} entities using LLM...")
                entity_filter_prompt = render_prompt(
                    "deep_research/entity_filtering.j2",
                    research_question=self.original_question,
                    tasks_completed=len(self.completed_tasks),
                    total_entities=len(all_entities_list),
                    entities_with_counts=entities_with_counts
                )

                entity_filter_schema = {
                    "type": "object",
                    "properties": {
                        "filtered_entities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of entities to KEEP (exclude low-value/generic ones)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of filtering decisions"
                        }
                    },
                    "required": ["filtered_entities", "reasoning"],
                    "additionalProperties": False
                }

                entity_filter_response = await acompletion(
                    model=config.get_model("analysis"),
                    messages=[{"role": "user", "content": entity_filter_prompt}],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "strict": True,
                            "name": "entity_filtering",
                            "schema": entity_filter_schema
                        }
                    }
                )

                filter_result = json.loads(entity_filter_response.choices[0].message.content)
                filtered_entity_names = set(e.lower() for e in filter_result.get("filtered_entities", []))
                filter_reasoning = filter_result.get("reasoning", "")

                # Update entity_graph to only include filtered entities
                filtered_entity_graph = {
                    entity: related
                    for entity, related in self.entity_graph.items()
                    if entity.lower() in filtered_entity_names
                }

                entities_filtered_out = len(self.entity_graph) - len(filtered_entity_graph)
                print(f"✓ Entity filtering: Removed {entities_filtered_out} entities ({len(self.entity_graph)} → {len(filtered_entity_graph)} kept)")
                print(f"  Reasoning: {filter_reasoning}")

                # Replace entity graph with filtered version
                self.entity_graph = filtered_entity_graph

            # Integration execution failure - log and continue with other integrations
            except Exception as e:
                logger.error(f"Entity filtering failed: {type(e).__name__}: {str(e)}", exc_info=True)
                print(f"⚠️  Entity filtering failed (using all entities): {type(e).__name__}")
                # On error, keep all entities (don't want to lose valid data)

        # Compile entity relationships (send filtered entities to synthesis)
        relationship_summary = []
        for entity, related in list(self.entity_graph.items()):  # Filtered entities only
            relationship_summary.append(f"- {entity}: connected to {', '.join(related)}")  # All relationships

        # Task 2A Fix: Use actual total_results from results_by_task instead of len(all_results[:20])
        actual_total_results = sum(r.get('total_results', 0) for r in self.results_by_task.values())

        # Task 2B: Separate integrations from discovered websites
        all_sources = list(set(r.get('source', 'Unknown') for r in all_results))
        integration_names = [registry.get_display_name(id) for id in self.integrations]

        integrations_used = [s for s in all_sources if s in integration_names]
        websites_found = [s for s in all_sources if s not in integration_names and s != 'Unknown']

        # Coverage snapshot: per-source result counts
        source_counts = {}
        for r in all_results:
            source = r.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        # Phase 1: Collect task diagnostics WITH reasoning notes
        task_diagnostics = []
        for task in self.completed_tasks:
            task_result = self.results_by_task.get(task.id, {})
            task_diagnostics.append({
                "id": task.id,
                "query": task.query,
                "status": "COMPLETED",
                "results_kept": task_result.get('total_results', 0),
                "results_total": task.accumulated_results and len(task.accumulated_results) or 0,
                "continuation_reason": "Task completed successfully",
                "reasoning_notes": task.reasoning_notes  # Phase 1: Include LLM reasoning breakdowns
            })

        # Sanity metrics: lightweight counts to spot regressions quickly
        sanity_metrics = []
        for task in self.completed_tasks:
            task_result = self.results_by_task.get(task.id, {})
            hypo_runs = getattr(task, "hypothesis_runs", []) or []
            sanity_metrics.append({
                "id": task.id,
                "query": task.query,
                "total_results": task_result.get('total_results', 0),
                "hypotheses_executed": len(hypo_runs),
                "hypothesis_result_counts": [run.get("results_count", 0) for run in hypo_runs]
            })

        # Phase 3A/B/C: Collect hypotheses and coverage decisions if enabled
        hypotheses_by_task = {}
        task_queries = {}
        hypothesis_execution_summary = {}
        coverage_decisions_by_task = {}  # Phase 3C
        hypothesis_id_to_statement = {}
        if self.hypothesis_branching_enabled:
            for task in (self.completed_tasks + self.failed_tasks):
                task_queries[task.id] = task.query
                if task.hypotheses:
                    hypotheses_by_task[task.id] = task.hypotheses
                    for hyp in task.hypotheses.get("hypotheses", []):
                        hypothesis_id_to_statement[hyp.get("id")] = hyp.get("statement", "")
                if task.hypothesis_runs:
                    hypothesis_execution_summary[task.id] = task.hypothesis_runs
                # Phase 3C: Collect coverage decisions
                if hasattr(task, 'metadata') and 'coverage_decisions' in task.metadata:
                    coverage_decisions_by_task[task.id] = task.metadata['coverage_decisions']

        # Build hypothesis findings: counts and sample links per hypothesis_id
        hypothesis_findings = []
        if hypothesis_id_to_statement:
            results_by_hypothesis = {}
            for r in all_results:
                hyp_ids = []
                if "hypothesis_ids" in r:
                    hyp_ids.extend(r.get("hypothesis_ids", []))
                if "hypothesis_id" in r:
                    hyp_ids.append(r.get("hypothesis_id"))
                if not hyp_ids:
                    continue
                for hid in hyp_ids:
                    results_by_hypothesis.setdefault(hid, []).append(r)

            for hid, res_list in results_by_hypothesis.items():
                samples = []
                for item in res_list[:3]:
                    if item.get("url"):
                        samples.append({
                            "title": item.get("title", "") or item.get("snippet", "")[:80],
                            "url": item.get("url", ""),
                            "source": item.get("source", "Unknown"),
                            "date": item.get("date")
                        })
                hypothesis_findings.append({
                    "hypothesis_id": hid,
                    "statement": hypothesis_id_to_statement.get(hid, ""),
                    "total_results": len(res_list),
                    "sample_results": samples
                })

        # Key documents: top results with URLs for quick access (default to empty safe values)
        key_documents = []
        for item in all_results:
            if item.get("url"):
                key_documents.append({
                    "title": item.get("title", "") or item.get("snippet", "")[:80],
                    "url": item.get("url", ""),
                    "source": item.get("source", "Unknown"),
                    "date": item.get("date")
                })
            if len(key_documents) >= 5:
                break

        # Basic timeline from dated items (if any)
        timeline = []
        for item in all_results:
            if item.get("date") and item.get("url"):
                timeline.append({
                    "date": item.get("date"),
                    "title": item.get("title", "") or item.get("snippet", "")[:80],
                    "url": item.get("url", "")
                })
            if len(timeline) >= 5:
                break

        prompt = render_prompt(
            "deep_research/report_synthesis.j2",
            original_question=original_question,
            tasks_executed=len(self.completed_tasks),
            total_results=actual_total_results,
            entities_discovered=len(entity_task_counts),
            relationship_summary=chr(10).join(relationship_summary),
            top_findings_json=json.dumps(all_results, indent=2),  # Send ALL findings to synthesis
            integrations_used=integrations_used,
            websites_found=websites_found,
            task_diagnostics=task_diagnostics,
            hypotheses_by_task=hypotheses_by_task,  # Phase 3A
            task_queries=task_queries,  # Phase 3A
            hypothesis_execution_summary=hypothesis_execution_summary,  # Phase 3B
            coverage_decisions_by_task=coverage_decisions_by_task,  # Phase 3C
            sanity_metrics=sanity_metrics,  # Sanity checks
            source_counts=source_counts,  # Coverage snapshot
            hypothesis_findings=hypothesis_findings,
            key_documents=key_documents,
            timeline=timeline,
            current_date=datetime.now(timezone.utc).date().isoformat()
        )

        report = None
        synthesis_json = None

        try:
            # Call LLM for structured JSON synthesis
            response = await acompletion(
                model=config.get_model("synthesis"),  # Use best model for synthesis
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}  # Enforce JSON output
            )

            # Parse JSON response
            synthesis_json = json.loads(response.choices[0].message.content)

            # Add critical source failures to limitations if needed
            if self.critical_source_failures:
                limitations_text = synthesis_json.get("report", {}).get("synthesis_quality_check", {}).get("limitations_noted", "")
                critical_failures_text = "Critical sources unavailable: " + ", ".join(self.critical_source_failures) + ". This research may be incomplete."

                if limitations_text:
                    synthesis_json["report"]["synthesis_quality_check"]["limitations_noted"] = f"{limitations_text}\n\n{critical_failures_text}"
                else:
                    synthesis_json["report"]["synthesis_quality_check"]["limitations_noted"] = critical_failures_text

            # Convert JSON to Markdown using formatter (NO decision logic, just templating)
            report = self._format_synthesis_json_to_markdown(synthesis_json)

            # Log synthesis quality check
            quality_check = synthesis_json.get("report", {}).get("synthesis_quality_check", {})
            all_have_citations = quality_check.get("all_claims_have_citations", False)
            grouping_reasoning = quality_check.get("source_grouping_reasoning", "")

            print(f"✓ Synthesis complete:")
            print(f"  - All claims have citations: {all_have_citations}")
            print(f"  - Source grouping strategy: {grouping_reasoning[:100]}...")

            if not all_have_citations:
                print(f"⚠️  WARNING: LLM reported not all claims have citations!")

        except json.JSONDecodeError as e:
            logger.error(f"Synthesis JSON parsing failed: {e}", exc_info=True)
            logger.error(f"Synthesis JSON parsing failed: {e}")
            report = f"# Research Report\n\nFailed to parse synthesis JSON.\n\nError: {e}\n\n## Raw Statistics\n\n- Tasks Executed: {len(self.completed_tasks)}\n- Tasks Failed: {len(self.failed_tasks)}\n"
        # Critical failure - report synthesis is the final output
        except Exception as e:
            logger.error(f"Synthesis failed: {type(e).__name__}: {e}", exc_info=True)
            report = f"# Research Report\n\nFailed to synthesize final report.\n\nError: {type(e).__name__}: {e}\n\n## Raw Statistics\n\n- Tasks Executed: {len(self.completed_tasks)}\n- Tasks Failed: {len(self.failed_tasks)}\n"

        return report
