#!/usr/bin/env python3
"""
Generate Relevance Descriptions for Boolean Queries

This script analyzes the keyword database and source articles to create
relevance descriptions explaining what type of content each query is looking for
and why it matters based on the investigative journalism context.

For each boolean query, we:
1. Identify which articles in the corpus used these keywords
2. Analyze the context/themes of those articles
3. Generate a relevance description explaining:
   - What type of content this query finds
   - Why it's relevant to investigative journalism
   - What kind of stories it would surface
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import logging
from dotenv import load_dotenv
from llm_utils import acompletion
import asyncio

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def generate_relevance_description(
    query_name: str,
    query_string: str,
    theme: str,
    keywords: List[str],
    sample_articles: List[Dict]
) -> str:
    """
    Generate a relevance description for a boolean query using LLM.

    Args:
        query_name: Name of the query
        query_string: The actual boolean query string
        theme: Theme category (e.g., "National Security & Intelligence")
        keywords: List of primary keywords from this theme
        sample_articles: Sample articles that mention these keywords

    Returns:
        Relevance description text
    """

    # Prepare article context
    article_context = ""
    if sample_articles:
        article_context = "\n\nSample articles mentioning these keywords:\n"
        for i, article in enumerate(sample_articles[:3], 1):
            article_context += f"\n{i}. Title: {article.get('title', 'Untitled')}\n"
            snippet = article.get('content', '')[:500]
            article_context += f"   Context: {snippet}...\n"

    prompt = f"""You are analyzing boolean search queries extracted from investigative journalism.

Theme: {theme}
Query Name: {query_name}
Boolean Query: {query_string}
Primary Keywords: {', '.join(keywords[:10])}
{article_context}

Task: Write a 2-3 sentence "relevance description" that explains:
1. What TYPE of content this query is designed to find
2. WHY this content matters to investigative journalists (based on the article context)
3. What KIND of stories/documents this would surface

Focus on:
- Government transparency, accountability, national security issues
- Patterns of official misconduct, surveillance, civil liberties
- Investigative journalism themes (not general news)

Be SPECIFIC to this query's focus. Don't be generic.

Example good description:
"This query monitors government communications about domestic extremism classification and threat assessments. Based on Klippenstein's reporting on FBI threat categorizations, this surfaces official documents that reveal how federal agencies define and track domestic threats, including controversial designations like 'Black Identity Extremists' or 'Nihilistic Violent Extremism' that may lack evidence or disproportionately target certain groups."

Write relevance description:"""

    try:
        response = await acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        description = response.choices[0].message.content.strip()
        # Remove quotes if LLM wrapped it
        description = description.strip('"').strip("'")

        return description

    except Exception as e:
        logger.error(f"Error generating description for {query_name}: {e}")
        return f"Query for {theme.lower()} topics including {', '.join(keywords[:3])}."


async def load_corpus_articles(corpus_dirs: List[str]) -> List[Dict]:
    """Load all articles from corpus directories"""
    articles = []

    for corpus_dir in corpus_dirs:
        if not os.path.exists(corpus_dir):
            logger.warning(f"Directory not found: {corpus_dir}")
            continue

        for json_file in Path(corpus_dir).glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    if 'content' in article and article['content']:
                        articles.append({
                            'title': article.get('title', ''),
                            'content': article['content'],
                            'url': article.get('url', ''),
                            'tags': article.get('tags', [])
                        })
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

    logger.info(f"Loaded {len(articles)} articles from corpus")
    return articles


def find_relevant_articles(keywords: List[str], articles: List[Dict], limit: int = 3) -> List[Dict]:
    """Find articles that mention any of the keywords"""
    relevant = []
    keywords_lower = [k.lower() for k in keywords]

    for article in articles:
        content_lower = (article['title'] + ' ' + article['content']).lower()

        # Check if any keyword appears
        for keyword in keywords_lower:
            if keyword in content_lower:
                relevant.append(article)
                break

        if len(relevant) >= limit:
            break

    return relevant


async def generate_all_descriptions():
    """Generate relevance descriptions for all boolean queries"""

    logger.info("="*80)
    logger.info("GENERATING RELEVANCE DESCRIPTIONS")
    logger.info("="*80)

    # Load keyword database
    db_path = 'data/keyword_database.json'
    if not os.path.exists(db_path):
        logger.error(f"Keyword database not found: {db_path}")
        return

    with open(db_path, 'r') as f:
        db = json.load(f)

    # Load corpus articles
    corpus_dirs = [
        'klippenstein_articles_extracted',
        'bills_blackbox_articles_extracted'
    ]
    articles = await load_corpus_articles(corpus_dirs)

    if not articles:
        logger.warning("No articles loaded from corpus - descriptions will be generic")

    # Process each theme's boolean queries
    enriched_queries = {}
    total_queries = sum(len(queries) for queries in db['boolean_queries'].values())
    processed = 0

    for theme, queries in db['boolean_queries'].items():
        logger.info(f"\nProcessing theme: {theme}")
        enriched_queries[theme] = []

        # Get keywords for this theme
        theme_keywords = db['themes'].get(theme, {}).get('primary_terms', [])[:20]

        for query in queries:
            processed += 1
            logger.info(f"  [{processed}/{total_queries}] {query['name']}")

            # Find sample articles for context
            sample_articles = find_relevant_articles(theme_keywords, articles, limit=3)

            # Generate relevance description
            description = await generate_relevance_description(
                query_name=query['name'],
                query_string=query['query'],
                theme=theme,
                keywords=theme_keywords,
                sample_articles=sample_articles
            )

            # Add to enriched query
            enriched_query = query.copy()
            enriched_query['relevance_description'] = description
            enriched_query['theme'] = theme
            enriched_queries[theme].append(enriched_query)

            logger.info(f"     Description: {description[:100]}...")

    # Save enriched database
    output = {
        'metadata': {
            'created': db['metadata']['created'],
            'enriched': str(Path(__file__).stat().st_mtime),
            'total_themes': len(enriched_queries),
            'total_queries': total_queries,
            'source_articles': len(articles)
        },
        'boolean_queries_with_descriptions': enriched_queries,
        'original_themes': db['themes']  # Keep original keyword data
    }

    output_path = 'data/keyword_database_enriched.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✓ Saved enriched database to: {output_path}")

    # Also create a human-readable report
    report_path = 'data/boolean_queries_with_relevance.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Boolean Queries with Relevance Descriptions\n\n")
        f.write(f"Generated from investigative journalism corpus ({len(articles)} articles)\n\n")
        f.write("---\n\n")

        for theme, queries in enriched_queries.items():
            f.write(f"## {theme}\n\n")

            for query in queries:
                f.write(f"### {query['name']}\n\n")
                f.write(f"**Query**: `{query['query']}`\n\n")
                f.write(f"**Relevance**: {query['relevance_description']}\n\n")
                f.write(f"**Sources**: {', '.join(query['sources'])}\n\n")
                f.write("---\n\n")

    logger.info(f"✓ Saved readable report to: {report_path}")

    logger.info("\n" + "="*80)
    logger.info(f"COMPLETE: Enriched {total_queries} queries across {len(enriched_queries)} themes")
    logger.info("="*80)


if __name__ == '__main__':
    asyncio.run(generate_all_descriptions())
