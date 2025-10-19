#!/usr/bin/env python3
"""
Scraper for Bill's Black Box of Government Secrets from Substack.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from urllib.parse import urljoin
import re

class SubstackScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_page(self, url, retries=3):
        """Fetch a page with retries."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def get_year_links(self):
        """Get all year sitemap links from main sitemap."""
        print("Fetching main sitemap...")
        html = self.get_page(f"{self.base_url}/sitemap")
        soup = BeautifulSoup(html, 'html.parser')

        year_links = []
        # Find all links that match the pattern /sitemap/YYYY
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/sitemap/' in href and re.search(r'/sitemap/\d{4}', href):
                full_url = urljoin(self.base_url, href)
                year = re.search(r'/sitemap/(\d{4})', href).group(1)
                year_links.append({'year': year, 'url': full_url})

        return year_links

    def get_article_links_from_year(self, year_url):
        """Get all article links from a year sitemap page."""
        print(f"Fetching articles from {year_url}...")
        html = self.get_page(year_url)
        soup = BeautifulSoup(html, 'html.parser')

        articles = []
        # Find all article links - typically in the main content area
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Filter for actual article links (not navigation, footer, etc.)
            if href.startswith('/p/') or '/p/' in href:
                full_url = urljoin(self.base_url, href)
                title = link.get_text(strip=True)
                if title and full_url not in [a['url'] for a in articles]:
                    articles.append({'title': title, 'url': full_url})

        return articles

    def scrape_article(self, article_url):
        """Scrape the content of an individual article."""
        print(f"Scraping: {article_url}")
        html = self.get_page(article_url)
        soup = BeautifulSoup(html, 'html.parser')

        article_data = {
            'url': article_url,
            'title': '',
            'date': '',
            'content': '',
            'raw_html': html
        }

        # Extract title
        title_tag = soup.find('h1')
        if title_tag:
            article_data['title'] = title_tag.get_text(strip=True)

        # Extract date - look for common date patterns
        date_tag = soup.find('time')
        if date_tag:
            article_data['date'] = date_tag.get_text(strip=True)

        # Extract main content - Substack typically uses specific classes
        content_div = soup.find('div', class_=re.compile(r'post-content|article-content|body'))
        if content_div:
            article_data['content'] = content_div.get_text(separator='\n', strip=True)
        else:
            # Fallback: get all paragraph text
            paragraphs = soup.find_all('p')
            article_data['content'] = '\n\n'.join([p.get_text(strip=True) for p in paragraphs])

        return article_data

    def run(self, output_dir):
        """Run the full scraping process."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        all_articles = []

        # Get all year links
        year_links = self.get_year_links()
        print(f"Found {len(year_links)} years: {[y['year'] for y in year_links]}")

        # Get article links from each year
        for year_data in year_links:
            print(f"\n--- Processing {year_data['year']} ---")
            articles = self.get_article_links_from_year(year_data['url'])
            print(f"Found {len(articles)} articles in {year_data['year']}")

            for article in articles:
                article['year'] = year_data['year']

            all_articles.extend(articles)
            time.sleep(1)  # Be polite to the server

        # Save article list
        print(f"\nTotal articles found: {len(all_articles)}")
        with open(output_path / 'article_list.json', 'w') as f:
            json.dump(all_articles, f, indent=2)

        # Scrape each article
        print("\n--- Starting article scraping ---")
        scraped_count = 0
        skipped_count = 0

        for i, article in enumerate(all_articles, 1):
            # Create filename from title
            safe_title = re.sub(r'[^\w\s-]', '', article['title'])
            safe_title = re.sub(r'[-\s]+', '-', safe_title)[:100]
            filename = f"{article['year']}_{safe_title}.json"
            file_path = output_path / filename

            # Skip if already downloaded
            if file_path.exists():
                print(f"[{i}/{len(all_articles)}] SKIP (already exists): {article['title']}")
                skipped_count += 1
                continue

            print(f"\n[{i}/{len(all_articles)}]")
            try:
                article_data = self.scrape_article(article['url'])

                # Save article data
                with open(file_path, 'w') as f:
                    json.dump(article_data, f, indent=2)

                scraped_count += 1
                time.sleep(2)  # Be polite to the server

            except Exception as e:
                print(f"ERROR scraping {article['url']}: {e}")
                continue

        print(f"\n✓ Scraping session complete!")
        print(f"  - Newly scraped: {scraped_count}")
        print(f"  - Skipped (already exists): {skipped_count}")
        print(f"  - Total in directory: {len(list(output_path.glob('*.json')))}")
        print(f"  - Articles saved to {output_path}/")

        return all_articles


if __name__ == '__main__':
    scraper = SubstackScraper("https://governmentsecrets.substack.com")
    scraper.run('bills_blackbox_articles')
