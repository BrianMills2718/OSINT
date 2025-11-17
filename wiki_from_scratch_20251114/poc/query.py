#!/usr/bin/env python3
"""
Phase 2: CLI Query Tool

Query entities across multiple investigative reports.
This demonstrates the core value proposition: cross-report entity pivoting.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple


def query_entity(conn: sqlite3.Connection, entity_name: str, verbose: bool = False):
    """Query all mentions of an entity across all reports."""

    cursor = conn.cursor()

    # Find entity (case-insensitive search in canonical_name and aliases)
    cursor.execute("""
        SELECT entity_id, canonical_name, entity_type, aliases, reports_seen_in, report_count
        FROM entities
        WHERE canonical_name LIKE ? OR aliases LIKE ?
    """, (f"%{entity_name}%", f"%{entity_name}%"))

    results = cursor.fetchall()

    if not results:
        print(f"[Query] No entity found matching: {entity_name}")
        return

    if len(results) > 1:
        print(f"[Query] Found {len(results)} entities matching '{entity_name}':")
        for entity_id, canonical_name, entity_type, _, reports_seen_in, report_count in results:
            reports = json.loads(reports_seen_in)
            print(f"[Query]   - {canonical_name} ({entity_type}): {report_count} report(s)")
        print(f"\n[Query] Showing details for first match...\n")

    # Show first match
    entity_id, canonical_name, entity_type, aliases, reports_seen_in, report_count = results[0]
    aliases_list = json.loads(aliases)
    reports = json.loads(reports_seen_in)

    print(f"Entity: {canonical_name}")
    print(f"Type: {entity_type}")
    print(f"Aliases: {', '.join(aliases_list[:10])}{'...' if len(aliases_list) > 10 else ''}")
    print(f"Seen in: {', '.join(reports)} ({report_count} report{'s' if report_count > 1 else ''})")

    # Get evidence
    cursor.execute("""
        SELECT e.report_id, e.snippet_text, e.context
        FROM evidence e
        JOIN entity_mentions em ON e.evidence_id = em.evidence_id
        WHERE em.entity_id = ?
        ORDER BY e.report_id
    """, (entity_id,))

    evidence = cursor.fetchall()

    print(f"\nEvidence ({len(evidence)} snippet{'s' if len(evidence) != 1 else ''}):")

    # Group by report
    current_report = None
    for report_id, snippet, context in evidence:
        if report_id != current_report:
            current_report = report_id
            print(f"\n  From {report_id}:")

        if verbose:
            print(f"    Snippet: {snippet[:200]}{'...' if len(snippet) > 200 else ''}")
            print(f"    Context: {context}")
        else:
            print(f"    - {context}")


def query_cross_report(conn: sqlite3.Connection):
    """List all entities appearing in 2+ reports."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT canonical_name, entity_type, report_count, reports_seen_in
        FROM entities
        WHERE report_count > 1
        ORDER BY report_count DESC, canonical_name
    """)

    results = cursor.fetchall()

    if not results:
        print(f"[Query] No entities found in multiple reports")
        return

    print(f"Entities appearing in 2+ reports ({len(results)} total):\n")

    for canonical_name, entity_type, report_count, reports_seen_in in results:
        reports = json.loads(reports_seen_in)
        print(f"  - {canonical_name} ({entity_type}): {report_count} reports ({', '.join(reports)})")


def query_by_type(conn: sqlite3.Connection, entity_type: str):
    """List all entities of a specific type."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT canonical_name, report_count, reports_seen_in
        FROM entities
        WHERE entity_type = ?
        ORDER BY report_count DESC, canonical_name
    """, (entity_type,))

    results = cursor.fetchall()

    if not results:
        print(f"[Query] No entities of type: {entity_type}")
        return

    print(f"Entities of type '{entity_type}' ({len(results)} total):\n")

    for canonical_name, report_count, reports_seen_in in results:
        reports = json.loads(reports_seen_in)
        report_str = f"{report_count} report{'s' if report_count > 1 else ''}"
        if report_count > 1:
            report_str += f" ({', '.join(reports)})"
        print(f"  - {canonical_name}: {report_str}")


def query_cooccurrence(conn: sqlite3.Connection, entity_name: str):
    """Show entities that co-occur with the target entity."""

    cursor = conn.cursor()

    # Find target entity
    cursor.execute("""
        SELECT entity_id, canonical_name, entity_type
        FROM entities
        WHERE canonical_name LIKE ? OR aliases LIKE ?
    """, (f"%{entity_name}%", f"%{entity_name}%"))

    results = cursor.fetchall()

    if not results:
        print(f"[Query] No entity found matching: {entity_name}")
        return

    entity_id, canonical_name, entity_type = results[0]

    print(f"Entities that co-occur with: {canonical_name} ({entity_type})\n")

    # Find co-occurring entities
    cursor.execute("""
        SELECT
            e.canonical_name,
            e.entity_type,
            ec.cooccurrence_count
        FROM entity_cooccurrence ec
        JOIN entities e ON (
            (ec.entity_id_1 = ? AND e.entity_id = ec.entity_id_2) OR
            (ec.entity_id_2 = ? AND e.entity_id = ec.entity_id_1)
        )
        ORDER BY ec.cooccurrence_count DESC, e.canonical_name
    """, (entity_id, entity_id))

    cooccurrences = cursor.fetchall()

    if not cooccurrences:
        print(f"  No co-occurrences found (entity appears alone in all snippets)")
        return

    for name, ent_type, count in cooccurrences:
        times_str = "time" if count == 1 else "times"
        print(f"  - {name} ({ent_type}): {count} {times_str}")


def query_bridges(conn: sqlite3.Connection, limit: int = 15):
    """Show bridge entities (entities connecting many others)."""

    cursor = conn.cursor()

    # Check if co-occurrence table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='entity_cooccurrence'
    """)

    if not cursor.fetchone():
        print(f"[Query] Co-occurrence table not found")
        print(f"[Query] Run analyze_cooccurrence.py first")
        return

    cursor.execute(f"""
        SELECT
            e.canonical_name,
            e.entity_type,
            COUNT(DISTINCT partner_entity_id) as connection_count,
            SUM(cooccurrence_count) as total_cooccurrences
        FROM entities e
        JOIN (
            SELECT entity_id_1 as entity_id, entity_id_2 as partner_entity_id, cooccurrence_count
            FROM entity_cooccurrence
            UNION ALL
            SELECT entity_id_2 as entity_id, entity_id_1 as partner_entity_id, cooccurrence_count
            FROM entity_cooccurrence
        ) connections ON e.entity_id = connections.entity_id
        GROUP BY e.entity_id
        ORDER BY connection_count DESC, total_cooccurrences DESC
        LIMIT {limit}
    """)

    results = cursor.fetchall()

    if not results:
        print(f"[Query] No bridge entities found")
        return

    print(f"Bridge Entities (top {limit} by connection count):\n")

    for name, ent_type, connection_count, total_cooccurrences in results:
        print(f"  {name} ({ent_type})")
        print(f"    Connects to: {connection_count} entities")
        print(f"    Total co-occurrences: {total_cooccurrences}")
        print()


