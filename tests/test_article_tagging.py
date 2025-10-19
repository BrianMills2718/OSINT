#!/usr/bin/env python3
"""
Test gpt-5-mini with structured output to generate tags for Klippenstein articles.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import litellm

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

def main():
    # Test with the FBI DNA article
    test_file = "/home/brian/sam_gov/klippenstein_articles_extracted/2023_FBI-Hoovered-Up-Over-21-Million-DNA-Profiles-7-of-the-US.json"

    print("="*70)
    print("Testing gpt-5-mini with structured output for article tagging")
    print("="*70)

    # Load the article
    print(f"\nLoading article: {os.path.basename(test_file)}")
    with open(test_file, 'r', encoding='utf-8') as f:
        article = json.load(f)

    print(f"Title: {article['title']}")
    print(f"Year: {article['year']}")
    print(f"Content length: {len(article['content'])} characters")

    # Generate tags
    print("\nGenerating tags with gpt-5-mini...")
    tags_result = generate_tags_for_article(article)

    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"\nPrimary Topic: {tags_result['primary_topic']}")
    print(f"\nTags ({len(tags_result['tags'])}):")
    for tag in tags_result['tags']:
        print(f"  - {tag}")
    print(f"\nSummary: {tags_result['summary']}")

    # Save the result
    output_file = test_file.replace('.json', '_tagged.json')
    article['tagging'] = tags_result

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(article, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Tagged article saved to: {output_file}")
    print("="*70)

if __name__ == "__main__":
    main()
