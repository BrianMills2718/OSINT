#!/usr/bin/env python3
"""
Phase 4: Generate tag index for website navigation.

Creates a comprehensive tag index with:
- All normalized tags with article counts
- Categorization by topic (10 categories from taxonomy)
- Article lists for each tag
- JSON and HTML outputs for web integration
"""

import json
from pathlib import Path
from collections import defaultdict

def load_taxonomy_categories():
    """Load tag categorizations from complete taxonomy (Phase 1 + Phase 5)"""

    # Use complete taxonomy file which includes Phase 1 + Phase 5
    taxonomy_file = Path("/home/brian/sam_gov/tag_taxonomy_complete.json")
    with open(taxonomy_file, 'r') as f:
        data = json.load(f)

    # Build mapping of tag -> category
    tag_to_category = {}
    for entry in data['taxonomy']:
        tag_to_category[entry['tag']] = {
            'category': entry['category'],
            'entity_type': entry['entity_type']
        }

    return tag_to_category

def collect_article_tags():
    """Collect all tags from normalized articles"""

    print("   Scanning normalized articles...")

    klippenstein_dir = Path("/home/brian/sam_gov/klippenstein_articles_extracted")
    bills_dir = Path("/home/brian/sam_gov/bills_blackbox_articles_extracted")

    # Find normalized articles
    klippenstein_normalized = list(klippenstein_dir.glob("*_normalized.json"))
    bills_normalized = list(bills_dir.glob("*_normalized.json"))

    all_normalized = klippenstein_normalized + bills_normalized

    print(f"   Found {len(all_normalized)} normalized articles")

    # Collect tag -> [articles] mapping
    tag_to_articles = defaultdict(list)

    for article_file in all_normalized:
        with open(article_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        article_info = {
            'title': data.get('title', ''),
            'url': data.get('url', ''),
            'year': data.get('year', ''),
            'file': str(article_file.name)
        }

        for tag in data.get('tags', []):
            tag_to_articles[tag].append(article_info)

    return tag_to_articles

def main():
    print("="*70)
    print("Phase 4: Generate Tag Index for Website")
    print("="*70)

    # Load taxonomy categories
    print("\n1. Loading taxonomy categories from Phase 1...")
    tag_to_category = load_taxonomy_categories()
    print(f"   Loaded categories for {len(tag_to_category)} tags")

    # Collect all tags from normalized articles
    print("\n2. Collecting tags from normalized articles...")
    tag_to_articles = collect_article_tags()
    print(f"   Found {len(tag_to_articles)} unique tags")

    # Build comprehensive tag index
    print("\n3. Building tag index...")

    tag_index = []

    for tag, articles in tag_to_articles.items():
        # Get category info if available
        category_info = tag_to_category.get(tag, {
            'category': 'Uncategorized',
            'entity_type': 'none'
        })

        tag_entry = {
            'tag': tag,
            'count': len(articles),
            'category': category_info['category'],
            'entity_type': category_info['entity_type'],
            'articles': sorted(articles, key=lambda x: x['year'], reverse=True)
        }

        tag_index.append(tag_entry)

    # Sort by count (descending)
    tag_index.sort(key=lambda x: x['count'], reverse=True)

    # Save full tag index (JSON)
    print("\n4. Saving tag index...")

    full_index_file = Path("/home/brian/sam_gov/tag_index_full.json")
    full_index_data = {
        "metadata": {
            "total_tags": len(tag_index),
            "total_articles": len(set(a['file'] for t in tag_index for a in t['articles'])),
            "generated": "Phase 4"
        },
        "tags": tag_index
    }

    with open(full_index_file, 'w', encoding='utf-8') as f:
        json.dump(full_index_data, f, indent=2, ensure_ascii=False)

    print(f"   ✅ {full_index_file}")

    # Create category-organized index
    print("\n5. Creating category-organized index...")

    categories = defaultdict(list)

    for tag_entry in tag_index:
        category = tag_entry['category']
        categories[category].append({
            'tag': tag_entry['tag'],
            'count': tag_entry['count'],
            'entity_type': tag_entry['entity_type']
        })

    # Sort tags within each category by count
    for category in categories:
        categories[category].sort(key=lambda x: x['count'], reverse=True)

    category_index_file = Path("/home/brian/sam_gov/tag_index_by_category.json")
    category_index_data = {
        "metadata": {
            "total_categories": len(categories),
            "total_tags": len(tag_index)
        },
        "categories": [
            {
                "name": category,
                "tag_count": len(tags),
                "tags": tags
            }
            for category, tags in sorted(categories.items())
        ]
    }

    with open(category_index_file, 'w', encoding='utf-8') as f:
        json.dump(category_index_data, f, indent=2, ensure_ascii=False)

    print(f"   ✅ {category_index_file}")

    # Create simple HTML index for preview
    print("\n6. Creating HTML preview...")

    html_file = Path("/home/brian/sam_gov/tag_index_preview.html")
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tag Index Preview</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 30px; }
        .tag { display: inline-block; background: #f0f0f0; padding: 5px 12px; margin: 5px; border-radius: 3px; font-size: 14px; }
        .tag-count { background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; margin-left: 5px; font-size: 12px; }
        .category-stats { color: #999; font-size: 14px; margin-left: 10px; }
        .top-tags { background: #fff9e6; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Tag Index Preview</h1>
    <p><strong>Total Tags:</strong> """ + str(len(tag_index)) + """</p>

    <div class="top-tags">
        <h3>Top 50 Tags</h3>
        <div>
"""

    for tag_entry in tag_index[:50]:
        html_content += f'            <span class="tag">{tag_entry["tag"]}<span class="tag-count">{tag_entry["count"]}</span></span>\n'

    html_content += """        </div>
    </div>

    <h2>Tags by Category</h2>
"""

    for cat_data in category_index_data['categories']:
        cat_name = cat_data['name']
        cat_tags = cat_data['tags']
        html_content += f'    <h2>{cat_name} <span class="category-stats">({len(cat_tags)} tags)</span></h2>\n'
        html_content += '    <div>\n'

        for tag_info in cat_tags[:50]:  # Show first 50 per category
            html_content += f'        <span class="tag">{tag_info["tag"]}<span class="tag-count">{tag_info["count"]}</span></span>\n'

        if len(cat_tags) > 50:
            html_content += f'        <span class="tag">... and {len(cat_tags) - 50} more</span>\n'

        html_content += '    </div>\n'

    html_content += """
</body>
</html>
"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"   ✅ {html_file}")

    # Display summary
    print("\n7. Summary:")
    print(f"   Total unique tags: {len(tag_index)}")
    print(f"   Total categories: {len(categories)}")
    print()
    print("   Tags per category:")
    for cat_data in sorted(category_index_data['categories'], key=lambda x: x['tag_count'], reverse=True):
        print(f"     {cat_data['name']:35s} {cat_data['tag_count']:4d} tags")

    print("\n8. Top 20 tags:")
    for i, tag_entry in enumerate(tag_index[:20]):
        print(f"   {i+1:2d}. {tag_entry['count']:4d} | {tag_entry['tag']:40s} ({tag_entry['category']})")

    print("\n" + "="*70)
    print("DONE!")
    print("="*70)
    print(f"\nFiles generated:")
    print(f"  - {full_index_file.name} - Complete tag index with articles")
    print(f"  - {category_index_file.name} - Tags organized by category")
    print(f"  - {html_file.name} - HTML preview (open in browser)")

if __name__ == "__main__":
    main()
