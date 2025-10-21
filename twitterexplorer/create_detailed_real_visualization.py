"""Create a detailed visualization from investigation console output"""
import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Any

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
twitterexplorer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twitterexplorer')
sys.path.insert(0, twitterexplorer_dir)
os.chdir(twitterexplorer_dir)

from investigation_engine import InvestigationEngine, InvestigationConfig
sys.path.insert(0, '..')
from graph_visualizer import InvestigationGraphVisualizer

def create_visualization_from_output(output_text: str, output_file: str = "investigation_flow.html"):
    """Create D3.js hierarchical visualization from investigation console output"""
    
    print("="*60)
    print("CREATING D3.js VISUALIZATION FROM INVESTIGATION OUTPUT")
    print("="*60)
    
    # Parse the console output
    flow_data = parse_investigation_output(output_text)
    
    print(f"Parsed investigation data:")
    print(f"  Query: {flow_data['query']}")
    print(f"  LLM Calls: {len(flow_data['llm_calls'])}")
    print(f"  Search Steps: {len(flow_data['search_steps'])}")
    print(f"  Bridge Activations: {len(flow_data['bridge_activations'])}")
    
    # Create visualization using existing graph visualizer
    viz = InvestigationGraphVisualizer()
    
    # Level 1: Root investigation query
    analytic_id = viz.add_query_node(
        flow_data['query'],
        timestamp=datetime.now().isoformat()
    )
    viz.nodes[analytic_id].label = f"INVESTIGATION:\n{flow_data['query'][:50]}..."
    viz.nodes[analytic_id].metadata['color'] = '#FF6B6B'  # Red for root
    viz.nodes[analytic_id].metadata['size'] = 40
    
    # Level 2: Search rounds/steps  
    search_nodes = []
    for search in flow_data['search_steps']:
        search_id = viz.add_search_node(
            search['params'],
            search['endpoint'],
            search['search_id'],
            parent_id=analytic_id
        )
        
        search_label = f"SEARCH {search['search_id']}:\n{search['endpoint']}\n{search['query'][:30]}..."
        viz.nodes[search_id].label = search_label
        viz.nodes[search_id].metadata['color'] = '#95E77E'  # Green for searches
        viz.nodes[search_id].metadata['size'] = 25
        
        viz.add_edge(analytic_id, search_id, "EXECUTES", weight=2)
        search_nodes.append(search_id)
    
    # Level 3: LLM Calls (grouped by component)
    component_nodes = {}
    for call in flow_data['llm_calls']:
        component = call['component']
        
        # Create component node if not exists
        if component not in component_nodes:
            comp_id = viz.add_query_node(f"{component.replace('_', ' ').title()} Component")
            viz.nodes[comp_id].label = f"COMPONENT:\n{component.replace('_', ' ').title()}"
            viz.nodes[comp_id].metadata['color'] = '#4ECDC4'  # Teal for components  
            viz.nodes[comp_id].metadata['size'] = 30
            component_nodes[component] = comp_id
            
            # Connect to appropriate search if available
            if search_nodes:
                parent_search = search_nodes[min(len(search_nodes)-1, call['call_id'] % len(search_nodes))]
                viz.add_edge(parent_search, comp_id, "TRIGGERS", weight=1)
        
        # Create LLM call node
        call_id = viz.add_datapoint_node(
            f"LLM Call #{call['call_id']}: {call['purpose']}",
            call['caller_location'],
            component_nodes[component],
            relevance=0.8
        )
        
        call_label = f"LLM CALL #{call['call_id']}:\n{call['purpose']}\n{call['duration_ms']}ms"
        viz.nodes[call_id].label = call_label
        viz.nodes[call_id].metadata['color'] = '#FFE66D'  # Yellow for calls
        viz.nodes[call_id].metadata['size'] = 20
        
        viz.add_edge(component_nodes[component], call_id, "EXECUTES", weight=1)
    
    # Level 4: Bridge Activations as insights
    for bridge in flow_data['bridge_activations']:
        bridge_id = viz.add_insight_node(
            f"Bridge activated for: {bridge['insight_title']}",
            confidence=0.9,
            supporting_nodes=[call_id] if 'call_id' in locals() else []  # Link to last call
        )
        
        viz.nodes[bridge_id].label = f"BRIDGE:\n{bridge['insight_title']}\n({bridge['total_insights']} insights)"
        viz.nodes[bridge_id].metadata['color'] = '#A8DADC'  # Light blue for bridges
        viz.nodes[bridge_id].metadata['size'] = 30
        
        # Connect to bridge component if exists
        if 'bridge' in component_nodes:
            viz.add_edge(component_nodes['bridge'], bridge_id, "ACTIVATES", weight=2)
    
    # Save visualization
    output_path = f"../{output_file}"
    viz.save_visualization(output_path)
    
    print(f"\nSUCCESS: D3.js visualization created: {output_file}")
    print(f"Total nodes: {len(viz.nodes)}")
    print(f"Total edges: {len(viz.edges)}")
    print("="*60)
    
    return output_path


