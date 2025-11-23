"""
Source metadata for query saturation.

Provides LLM with context about each data source to guide intelligent
query generation and saturation decisions.
"""

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class SourceMetadata:
    """Metadata about a data source to guide LLM query generation."""
    name: str
    description: str
    characteristics: Dict[str, Any]
    query_strategies: List[str]
    typical_result_count: int
    max_queries_recommended: int


# Define metadata for each source
SOURCE_METADATA = {
    'SAM.gov': SourceMetadata(
        name='SAM.gov',
        description='Federal contract awards and opportunities (System for Award Management)',
        characteristics={
            'requires_formal_names': True,  # "Department of Defense" not "DoD"
            'date_format': 'YYYY-MM-DD',
            'rich_metadata': True,
            'structured_data': True,
            'naics_codes': True,
            'contract_ids': True
        },
        query_strategies=[
            'exact_contract_id',
            'agency_name_keyword_date',
            'naics_code_filter',
            'contractor_name',
            'award_amount_range'
        ],
        typical_result_count=50,
        max_queries_recommended=10
    ),

    'USAspending': SourceMetadata(
        name='USAspending',
        description='Historical federal spending data: awarded contracts, grants, loans, budget information',
        characteristics={
            'historical_spending': True,
            'post_award_data': True,  # NOT pre-award opportunities
            'structured_data': True,
            'rich_metadata': True,
            'budget_data': True,
            'recipient_tracking': True,
            'geographic_data': True,
            'time_series': True,
            'award_amounts': True,
            'date_format': 'YYYY-MM-DD',
            'requires_verification': False  # Official government data
        },
        query_strategies=[
            'recipient_name_search',  # Find awards to specific companies/orgs
            'agency_spending_analysis',  # Track agency budgets and spending
            'award_amount_filter',  # Filter by dollar ranges
            'time_period_comparison',  # Compare spending across fiscal years
            'award_type_filter',  # Contracts vs grants vs loans
            'keyword_description_search',  # Search award descriptions
            'geographic_spending',  # Spending by state/location
            'disaster_emergency_tracking'  # COVID, Infrastructure spending via def_codes
        ],
        typical_result_count=100,  # Rich dataset, returns more results
        max_queries_recommended=7  # Historical data, moderate saturation
    ),

    'DVIDS': SourceMetadata(
        name='DVIDS',
        description='Department of Defense news and media (Defense Visual Information Distribution Service)',
        characteristics={
            'news_articles': True,
            'military_focused': True,
            'formal_tone': True,
            'image_video_content': True,
            'unit_attribution': True
        },
        query_strategies=[
            'keyword_search',
            'unit_name_search',
            'topic_search',
            'location_search',
            'date_range_filter'
        ],
        typical_result_count=20,
        max_queries_recommended=5
    ),

    'USAJobs': SourceMetadata(
        name='USAJobs',
        description='Federal government job postings (official federal job board)',
        characteristics={
            'job_postings': True,
            'clearance_levels': True,
            'salary_ranges': True,
            'location_based': True,
            'requires_keywords': True
        },
        query_strategies=[
            'keyword_search',
            'position_title',
            'agency_filter',
            'location_filter',
            'clearance_level_filter'
        ],
        typical_result_count=30,
        max_queries_recommended=5
    ),

    'ClearanceJobs': SourceMetadata(
        name='ClearanceJobs',
        description='Security-cleared job postings (defense and intelligence sectors)',
        characteristics={
            'security_clearance_required': True,
            'defense_contractors': True,
            'specialized_skills': True,
            'location_based': True,
            'requires_keywords': True
        },
        query_strategies=[
            'keyword_search',
            'clearance_level_filter',
            'location_search',
            'company_name',
            'skill_requirements'
        ],
        typical_result_count=25,
        max_queries_recommended=5
    ),

    'CIA CREST': SourceMetadata(
        name='CIA CREST',
        description='CIA declassified document reading room (FOIA records from 1940s-1990s)',
        characteristics={
            'historical_documents': True,
            'declassified_intelligence': True,
            'formal_government_prose': True,
            'pre_2000_focus': True,
            'full_text_available': True,
            'requires_verification': False  # Official government docs
        },
        query_strategies=[
            'keyword_search',
            'operation_name',
            'country_region_focus',
            'time_period',
            'intelligence_topic'
        ],
        typical_result_count=20,
        max_queries_recommended=3  # Historical docs, focused topics
    ),

    'Congress.gov': SourceMetadata(
        name='Congress.gov',
        description='U.S. Congressional bills, members, votes, and legislative records',
        characteristics={
            'official_government_data': True,
            'legislative_focus': True,
            'structured_data': True,
            'historical_records': True,
            'member_tracking': True,
            'requires_verification': False  # Official government data
        },
        query_strategies=[
            'bill_search',
            'member_search',
            'keyword_search',
            'congress_number_filter',
            'committee_search',
            'vote_tracking'
        ],
        typical_result_count=50,
        max_queries_recommended=5  # Legislative data, moderate saturation
    ),

    'Federal Register': SourceMetadata(
        name='Federal Register',
        description='Official daily publication of U.S. federal rules, proposed rules, notices, and executive orders',
        characteristics={
            'official_government_data': True,
            'regulatory_focus': True,
            'daily_publication': True,
            'structured_data': True,
            'agency_specific': True,
            'document_types': ['RULE', 'PRORULE', 'NOTICE', 'PRESDOCU'],
            'date_searchable': True,
            'requires_verification': False  # Official government publication
        },
        query_strategies=[
            'keyword_search',  # General term search
            'agency_filter',  # Filter by specific agencies
            'document_type_filter',  # Rules vs notices vs presidential docs
            'date_range_search',  # Recent vs historical
            'topic_monitoring',  # Track specific regulatory topics over time
            'proposed_vs_final'  # Distinguish between proposed and final rules
        ],
        typical_result_count=100,  # Daily publication, rich dataset
        max_queries_recommended=8  # Regulatory data, good for monitoring topics
    ),

    'Twitter': SourceMetadata(
        name='Twitter',
        description='Social media platform (real-time news, announcements, discussions)',
        characteristics={
            'real_time': True,
            'informal_language': True,
            'hashtags': True,
            'short_content': True,
            'high_noise': True,
            'requires_verification': True
        },
        query_strategies=[
            'keyword_search',
            'hashtag_search',
            'account_search',
            'quoted_phrases',
            'boolean_operators'
        ],
        typical_result_count=20,
        max_queries_recommended=3  # High noise, quick saturation
    ),

    'Reddit': SourceMetadata(
        name='Reddit',
        description='Community discussions and link aggregation (various subreddits)',
        characteristics={
            'community_discussions': True,
            'informal_language': True,
            'varied_credibility': True,
            'context_rich': True,
            'requires_verification': True
        },
        query_strategies=[
            'keyword_search',
            'subreddit_specific',
            'title_search',
            'quoted_phrases',
            'boolean_operators'
        ],
        typical_result_count=15,
        max_queries_recommended=3  # Community discussions, quick saturation
    ),

    'Discord': SourceMetadata(
        name='Discord',
        description='Chat platform exports (OSINT communities, professional groups)',
        characteristics={
            'chat_messages': True,
            'informal_language': True,
            'community_focused': True,
            'temporal_discussions': True,
            'requires_verification': True
        },
        query_strategies=[
            'keyword_search',
            'channel_specific',
            'author_search',
            'date_range',
            'quoted_phrases'
        ],
        typical_result_count=30,
        max_queries_recommended=3  # Chat data, quick saturation
    ),

    'Brave Search': SourceMetadata(
        name='Brave Search',
        description='Web search engine (general web content, news, blogs, official sites)',
        characteristics={
            'general_web': True,
            'varied_sources': True,
            'news_coverage': True,
            'official_documents': True,
            'broad_coverage': True
        },
        query_strategies=[
            'keyword_search',
            'quoted_phrases',
            'site_specific',
            'boolean_operators',
            'date_filters',
            'entity_names'
        ],
        typical_result_count=10,
        max_queries_recommended=5  # Broad coverage, moderate saturation
    ),
}


def get_source_metadata(source_name: str) -> SourceMetadata:
    """
    Get metadata for a source.

    Args:
        source_name: Name of the source

    Returns:
        SourceMetadata object or None if not found
    """
    return SOURCE_METADATA.get(source_name)


def get_max_queries_for_source(source_name: str) -> int:
    """
    Get recommended max queries for a source.

    Args:
        source_name: Name of the source

    Returns:
        Recommended max queries (default: 5)
    """
    metadata = get_source_metadata(source_name)
    return metadata.max_queries_recommended if metadata else 5
