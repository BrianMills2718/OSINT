#!/usr/bin/env python3
"""
Calculate entity co-occurrence based on proximity (character offsets).

Two entities co-occur if their mentions are within PROXIMITY_THRESHOLD characters
of each other in the source text.

This approach doesn't require exact snippet matching - it uses the actual
positions of entities in the source document.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Proximity threshold: entities within 500 characters co-occur
PROXIMITY_THRESHOLD = 500


def calculate_proximity_cooccurrence(extraction_file: str) -> Dict:
    """
    Calculate co-occurrence based on character offset proximity.

    Args:
        extraction_file: Path to entity extraction JSON with char_start/char_end

    Returns:
        Dict with co-occurrence statistics
    """
    # Load extraction data
    with open(extraction_file, 'r') as f:
        data = json.load(f)

    entities = data['entities']
    report_id = data['metadata']['report_id']

    print(f"[Proximity Co-occurrence] Analyzing {len(entities)} entities from {report_id}")
    print(f"[Proximity Co-occurrence] Proximity threshold: {PROXIMITY_THRESHOLD} characters\n")

    # Build list of all mentions with their positions
    mentions = []
    for entity in entities:
        for mention in entity['mentions']:
            mentions.append({
                'entity_id': entity['entity_id'],
                'canonical_name': entity['canonical_name'],
                'entity_type': entity['entity_type'],
                'char_start': mention['char_start'],
                'char_end': mention['char_end'],
                'snippet': mention['snippet']
            })

    print(f"[Proximity Co-occurrence] Total mentions: {len(mentions)}")

    # Calculate co-occurrence for each pair of mentions
    cooccurrences = defaultdict(lambda: {'count': 0, 'mention_pairs': []})

    for i, m1 in enumerate(mentions):
        for m2 in mentions[i+1:]:
            # Skip if same entity
            if m1['entity_id'] == m2['entity_id']:
                continue

            # Calculate distance between mentions
            # Distance is 0 if they overlap, otherwise the gap between them
            if m1['char_end'] < m2['char_start']:
                distance = m2['char_start'] - m1['char_end']
            elif m2['char_end'] < m1['char_start']:
                distance = m1['char_start'] - m2['char_end']
            else:
                # Overlapping mentions
                distance = 0

            # Check if within proximity threshold
            if distance <= PROXIMITY_THRESHOLD:
                # Create canonical pair key (alphabetically sorted)
                pair_key = tuple(sorted([m1['entity_id'], m2['entity_id']]))

                cooccurrences[pair_key]['count'] += 1
                cooccurrences[pair_key]['mention_pairs'].append({
                    'entity1': m1['canonical_name'],
                    'entity2': m2['canonical_name'],
                    'distance': distance,
                    'char_range': f"{min(m1['char_start'], m2['char_start'])}-{max(m1['char_end'], m2['char_end'])}"
                })

    print(f"[Proximity Co-occurrence] Found {len(cooccurrences)} unique entity pairs\n")

    # Build entity name lookup
    entity_lookup = {e['entity_id']: (e['canonical_name'], e['entity_type']) for e in entities}

    # Convert to sorted list
    cooccurrence_list = []
    for (e1_id, e2_id), data in cooccurrences.items():
        e1_name, e1_type = entity_lookup[e1_id]
        e2_name, e2_type = entity_lookup[e2_id]

        cooccurrence_list.append({
            'entity1_id': e1_id,
            'entity1_name': e1_name,
            'entity1_type': e1_type,
            'entity2_id': e2_id,
            'entity2_name': e2_name,
            'entity2_type': e2_type,
            'cooccurrence_count': data['count'],
            'mention_pairs': data['mention_pairs']
        })

    # Sort by co-occurrence count (descending)
    cooccurrence_list.sort(key=lambda x: x['cooccurrence_count'], reverse=True)

    # Calculate bridge entities (entities with most connections)
    entity_connections = defaultdict(set)
    for pair in cooccurrence_list:
        entity_connections[pair['entity1_id']].add(pair['entity2_id'])
        entity_connections[pair['entity2_id']].add(pair['entity1_id'])

    bridge_entities = []
    for entity_id, connected_ids in entity_connections.items():
        name, etype = entity_lookup[entity_id]
        bridge_entities.append({
            'entity_id': entity_id,
            'canonical_name': name,
            'entity_type': etype,
            'connection_count': len(connected_ids),
            'total_cooccurrences': sum(
                c['cooccurrence_count']
                for c in cooccurrence_list
                if c['entity1_id'] == entity_id or c['entity2_id'] == entity_id
            )
        })

    bridge_entities.sort(key=lambda x: x['connection_count'], reverse=True)

    return {
        'report_id': report_id,
        'total_entities': len(entities),
        'total_mentions': len(mentions),
        'proximity_threshold': PROXIMITY_THRESHOLD,
        'unique_entity_pairs': len(cooccurrence_list),
        'cooccurrences': cooccurrence_list,
        'bridge_entities': bridge_entities
    }


def main():
    """Main entry point."""

    print("===== Proximity-Based Co-occurrence Analysis =====\n")

    # Analyze synthetic document
    extraction_file = Path(__file__).parent / "phase1_output.json"

    if not extraction_file.exists():
        print(f"[ERROR] Extraction file not found: {extraction_file}")
        return 1

    # Calculate co-occurrence
    results = calculate_proximity_cooccurrence(str(extraction_file))

    # Save results
    output_file = Path(__file__).parent / "proximity_cooccurrence_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✓ Results saved to: {output_file}\n")

    # Print summary
    print("===== SUMMARY =====\n")
    print(f"Total entities: {results['total_entities']}")
    print(f"Total mentions: {results['total_mentions']}")
    print(f"Proximity threshold: {results['proximity_threshold']} characters")
    print(f"Unique entity pairs: {results['unique_entity_pairs']}\n")

    # Print top 10 co-occurrences
    print("Top 10 Co-occurrences:\n")
    for i, cooccur in enumerate(results['cooccurrences'][:10], 1):
        print(f"{i}. {cooccur['entity1_name']} ({cooccur['entity1_type']}) <-> "
              f"{cooccur['entity2_name']} ({cooccur['entity2_type']})")
        print(f"   Co-occurrences: {cooccur['cooccurrence_count']}")
        print(f"   Avg distance: {sum(mp['distance'] for mp in cooccur['mention_pairs']) / len(cooccur['mention_pairs']):.0f} chars\n")

    # Print top 10 bridge entities
    print("\nTop 10 Bridge Entities:\n")
    for i, bridge in enumerate(results['bridge_entities'][:10], 1):
        print(f"{i}. {bridge['canonical_name']} ({bridge['entity_type']})")
        print(f"   Connections: {bridge['connection_count']} entities")
        print(f"   Total co-occurrences: {bridge['total_cooccurrences']}\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