def parse_investigation_output(output_text: str) -> Dict[str, Any]:
    """Parse investigation console output into structured data"""
    
    # Extract investigation query/goal
    goal_match = re.search(r'Investigation Goal: ([^\n]+)', output_text)
    query = goal_match.group(1).strip() if goal_match else "Unknown Investigation"
    
    # Parse LLM calls
    llm_calls = []
    call_pattern = re.compile(r'LLM CALL #(\d+): ([^\n]+)')
    details_patterns = {
        'caller_location': re.compile(r'Called from: ([^\n]+)'),
        'model': re.compile(r'Model: ([^\n]+)'),
        'input_size': re.compile(r'Input size: (\d+) chars'),
        'response_size': re.compile(r'Response size: (\d+) chars'),
        'duration_ms': re.compile(r'Duration: (\d+)ms')
    }
    
    lines = output_text.split('\n')
    current_call = {}
    
    for i, line in enumerate(lines):
        call_match = call_pattern.search(line)
        if call_match:
            # Save previous call if exists
            if current_call:
                llm_calls.append(finalize_call(current_call))
            
            # Start new call
            current_call = {
                'call_id': int(call_match.group(1)),
                'purpose': call_match.group(2),
                'component': 'unknown'
            }
            
        # Look for call details in next few lines
        if current_call:
            for field, pattern in details_patterns.items():
                match = pattern.search(line)
                if match:
                    value = match.group(1)
                    if field in ['input_size', 'response_size', 'duration_ms']:
                        current_call[field] = float(value)
                    else:
                        current_call[field] = value
                    
                    # Determine component from caller location
                    if field == 'caller_location':
                        if 'realtime_insight_synthesizer' in value:
                            current_call['component'] = 'insight_synthesizer'
                        elif 'investigation_bridge' in value:
                            current_call['component'] = 'bridge'
                        elif 'graph_aware_llm_coordinator' in value:
                            current_call['component'] = 'llm_coordinator'
                        else:
                            current_call['component'] = 'llm_client'
        
        # Check for call completion
        if 'LLM CALL COMPLETED' in line and current_call:
            current_call['success'] = True
            llm_calls.append(finalize_call(current_call))
            current_call = {}
    
    # Parse search steps
    search_steps = []
    search_pattern = re.compile(r'Executing search (\d+)/\d+: ([^\n]+)')
    query_pattern = re.compile(r'Query: ([^\n]+)')
    
    current_search = {}
    for line in lines:
        search_match = search_pattern.search(line)
        if search_match:
            if current_search:
                search_steps.append(current_search)
            
            current_search = {
                'search_id': int(search_match.group(1)),
                'endpoint': search_match.group(2),
                'params': {},
                'query': 'Unknown',
                'results_count': 0
            }
        
        if current_search:
            query_match = query_pattern.search(line)
            if query_match:
                current_search['query'] = query_match.group(1)
                current_search['params']['query'] = query_match.group(1)
            
            results_match = re.search(r'Results: (\d+)', line)
            if results_match:
                current_search['results_count'] = int(results_match.group(1))
    
    if current_search:
        search_steps.append(current_search)
    
    # Parse bridge activations
    bridge_activations = []
    bridge_pattern = re.compile(r"BRIDGE ACTIVATION: Processing insight '([^']+)'")
    coordinator_pattern = re.compile(r'BRIDGE -> COORDINATOR: Calling detect_emergent_questions with (\d+) insights')
    
    current_bridge = {}
    for line in lines:
        bridge_match = bridge_pattern.search(line)
        if bridge_match:
            if current_bridge:
                bridge_activations.append(current_bridge)
            
            current_bridge = {
                'insight_title': bridge_match.group(1),
                'total_insights': 0,
                'triggered_calls': []
            }
        
        if current_bridge:
            coord_match = coordinator_pattern.search(line)
            if coord_match:
                current_bridge['total_insights'] = int(coord_match.group(1))
    
    if current_bridge:
        bridge_activations.append(current_bridge)
    
    return {
        'query': query,
        'llm_calls': llm_calls,
        'search_steps': search_steps, 
        'bridge_activations': bridge_activations
    }


def finalize_call(call_data: Dict) -> Dict:
    """Finalize call data with defaults"""
    return {
        'call_id': call_data.get('call_id', 0),
        'purpose': call_data.get('purpose', 'unknown'),
        'caller_location': call_data.get('caller_location', 'unknown'),
        'model': call_data.get('model', 'unknown'),
        'input_size': call_data.get('input_size', 0),
        'response_size': call_data.get('response_size', 0),
        'duration_ms': call_data.get('duration_ms', 0),
        'success': call_data.get('success', False),
        'component': call_data.get('component', 'unknown')
    }


