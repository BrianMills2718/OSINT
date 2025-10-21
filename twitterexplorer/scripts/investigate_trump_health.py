"""Investigation into Trump health rumors"""

import sys
import os
sys.path.insert(0, 'twitterexplorer')

from investigation_engine import InvestigationEngine, InvestigationConfig
import toml
from datetime import datetime

# Load API key
secrets_path = r'twitterexplorer\.streamlit\secrets.toml'
secrets = toml.load(secrets_path)
api_key = secrets.get('RAPIDAPI_KEY')

print("=" * 60)
print("INVESTIGATING: Donald Trump Health/Death Rumors")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# Configure investigation
config = InvestigationConfig(
    max_searches=5,  # More searches for thorough investigation
    pages_per_search=2,  # Get more results per search
    show_search_details=True,
    show_effectiveness_scores=True
)

# Create engine
engine = InvestigationEngine(api_key)

# Run investigation
print("\nStarting investigation...")
print("-" * 60)

try:
    result = engine.conduct_investigation(
        "Donald Trump dead sick health rumors hospital 2024",
        config
    )
    
    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)
    
    # Summary statistics
    print(f"\nStatistics:")
    print(f"  Total searches: {len(result.search_history)}")
    print(f"  Total results: {sum(s.results_count for s in result.search_history)}")
    print(f"  Findings generated: {len(result.accumulated_findings)}")
    print(f"  Satisfaction score: {result.satisfaction_metrics.overall_satisfaction():.2f}")
    
    # Analyze search effectiveness
    print(f"\nSearch Performance:")
    for search in result.search_history:
        endpoint = search.endpoint
        query = search.params.get('query', search.params.get('screenname', 'N/A'))
        print(f"  - {endpoint}: {query[:50]}...")
        print(f"    Results: {search.results_count}, Score: {search.effectiveness_score:.1f}")
    
    # Show key findings
    if result.accumulated_findings:
        print(f"\n" + "=" * 60)
        print("KEY FINDINGS (Who's Saying What):")
        print("=" * 60)
        
        # Group findings by credibility
        high_cred = [f for f in result.accumulated_findings if f.credibility_score > 0.7]
        med_cred = [f for f in result.accumulated_findings if 0.5 <= f.credibility_score <= 0.7]
        low_cred = [f for f in result.accumulated_findings if f.credibility_score < 0.5]
        
        if high_cred:
            print(f"\nHIGH CREDIBILITY ({len(high_cred)} findings):")
            for i, finding in enumerate(high_cred[:5], 1):
                # Clean up the text for display
                text = finding.content.replace('\n', ' ').replace('\r', '')
                # Remove emojis and special characters that cause encoding issues
                text = text.encode('ascii', 'ignore').decode('ascii')
                if len(text) > 150:
                    text = text[:150] + "..."
                print(f"\n  {i}. {text}")
                print(f"     Source: {finding.source}")
                print(f"     Credibility: {finding.credibility_score:.2f}")
        
        if med_cred:
            print(f"\nMEDIUM CREDIBILITY ({len(med_cred)} findings):")
            for i, finding in enumerate(med_cred[:3], 1):
                text = finding.content.replace('\n', ' ').replace('\r', '')
                text = text.encode('ascii', 'ignore').decode('ascii')
                if len(text) > 150:
                    text = text[:150] + "..."
                print(f"\n  {i}. {text}")
                print(f"     Source: {finding.source}")
        
        # Analyze perspectives
        print(f"\n" + "=" * 60)
        print("PERSPECTIVE ANALYSIS:")
        print("=" * 60)
        
        # Look for patterns in findings
        rumors_count = 0
        denials_count = 0
        jokes_count = 0
        news_count = 0
        
        for finding in result.accumulated_findings:
            content_lower = finding.content.lower()
            if any(word in content_lower for word in ['rumor', 'fake', 'hoax', 'false']):
                denials_count += 1
            if any(word in content_lower for word in ['dead', 'died', 'death', 'hospital', 'sick']):
                rumors_count += 1
            if any(word in content_lower for word in ['joke', 'meme', 'lol', 'funny', 'satire']):
                jokes_count += 1
            if any(word in content_lower for word in ['news', 'report', 'confirmed', 'official']):
                news_count += 1
        
        print(f"  Rumor mentions: {rumors_count}")
        print(f"  Denial/debunking mentions: {denials_count}")
        print(f"  Jokes/satire: {jokes_count}")
        print(f"  News/reports: {news_count}")
        
    else:
        print("\n[No findings generated - may need to adjust search terms]")
    
    print("\n" + "=" * 60)
    print("INVESTIGATION SUMMARY")
    print("=" * 60)
    print("Based on the Twitter investigation, here's what people are saying:")
    print("- Total perspectives analyzed:", len(result.accumulated_findings))
    print("- Investigation confidence:", f"{result.satisfaction_metrics.overall_satisfaction():.0%}")
    
except Exception as e:
    print(f"\n[ERROR] Investigation failed: {e}")
    import traceback
    traceback.print_exc()