#!/usr/bin/env python3
"""
Boolean Monitor - Automated keyword-based monitoring with alerts.

This module provides the BooleanMonitor class which orchestrates:
1. Keyword-based searches across multiple data sources
2. Result deduplication
3. New result detection (vs previous runs)
4. Email alert delivery

Usage:
    monitor = BooleanMonitor("data/monitors/configs/nve_monitor.yaml")
    await monitor.run()
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib
import json
import yaml
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('BooleanMonitor')


@dataclass
class MonitorConfig:
    """Configuration for a single Boolean monitor."""
    name: str
    keywords: List[str]
    sources: List[str]
    schedule: str
    alert_email: str
    enabled: bool = True


class BooleanMonitor:
    """
    Boolean keyword monitor with alerting.

    Workflow:
    1. Load config from YAML file
    2. Execute searches across configured sources
    3. Deduplicate results
    4. Compare against previous results
    5. Send alert if new results found
    6. Save results for next run
    """

    def __init__(self, config_path: str):
        """
        Initialize monitor with configuration file.

        Args:
            config_path: Path to YAML config file
        """
        logger.info(f"Initializing BooleanMonitor from: {config_path}")
        self.config: MonitorConfig = self.load_config(config_path)
        self.storage_path: Path = Path(f"data/monitors/{self.config.name.replace(' ', '_')}_results.json")
        self.previous_results: Set[str] = self._load_previous_results()
        logger.info(f"Monitor '{self.config.name}' initialized")
        logger.info(f"  Keywords: {len(self.config.keywords)}")
        logger.info(f"  Sources: {self.config.sources}")
        logger.info(f"  Previous results: {len(self.previous_results)}")

    def load_config(self, path: str) -> MonitorConfig:
        """
        Load monitor configuration from YAML file.

        Args:
            path: Path to YAML config file

        Returns:
            MonitorConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        logger.info(f"Loading config from: {path}")

        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        # Validate required fields
        required_fields = ['name', 'keywords', 'sources', 'schedule', 'alert_email']
        for field in required_fields:
            if field not in config_data:
                raise ValueError(f"Missing required field in config: {field}")

        config = MonitorConfig(
            name=config_data['name'],
            keywords=config_data['keywords'],
            sources=config_data['sources'],
            schedule=config_data['schedule'],
            alert_email=config_data['alert_email'],
            enabled=config_data.get('enabled', True)
        )

        logger.info(f"Config loaded: {config.name}")
        return config

    async def execute_search(self, keywords: List[str]) -> List[Dict]:
        """
        Execute searches across configured sources IN PARALLEL.

        Calls existing integrations:
        - DVIDSIntegration
        - SAMIntegration
        - USAJobsIntegration
        - search_clearancejobs (Playwright)
        - FederalRegisterIntegration

        Args:
            keywords: List of keywords to search (supports Boolean operators)

        Returns:
            List of standardized results: [{"title": ..., "url": ..., "source": ..., "date": ...}]
        """
        logger.info(f"Executing PARALLEL search for {len(keywords)} keywords across {len(self.config.sources)} sources")

        # Import integrations (add parent directory to path for imports)
        import sys
        from pathlib import Path
        import asyncio

        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from dotenv import load_dotenv
        import os

        load_dotenv()

        # Create search tasks for ALL keyword+source combinations
        search_tasks = []

        for source in self.config.sources:
            for keyword in keywords:
                # Create a task for each keyword+source combination
                task = self._search_single_source(source, keyword)
                search_tasks.append(task)

        # Execute ALL searches in parallel
        logger.info(f"Launching {len(search_tasks)} parallel searches ({len(keywords)} keywords × {len(self.config.sources)} sources)")
        results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten results and handle exceptions
        all_results = []
        errors = 0
        for result in results_lists:
            if isinstance(result, Exception):
                logger.warning(f"Search task failed: {str(result)}")
                errors += 1
            elif isinstance(result, list):
                all_results.extend(result)

        logger.info(f"Parallel search complete: {len(all_results)} total results from {len(search_tasks)} searches ({errors} errors)")
        return all_results

    async def _search_single_source(self, source: str, keyword: str) -> List[Dict]:
        """
        Search a single source for a single keyword using registry.

        This method is called in parallel by execute_search().

        Args:
            source: Source ID ("dvids", "sam", "usajobs", "clearancejobs", "discord", etc.)
            keyword: Keyword to search (supports Boolean operators)

        Returns:
            List of results from this source+keyword combination
        """
        import os
        from integrations.registry import registry

        results = []

        try:
            # Get integration from registry
            integration_class = registry.get(source)
            if not integration_class:
                logger.warning(f"Unknown source: {source}")
                return []

            # Instantiate integration
            integration = integration_class()

            # Get API key if needed
            api_key = None
            if integration.metadata.requires_api_key:
                # Map source ID to env var name
                # Special case for Twitter (uses RAPIDAPI_KEY)
                if source == "twitter":
                    api_key_var = "RAPIDAPI_KEY"
                else:
                    api_key_var = f"{source.upper().replace('-', '_')}_API_KEY"
                api_key = os.getenv(api_key_var, '')

                if not api_key:
                    logger.warning(f"  {integration.metadata.name}: Skipped (no API key found in {api_key_var})")
                    return []

            # Generate query parameters
            query_params = await integration.generate_query(research_question=keyword)

            if not query_params:
                logger.info(f"  {integration.metadata.name}: Skipped (not relevant for '{keyword}')")
                return []

            # Execute search
            result = await integration.execute_search(query_params, api_key, limit=10)

            if result.success:
                # Convert QueryResult to standardized format
                for item in result.results:
                    # Try common field names for title
                    title = (item.get('title') or
                            item.get('job_name') or
                            item.get('name') or
                            item.get('PositionTitle') or
                            'Untitled')

                    # Try common field names for URL
                    url = (item.get('url') or
                          item.get('job_url') or
                          item.get('uiLink') or
                          item.get('PositionURI') or
                          item.get('html_url') or
                          '')

                    # Try common field names for date
                    date = (item.get('date') or
                           item.get('date_published') or
                           item.get('publishdate') or
                           item.get('postedDate') or
                           item.get('PublicationStartDate') or
                           item.get('publication_date') or
                           item.get('updated') or
                           '')

                    # Try common field names for description
                    description = (item.get('description') or
                                  item.get('abstract') or
                                  item.get('content') or
                                  item.get('preview_text') or
                                  '')

                    # Handle USAJobs special case for description
                    if not description and item.get('PositionFormattedDescription'):
                        desc_list = item.get('PositionFormattedDescription', [])
                        if desc_list and len(desc_list) > 0:
                            description = desc_list[0].get('Content', '')

                    results.append({
                        "title": title,
                        "url": url,
                        "source": integration.metadata.name,
                        "date": str(date)[:10] if date else '',
                        "description": description,
                        "keyword": keyword  # Track which keyword found this
                    })

                logger.info(f"  {integration.metadata.name}: Found {len(result.results)} results for '{keyword}'")
            else:
                logger.warning(f"  {integration.metadata.name}: Search failed: {result.error}")

        except Exception as e:
            logger.error(f"Error searching {source} for '{keyword}': {str(e)}")
            # Return empty list on error (don't crash entire monitor)

        return results

    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate results based on URL hash.

        Strategy: Hash each result URL, keep only unique hashes

        Args:
            results: List of search results

        Returns:
            Deduplicated list of results
        """
        logger.info(f"Deduplicating {len(results)} results")

        seen_hashes = set()
        unique_results = []

        for result in results:
            url = result.get('url', '')
            if not url:
                continue

            # Create hash of URL
            url_hash = hashlib.sha256(url.encode()).hexdigest()

            if url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                unique_results.append(result)

        logger.info(f"Deduplication complete: {len(unique_results)} unique results (removed {len(results) - len(unique_results)} duplicates)")
        return unique_results

    def check_for_new_results(self, current_results: List[Dict]) -> List[Dict]:
        """
        Compare current results against previous run.

        Returns only NEW results (not seen in previous run)

        Args:
            current_results: Results from current search

        Returns:
            List of new results only
        """
        logger.info(f"Checking for new results (previous: {len(self.previous_results)}, current: {len(current_results)})")

        new_results = []

        for result in current_results:
            url = result.get('url', '')
            if not url:
                continue

            url_hash = hashlib.sha256(url.encode()).hexdigest()

            if url_hash not in self.previous_results:
                new_results.append(result)

        logger.info(f"Found {len(new_results)} new results")
        return new_results

    async def filter_by_relevance(self, results: List[Dict]) -> List[Dict]:
        """
        Filter results by LLM relevance scoring.

        For each result, asks LLM:
        1. Is this result relevant to the keyword that found it?
        2. Why is it relevant (or not)?
        3. Relevance score (0-10)

        Only keeps results with score >= 6

        Args:
            results: List of search results with keyword field

        Returns:
            List of relevant results with added 'relevance_score' and 'relevance_reason' fields
        """
        logger.info(f"Filtering {len(results)} results by LLM relevance")

        from llm_utils import acompletion
        import json

        relevant_results = []
        filtered_out = 0

        for result in results:
            title = result.get('title', 'Untitled')
            description = (result.get('description') or '')[:500]  # Limit to 500 chars, handle None
            keyword = result.get('keyword', '')
            source = result.get('source', 'Unknown')

            # Ask LLM to score relevance
            prompt = f"""You are analyzing search results for relevance to a monitoring keyword.