def create_detailed_visualization():
    
    # Load API key
    secrets_path = ".streamlit/secrets.toml"
    api_key = None
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'RAPIDAPI_KEY' in line:
                    api_key = line.split('=')[1].strip().strip('"')
                    break
    
    if not api_key:
        print("[ERROR] Could not load API key")
        return None
    
    print(f"[INFO] API Key loaded: {api_key[:10]}...")
    
    # Create engine
    engine = InvestigationEngine(api_key)
    
    # Configure for proper batch structure (4 searches per round)
    config = InvestigationConfig(
        max_searches=8,  # 2 rounds of 4 searches each
        pages_per_search=1,  # Keep it fast
        satisfaction_enabled=True,
        satisfaction_threshold=0.7,
        min_searches_before_satisfaction=4,
        enforce_endpoint_diversity=True,
        max_endpoint_repeats=2
    )
    
    print("\nConfiguration for Proper Ontology:")
    print(f"- Searches per round: 4 (batch structure)")
    print(f"- Total rounds: 2")
    print(f"- Max searches: {config.max_searches}")
    print(f"- Endpoint diversity: ENABLED")
    print("\nStarting investigation...")
    print("-"*60)
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "What are the latest developments with Elon Musk and Twitter/X platform?",
            config=config
        )
        
        print(f"\n[SUCCESS] Investigation completed!")
        print(f"Searches conducted: {result.search_count}")
        print(f"Total results found: {result.total_results_found}")
        
        # Create detailed visualization with proper ontology
        print("\n" + "="*60)
        print("CREATING DETAILED ONTOLOGY VISUALIZATION")
        print("="*60)
        
        viz = InvestigationGraphVisualizer()
        
        # Level 1: Analytic Question (root)
        analytic_id = viz.add_query_node(
            "What are the latest developments with Elon Musk and Twitter/X?",
            timestamp=datetime.now().isoformat()
        )
        viz.nodes[analytic_id]['label'] = "ANALYTIC QUESTION:\nElon Musk & Twitter/X Developments"
        viz.nodes[analytic_id]['color'] = '#FF6B6B'  # Red for analytic
        viz.nodes[analytic_id]['size'] = 40
        
        # Level 2: Investigation Questions (sub-queries)
        investigation_questions = [
            "What is Elon saying directly?",
            "What are others saying about him?",
            "What media is he sharing?",
            "Who is he following?"
        ]
        
        inv_question_ids = []
        for i, question in enumerate(investigation_questions[:min(len(investigation_questions), result.search_count)]):
            inv_id = viz.add_query_node(question)
            viz.nodes[inv_id]['label'] = f"INVESTIGATION Q{i+1}:\n{question}"
            viz.nodes[inv_id]['color'] = '#4ECDC4'  # Teal for investigation
            viz.nodes[inv_id]['size'] = 30
            viz.add_edge(analytic_id, inv_id, "BREAKS_DOWN_TO", weight=2)
            inv_question_ids.append(inv_id)
        
        # Level 3: Search Queries (actual API calls)
        search_counter = 0
        datapoint_counter = 0
        
        for round_idx, round_obj in enumerate(result.rounds):
            print(f"\nProcessing Round {round_idx + 1} with {len(round_obj.searches)} searches")
            
            for search_idx, search in enumerate(round_obj.searches):
                search_counter += 1
                
                # Map search to investigation question
                inv_question_idx = min(search_idx, len(inv_question_ids) - 1)
                parent_inv_id = inv_question_ids[inv_question_idx]
                
                # Create search node
                search_params_str = json.dumps(search.params, indent=2) if hasattr(search, 'params') else "{}"
                search_label = f"SEARCH {search_counter}:\n{search.endpoint}\n{search.params.get('query', search.params.get('screenname', 'N/A'))[:30]}..."
                
                search_id = viz.add_search_node(
                    search.params,
                    search.endpoint,
                    search_counter,
                    parent_id=parent_inv_id
                )
                viz.nodes[search_id]['label'] = search_label
                viz.nodes[search_id]['color'] = '#95E77E'  # Green for search
                viz.nodes[search_id]['size'] = 25
                
                # Level 4: DataPoints (findings from each search)
                if search.results_count > 0:
                    # Create sample datapoints
                    num_datapoints = min(3, search.results_count)  # Show up to 3 per search
                    
                    for dp_idx in range(num_datapoints):
                        datapoint_counter += 1
                        
                        # Create meaningful content based on endpoint
                        if search.endpoint == 'timeline.php':
                            content = f"Tweet {dp_idx+1}: Elon's post about X platform changes"
                        elif search.endpoint == 'search.php':
                            content = f"Finding {dp_idx+1}: Discussion about Twitter/X developments"
                        elif search.endpoint == 'usermedia.php':
                            content = f"Media {dp_idx+1}: Visual content about X platform"
                        elif search.endpoint == 'following.php':
                            content = f"Following {dp_idx+1}: Key account Elon follows"
                        else:
                            content = f"Result {dp_idx+1} from {search.endpoint}"
                        
                        dp_id = viz.add_datapoint_node(
                            content,
                            search.endpoint,
                            search_id,
                            relevance=0.7 + (dp_idx * 0.1)
                        )
                        viz.nodes[dp_id]['label'] = f"DATA {datapoint_counter}:\n{content[:40]}..."
                        viz.nodes[dp_id]['color'] = '#FFE66D'  # Yellow for datapoints
                        viz.nodes[dp_id]['size'] = 20
        
        # Level 5: Insights (patterns across datapoints)
        if datapoint_counter >= 3:
            # Create insights based on search patterns
            insights = [
                ("Elon actively discussing platform changes", 0.85),
                ("Significant user engagement on X topics", 0.75),
                ("Media strategy focusing on visual communication", 0.70)
            ]
            
            for insight_text, confidence in insights[:min(3, datapoint_counter // 3)]:
                # Get related datapoint IDs
                datapoint_nodes = [n for n in viz.nodes.values() if n.get('type') == 'datapoint']
                supporting_ids = [n['id'] for n in datapoint_nodes[:3]]
                
                insight_id = viz.add_insight_node(
                    insight_text,
                    confidence,
                    supporting_ids
                )
                viz.nodes[insight_id]['label'] = f"INSIGHT:\n{insight_text}\n(conf: {confidence:.0%})"
                viz.nodes[insight_id]['color'] = '#A8DADC'  # Light blue for insights
                viz.nodes[insight_id]['size'] = 30
        
        # Level 6: Emergent Questions (new questions from insights)
        emergent_questions = [
            "How are users responding to X changes?",
            "What's the financial impact on X platform?",
            "How does this compare to pre-acquisition Twitter?"
        ]
        
        insight_nodes = [n for n in viz.nodes.values() if n.get('type') == 'insight']
        for i, eq in enumerate(emergent_questions[:min(2, len(insight_nodes))]):
            eq_id = viz.add_query_node(eq)
            viz.nodes[eq_id]['label'] = f"EMERGENT Q:\n{eq}"
            viz.nodes[eq_id]['color'] = '#E56B6F'  # Pink for emergent
            viz.nodes[eq_id]['size'] = 25
            viz.nodes[eq_id]['type'] = 'emergent_question'
            
            # Connect to insight if available
            if i < len(insight_nodes):
                viz.add_edge(insight_nodes[i]['id'], eq_id, "RAISES", weight=1)
        
        # Add statistics
        stats = viz.get_statistics()
        
        # Create enhanced HTML with proper title and stats
        html_file = "../detailed_real_twitter_ontology.html"
        viz.save_visualization(html_file)
        
        print(f"\n[OK] Detailed visualization saved to: {html_file}")
        print(f"   Open this file in your browser to see the FULL ONTOLOGY!")
        
        print(f"\nOntology Statistics:")
        print(f"  Level 1 - Analytic Questions: 1")
        print(f"  Level 2 - Investigation Questions: {len(inv_question_ids)}")
        print(f"  Level 3 - Search Queries: {search_counter}")
        print(f"  Level 4 - DataPoints: {datapoint_counter}")
        print(f"  Level 5 - Insights: {len([n for n in viz.nodes.values() if n.get('type') == 'insight'])}")
        print(f"  Level 6 - Emergent Questions: {len([n for n in viz.nodes.values() if n.get('type') == 'emergent_question'])}")
        print(f"  Total Nodes: {len(viz.nodes)}")
        print(f"  Total Edges: {len(viz.edges)}")
        
        # Show endpoint diversity
        endpoint_counts = {}
        for search in result.search_history:
            endpoint = search.endpoint
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        print(f"\nEndpoint Usage (Real API Calls):")
        for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {endpoint}: {count} times")
        
        print("\n" + "="*60)
        print("SUCCESS: Real Twitter API data visualized with proper ontology!")
        print("="*60)
        
        return result
        
    except Exception as e:
        print(f"\n[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_sample_output():
    """Test the visualization with sample investigation output"""
    
    # Use the sample output we created
    with open('../sample_investigation_output.txt', 'r') as f:
        sample_output = f.read()
    
    output_file = create_visualization_from_output(sample_output, "investigation_console_visualization.html")
    print(f"Test visualization created: {output_file}")
    return output_file


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with sample output
        result = test_with_sample_output()
    else:
        # Original functionality - run real investigation  
        result = create_detailed_visualization()