#!/usr/bin/env python3
"""Quick script to visualize the latest investigation graph"""
import json
import os
from datetime import datetime

def show_latest_investigation():
    # Find latest session
    sessions_dir = "logs/sessions/2025-09-04"
    if not os.path.exists(sessions_dir):
        print("No sessions found for today")
        return
    
    # Get all session files
    session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.jsonl')]
    if not session_files:
        print("No session files found")
        return
    
    # Get most recent session
    latest_session = max(session_files, key=lambda f: os.path.getctime(os.path.join(sessions_dir, f)))
    session_id = latest_session.replace('.jsonl', '')
    
    print("LATEST INVESTIGATION ANALYSIS")
    print(f"Session ID: {session_id}")
    print("=" * 60)
    
    # Load session data
    session_path = os.path.join(sessions_dir, latest_session)
    events = []
    
    with open(session_path, 'r') as f:
        for line in f:
            events.append(json.loads(line.strip()))
    
    # Analyze events
    searches = []
    results_count = 0
    
    for event in events:
        if event.get('event') == 'search_executed':
            search_data = event.get('data', {})
            searches.append({
                'endpoint': search_data.get('endpoint', 'unknown'),
                'query': search_data.get('params', {}).get('query', 'N/A'),
                'results': search_data.get('results_count', 0)
            })
            results_count += search_data.get('results_count', 0)
        elif event.get('event') == 'session_completed':
            completion_data = event.get('data', {})
            print("INVESTIGATION COMPLETED")
            print(f"Duration: {completion_data.get('duration_seconds', 0):.1f} seconds")
            print(f"Total Results: {results_count}")
            print(f"Satisfaction: {completion_data.get('satisfaction_score', 0):.2f}")
            print()
    
    print("SEARCH STRATEGY USED:")
    for i, search in enumerate(searches, 1):
        print(f"{i}. {search['endpoint']}")
        if search['query'] != 'N/A':
            print(f"   Query: {search['query'][:80]}...")
        print(f"   Results: {search['results']}")
        print()
    
    print("INTELLIGENCE ASSESSMENT:")
    unique_endpoints = set(s['endpoint'] for s in searches)
    print(f"Endpoint Diversity: {len(unique_endpoints)} different endpoints")
    print(f"Endpoints Used: {', '.join(unique_endpoints)}")
    print(f"Average Results per Search: {results_count/len(searches) if searches else 0:.1f}")
    
    if len(unique_endpoints) > 2:
        print("SUCCESS: GPT-5-mini shows MULTI-ENDPOINT intelligence!")
    else:
        print("WARNING: Limited endpoint diversity")
    
    if results_count > 100:
        print("SUCCESS: Strong data collection capability")
    else:
        print("WARNING: Limited data collection")

if __name__ == "__main__":
    show_latest_investigation()