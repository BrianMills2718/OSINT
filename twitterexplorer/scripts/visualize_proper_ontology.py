"""Create investigation graph with proper ontology and batch structure"""
from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer
from datetime import datetime
import json
import random

def create_proper_investigation_graph():
    """Create a graph following the actual ontology and batch structure"""
    
    print("\n" + "="*80)
    print(" INVESTIGATION GRAPH WITH PROPER ONTOLOGY")
    print("="*80)
    
    viz = InvestigationGraphVisualizer()
    
    # LEVEL 1: Analytic Question (root)
    analytic_question = "What are the current controversies surrounding Trump and Epstein's relationship?"
    print(f"\nAnalytic Question: {analytic_question}")
    print("-"*80)
    
    # We'll use 'query' node type for the analytic question since our visualizer doesn't have separate types yet
    analytic_id = viz.add_query_node(analytic_question)
    
    # LEVEL 2: Investigation Questions (operationalize the analytic question)
    investigation_questions = [
        "What evidence exists of Trump-Epstein meetings in 2002?",
        "How does Trump's current narrative compare to historical records?",
        "What financial connections existed between Trump and Epstein?",
        "What do witnesses say about Trump-Epstein interactions?"
    ]
    
    print("\n[INVESTIGATION QUESTIONS]")
    investigation_ids = []
    for i, iq in enumerate(investigation_questions, 1):
        # Using search nodes to represent investigation questions for now
        iq_id = viz.add_search_node(
            {"investigation_question": iq},
            "investigation",
            i,
            parent_id=analytic_id
        )
        investigation_ids.append(iq_id)
        print(f"  IQ{i}: {iq[:60]}...")
    
    # LEVEL 3: Search Queries (4 searches per round, multiple rounds)
    # Simulate 5 rounds of 4 searches each = 20 searches total
    num_rounds = 5
    searches_per_round = 4
    total_searches = num_rounds * searches_per_round
    
    print(f"\n[SEARCH EXECUTION: {num_rounds} rounds × {searches_per_round} searches = {total_searches} total]")
    print("-"*40)
    
    search_counter = 0
    all_datapoint_ids = []
    
    for round_num in range(1, num_rounds + 1):
        print(f"\n== ROUND {round_num} ==")
        
        # Each round focuses on one investigation question
        current_iq_id = investigation_ids[(round_num - 1) % len(investigation_ids)]
        
        round_searches = []
        
        # Batch of 4 searches per round
        for batch_idx in range(searches_per_round):
            search_counter += 1
            
            # Define search based on round and position in batch
            if round_num == 1:
                # Round 1: Broad searches
                searches = [
                    ("Trump Epstein 2002", "search.php", 127),
                    ("Epstein flight logs Trump", "search.php", 89),
                    ("Mar-a-Lago parties 2002", "search.php", 45),
                    ("Trump Epstein photos evidence", "search.php", 67)
                ]
            elif round_num == 2:
                # Round 2: Timeline searches
                searches = [
                    ("realDonaldTrump", "timeline.php", 234),
                    ("VirginiaGiuffre", "timeline.php", 156),
                    ("AlanDershowitz", "timeline.php", 89),
                    ("jeffreyepstein", "timeline.php", 0)  # Account suspended
                ]
            elif round_num == 3:
                # Round 3: Specific date searches
                searches = [
                    ("Trump March 15 2002", "search.php", 34),
                    ("Epstein Palm Beach February 2002", "search.php", 78),
                    ("calendar girl audition Mar-a-Lago", "search.php", 12),
                    ("Trump Epstein court documents 2002", "search.php", 56)
                ]
            elif round_num == 4:
                # Round 4: Financial searches
                searches = [
                    ("Trump Organization Epstein payment", "search.php", 8),
                    ("Epstein Trump business deal", "search.php", 0),
                    ("3.5 million transaction 2002", "search.php", 2),
                    ("shell company Trump Epstein", "search.php", 4)
                ]
            else:
                # Round 5: Fact checking
                searches = [
                    ("fact check Trump Epstein friendship", "search.php", 145),
                    ("Trump denies knowing Epstein", "search.php", 234),
                    ("NBC 1992 Trump Epstein video", "search.php", 67),
                    ("Trump Epstein contradiction timeline", "search.php", 89)
                ]
            
            query, endpoint, results = searches[batch_idx]
            
            # Create search parameters
            if endpoint == "timeline.php":
                params = {"screenname": query, "count": 20}
            else:
                params = {"query": query}
            
            # Add search node
            search_id = viz.add_search_node(
                params,
                endpoint,
                search_counter,
                parent_id=current_iq_id
            )
            round_searches.append((search_id, results))
            
            # Display search result
            status = "[OK]" if results > 0 else "[--]"
            print(f"{status} Search #{search_counter:2d}: {query[:35]:<35} | Results: {results:3d}")
            
            # LEVEL 4: DataPoints (findings from searches)
            if results > 0:
                # Add 1-3 significant findings per successful search
                num_findings = min(3, max(1, results // 50))
                for _ in range(num_findings):
                    finding_templates = [
                        f"Court documents show Trump-Epstein meeting on {random.choice(['Jan', 'Feb', 'Mar'])} {random.randint(1,28)}, 2002",
                        f"Witness testimony: '{random.choice(['Saw them together', 'They were close', 'Regular meetings'])}'",
                        f"Financial record: ${random.randint(1,9)}.{random.randint(1,9)}M transaction detected",
                        f"Photo evidence from {random.choice(['party', 'event', 'meeting'])} at {random.choice(['Mar-a-Lago', 'Trump Tower', 'Palm Beach'])}",
                        f"Flight log entry: {random.choice(['Feb', 'Mar', 'Apr'])} {random.randint(1,28)}, 2002",
                        f"Email correspondence mentioning {random.choice(['business deal', 'party planning', 'mutual friends'])}"
                    ]
                    
                    finding = random.choice(finding_templates)
                    dp_id = viz.add_datapoint_node(
                        finding,
                        endpoint,
                        search_id,
                        relevance=0.5 + random.random() * 0.5
                    )
                    all_datapoint_ids.append(dp_id)
        
        # After each round, evaluate for insights
        if len(all_datapoint_ids) >= 3:
            # LEVEL 5: Insights (patterns from datapoints)
            if round_num % 2 == 0:  # Add insights every other round
                insight_text = f"Pattern from Round {round_num}: Multiple sources confirm ongoing relationship"
                viz.add_insight_node(
                    insight_text,
                    confidence=0.7 + random.random() * 0.3,
                    supporting_nodes=random.sample(all_datapoint_ids, min(3, len(all_datapoint_ids)))
                )
                print(f"  -> INSIGHT: {insight_text}")
    
    # LEVEL 6: Emergent Questions (new questions from insights)
    emergent_questions = [
        "Why did Trump's narrative change after 2019?",
        "What triggered the business relationship to end?",
        "Were there other witnesses to these meetings?"
    ]
    
    print(f"\n[EMERGENT QUESTIONS]")
    for eq in emergent_questions:
        # Add as a special type of node (using search node with special marking)
        viz.add_search_node(
            {"emergent_question": eq},
            "emergent",
            999,  # Special number to indicate emergent
            parent_id=analytic_id
        )
        print(f"  NEW: {eq}")
    
    # Get and display statistics
    print(f"\n[GRAPH STATISTICS]")
    print("-"*40)
    stats = viz.get_statistics()
    
    print(f"Total Nodes: {stats['total_nodes']}")
    print(f"  - Analytic Question: 1")
    print(f"  - Investigation Questions: {len(investigation_ids)}")
    print(f"  - Search Queries: {total_searches}")
    print(f"  - DataPoints: {stats['node_counts']['datapoint']}")
    print(f"  - Insights: {stats['node_counts']['insight']}")
    print(f"  - Emergent Questions: {len(emergent_questions)}")
    
    print(f"\nTotal Connections: {stats['total_edges']}")
    print(f"\nGraph Structure:")
    print(f"  - {num_rounds} rounds of {searches_per_round} searches each")
    print(f"  - Follows proper ontology: Analytic -> Investigation -> Search -> DataPoint -> Insight -> Emergent")
    
    dead_ends = stats['metrics'].get('dead_end_searches', [])
    if dead_ends:
        print(f"\nDead-end Searches: {len(dead_ends)}")
    
    # Save visualization
    print(f"\n[SAVING FILES]")
    print("-"*40)
    
    html_file = "investigation_proper_ontology.html"
    viz.save_visualization(html_file)
    print(f"[OK] HTML visualization saved to: {html_file}")
    
    json_file = "investigation_proper_ontology.json"
    data = viz.export_vis_data()
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Graph data saved to: {json_file}")
    
    print("\n" + "="*80)
    print(" PROPER ONTOLOGY GRAPH COMPLETE")
    print("="*80)
    print(f"\nOpen {html_file} in your browser to view the investigation graph!")
    print("\nThis graph correctly shows:")
    print(f"  - {num_rounds} rounds with {searches_per_round} searches each (total: {total_searches})")
    print("  - Proper ontology hierarchy:")
    print("    1. Analytic Question (root)")
    print("    2. Investigation Questions (operationalize)")
    print("    3. Search Queries (in batches of 4)")
    print("    4. DataPoints (findings)")
    print("    5. Insights (patterns)")
    print("    6. Emergent Questions (new directions)")
    
    return viz

if __name__ == "__main__":
    viz = create_proper_investigation_graph()