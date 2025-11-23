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
        description='U.S. Congressional bills, resolutions, votes, and legislative records',
        characteristics={
            'official_government_data': True,
            'legislative_focus': True,
            'structured_data': True,
            'historical_records': True,
            'member_tracking': True,
            'no_keyword_search': True,  # API lists bills by congress number, not keyword
            'requires_api_key': True,
            'requires_verification': False  # Official government data
        },
        query_strategies=[
            'congress_number_filter',  # Primary: Filter by congress (118th, 117th, etc.)
            'bill_type_filter',  # Filter by HR, S, etc.
            'chamber_filter',  # House vs Senate
            'list_recent_bills',  # List all bills from congress (no keyword search)
            'member_sponsorship',  # Track bills by sponsor (requires member endpoint)
            'vote_tracking'  # Track votes (requires vote endpoint)
        ],
        typical_result_count=20,  # Default API response
        max_queries_recommended=3  # Limited by no keyword search
    ),

    'SEC EDGAR': SourceMetadata(
        name='SEC EDGAR',
        description='Corporate financial filings, 10-K/10-Q reports, insider trading (Form 4), executive compensation',
        characteristics={
            'financial_data': True,
            'corporate_filings': True,
            'insider_trading': True,
            'executive_compensation': True,
            'structured_data': True,
            'historical_records': True,
            'company_search': True,
            'free_access': True,
            'requires_user_agent': True,  # Needs email in User-Agent header
            'requires_verification': False  # Official SEC data
        },
        query_strategies=[
            'company_name_search',  # Search by company name (with CIK lookup)
            'filing_type_filter',  # Filter by form type (10-K, 10-Q, 8-K, Form 4, etc.)
            'recent_filings',  # Get latest filings for a company
            'insider_trading_tracking',  # Track Form 4 filings (insider buys/sells)
            'executive_compensation',  # DEF 14A proxy statements
            'financial_statements',  # 10-K annual, 10-Q quarterly reports
            'material_events'  # 8-K current reports (major events)
        ],
        typical_result_count=10,  # Usually returns 10-20 filings
        max_queries_recommended=5  # Corporate data, moderate saturation
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

    'CourtListener': SourceMetadata(
        name='CourtListener',
        description='Federal and state court opinions, RECAP filings, judicial disclosures (Free Law Project)',
        characteristics={
            'legal_opinions': True,
            'court_filings': True,
            'federal_courts': True,
            'state_courts': True,
            'historical_depth': True,  # Opinions back to 1754
            'full_text_search': True,
            'structured_data': True,
            'free_access': True,
            'requires_api_key': True,  # Free API key required
            'requires_verification': False  # Official court documents
        },
        query_strategies=[
            'case_name_search',  # Search by party names (e.g., "United States v. Google")
            'full_text_keyword',  # Search opinion text for legal concepts
            'court_filter',  # Filter by jurisdiction (SCOTUS, Circuit, District)
            'date_range_litigation',  # Track litigation over time periods
            'corporate_litigation_history',  # Find all cases involving a company
            'bankruptcy_filings',  # RECAP bankruptcy court documents
            'government_enforcement',  # DOJ, SEC, FTC enforcement actions
            'class_action_tracking'  # Track class action lawsuits
        ],
        typical_result_count=50,  # Varies by query specificity
        max_queries_recommended=6  # Legal research, moderate depth needed
    ),

    'FEC': SourceMetadata(
        name='FEC',
        description='Federal Election Commission campaign finance data: contributions, expenditures, PACs, Super PACs',
        characteristics={
            'official_government_data': True,
            'campaign_finance': True,
            'itemized_contributions': True,
            'pac_spending': True,
            'super_pac_data': True,
            'candidate_financials': True,
            'independent_expenditures': True,
            'real_time_updates': True,  # Filings appear within days
            'requires_api_key': True,  # Same api.data.gov key as Congress.gov
            'requires_verification': False  # Official FEC data
        },
        query_strategies=[
            'candidate_fundraising',  # Track how much candidates have raised
            'donor_search',  # Find all donations from specific individual/organization
            'recipient_search',  # Find all donations TO specific candidate/committee
            'pac_super_pac_tracking',  # Monitor PAC and Super PAC activity
            'independent_expenditures',  # Track outside spending (ads for/against candidates)
            'industry_donations',  # Track donations from specific industries
            'committee_search',  # Find and analyze specific committees
            'party_comparison'  # Compare fundraising across parties
        ],
        typical_result_count=100,  # Rich dataset, many transactions
        max_queries_recommended=7  # Follow-the-money investigations need depth
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

    'ProPublica Nonprofit Explorer': SourceMetadata(
        name='ProPublica Nonprofit Explorer',
        description='IRS Form 990 data for U.S. nonprofits: revenue, expenses, executive compensation, grants',
        characteristics={
            'financial_data': True,
            'nonprofit_focus': True,
            'irs_data': True,
            'executive_compensation': True,
            'tax_filings': True,
            'searchable_by_state': True,
            'searchable_by_category': True,
            'searchable_by_tax_code': True,
            'requires_verification': False  # Official IRS data
        },
        query_strategies=[
            'organization_name_search',  # Search by nonprofit name
            'keyword_mission_search',  # Search by mission/activity keywords
            'state_filter',  # Filter by state location
            'tax_code_filter',  # 501(c)(3), 501(c)(4), etc.
            'category_filter',  # NTEE categories (health, education, etc.)
            'dark_money_investigation',  # 501(c)(4) political nonprofits
            'foundation_grants'  # Search for foundations and their grants
        ],
        typical_result_count=50,  # Rich dataset of 1.8M+ nonprofits
        max_queries_recommended=7  # Financial data, good for investigations
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