Keyword: "{keyword}"
Source: {source}
Title: {title}
Description: {description[:300]}

Task: Determine if this result is genuinely relevant to the keyword "{keyword}".

Consider:
- Is the title/description actually about {keyword}?
- Is this a substantive result (not just keyword spam)?
- Would a journalist researching {keyword} want to see this?

Provide:
1. relevance_score (0-10, where 10 = highly relevant, 0 = not relevant)
2. reasoning (1-2 sentences explaining why relevant or not)

Return ONLY valid JSON with this exact structure:
{{
  "relevance_score": <number 0-10>,
  "reasoning": "<your explanation>"
}}"""

            try:
                response = await acompletion(
                    model="gpt-5-nano",  # Fast, cheap model for relevance filtering
                    messages=[{"role": "user", "content": prompt}],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "strict": True,
                            "name": "relevance_analysis",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "relevance_score": {"type": "number"},
                                    "reasoning": {"type": "string"}
                                },
                                "required": ["relevance_score", "reasoning"],
                                "additionalProperties": False
                            }
                        }
                    }
                )

                analysis = json.loads(response.choices[0].message.content)
                score = analysis.get('relevance_score', 0)
                reasoning = analysis.get('reasoning', 'No reasoning provided')

                # Keep results with score >= 6
                if score >= 6:
                    result['relevance_score'] = score
                    result['relevance_reason'] = reasoning
                    relevant_results.append(result)
                    logger.info(f"  ✓ RELEVANT ({score}/10): {title[:60]}...")
                else:
                    filtered_out += 1
                    logger.info(f"  ✗ FILTERED ({score}/10): {title[:60]}...")

            except Exception as e:
                logger.warning(f"Error scoring result relevance: {str(e)}")
                # On error, keep the result (don't filter out due to technical issues)
                result['relevance_score'] = 5
                result['relevance_reason'] = f"Could not score relevance due to error: {str(e)}"
                relevant_results.append(result)

        logger.info(f"Relevance filtering complete: {len(relevant_results)} relevant, {filtered_out} filtered out")
        return relevant_results

    async def send_alert(self, new_results: List[Dict]):
        """
        Send email alert with new results.

        Email format:
        - Subject: "[Monitor Name] - X new results"
        - Body: HTML formatted list of new results with links

        Args:
            new_results: List of new results to include in alert
        """
        logger.info(f"Sending alert for {len(new_results)} new results to {self.config.alert_email}")

        # Log results for debugging
        logger.info(f"ALERT: {len(new_results)} new results found")
        for i, result in enumerate(new_results[:5], 1):  # Show first 5
            logger.info(f"  {i}. {result.get('title', 'Untitled')} ({result.get('source', 'Unknown')})")

        if len(new_results) > 5:
            logger.info(f"  ... and {len(new_results) - 5} more")

        # Send email if configured
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import os

            # Check if email configuration exists
            smtp_host = os.getenv('SMTP_HOST', 'localhost')
            smtp_port = int(os.getenv('SMTP_PORT', '25'))
            smtp_user = os.getenv('SMTP_USERNAME', '')
            smtp_password = os.getenv('SMTP_PASSWORD', '')
            smtp_from = os.getenv('SMTP_FROM_EMAIL', f'{self.config.name}@localhost')

            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{self.config.name}] - {len(new_results)} new results"
            msg['From'] = smtp_from
            msg['To'] = self.config.alert_email

            # Create plain text version
            text_body = f"""
{self.config.name} - New Results