def query_stats(conn: sqlite3.Connection):
    """Show database statistics."""

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM evidence")
    evidence_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entities WHERE report_count > 1")
    cross_report_count = cursor.fetchone()[0]

    cursor.execute("SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC")
    type_breakdown = cursor.fetchall()

    print("Database Statistics:\n")
    print(f"  Total entities: {entity_count}")
    print(f"  Total evidence snippets: {evidence_count}")
    print(f"  Cross-report entities (2+ reports): {cross_report_count}")

    # Check for co-occurrence data
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='entity_cooccurrence'
    """)
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM entity_cooccurrence")
        cooccurrence_count = cursor.fetchone()[0]
        print(f"  Entity co-occurrence pairs: {cooccurrence_count}")

    print(f"\n  Entity type breakdown:")
    for entity_type, count in type_breakdown:
        print(f"    - {entity_type}: {count}")


def main():
    """Main CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Query entities across investigative reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --entity "MH17"               # Show all mentions of MH17 across reports
  %(prog)s --entity "Igor Egorov" -v     # Show detailed evidence for Igor Egorov
  %(prog)s --cross-report                # List entities in 2+ reports
  %(prog)s --type person                 # List all people mentioned
  %(prog)s --cooccur "MH17"              # Show entities that co-occur with MH17
  %(prog)s --bridges                     # Show bridge entities (connecting many others)
  %(prog)s --stats                       # Show database statistics
        """
    )

    parser.add_argument("--entity", "-e", help="Search for entity by name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full snippets")
    parser.add_argument("--cross-report", "-x", action="store_true", help="List cross-report entities")
    parser.add_argument("--type", "-t", help="List entities of type (person, organization, location, etc.)")
    parser.add_argument("--cooccur", "-c", help="Show entities that co-occur with target entity")
    parser.add_argument("--bridges", "-b", action="store_true", help="Show bridge entities (most connections)")
    parser.add_argument("--stats", "-s", action="store_true", help="Show database statistics")

    args = parser.parse_args()

    # Check for database
    db_path = Path(__file__).parent / "entities.db"
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print(f"[ERROR] Run build_database.py first")
        return 1

    # Connect to database
    conn = sqlite3.connect(str(db_path))

    try:
        # Execute query based on arguments
        if args.entity:
            query_entity(conn, args.entity, args.verbose)
        elif args.cross_report:
            query_cross_report(conn)
        elif args.type:
            query_by_type(conn, args.type)
        elif args.cooccur:
            query_cooccurrence(conn, args.cooccur)
        elif args.bridges:
            query_bridges(conn)
        elif args.stats:
            query_stats(conn)
        else:
            parser.print_help()
            return 1

        conn.close()
        return 0

    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
