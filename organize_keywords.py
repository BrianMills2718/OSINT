#!/usr/bin/env python3
"""
Organize Keywords into Boolean Search Database

Takes raw extracted keywords and:
1. Filters out noise (common phrases, boilerplate text)
2. Organizes by investigative theme
3. Creates synonym mappings
4. Generates Boolean query templates
5. Ranks by importance/specificity

Output: keyword_database.json - ready for Boolean search system
"""

import json
import re
import logging
from datetime import datetime
from collections import defaultdict, Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KeywordOrganizer:
    """Organize extracted keywords into searchable database"""

    def __init__(self, raw_keywords_path, taxonomy_path=None):
        with open(raw_keywords_path, 'r') as f:
            self.raw_keywords = json.load(f)

        self.taxonomy = None
        if taxonomy_path:
            with open(taxonomy_path, 'r') as f:
                self.taxonomy = json.load(f)

        # Noise patterns to filter out
        self.noise_patterns = [
            r'leave a comment',
            r'subscribe',
            r'paid subscriber',
            r'become a paid',
            r'edited by william',
            r'ken klippenstein',
            r'box of government',
            r'comment share',
            r'bill.*s black box',
            r'receive new posts',
            r'support my work',
            r'i (ve|can|don|m)\b',
            r'\bu s\b',  # "u s" from splitting "U.S."
            r'trump s\b',  # possessive artifacts
            r'^don t\b',
            r'^i ve\b',
            r'pdf$',  # PDF is document format, not substantive
        ]

    def is_noise(self, phrase):
        """Check if phrase matches noise patterns"""
        phrase_lower = phrase.lower()

        for pattern in self.noise_patterns:
            if re.search(pattern, phrase_lower):
                return True

        # Filter very common terms
        if phrase_lower in {'us', 'uk', 'ceo', 'cnn', 'nbc', 'pdf', 'ai'}:
            return True

        # Filter if all words are too short
        words = phrase_lower.split()
        if all(len(w) <= 2 for w in words):
            return True

        return False

    def extract_substantive_ngrams(self):
        """Extract meaningful n-grams, filtered for noise"""
        logger.info("Filtering n-grams for substantive terms...")

        substantive = {}

        if 'ngrams' in self.raw_keywords:
            for n, ngrams in self.raw_keywords['ngrams'].items():
                filtered = {}
                for phrase, count in ngrams.items():
                    if not self.is_noise(phrase) and count >= 3:  # minimum 3 mentions
                        filtered[phrase] = count

                substantive[n] = filtered
                logger.info(f"  {n}-grams: {len(ngrams)} → {len(filtered)} (after filtering)")

        return substantive

    def extract_substantive_acronyms(self):
        """Extract meaningful acronyms"""
        logger.info("Filtering acronyms...")

        substantive = {}

        if 'acronyms' in self.raw_keywords:
            for acr, data in self.raw_keywords['acronyms'].items():
                if not self.is_noise(acr) and data['count'] >= 3:
                    substantive[acr] = data['count']

        logger.info(f"  Acronyms: {len(self.raw_keywords.get('acronyms', {}))} → {len(substantive)}")
        return substantive

    def organize_by_theme(self, ngrams, acronyms):
        """Organize keywords by investigative theme using taxonomy categories"""
        logger.info("Organizing keywords by theme...")

        # Initialize themes from taxonomy categories
        themes = defaultdict(lambda: {
            'primary_terms': [],
            'related_concepts': [],
            'organizations': [],
            'acronyms': [],
            'multi_word_phrases': [],
            'indicators': []
        })

        # Map taxonomy categories to themes
        if self.taxonomy:
            for tag_entry in self.taxonomy['taxonomy']:
                tag = tag_entry['tag']
                category = tag_entry['category']
                entity_type = tag_entry['entity_type']

                # Determine where to place this tag
                if entity_type == 'organization':
                    themes[category]['organizations'].append(tag)
                elif entity_type in ['person', 'place', 'event']:
                    themes[category]['primary_terms'].append(tag)
                else:
                    themes[category]['related_concepts'].append(tag)

        # Add extracted acronyms to appropriate themes
        acronym_mappings = {
            'FBI': 'Law Enforcement & Justice',
            'CIA': 'National Security & Intelligence',
            'DHS': 'National Security & Intelligence',
            'ICE': 'Immigration',
            'NATO': 'International Relations & Diplomacy',
            'ISIS': 'Terrorism & Counterterrorism',
            'NSA': 'National Security & Intelligence',
            'IRS': 'Government Oversight & Accountability',
            'CBP': 'Immigration',
            'USAID': 'International Relations & Diplomacy',
            'DOD': 'Military & Defense',
            'DOJ': 'Law Enforcement & Justice'
        }

        for acr, count in acronyms.items():
            if acr in acronym_mappings:
                theme = acronym_mappings[acr]
                if acr not in themes[theme]['acronyms']:
                    themes[theme]['acronyms'].append(acr)

        # Add substantive n-grams to themes based on keyword matching
        theme_keywords = {
            'National Security & Intelligence': [
                'national security', 'intelligence', 'classified', 'security clearance',
                'intelligence community', 'counterintelligence', 'espionage', 'surveillance'
            ],
            'Military & Defense': [
                'military', 'defense', 'pentagon', 'armed forces', 'department of defense',
                'troops', 'deployment', 'combat', 'warfare'
            ],
            'Terrorism & Counterterrorism': [
                'terrorism', 'terrorist', 'extremism', 'extremist', 'counterterrorism',
                'jihadist', 'radicalization', 'threat assessment'
            ],
            'Domestic Policy & Social Issues': [
                'domestic', 'violence', 'extremism', 'nihilistic violent', 'accelerationism',
                'white supremacy', 'hate crime'
            ],
            'Law Enforcement & Justice': [
                'law enforcement', 'police', 'investigation', 'arrest', 'prosecution',
                'justice department', 'fbi', 'federal agents'
            ],
            'Government Oversight & Accountability': [
                'foia', 'transparency', 'whistleblower', 'oversight', 'accountability',
                'inspector general', 'classified documents', 'declassified'
            ],
            'Cybersecurity & Technology': [
                'cyber', 'hacking', 'malware', 'encryption', 'digital', 'technology',
                'artificial intelligence', 'surveillance technology'
            ],
            'Immigration': [
                'immigration', 'border', 'migrant', 'asylum', 'deportation', 'ice', 'cbp'
            ]
        }

        # Match n-grams to themes
        for n, ngrams_dict in ngrams.items():
            for phrase, count in sorted(ngrams_dict.items(), key=lambda x: x[1], reverse=True)[:200]:  # Top 200 per n-gram size
                phrase_lower = phrase.lower()

                # Try to match to theme
                matched = False
                for theme, keywords in theme_keywords.items():
                    if any(kw in phrase_lower for kw in keywords):
                        themes[theme]['multi_word_phrases'].append({
                            'phrase': phrase,
                            'count': count,
                            'importance': min(10, count // 10)  # Scale importance
                        })
                        matched = True
                        break

                # If no match, add to general category
                if not matched and count >= 10:  # Only high-frequency phrases
                    themes['General']['multi_word_phrases'].append({
                        'phrase': phrase,
                        'count': count,
                        'importance': min(10, count // 10)
                    })

        logger.info(f"Organized keywords into {len(themes)} themes")
        return dict(themes)

    def create_synonym_mappings(self, themes):
        """Create synonym mappings for common variations"""
        logger.info("Creating synonym mappings...")

        synonyms = {}

        # Common intelligence/security synonyms
        synonyms.update({
            'FBI': ['Federal Bureau of Investigation', 'FBI', 'Bureau'],
            'CIA': ['Central Intelligence Agency', 'CIA', 'Agency'],
            'DHS': ['Department of Homeland Security', 'DHS', 'Homeland Security'],
            'DOD': ['Department of Defense', 'DOD', 'Pentagon'],
            'NSA': ['National Security Agency', 'NSA'],
            'ICE': ['Immigration and Customs Enforcement', 'ICE'],
            'CBP': ['Customs and Border Protection', 'CBP', 'Border Patrol'],
            'FOIA': ['Freedom of Information Act', 'FOIA'],
            'ISIS': ['Islamic State', 'ISIS', 'ISIL', 'Daesh'],
            'NATO': ['North Atlantic Treaty Organization', 'NATO']
        })

        # Extremism synonyms
        synonyms.update({
            'domestic terrorism': ['domestic terrorism', 'domestic extremism', 'homegrown terrorism'],
            'white supremacy': ['white supremacy', 'white nationalism', 'white nationalist'],
            'accelerationism': ['accelerationism', 'accelerationist', 'militant accelerationism']
        })

        # Extract acronym expansions from corpus if present
        for theme, data in themes.items():
            for acr in data.get('acronyms', []):
                if acr not in synonyms:
                    synonyms[acr] = [acr]

        logger.info(f"Created {len(synonyms)} synonym mappings")
        return synonyms

    def generate_boolean_queries(self, themes, synonyms):
        """Generate Boolean query templates for each theme"""
        logger.info("Generating Boolean query templates...")

        queries = {}

        for theme, data in themes.items():
            theme_queries = []

            # Query 1: Government documents
            if data['acronyms'] or data['organizations']:
                orgs = ' OR '.join([f'"{org}"' for org in data['acronyms'][:5]])
                if orgs:
                    theme_queries.append({
                        'name': f'{theme} - Government Documents',
                        'query': f'site:(.gov OR .mil) ({orgs}) AND ("report" OR "assessment" OR "memo")',
                        'sources': ['Google', 'Government sites']
                    })

            # Query 2: News coverage
            primary = data['primary_terms'][:3] + [p['phrase'] for p in data['multi_word_phrases'][:2]]
            if primary:
                terms = ' OR '.join([f'"{term}"' for term in primary if isinstance(term, str)])
                if terms:
                    theme_queries.append({
                        'name': f'{theme} - News Coverage',
                        'query': f'({terms}) AND (news OR investigation OR report)',
                        'sources': ['Google News', 'NewsAPI']
                    })

            # Query 3: Academic/Research
            if data['related_concepts']:
                concepts = ' OR '.join([f'"{c}"' for c in data['related_concepts'][:5] if isinstance(c, str)])
                if concepts:
                    theme_queries.append({
                        'name': f'{theme} - Academic Research',
                        'query': f'({concepts}) AND (study OR research OR analysis)',
                        'sources': ['Google Scholar', 'Academic databases']
                    })

            if theme_queries:
                queries[theme] = theme_queries

        logger.info(f"Generated {sum(len(q) for q in queries.values())} Boolean queries across {len(queries)} themes")
        return queries

    def calculate_importance(self, keyword, count):
        """Calculate importance score for keyword (1-10)"""
        # Higher count = higher importance
        freq_score = min(5, count // 20)

        # Length matters - longer phrases tend to be more specific
        length_score = min(3, len(keyword.split()))

        # Specific domains get boost
        domain_boost = 0
        if any(term in keyword.lower() for term in ['extremism', 'classified', 'operational security', 'threat assessment']):
            domain_boost = 2

        return min(10, freq_score + length_score + domain_boost)

    def build_keyword_database(self):
        """Build complete keyword database"""
        logger.info("="*70)
        logger.info("BUILDING KEYWORD DATABASE")
        logger.info("="*70)

        # Step 1: Filter noise
        ngrams = self.extract_substantive_ngrams()
        acronyms = self.extract_substantive_acronyms()

        # Step 2: Organize by theme
        themes = self.organize_by_theme(ngrams, acronyms)

        # Step 3: Create synonyms
        synonyms = self.create_synonym_mappings(themes)

        # Step 4: Generate Boolean queries
        boolean_queries = self.generate_boolean_queries(themes, synonyms)

        # Step 5: Assemble database
        database = {
            'metadata': {
                'created': str(datetime.now()),
                'total_themes': len(themes),
                'total_keywords': sum(
                    len(data['primary_terms']) +
                    len(data['related_concepts']) +
                    len(data['organizations']) +
                    len(data['acronyms']) +
                    len(data['multi_word_phrases'])
                    for data in themes.values()
                ),
                'total_boolean_queries': sum(len(q) for q in boolean_queries.values())
            },
            'themes': themes,
            'synonyms': synonyms,
            'boolean_queries': boolean_queries
        }

        return database

    def save_database(self, database, output_path):
        """Save organized keyword database"""
        logger.info(f"Saving keyword database to {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(database, f, indent=2, ensure_ascii=False)

        # Create human-readable summary
        summary_path = output_path.replace('.json', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("KEYWORD DATABASE SUMMARY\n")
            f.write("="*70 + "\n\n")
            f.write(f"Created: {database['metadata']['created']}\n")
            f.write(f"Total Themes: {database['metadata']['total_themes']}\n")
            f.write(f"Total Keywords: {database['metadata']['total_keywords']}\n")
            f.write(f"Total Boolean Queries: {database['metadata']['total_boolean_queries']}\n\n")

            f.write("="*70 + "\n")
            f.write("THEMES & KEYWORDS\n")
            f.write("="*70 + "\n\n")

            for theme, data in database['themes'].items():
                total_keywords = (
                    len(data['primary_terms']) +
                    len(data['related_concepts']) +
                    len(data['organizations']) +
                    len(data['acronyms']) +
                    len(data['multi_word_phrases'])
                )

                f.write(f"\n{theme} ({total_keywords} keywords)\n")
                f.write("-"*70 + "\n")

                if data['acronyms']:
                    f.write(f"  Acronyms: {', '.join(data['acronyms'][:10])}\n")

                if data['organizations']:
                    f.write(f"  Organizations: {', '.join(data['organizations'][:5])}\n")

                if data['multi_word_phrases']:
                    top_phrases = sorted(data['multi_word_phrases'],
                                       key=lambda x: x['count'], reverse=True)[:5]
                    f.write("  Top Phrases:\n")
                    for p in top_phrases:
                        f.write(f"    - {p['phrase']} ({p['count']} mentions)\n")

            f.write("\n" + "="*70 + "\n")
            f.write("BOOLEAN QUERY EXAMPLES\n")
            f.write("="*70 + "\n\n")

            for theme, queries in database['boolean_queries'].items():
                f.write(f"\n{theme}:\n")
                for q in queries[:2]:  # Show first 2 queries per theme
                    f.write(f"  {q['name']}:\n")
                    f.write(f"    {q['query']}\n")
                    f.write(f"    Sources: {', '.join(q['sources'])}\n\n")

        logger.info(f"Summary saved to {summary_path}")


def main():
    """Main execution"""
    print("="*70)
    print("ORGANIZING KEYWORDS FOR BOOLEAN SEARCH")
    print("="*70)
    print()

    raw_keywords_path = 'keyword_extraction_raw.json'
    taxonomy_path = 'experiments/tag_management/tag_taxonomy_complete.json'
    output_path = 'keyword_database.json'

    organizer = KeywordOrganizer(raw_keywords_path, taxonomy_path)
    database = organizer.build_keyword_database()
    organizer.save_database(database, output_path)

    print("\n" + "="*70)
    print("ORGANIZATION COMPLETE")
    print("="*70)
    print(f"\nKeyword database saved to: {output_path}")
    print(f"Summary saved to: keyword_database_summary.txt")
    print(f"\nThemes: {database['metadata']['total_themes']}")
    print(f"Keywords: {database['metadata']['total_keywords']}")
    print(f"Boolean Queries: {database['metadata']['total_boolean_queries']}")
    print("\nReady for Boolean search system!")
    print()


if __name__ == '__main__':
    main()