Found {len(new_results)} new results:

"""
            for i, result in enumerate(new_results, 1):
                text_body += f"{i}. {result.get('title', 'Untitled')}\n"
                text_body += f"   Source: {result.get('source', 'Unknown')}\n"
                text_body += f"   Keyword: {result.get('keyword', 'N/A')}\n"
                text_body += f"   Date: {result.get('date', 'N/A')}\n"
                if result.get('url'):
                    text_body += f"   URL: {result['url']}\n"
                if result.get('relevance_score'):
                    text_body += f"   Relevance: {result['relevance_score']}/10\n"
                if result.get('relevance_reason'):
                    text_body += f"   Why: {result['relevance_reason']}\n"
                text_body += "\n"

            # Create HTML version
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        .result {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }}
        .result-title {{ font-size: 16px; font-weight: bold; color: #2c3e50; }}
        .result-meta {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
        .result-keyword {{ font-size: 13px; color: #3498db; font-weight: bold; margin-top: 8px; }}
        .result-relevance {{ font-size: 13px; color: #27ae60; margin-top: 5px; background: #eafaf1; padding: 8px; border-radius: 4px; }}
        .result-description {{ font-size: 14px; margin-top: 10px; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #7f8c8d; }}
    </style>
</head>
<body>
    <h1>{self.config.name} - New Results</h1>
    <p>Found <strong>{len(new_results)}</strong> new results:</p>
"""

            for i, result in enumerate(new_results, 1):
                title = result.get('title', 'Untitled')
                url = result.get('url', '')
                source = result.get('source', 'Unknown')
                date = result.get('date', 'N/A')
                keyword = result.get('keyword', 'N/A')
                relevance_score = result.get('relevance_score')
                relevance_reason = result.get('relevance_reason', '')
                description = result.get('description', '')

                html_body += '<div class="result">\n'

                if url:
                    html_body += f'<div class="result-title">{i}. <a href="{url}">{title}</a></div>\n'
                else:
                    html_body += f'<div class="result-title">{i}. {title}</div>\n'

                html_body += f'<div class="result-meta">Source: {source} | Date: {date}</div>\n'
                html_body += f'<div class="result-keyword">🔍 Matched keyword: "{keyword}"</div>\n'

                if relevance_score is not None:
                    html_body += f'<div class="result-relevance"><strong>Relevance: {relevance_score}/10</strong> — {relevance_reason}</div>\n'

                if description:
                    # Truncate long descriptions
                    desc_truncated = description[:300] + "..." if len(description) > 300 else description
                    html_body += f'<div class="result-description">{desc_truncated}</div>\n'

                html_body += '</div>\n'

            html_body += """
    <div class="footer">
        <p>This alert was generated by the Boolean Monitoring System.</p>
        <p>To unsubscribe or modify your alerts, please update your monitor configuration.</p>
    </div>
</body>
</html>
"""

            # Attach both versions
            part_text = MIMEText(text_body, 'plain')
            part_html = MIMEText(html_body, 'html')
            msg.attach(part_text)
            msg.attach(part_html)

            # Send email
            try:
                if smtp_user and smtp_password:
                    # Use authentication
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.send_message(msg)
                    logger.info(f"Email sent successfully to {self.config.alert_email} (authenticated)")
                else:
                    # No authentication (localhost)
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.send_message(msg)
                    logger.info(f"Email sent successfully to {self.config.alert_email} (no auth)")

            except smtplib.SMTPException as e:
                logger.warning(f"Failed to send email via SMTP: {str(e)}")
                logger.info("Email alert disabled - results logged above")
            except ConnectionRefusedError:
                logger.warning(f"SMTP connection refused to {smtp_host}:{smtp_port}")
                logger.info("Email alert disabled - results logged above")

        except Exception as e:
            logger.error(f"Error preparing email alert: {str(e)}")
            logger.info("Email alert disabled - results logged above")

    def _save_results(self, results: List[Dict]):
        """
        Save current results to JSON file for next comparison.

        Args:
            results: Current search results to save
        """
        logger.info(f"Saving {len(results)} results to {self.storage_path}")

        # Create result hashes
        result_hashes = []
        for result in results:
            url = result.get('url', '')
            if url:
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                result_hashes.append(url_hash)

        # Prepare storage data
        storage_data = {
            "last_run": datetime.now().isoformat(),
            "result_hashes": result_hashes,
            "result_count": len(results)
        }

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to JSON
        with open(self.storage_path, 'w') as f:
            json.dump(storage_data, f, indent=2)

        logger.info(f"Results saved successfully")

    def _load_previous_results(self) -> Set[str]:
        """
        Load previous result hashes from JSON file.

        Returns:
            Set of previous result hashes
        """
        if not self.storage_path.exists():
            logger.info("No previous results found (first run)")
            return set()

        logger.info(f"Loading previous results from {self.storage_path}")

        with open(self.storage_path, 'r') as f:
            storage_data = json.load(f)

        result_hashes = set(storage_data.get('result_hashes', []))
        logger.info(f"Loaded {len(result_hashes)} previous result hashes")

        return result_hashes

    async def run(self):
        """
        Main execution method.

        Steps:
        1. Execute searches for all keywords
        2. Deduplicate results
        3. Check for new results
        4. Send alert if new results found
        5. Save results for next run
        """
        logger.info(f"Starting monitor run: {self.config.name}")

        if not self.config.enabled:
            logger.warning(f"Monitor '{self.config.name}' is disabled, skipping")
            return

        try:
            # 1. Execute searches
            results = await self.execute_search(self.config.keywords)

            # 2. Deduplicate
            unique_results = self.deduplicate_results(results)

            # 3. Check for new results
            new_results = self.check_for_new_results(unique_results)

            # 4. Filter by LLM relevance
            if new_results:
                relevant_results = await self.filter_by_relevance(new_results)
            else:
                relevant_results = []

            # 5. Send alert if relevant results found
            if relevant_results:
                await self.send_alert(relevant_results)
            else:
                if new_results:
                    logger.info(f"Found {len(new_results)} new results, but all filtered out as not relevant")
                else:
                    logger.info("No new results found, skipping alert")

            # 6. Save results for next run
            self._save_results(unique_results)

            logger.info(f"Monitor run complete: {len(unique_results)} total results, {len(new_results)} new")

        except Exception as e:
            logger.error(f"Monitor run failed: {str(e)}", exc_info=True)
            raise


# Example usage
async def main():
    """Test the BooleanMonitor with example config."""
    import asyncio

    # Create monitor
    monitor = BooleanMonitor("data/monitors/configs/nve_monitor.yaml")

    # Run monitor
    await monitor.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
