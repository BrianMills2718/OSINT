#!/usr/bin/env python3
"""
Test synthesis JSON → Markdown formatter.
Validates that the formatter correctly converts structured JSON to markdown without making decisions.
"""

import sys
sys.path.insert(0, '/home/brian/sam_gov')

from research.deep_research import SimpleDeepResearch


def test_synthesis_formatter():
    """Test JSON to Markdown formatter with sample data."""

    # Sample structured synthesis JSON
    sample_json = {
        "report": {
            "title": "Research Report: Test Synthesis",

            "executive_summary": {
                "text": "This is a test of the structured synthesis formatter with inline citations.",
                "key_points": [
                    {
                        "point": "First key finding about government contracts",
                        "inline_citations": [
                            {
                                "title": "SAM.gov Contract Award",
                                "url": "https://sam.gov/example1",
                                "date": "2025-11-15",
                                "source": "SAM.gov"
                            }
                        ]
                    },
                    {
                        "point": "Second finding about job market trends",
                        "inline_citations": [
                            {
                                "title": "USAJobs Posting",
                                "url": "https://usajobs.gov/example2",
                                "date": None,
                                "source": "USAJobs"
                            },
                            {
                                "title": "ClearanceJobs Analysis",
                                "url": "https://clearancejobs.com/example3",
                                "date": "2025-11-20",
                                "source": "ClearanceJobs"
                            }
                        ]
                    }
                ]
            },

            "source_groups": [
                {
                    "group_name": "Official Government Sources",
                    "group_description": "Direct from federal agencies and departments",
                    "reliability_context": "Highly reliable - authoritative government data",
                    "findings": [
                        {
                            "claim": "Department of Defense awarded $50M contract to Example Corp",
                            "inline_citations": [
                                {
                                    "title": "DoD Contract Award Notice",
                                    "url": "https://sam.gov/contract1",
                                    "date": "2025-10-15",
                                    "source": "SAM.gov"
                                }
                            ],
                            "supporting_detail": "Contract for cybersecurity services over 3-year period"
                        },
                        {
                            "claim": "TS/SCI clearance required for NSA cyber analyst positions",
                            "inline_citations": [
                                {
                                    "title": "NSA Job Posting JOB-12345",
                                    "url": "https://usajobs.gov/job12345",
                                    "date": "2025-11-01",
                                    "source": "USAJobs"
                                }
                            ],
                            "supporting_detail": None
                        }
                    ]
                },
                {
                    "group_name": "Community Discussions",
                    "group_description": "User experiences and perspectives from online communities",
                    "reliability_context": "Valuable context but requires verification - anecdotal experiences",
                    "findings": [
                        {
                            "claim": "Reddit users report 6-12 month delays for polygraph clearances",
                            "inline_citations": [
                                {
                                    "title": "r/SecurityClearance Discussion Thread",
                                    "url": "https://reddit.com/r/SecurityClearance/example",
                                    "date": "2025-10-20",
                                    "source": "Reddit"
                                }
                            ],
                            "supporting_detail": "Multiple users reported similar timelines in October 2025"
                        }
                    ]
                }
            ],

            "entity_network": {
                "description": "Key entities include government agencies (DoD, NSA) and contractors (Example Corp) connected through contract awards and hiring.",
                "key_entities": [
                    {
                        "name": "Department of Defense",
                        "relationships": ["awarded contracts to Example Corp", "employs NSA"],
                        "context": "Primary customer for cleared cybersecurity services"
                    },
                    {
                        "name": "Example Corp",
                        "relationships": ["received DoD contract", "hires cleared professionals"],
                        "context": "Major defense contractor for cyber services"
                    }
                ]
            },

            "timeline": [
                {
                    "date": "2025-10-15",
                    "event": "DoD awards $50M contract to Example Corp",
                    "sources": [
                        {
                            "title": "Contract Award Notice",
                            "url": "https://sam.gov/contract1"
                        }
                    ]
                },
                {
                    "date": "2025-11-01",
                    "event": "NSA posts new cyber analyst positions requiring TS/SCI",
                    "sources": [
                        {
                            "title": "USAJobs Posting",
                            "url": "https://usajobs.gov/job12345"
                        }
                    ]
                }
            ],

            "methodology": {
                "approach": "Multi-source research combining government databases, job boards, and community discussions",
                "tasks_executed": 3,
                "total_results": 15,
                "entities_discovered": 8,
                "integrations_used": ["SAM.gov", "USAJobs", "Reddit"],
                "coverage_summary": {
                    "SAM.gov": 5,
                    "USAJobs": 7,
                    "Reddit": 3
                }
            },

            "synthesis_quality_check": {
                "all_claims_have_citations": True,
                "source_grouping_reasoning": "Grouped by authority level: official government sources vs community experiences",
                "limitations_noted": "Reddit data is anecdotal and not officially verified"
            }
        }
    }

    # Create engine instance to access formatter
    engine = SimpleDeepResearch()

    # Format JSON to Markdown
    markdown = engine._format_synthesis_json_to_markdown(sample_json)

    print("=" * 80)
    print("SYNTHESIS FORMATTER TEST")
    print("=" * 80)
    print("\n[Generated Markdown]\n")
    print(markdown)
    print("\n" + "=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)

    # Validation checks
    checks = []

    # Check 1: Title present
    if "# Research Report: Test Synthesis" in markdown:
        checks.append("✅ Title formatted correctly")
    else:
        checks.append("❌ Title missing or incorrect")

    # Check 2: Executive summary present
    if "## Executive Summary" in markdown:
        checks.append("✅ Executive summary section present")
    else:
        checks.append("❌ Executive summary section missing")

    # Check 3: Inline citations in key points
    if "[SAM.gov Contract Award](https://sam.gov/example1)" in markdown:
        checks.append("✅ Inline citation in key points formatted correctly")
    else:
        checks.append("❌ Inline citation in key points missing or incorrect")

    # Check 4: Source groups present
    if "### Official Government Sources" in markdown and "### Community Discussions" in markdown:
        checks.append("✅ Source groups formatted correctly")
    else:
        checks.append("❌ Source groups missing or incorrect")

    # Check 5: Reliability context present
    if "*Highly reliable - authoritative government data*" in markdown:
        checks.append("✅ Reliability context formatted correctly")
    else:
        checks.append("❌ Reliability context missing")

    # Check 6: Inline citations in findings
    if "[DoD Contract Award Notice](https://sam.gov/contract1)" in markdown:
        checks.append("✅ Inline citations in findings formatted correctly")
    else:
        checks.append("❌ Inline citations in findings missing or incorrect")

    # Check 7: Supporting detail present
    if "Contract for cybersecurity services" in markdown:
        checks.append("✅ Supporting detail formatted correctly")
    else:
        checks.append("❌ Supporting detail missing")

    # Check 8: Entity network present
    if "## Entity Network" in markdown and "Department of Defense" in markdown:
        checks.append("✅ Entity network formatted correctly")
    else:
        checks.append("❌ Entity network missing or incorrect")

    # Check 9: Timeline present
    if "## Timeline" in markdown and "2025-10-15" in markdown:
        checks.append("✅ Timeline formatted correctly")
    else:
        checks.append("❌ Timeline missing or incorrect")

    # Check 10: Methodology present
    if "## Methodology" in markdown and "coverage_summary" in markdown.lower():
        checks.append("✅ Methodology formatted correctly")
    else:
        checks.append("❌ Methodology missing or incorrect")

    # Check 11: Limitations present
    if "## Research Limitations" in markdown and "Reddit data is anecdotal" in markdown:
        checks.append("✅ Limitations formatted correctly")
    else:
        checks.append("❌ Limitations missing or incorrect")

    # Print validation results
    for check in checks:
        print(check)

    # Summary
    passed = sum(1 for c in checks if c.startswith("✅"))
    total = len(checks)

    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} checks passed")
    print("=" * 80)

    if passed == total:
        print("\n✅ [PASS] Synthesis formatter working correctly!")
        return True
    else:
        print(f"\n❌ [FAIL] {total - passed} check(s) failed")
        return False


if __name__ == "__main__":
    success = test_synthesis_formatter()
    sys.exit(0 if success else 1)
