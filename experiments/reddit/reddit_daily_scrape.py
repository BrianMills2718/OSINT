#!/usr/bin/env python3
"""
Reddit Daily Scraper

Scrapes last 24 hours of posts from curated subreddits for investigative journalism.
Implements Codex recommendations:
- Rate limiting (1-2s between subreddits)
- Comment depth limiting (top-level only)
- Credentials from .env
- Error handling per-subreddit
- JSON output to data/reddit/
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "../../data/reddit"
LOGS_DIR = SCRIPT_DIR / "../../data/logs"
CONFIG_FILE = SCRIPT_DIR / "reddit_config.json"

# Rate limiting settings
SLEEP_BETWEEN_SUBREDDITS = 1.5  # seconds (Codex recommendation: 1-2s)
SLEEP_BETWEEN_POSTS = 0.5  # seconds

# Comment settings
COMMENT_DEPTH_LIMIT = 0  # Codex recommendation: top-level only (0 = direct replies)


def load_config() -> Dict:
    """Load configuration from reddit_config.json."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def get_reddit_client():
    """Create Reddit client using credentials from .env."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    if not all([client_id, client_secret, username, password]):
        raise ValueError("Reddit credentials not found in .env file")

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent="SIGINT_Platform_Daily_Scraper/1.0"
    )


def get_post_data(submission) -> Dict:
    """Extract relevant data from a Reddit submission."""
    return {
        "id": submission.id,
        "title": submission.title,
        "url": submission.url,
        "score": submission.score,
        "upvote_ratio": submission.upvote_ratio,
        "num_comments": submission.num_comments,
        "author": submission.author.name if submission.author else "[deleted]",
        "created_utc": submission.created_utc,
        "created_date": datetime.fromtimestamp(submission.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
        "subreddit": submission.subreddit.display_name,
        "text": submission.selftext[:1000] if submission.selftext else "",
        "is_self": submission.is_self,
        "link_flair_text": submission.link_flair_text,
        "permalink": f"https://reddit.com{submission.permalink}"
    }


def get_comments_for_submission(submission) -> List[Dict]:
    """
    Fetch comments for a submission with depth limiting.

    Codex recommendation: Limit to top-level comments only (replace_more(limit=0))
    to reduce API load and runtime.
    """
    all_comments = []

    try:
        # Limit comment tree expansion (0 = top-level + direct replies only)
        submission.comments.replace_more(limit=COMMENT_DEPTH_LIMIT)

        for comment in submission.comments.list():
            if not hasattr(comment, 'body'):
                continue

            all_comments.append({
                "id": comment.id,
                "post_id": submission.id,
                "author": comment.author.name if comment.author else "[deleted]",
                "score": comment.score,
                "created_utc": comment.created_utc,
                "body": comment.body[:500]
            })
    except Exception as e:
        print(f"    Warning: Failed to fetch comments: {e}")

    return all_comments


def scrape_subreddit(reddit_client, subreddit_name: str, cutoff_time: float) -> Dict:
    """
    Scrape a single subreddit for posts in last 24 hours.

    Returns dict with success status and results.
    """
    try:
        subreddit = reddit_client.subreddit(subreddit_name)
        posts = []
        total_comments = 0

        # Get new posts
        for submission in subreddit.new(limit=100):  # Limit to avoid excessive scraping
            # Check if post is within last 24 hours
            if (time.time() - submission.created_utc) > 86400:
                continue  # Skip older posts

            # Get post data
            post_data = get_post_data(submission)

            # Get comments (limited depth)
            comments = get_comments_for_submission(submission)
            post_data["comments"] = comments
            total_comments += len(comments)

            posts.append(post_data)

            # Rate limiting between posts
            time.sleep(SLEEP_BETWEEN_POSTS)

        return {
            "success": True,
            "subreddit": subreddit_name,
            "posts": posts,
            "post_count": len(posts),
            "comment_count": total_comments,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "subreddit": subreddit_name,
            "posts": [],
            "post_count": 0,
            "comment_count": 0,
            "error": str(e)
        }


def main():
    """Main scraper entry point."""
    print("Reddit Daily Scraper - SIGINT Platform")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please create reddit_config.json with subreddit list.")
        return 1

    # Get Reddit client
    try:
        reddit = get_reddit_client()
        user = reddit.user.me()
        print(f"Authenticated as: {user}")
    except Exception as e:
        print(f"ERROR: Failed to authenticate with Reddit: {e}")
        return 1

    # Flatten subreddit list from config
    all_subreddits = []
    for category, subs in config.get("subreddits", {}).items():
        all_subreddits.extend(subs)

    print(f"Subreddits to scrape: {len(all_subreddits)}")
    print()

    # Calculate cutoff time (24 hours ago)
    cutoff_time = time.time() - 86400
    cutoff_dt = datetime.fromtimestamp(cutoff_time)

    # Create output directory
    today_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = DATA_DIR / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # Scrape each subreddit
    results = []
    successful = 0
    failed = 0
    total_posts = 0
    total_comments = 0

    for i, subreddit_name in enumerate(all_subreddits, 1):
        print(f"[{i}/{len(all_subreddits)}] Scraping r/{subreddit_name}...")

        result = scrape_subreddit(reddit, subreddit_name, cutoff_time)
        results.append(result)

        if result["success"]:
            successful += 1
            total_posts += result["post_count"]
            total_comments += result["comment_count"]
            print(f"  ✓ {result['post_count']} posts, {result['comment_count']} comments")
        else:
            failed += 1
            print(f"  ✗ Error: {result['error']}")

        # Rate limiting between subreddits (Codex recommendation: 1-2s)
        if i < len(all_subreddits):  # Don't sleep after last one
            time.sleep(SLEEP_BETWEEN_SUBREDDITS)

    # Save results
    output_file = output_dir / f"reddit_scrape_{today_str}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "scrape_date": today_str,
            "scrape_time": datetime.now().isoformat(),
            "cutoff_time": cutoff_dt.isoformat(),
            "total_subreddits": len(all_subreddits),
            "successful": successful,
            "failed": failed,
            "total_posts": total_posts,
            "total_comments": total_comments,
            "results": results
        }, f, indent=2)

    print()
    print("=" * 80)
    print("Scrape Complete")
    print(f"  Subreddits: {successful} successful, {failed} failed")
    print(f"  Posts: {total_posts}")
    print(f"  Comments: {total_comments}")
    print(f"  Output: {output_file}")
    print("=" * 80)

    # Create log entry
    log_file = LOGS_DIR / "reddit_daily_scrape.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a') as f:
        f.write(f"\n{datetime.now().isoformat()} - Scrape complete: {total_posts} posts, {total_comments} comments from {successful}/{len(all_subreddits)} subreddits\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
