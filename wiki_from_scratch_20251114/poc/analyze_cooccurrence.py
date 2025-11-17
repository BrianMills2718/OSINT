#!/usr/bin/env python3
"""
Phase 3: Entity Co-occurrence Analysis

Identifies which entities frequently appear together in the same evidence snippets.
Creates entity_cooccurrence table for network analysis.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def analyze_cooccurrence(db_path: Path):
    """Analyze entity co-occurrence patterns."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("[Phase 3] ===== Entity Co-occurrence Analysis =====\n")

    # Get all evidence snippets - group by snippet_text to find overlapping mentions
    cursor.execute("""
        SELECT
            e.snippet_text,
            e.report_id,
            GROUP_CONCAT(em.entity_id, '|') as entity_ids,
            GROUP_CONCAT(e.evidence_id, '|') as evidence_ids_str
        FROM evidence e
        JOIN entity_mentions em ON e.evidence_id = em.evidence_id
        GROUP BY e.snippet_text, e.report_id
        HAVING COUNT(em.entity_id) > 1
    """)

    snippets = cursor.fetchall()
    print(f"[Phase 3] Found {len(snippets)} unique text snippets with 2+ entities")

    # Track co-occurrences
    cooccurrence = defaultdict(int)
    cooccurrence_evidence = defaultdict(list)

    # Analyze co-occurrences
    for snippet_text, report_id, entity_ids_str, evidence_ids_str in snippets:
        entity_ids = entity_ids_str.split('|')
        evidence_ids = evidence_ids_str.split('|')

        # Create all pairs of entities in this snippet
        for entity1, entity2 in combinations(sorted(entity_ids), 2):
            pair = (entity1, entity2)
            cooccurrence[pair] += 1
            # Store all evidence IDs where this pair co-occurs
            cooccurrence_evidence[pair].extend(evidence_ids)

    print(f"[Phase 3] Found {len(cooccurrence)} unique entity pairs")

    if len(cooccurrence) == 0:
        print(f"[Phase 3] WARNING: No co-occurrences found!")
        print(f"[Phase 3] This means entities don't appear together in same text snippets.")
        print(f"[Phase 3] Co-occurrence analysis requires entities mentioned in same snippet.")
        conn.close()
        return

    print(f"[Phase 3] Average co-occurrence count: {sum(cooccurrence.values()) / len(cooccurrence):.2f}")

    # Create co-occurrence table
    cursor.execute("DROP TABLE IF EXISTS entity_cooccurrence")
    cursor.execute("""
        CREATE TABLE entity_cooccurrence (
            entity_id_1 TEXT,
            entity_id_2 TEXT,
            cooccurrence_count INTEGER,
            evidence_ids TEXT,
            PRIMARY KEY (entity_id_1, entity_id_2),
            FOREIGN KEY (entity_id_1) REFERENCES entities(entity_id),
            FOREIGN KEY (entity_id_2) REFERENCES entities(entity_id)
        )
    """)

    # Insert co-occurrence data
    for (entity1, entity2), count in cooccurrence.items():
        evidence_ids = json.dumps(cooccurrence_evidence[(entity1, entity2)])
        cursor.execute("""
            INSERT INTO entity_cooccurrence (entity_id_1, entity_id_2, cooccurrence_count, evidence_ids)
            VALUES (?, ?, ?, ?)
        """, (entity1, entity2, count, evidence_ids))

    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX idx_cooccurrence_e1 ON entity_cooccurrence(entity_id_1)
    """)
    cursor.execute("""
        CREATE INDEX idx_cooccurrence_e2 ON entity_cooccurrence(entity_id_2)
    """)

    conn.commit()

    print(f"[Phase 3] ✓ Created entity_cooccurrence table with {len(cooccurrence)} pairs")

    # Calculate bridge entities (entities with most connections)
    print(f"\n[Phase 3] Calculating bridge entities...")

    cursor.execute("""
        SELECT
            e.entity_id,
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
        ORDER BY connection_count DESC
        LIMIT 10
    """)

    bridge_entities = cursor.fetchall()

    print(f"[Phase 3] Top 10 Bridge Entities (most connections):\n")
    for entity_id, name, entity_type, connection_count, total_cooccurrences in bridge_entities:
        print(f"  {name} ({entity_type})")
        print(f"    Connections: {connection_count} entities")
        print(f"    Total co-occurrences: {total_cooccurrences}")
        print()

    # Save statistics
    stats = {
        "total_entity_pairs": len(cooccurrence),
        "average_cooccurrence_count": sum(cooccurrence.values()) / len(cooccurrence),
        "max_cooccurrence_count": max(cooccurrence.values()),
        "top_bridge_entities": [
            {
                "entity_id": entity_id,
                "name": name,
                "type": entity_type,
                "connection_count": connection_count,
                "total_cooccurrences": total_cooccurrences
            }
            for entity_id, name, entity_type, connection_count, total_cooccurrences in bridge_entities
        ]
    }

    stats_path = Path(__file__).parent / "cooccurrence_stats.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"[Phase 3] ✓ Statistics saved to: {stats_path.name}")

    # Show some interesting co-occurrence patterns
    print(f"\n[Phase 3] Most Frequent Co-occurrences:\n")

    cursor.execute("""
        SELECT
            e1.canonical_name,
            e1.entity_type,
            e2.canonical_name,
            e2.entity_type,
            ec.cooccurrence_count
        FROM entity_cooccurrence ec
        JOIN entities e1 ON ec.entity_id_1 = e1.entity_id
        JOIN entities e2 ON ec.entity_id_2 = e2.entity_id
        ORDER BY ec.cooccurrence_count DESC
        LIMIT 10
    """)

    for name1, type1, name2, type2, count in cursor.fetchall():
        print(f"  {name1} ({type1}) <-> {name2} ({type2}): {count} times")

    conn.close()

    print(f"\n[Phase 3] ✓ Co-occurrence analysis complete")
    print(f"[Phase 3] Next step: Run query.py with new --cooccur and --bridges flags")


def main():
    """Main entry point."""

    db_path = Path(__file__).parent / "entities.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print(f"[ERROR] Run build_database.py first")
        return 1

    try:
        analyze_cooccurrence(db_path)
        return 0

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
