#!/usr/bin/env python3
"""
Generate a comprehensive, interactive HTML page for the tag taxonomy.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_data():
    """Load taxonomy and tag index data"""

    with open('tag_taxonomy_complete.json', 'r') as f:
        taxonomy = json.load(f)

    with open('tag_index_full.json', 'r') as f:
        tag_index = json.load(f)

    return taxonomy, tag_index

def organize_by_category(taxonomy_data, tag_counts):
    """Organize tags by category and sort by count"""

    by_category = defaultdict(list)

    for entry in taxonomy_data['taxonomy']:
        by_category[entry['category']].append(entry)

    # Sort tags within each category by count (high to low)
    for category in by_category:
        by_category[category].sort(key=lambda x: tag_counts.get(x['tag'], 0), reverse=True)

    return by_category

def generate_html(taxonomy, tag_index):
    """Generate complete HTML page"""

    # Get tag counts from tag_index
    tag_counts = {item['tag']: item['count'] for item in tag_index['tags']}

    # Get articles for each tag
    tag_articles = {item['tag']: item['articles'] for item in tag_index['tags']}

    # Count articles by source
    all_urls = set()
    for tag_entry in tag_index['tags']:
        for article in tag_entry['articles']:
            all_urls.add(article['url'])

    ken_count = len([url for url in all_urls if 'kenklippenstein.com' in url])
    bill_count = len([url for url in all_urls if 'governmentsecrets.substack.com' in url])

    # Organize by category and sort by count
    by_category = organize_by_category(taxonomy, tag_counts)

    # Sort categories by tag count
    sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ken and Bill Articles Tagging</title>
    <style>
        * {{{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}}}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .explanation {{
            background: #fff;
            padding: 20px 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}

        .explanation h3 {{
            color: #667eea;
            margin-bottom: 12px;
            font-size: 1.2em;
        }}

        .explanation p {{
            color: #555;
            line-height: 1.8;
            margin-bottom: 8px;
        }}

        .explanation strong {{
            color: #333;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}

        .stat-label {{
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }}

        .controls {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .search-box {{
            width: 100%;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 6px;
            transition: border-color 0.3s;
        }}

        .search-box:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .category-nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}

        .category-btn {{
            padding: 8px 16px;
            background: #f0f0f0;
            border: 2px solid transparent;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }}

        .category-btn:hover {{
            background: #e0e0e0;
        }}

        .category-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}

        .category-section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .category-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .category-header h2 {{
            font-size: 1.5em;
        }}

        .category-count {{
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }}

        .category-content {{
            padding: 30px;
        }}

        .tags-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}

        .tag-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            transition: all 0.3s;
            cursor: pointer;
        }}

        .tag-card:hover {{
            background: #e9ecef;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}

        .tag-name {{
            font-weight: 600;
            font-size: 1.1em;
            color: #333;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .tag-badge {{
            background: #667eea;
            color: white;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: normal;
        }}

        .tag-meta {{
            display: flex;
            gap: 15px;
            font-size: 0.85em;
            color: #666;
            margin-top: 8px;
        }}

        .tag-type {{
            background: #e9ecef;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .tag-fit {{
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .fit-good {{
            background: #d4edda;
            color: #155724;
        }}

        .fit-fair {{
            background: #fff3cd;
            color: #856404;
        }}

        .tag-articles {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #dee2e6;
            display: none;
        }}

        .tag-card.expanded .tag-articles {{
            display: block;
        }}

        .articles-header {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}

        .article-item {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .article-item:last-child {{
            border-bottom: none;
        }}

        .article-title {{
            font-size: 0.9em;
            color: #667eea;
            text-decoration: none;
            display: block;
            margin-bottom: 4px;
        }}

        .article-title:hover {{
            text-decoration: underline;
            color: #764ba2;
        }}

        .article-meta {{
            font-size: 0.8em;
            color: #999;
        }}

        .tag-card.expanded {{
            background: #fff;
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}

        .hidden {{
            display: none;
        }}

        .no-results {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 1.1em;
        }}

        .expand-icon {{
            transition: transform 0.3s;
        }}

        .category-section.collapsed .category-content {{
            display: none;
        }}

        .category-section.collapsed .expand-icon {{
            transform: rotate(-90deg);
        }}

        footer {{
            text-align: center;
            padding: 40px 0;
            color: #666;
            margin-top: 40px;
        }}

        @media (max-width: 768px) {{
            .tags-grid {{
                grid-template-columns: 1fr;
            }}

            .category-nav {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Ken and Bill Articles Tagging</h1>
            <p>{ken_count} articles from Ken Klippenstein • {bill_count} articles from Bills Blackbox</p>
        </div>
    </header>

    <div class="container">
        <div class="explanation">
            <h3>About Tag Quality</h3>
            <p><strong>Good Fit:</strong> Tag clearly belongs to its assigned category with no ambiguity. The categorization is intuitive and accurate.</p>
            <p><strong>Fair Fit:</strong> Tag fits the category reasonably well, but could potentially belong to another category or has some ambiguity. Still acceptable for the taxonomy.</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_tags}</div>
                <div class="stat-label">Total Tags</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_categories}</div>
                <div class="stat-label">Categories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{good_fit_pct}%</div>
                <div class="stat-label">Good Fit</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{fair_fit_pct}%</div>
                <div class="stat-label">Fair Fit</div>
            </div>
        </div>

        <div class="controls">
            <input type="text"
                   class="search-box"
                   id="searchBox"
                   placeholder="🔍 Search tags by name..."
                   onkeyup="filterTags()">

            <div class="category-nav" id="categoryNav">
                <button class="category-btn active" onclick="filterByCategory('all')">All Categories</button>
{category_buttons}
            </div>
        </div>

        <div id="taxonomyContent">
{category_sections}
        </div>

        <div id="noResults" class="no-results hidden">
            No tags found matching your search.
        </div>
    </div>

    <footer>
        <p>Generated from {total_articles} normalized articles • {total_tags} unique tags across {total_categories} categories</p>
        <p style="margin-top: 10px; color: #999;">Tag Taxonomy v1.0 • Last Updated: 2025</p>
    </footer>

    <script>
        let currentCategory = 'all';

        function filterByCategory(category) {{
            currentCategory = category;

            // Update active button
            document.querySelectorAll('.category-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');

            // Show/hide category sections
            document.querySelectorAll('.category-section').forEach(section => {{
                if (category === 'all' || section.dataset.category === category) {{
                    section.classList.remove('hidden');
                }} else {{
                    section.classList.add('hidden');
                }}
            }});

            // Re-apply search filter
            filterTags();
        }}

        function filterTags() {{
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            let visibleCount = 0;

            document.querySelectorAll('.category-section').forEach(section => {{
                if (currentCategory !== 'all' && section.dataset.category !== currentCategory) {{
                    return;
                }}

                let sectionHasVisible = false;

                section.querySelectorAll('.tag-card').forEach(card => {{
                    const tagName = card.dataset.tag.toLowerCase();
                    const matches = tagName.includes(searchTerm);

                    if (matches) {{
                        card.classList.remove('hidden');
                        sectionHasVisible = true;
                        visibleCount++;
                    }} else {{
                        card.classList.add('hidden');
                    }}
                }});

                // Hide category section if no tags match
                if (sectionHasVisible) {{
                    section.classList.remove('hidden');
                }} else {{
                    section.classList.add('hidden');
                }}
            }});

            // Show "no results" message
            if (visibleCount === 0) {{
                document.getElementById('noResults').classList.remove('hidden');
            }} else {{
                document.getElementById('noResults').classList.add('hidden');
            }}
        }}

        function toggleCategory(categoryName) {{
            const section = document.querySelector(`[data-category="${{categoryName}}"]`);
            section.classList.toggle('collapsed');
        }}

        function toggleTag(element) {{
            element.classList.toggle('expanded');
        }}
    </script>
</body>
</html>"""

    # Generate category buttons
    category_buttons = []
    for category, tags in sorted_categories:
        if category == 'Uncategorized':
            continue
        safe_name = category.replace('&', 'and').replace('/', '-')
        category_buttons.append(
            f'                <button class="category-btn" onclick="filterByCategory(\'{safe_name}\')">{category} ({len(tags)})</button>'
        )

    # Generate category sections
    category_sections = []
    for category, tags in sorted_categories:
        safe_name = category.replace('&', 'and').replace('/', '-')

        # Generate tag cards
        tag_cards = []
        for tag_entry in tags:
            tag_name = tag_entry['tag']
            count = tag_counts.get(tag_name, 0)
            entity_type = tag_entry['entity_type']
            taxonomy_fit = tag_entry['taxonomy_fit']

            fit_class = 'fit-good' if taxonomy_fit == 'good' else 'fit-fair'
            fit_label = taxonomy_fit.upper()

            # Get articles for this tag
            articles = tag_articles.get(tag_name, [])

            # Generate article list HTML
            articles_html = ''
            if articles:
                article_items = []
                for article in articles[:10]:  # Show first 10 articles
                    title = article.get('title', 'Untitled')
                    url = article.get('url', '#')
                    year = article.get('year', '')
                    article_items.append(f'''
                        <div class="article-item">
                            <a href="{url}" target="_blank" class="article-title">{title}</a>
                            <div class="article-meta">{year}</div>
                        </div>''')

                more_text = f'<div class="article-meta" style="text-align: center; padding-top: 8px;">... and {len(articles) - 10} more</div>' if len(articles) > 10 else ''
                articles_html = f'''
                    <div class="tag-articles">
                        <div class="articles-header">Articles ({len(articles)}):</div>
                        {''.join(article_items)}
                        {more_text}
                    </div>'''

            tag_cards.append(f'''
                <div class="tag-card" data-tag="{tag_name}" onclick="toggleTag(this)">
                    <div class="tag-name">
                        <span>{tag_name}</span>
                        <span class="tag-badge">{count}</span>
                    </div>
                    <div class="tag-meta">
                        <span class="tag-type">{entity_type}</span>
                        <span class="tag-fit {fit_class}">{fit_label}</span>
                    </div>{articles_html}
                </div>''')

        tags_html = '\n'.join(tag_cards)

        category_sections.append(f'''
        <div class="category-section" data-category="{safe_name}">
            <div class="category-header" onclick="toggleCategory('{safe_name}')">
                <h2>{category}</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="category-count">{len(tags)} tags</span>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            <div class="category-content">
                <div class="tags-grid">{tags_html}
                </div>
            </div>
        </div>''')

    # Fill in template
    html = html.format(
        total_tags=taxonomy['metadata']['total_tags'],
        total_articles=tag_index['metadata']['total_articles'],
        total_categories=len(by_category),
        good_fit_pct=round(taxonomy['metadata']['good_fit'] / taxonomy['metadata']['total_tags'] * 100, 1),
        fair_fit_pct=round(taxonomy['metadata']['fair_fit'] / taxonomy['metadata']['total_tags'] * 100, 1),
        ken_count=ken_count,
        bill_count=bill_count,
        category_buttons='\n'.join(category_buttons),
        category_sections='\n'.join(category_sections)
    )

    return html

def main():
    print("="*70)
    print("Generating Interactive Tag Taxonomy HTML")
    print("="*70)
    print()

    # Load data
    print("1. Loading taxonomy and tag index data...")
    taxonomy, tag_index = load_data()
    print(f"   ✅ Loaded {taxonomy['metadata']['total_tags']} tags")

    # Generate HTML
    print("\n2. Generating HTML...")
    html = generate_html(taxonomy, tag_index)

    # Save to file
    output_file = Path("/home/brian/sam_gov/taxonomy_browse.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"   ✅ Generated HTML")

    print(f"\n3. Saved to: {output_file}")
    print()
    print("="*70)
    print("DONE!")
    print("="*70)
    print()
    print(f"📄 Open in browser: file://{output_file.absolute()}")
    print()

if __name__ == "__main__":
    main()
