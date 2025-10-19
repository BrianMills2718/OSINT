#!/usr/bin/env python3
"""
Unified batch tagging for both Klippenstein and Bills Blackbox articles.
Uses 5 workers at a time to tag articles using gpt-5-mini.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import litellm
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Try to load .env from multiple locations
env_locations = [
    Path("/home/brian/sam_gov/.env"),
    Path("/home/brian/projects/autocoder4_cc/.env"),
    Path("/home/brian/projects/qualitative_coding/.env"),
    Path.home() / ".env"
]

for env_path in env_locations:
    if env_path.exists():
        print(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
        break
else:
    print("No .env file found, using system environment variables")
    load_dotenv()

# Verify API key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment. Please set it in .env or as an environment variable.")

def get_text(resp):
    """Extract text from gpt-5-mini responses() API response"""
    texts = []
    if hasattr(resp, 'output') and resp.output:
        for item in resp.output:
            if hasattr(item, "content") and item.content is not None:
                for c in item.content:
                    if hasattr(c, "text") and c.text is not None:
                        texts.append(c.text)

    if not texts:
        # Fallback: try to get text from string representation
        return str(resp)

    return "\n".join(texts)

def is_news_roundup(content):
    """
    Detect if article is a collection/roundup style with multiple stories.
    Returns True if it contains section markers like "Watch", "Feel Like This Should Be", etc.
    """
    roundup_markers = [
        "Watch",
        "Feel Like This Should Be",
        "Quick Hits",
        "Round-Up",
        "roundup",
        "Round up"
    ]
    return any(marker in content for marker in roundup_markers)

def generate_tags_for_article(article_data):
    """
    Use gpt-5-mini to generate relevant tags for an article.
    Returns structured JSON with tags.
    """

    # Check if this is a news roundup article
    is_roundup = is_news_roundup(article_data['content'])

    roundup_instruction = ""
    if is_roundup:
        roundup_instruction = '\n\nIMPORTANT: This appears to be a news roundup/collection article with multiple stories. Include "news-roundup" as one of your tags in addition to tags for the main topics covered.'

    # Create the prompt
    prompt = f"""Analyze this article and generate relevant tags for categorization.

Article Title: {article_data['title']}
Article URL: {article_data['url']}
Year: {article_data['year']}

Article Content:
{article_data['content'][:3000]}...

Generate 5-10 relevant tags that categorize this article. Tags should cover:
- Main topics (e.g., "surveillance", "FBI", "privacy")
- Specific entities mentioned (e.g., "Congress", "DOJ")
- Themes (e.g., "civil-liberties", "national-security")
- Geographic focus if relevant (e.g., "USA", "Middle-East"){roundup_instruction}

IMPORTANT: Do NOT create meta/administrative tags like: years (2023, 2024), newsletter-related (email, contact, subscription, support, customer-service), or website mechanics. Only create tags about the article's actual content and topics.

Return the tags as a JSON object according to the schema."""

    # Define the JSON schema for structured output
    tag_schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "minItems": 5,
                "maxItems": 10
            },
            "primary_topic": {
                "type": "string",
                "description": "The main topic of the article in 1-3 words"
            },
            "summary": {
                "type": "string",
                "description": "One sentence summary of why these tags were chosen"
            }
        },
        "required": ["tags", "primary_topic", "summary"],
        "additionalProperties": False
    }

    # Call gpt-5-mini with structured output
    response = litellm.responses(
        model="gpt-5-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "article_tags",
                "schema": tag_schema,
                "strict": True
            }
        }
    )

    # Extract and parse the response
    result_text = get_text(response)
    return json.loads(result_text)

def tag_article(file_path):
    """Tag a single article and return result"""
    filename = os.path.basename(file_path)

    try:
        # Load the article
        with open(file_path, 'r', encoding='utf-8') as f:
            article = json.load(f)

        # Generate tags
        start_time = time.time()
        tags_result = generate_tags_for_article(article)
        elapsed = time.time() - start_time

        # Add tagging to article
        article['tagging'] = tags_result

        # Save the tagged article
        output_file = str(file_path).replace('.json', '_tagged.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(article, f, indent=2, ensure_ascii=False)

        return {
            'status': 'success',
            'filename': filename,
            'tags': tags_result['tags'],
            'primary_topic': tags_result['primary_topic'],
            'elapsed': elapsed
        }

    except Exception as e:
        return {
            'status': 'error',
            'filename': filename,
            'error': str(e)
        }

def get_untagged_articles(directory):
    """Get all untagged articles from a directory"""
    all_files = list(Path(directory).glob("*.json"))
    # Filter out files that end with _tagged.json
    source_files = [f for f in all_files if not f.name.endswith('_tagged.json')]

    # Filter out files that already have a corresponding _tagged.json file
    untagged_files = []
    for f in source_files:
        tagged_version = str(f).replace('.json', '_tagged.json')
        if not Path(tagged_version).exists():
            untagged_files.append(f)

    return untagged_files

def main():
    # Parse command line arguments
    batch_size = 20
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except ValueError:
            print(f"Invalid batch size: {sys.argv[1]}, using default: 20")

    # Get untagged articles from both collections
    klippenstein_dir = Path("/home/brian/sam_gov/klippenstein_articles_extracted")
    bills_dir = Path("/home/brian/sam_gov/bills_blackbox_articles_extracted")

    klippenstein_files = get_untagged_articles(klippenstein_dir)
    bills_files = get_untagged_articles(bills_dir)

    # Combine all files
    all_untagged = klippenstein_files + bills_files

    # Select articles to tag
    files_to_tag = all_untagged[:batch_size]

    print("="*70)
    print(f"Unified Batch Tagging with gpt-5-mini")
    print("="*70)
    print(f"Klippenstein articles available: {len(klippenstein_files)}")
    print(f"Bills Blackbox articles available: {len(bills_files)}")
    print(f"Total untagged articles: {len(all_untagged)}")
    print(f"Tagging this batch: {batch_size} articles")
    print(f"Workers: 5 parallel")
    print("="*70)
    print()

    if not files_to_tag:
        print("No untagged articles found!")
        return

    # Process with 5 workers at a time
    results = []
    successful = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks
        future_to_file = {executor.submit(tag_article, file): file for file in files_to_tag}

        # Process completed tasks
        for future in as_completed(future_to_file):
            result = future.result()
            results.append(result)

            if result['status'] == 'success':
                successful += 1
                print(f"✅ [{successful + failed}/{len(files_to_tag)}] {result['filename']}")
                print(f"   Primary: {result['primary_topic']}")
                print(f"   Tags: {', '.join(result['tags'][:5])}{'...' if len(result['tags']) > 5 else ''}")
                print(f"   Time: {result['elapsed']:.1f}s")
            else:
                failed += 1
                print(f"❌ [{successful + failed}/{len(files_to_tag)}] {result['filename']}")
                print(f"   Error: {result['error']}")
            print()

    # Summary
    print("="*70)
    print("BATCH TAGGING COMPLETE")
    print("="*70)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(files_to_tag)}")
    print(f"Remaining untagged: {len(all_untagged) - len(files_to_tag)}")

    if successful > 0:
        avg_time = sum(r['elapsed'] for r in results if r['status'] == 'success') / successful
        print(f"Average time per article: {avg_time:.1f}s")

    print("="*70)

    if len(all_untagged) > len(files_to_tag):
        print(f"\nTo continue tagging, run: python3 {sys.argv[0]} {batch_size}")

if __name__ == "__main__":
    main()
