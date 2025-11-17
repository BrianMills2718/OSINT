#!/usr/bin/env python3
"""
Phase 2: SQLite Database Builder

Creates database with cross-report entity linking.
Enables querying: "Show me all mentions of Entity X across all reports"
"""

import json
import sqlite3
import sys
from pathlib import Path


def create_schema(conn: sqlite3.Connection):
    """Create database tables."""

    cursor = conn.cursor()

    # Entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            aliases TEXT,
            reports_seen_in TEXT,
            report_count INTEGER
        )
    """)

    # Evidence table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            report_title TEXT,
            snippet_text TEXT NOT NULL,
            context TEXT
        )
    """)

    # Entity-evidence junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_mentions (
            entity_id TEXT,
            evidence_id TEXT,
            PRIMARY KEY (entity_id, evidence_id),
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
        )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_report_count ON entities(report_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_report ON evidence(report_id)")

    conn.commit()
    print("[Phase 2] ✓ Database schema created")


def populate_database(conn: sqlite3.Connection):
    """Populate database with canonical entities and evidence."""

    cursor = conn.cursor()

    # Load canonical entities
    canonical_path = Path(__file__).parent / "canonical_entities.json"
    with open(canonical_path, 'r', encoding='utf-8') as f:
        canonical_data = json.load(f)

    # Load all report data (for evidence snippets)
    all_reports_path = Path(__file__).parent / "all_reports_raw.json"
    with open(all_reports_path, 'r', encoding='utf-8') as f:
        all_reports = json.load(f)

    # Create lookup for entities by (report_id, entity_id)
    entity_lookup = {}
    for report_data in all_reports["reports"]:
        report_id = report_data["metadata"]["report_id"]
        for entity in report_data["entities"]:
            key = (report_id, entity["entity_id"])
            entity_lookup[key] = entity

    print(f"[Phase 2] Populating database with {len(canonical_data['canonical_entities'])} canonical entities...")

    evidence_counter = 0

    # Populate entities and evidence
    for canon_entity in canonical_data["canonical_entities"]:
        entity_id = canon_entity["canonical_id"]
        canonical_name = canon_entity["canonical_name"]
        entity_type = canon_entity["entity_type"]
        all_aliases = json.dumps(canon_entity["all_aliases"])

        # Get unique reports this entity appears in
        reports_seen = sorted(set(se["report_id"] for se in canon_entity["source_entities"]))
        reports_seen_in = json.dumps(reports_seen)
        report_count = len(reports_seen)

        # Insert entity
        cursor.execute("""
            INSERT INTO entities (entity_id, canonical_name, entity_type, aliases, reports_seen_in, report_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entity_id, canonical_name, entity_type, all_aliases, reports_seen_in, report_count))

        # Get all evidence snippets for this entity
        for source_entity in canon_entity["source_entities"]:
            report_id = source_entity["report_id"]
            orig_entity_id = source_entity["entity_id"]

            # Look up original entity to get mentions
            key = (report_id, orig_entity_id)
            if key not in entity_lookup:
                continue

            orig_entity = entity_lookup[key]

            # Insert evidence for each mention
            for mention in orig_entity.get("mentions", []):
                evidence_counter += 1
                evidence_id = f"EV{evidence_counter}"

                cursor.execute("""
                    INSERT INTO evidence (evidence_id, report_id, snippet_text, context)
                    VALUES (?, ?, ?, ?)
                """, (evidence_id, report_id, mention["snippet"], mention["context"]))

                # Link entity to evidence
                cursor.execute("""
                    INSERT INTO entity_mentions (entity_id, evidence_id)
                    VALUES (?, ?)
                """, (entity_id, evidence_id))

    conn.commit()

    print(f"[Phase 2] ✓ Populated {len(canonical_data['canonical_entities'])} entities")
    print(f"[Phase 2] ✓ Populated {evidence_counter} evidence snippets")


def print_statistics(conn: sqlite3.Connection):
    """Print database statistics."""

    cursor = conn.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM evidence")
    evidence_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM entity_mentions")
    mention_count = cursor.fetchone()[0]

    # Cross-report entities
    cursor.execute("SELECT COUNT(*) FROM entities WHERE report_count > 1")
    cross_report_count = cursor.fetchone()[0]

    # Entity type breakdown
    cursor.execute("SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type ORDER BY COUNT(*) DESC")
    type_breakdown = cursor.fetchall()

    print(f"\n[Phase 2] ===== Database Statistics =====")
    print(f"[Phase 2] Total entities: {entity_count}")
    print(f"[Phase 2] Total evidence snippets: {evidence_count}")
    print(f"[Phase 2] Total entity-evidence links: {mention_count}")
    print(f"[Phase 2] Cross-report entities (2+ reports): {cross_report_count}")
    print(f"\n[Phase 2] Entity type breakdown:")
    for entity_type, count in type_breakdown:
        print(f"[Phase 2]   - {entity_type}: {count}")


def main():
    """Main entry point for database builder."""

    print("[Phase 2] ===== SQLite Database Builder =====\n")

    db_path = Path(__file__).parent / "entities.db"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        print(f"[Phase 2] Removed existing database")

    try:
        # Create database and connect
        conn = sqlite3.connect(str(db_path))
        print(f"[Phase 2] Created database: {db_path.name}")

        # Create schema
        create_schema(conn)

        # Populate with data
        populate_database(conn)

        # Print statistics
        print_statistics(conn)

        # Close connection
        conn.close()

        print(f"\n[Phase 2] ✓ Database ready: {db_path.name}")
        print(f"[Phase 2] Next step: Run query.py to test cross-report queries")

        return 0

    except Exception as e:
        print(f"[ERROR] Database build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
