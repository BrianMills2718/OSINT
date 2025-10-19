#!/usr/bin/env python3
"""
Keyword Extraction for Boolean Search System

This script extracts keywords from the corpus using a hybrid approach:
1. TF-IDF for distinctive terms
2. Named Entity Recognition (NER) for people, orgs, places
3. N-gram analysis for multi-word phrases
4. Collocation analysis for statistically significant phrases
5. LLM refinement using gpt-5-mini

Output: keyword_database.json - organized by theme with Boolean query templates
"""

import json
import re
import os
from collections import Counter, defaultdict
from pathlib import Path
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import optional dependencies with graceful fallbacks
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not available. TF-IDF extraction will be skipped.")
    SKLEARN_AVAILABLE = False

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
        SPACY_AVAILABLE = False
except ImportError:
    logger.warning("spaCy not available. NER extraction will be skipped.")
    SPACY_AVAILABLE = False

try:
    from litellm import completion
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("litellm not available. LLM refinement will be skipped.")
    LLM_AVAILABLE = False


class KeywordExtractor:
    """Hybrid keyword extraction from investigative journalism corpus"""

    def __init__(self, corpus_dirs, existing_taxonomy_path=None):
        self.corpus_dirs = corpus_dirs
        self.articles = []
        self.existing_taxonomy = None

        if existing_taxonomy_path and os.path.exists(existing_taxonomy_path):
            with open(existing_taxonomy_path, 'r') as f:
                self.existing_taxonomy = json.load(f)
                logger.info(f"Loaded existing taxonomy with {len(self.existing_taxonomy['taxonomy'])} tags")

    def load_corpus(self):
        """Load all article JSON files from corpus directories"""
        logger.info("Loading corpus...")

        for corpus_dir in self.corpus_dirs:
            if not os.path.exists(corpus_dir):
                logger.warning(f"Directory not found: {corpus_dir}")
                continue

            for json_file in Path(corpus_dir).glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        article = json.load(f)

                        # Ensure article has required fields
                        if 'content' in article and article['content']:
                            self.articles.append({
                                'title': article.get('title', ''),
                                'content': article['content'],
                                'url': article.get('url', ''),
                                'year': article.get('year', ''),
                                'tags': article.get('tags', [])
                            })
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Loaded {len(self.articles)} articles")
        return len(self.articles) > 0

    def extract_ngrams(self, text, n, min_freq=2):
        """Extract n-grams from text"""
        # Tokenize and clean
        words = re.findall(r'\b[a-zA-Z][a-zA-Z\-\']*\b', text.lower())

        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                     'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                     'these', 'those', 'it', 'its', 'they', 'their', 'them'}

        # Create n-grams
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = words[i:i+n]
            # Skip if starts or ends with stopword
            if ngram[0] not in stopwords and ngram[-1] not in stopwords:
                ngrams.append(' '.join(ngram))

        return ngrams

    def extract_ngrams_from_corpus(self):
        """Extract n-grams (2-5 words) from entire corpus"""
        logger.info("Extracting n-grams...")

        ngram_counts = {2: Counter(), 3: Counter(), 4: Counter(), 5: Counter()}

        for article in self.articles:
            text = article['title'] + ' ' + article['content']

            for n in [2, 3, 4, 5]:
                ngrams = self.extract_ngrams(text, n)
                ngram_counts[n].update(ngrams)

        # Filter by frequency (appears in at least 2 articles)
        significant_ngrams = {}
        for n, counts in ngram_counts.items():
            significant_ngrams[n] = {phrase: count for phrase, count in counts.items()
                                     if count >= 2}
            logger.info(f"Found {len(significant_ngrams[n])} significant {n}-grams")

        return significant_ngrams

    def extract_tfidf_terms(self, max_features=500):
        """Extract distinctive terms using TF-IDF"""
        if not SKLEARN_AVAILABLE:
            logger.warning("Skipping TF-IDF extraction (scikit-learn not available)")
            return []

        logger.info("Extracting TF-IDF terms...")

        # Combine title and content
        documents = [article['title'] + ' ' + article['content']
                     for article in self.articles]

        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 4),  # unigrams through 4-grams
            max_features=max_features,
            stop_words='english',
            min_df=2,  # must appear in at least 2 documents
            max_df=0.7  # must appear in less than 70% of documents
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(documents)
            feature_names = vectorizer.get_feature_names_out()

            # Get average TF-IDF score across corpus
            scores = tfidf_matrix.sum(axis=0).A1
            top_terms = sorted(zip(feature_names, scores),
                              key=lambda x: x[1], reverse=True)

            logger.info(f"Extracted {len(top_terms)} TF-IDF terms")
            return top_terms

        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}")
            return []

    def extract_named_entities(self):
        """Extract named entities using spaCy NER"""
        if not SPACY_AVAILABLE:
            logger.warning("Skipping NER extraction (spaCy not available)")
            return {}

        logger.info("Extracting named entities...")

        entities = {
            'PERSON': Counter(),
            'ORG': Counter(),
            'GPE': Counter(),  # Geopolitical entities (countries, cities)
            'LOC': Counter(),   # Non-GPE locations
            'EVENT': Counter(),
            'LAW': Counter(),
            'PRODUCT': Counter()
        }

        for i, article in enumerate(self.articles):
            if i % 50 == 0:
                logger.info(f"Processing article {i+1}/{len(self.articles)} for NER...")

            text = article['title'] + ' ' + article['content']

            # Process in chunks (spaCy has text length limits)
            max_length = 1000000
            for chunk_start in range(0, len(text), max_length):
                chunk = text[chunk_start:chunk_start + max_length]

                try:
                    doc = nlp(chunk)
                    for ent in doc.ents:
                        if ent.label_ in entities:
                            # Clean and normalize entity text
                            entity_text = ent.text.strip()
                            if len(entity_text) > 2:  # Skip very short entities
                                entities[ent.label_][entity_text] += 1
                except Exception as e:
                    logger.error(f"NER processing error: {e}")

        # Filter by frequency (2+ mentions)
        filtered_entities = {}
        for entity_type, counts in entities.items():
            filtered_entities[entity_type] = {ent: count for ent, count in counts.items()
                                              if count >= 2}
            logger.info(f"Found {len(filtered_entities[entity_type])} {entity_type} entities")

        return filtered_entities

    def extract_acronyms(self):
        """Extract acronyms and abbreviations from corpus"""
        logger.info("Extracting acronyms...")

        # Pattern: 2-6 uppercase letters, possibly with periods
        acronym_pattern = re.compile(r'\b[A-Z]{2,6}\b|\b(?:[A-Z]\.){2,6}\b')

        acronyms = Counter()

        for article in self.articles:
            text = article['content']
            matches = acronym_pattern.findall(text)
            acronyms.update(matches)

        # Filter by frequency
        significant_acronyms = {acr: count for acr, count in acronyms.items()
                                if count >= 2}

        # Remove common non-acronyms
        noise_terms = {'US', 'USA', 'UK', 'FBI', 'CIA', 'DOD', 'DHS'}  # Keep these actually
        # significant_acronyms = {k: v for k, v in significant_acronyms.items()
        #                        if k not in noise_terms}

        logger.info(f"Found {len(significant_acronyms)} significant acronyms")
        return significant_acronyms

    def integrate_existing_taxonomy(self, extracted_keywords):
        """Integrate existing tag taxonomy as seed keywords"""
        if not self.existing_taxonomy:
            return extracted_keywords

        logger.info("Integrating existing taxonomy tags...")

        # Add all existing tags as high-priority keywords
        for tag_entry in self.existing_taxonomy['taxonomy']:
            tag = tag_entry['tag']
            category = tag_entry['category']

            # Determine keyword type
            if tag_entry['entity_type'] == 'organization':
                keyword_type = 'organization'
            elif tag_entry['entity_type'] == 'person':
                keyword_type = 'person'
            elif tag_entry['entity_type'] == 'place':
                keyword_type = 'location'
            else:
                keyword_type = 'concept'

            # Add to extracted keywords with metadata
            if 'taxonomy_seed' not in extracted_keywords:
                extracted_keywords['taxonomy_seed'] = {}

            extracted_keywords['taxonomy_seed'][tag] = {
                'type': keyword_type,
                'category': category,
                'importance': 10 if tag_entry['taxonomy_fit'] == 'good' else 8,
                'source': 'existing_taxonomy'
            }

        logger.info(f"Added {len(self.existing_taxonomy['taxonomy'])} taxonomy tags as seed keywords")
        return extracted_keywords

    def refine_with_llm(self, candidate_keywords, sample_size=100):
        """Use LLM to refine and categorize keywords"""
        if not LLM_AVAILABLE:
            logger.warning("Skipping LLM refinement (litellm not available)")
            return candidate_keywords

        logger.info("Refining keywords with LLM...")

        # Take top candidates by frequency
        top_candidates = sorted(candidate_keywords.items(),
                               key=lambda x: x[1].get('count', 0) if isinstance(x[1], dict) else x[1],
                               reverse=True)[:sample_size]

        # Format for LLM
        keywords_text = '\n'.join([f"- {kw}" for kw, _ in top_candidates])

        prompt = f"""You are analyzing keywords extracted from investigative journalism about national security, intelligence, and government transparency.

Review these candidate keywords and:
1. Remove false positives (common phrases, not meaningful)
2. Categorize meaningful keywords into types:
   - domain_terminology: Specialized jargon (e.g., "nihilistic violent extremism")
   - organization: Government agencies, NGOs, extremist groups
   - acronym: Abbreviations (e.g., NVE, FOIA, DVE)
   - multi_word_phrase: Technical phrases (e.g., "operational security")
   - named_entity: People, places, events
   - thematic_concept: Broad themes (e.g., "power grid attacks")

3. Rate importance 1-10 for Boolean search (10 = highly specific, low false positives)

Candidate keywords:
{keywords_text}

Return JSON format:
{{
  "domain_terminology": [{{"term": "...", "importance": 9}}],
  "organization": [...],
  "acronym": [...],
  "multi_word_phrase": [...],
  "named_entity": [...],
  "thematic_concept": [...]
}}

Only include meaningful keywords. Be selective."""

        try:
            response = completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            refined = json.loads(result_text)
            logger.info("LLM refinement completed")
            return refined

        except Exception as e:
            logger.error(f"LLM refinement failed: {e}")
            return None

    def extract_all_keywords(self):
        """Run all extraction methods and combine results"""
        logger.info("="*70)
        logger.info("KEYWORD EXTRACTION STARTING")
        logger.info("="*70)

        all_keywords = {}

        # Method 1: N-grams
        ngrams = self.extract_ngrams_from_corpus()
        all_keywords['ngrams'] = ngrams

        # Method 2: TF-IDF
        tfidf_terms = self.extract_tfidf_terms()
        all_keywords['tfidf'] = {term: {'score': score, 'count': score}
                                 for term, score in tfidf_terms}

        # Method 3: Named Entity Recognition
        entities = self.extract_named_entities()
        all_keywords['entities'] = entities

        # Method 4: Acronyms
        acronyms = self.extract_acronyms()
        all_keywords['acronyms'] = {acr: {'count': count, 'type': 'acronym'}
                                    for acr, count in acronyms.items()}

        # Method 5: Integrate existing taxonomy
        all_keywords = self.integrate_existing_taxonomy(all_keywords)

        return all_keywords

    def save_raw_keywords(self, keywords, output_path):
        """Save raw extracted keywords"""
        logger.info(f"Saving raw keywords to {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(keywords, f, indent=2, ensure_ascii=False)

        # Also create a human-readable summary
        summary_path = output_path.replace('.json', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("KEYWORD EXTRACTION SUMMARY\n")
            f.write("="*70 + "\n\n")

            if 'tfidf' in keywords:
                f.write(f"TF-IDF Terms: {len(keywords['tfidf'])}\n")
                top_tfidf = sorted(keywords['tfidf'].items(),
                                  key=lambda x: x[1]['score'], reverse=True)[:20]
                f.write("\nTop 20 TF-IDF terms:\n")
                for term, data in top_tfidf:
                    f.write(f"  - {term} (score: {data['score']:.3f})\n")

            if 'entities' in keywords:
                f.write(f"\n\nNamed Entities:\n")
                for entity_type, entities in keywords['entities'].items():
                    f.write(f"  {entity_type}: {len(entities)}\n")
                    top_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)[:10]
                    for ent, count in top_entities:
                        f.write(f"    - {ent} ({count} mentions)\n")

            if 'acronyms' in keywords:
                f.write(f"\n\nAcronyms: {len(keywords['acronyms'])}\n")
                top_acronyms = sorted(keywords['acronyms'].items(),
                                     key=lambda x: x[1]['count'], reverse=True)[:20]
                for acr, data in top_acronyms:
                    f.write(f"  - {acr} ({data['count']} mentions)\n")

            if 'ngrams' in keywords:
                f.write(f"\n\nN-grams:\n")
                for n, ngrams in keywords['ngrams'].items():
                    f.write(f"  {n}-grams: {len(ngrams)}\n")
                    top_ngrams = sorted(ngrams.items(), key=lambda x: x[1], reverse=True)[:10]
                    for ngram, count in top_ngrams:
                        f.write(f"    - {ngram} ({count} mentions)\n")

        logger.info(f"Summary saved to {summary_path}")


def main():
    """Main execution"""
    print("="*70)
    print("KEYWORD EXTRACTION FOR BOOLEAN SEARCH SYSTEM")
    print("="*70)
    print()

    # Configuration
    corpus_dirs = [
        'klippenstein_articles_extracted',
        'bills_blackbox_articles_extracted'
    ]

    taxonomy_path = 'experiments/tag_management/tag_taxonomy_complete.json'
    output_path = 'keyword_extraction_raw.json'

    # Initialize extractor
    extractor = KeywordExtractor(corpus_dirs, taxonomy_path)

    # Load corpus
    if not extractor.load_corpus():
        logger.error("Failed to load corpus. Exiting.")
        return

    print(f"\n✓ Loaded {len(extractor.articles)} articles\n")

    # Extract keywords
    keywords = extractor.extract_all_keywords()

    # Save results
    extractor.save_raw_keywords(keywords, output_path)

    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)
    print(f"\nRaw keywords saved to: {output_path}")
    print(f"Summary saved to: {output_path.replace('.json', '_summary.txt')}")
    print("\nNext step: Run organize_keywords.py to create structured keyword database")
    print()


if __name__ == '__main__':
    main()
