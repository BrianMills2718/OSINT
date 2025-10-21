"""Run investigation and show results"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from twitterexplorer.investigation_engine import InvestigationEngine, InvestigationConfig
from twitterexplorer.investigation_graph import InvestigationGraph
import json
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime

def run_investigation_with_graph():
    """Run investigation and visualize the graph"""
    
    print("="*60)
    print("INVESTIGATION: Debunking Michael Herrera")
    print("="*60)
    
    # Create engine
    engine = InvestigationEngine("d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f")
    
    # Configure for focused investigation
    config = InvestigationConfig(
        max_searches=15,
        pages_per_search=2,
        satisfaction_enabled=True,
        satisfaction_threshold=0.7,
        min_searches_before_satisfaction=5
    )
    
    print("\nStarting investigation...")
    print("-"*60)
    
    # Run investigation
    try:
        result = engine.conduct_investigation(
            "find me information that debunks michael herrera",
            config=config
        )
        
        print(f"\n[SUCCESS] Investigation completed!")
        print(f"Searches conducted: {result.search_count}")
        print(f"Total results found: {result.total_results_found}")
        print(f"Satisfaction score: {result.satisfaction_metrics.overall_satisfaction():.2f}")
        
        # Show search history
        print("\n### SEARCH HISTORY ###")
        for i, search in enumerate(result.search_history[:10], 1):
            endpoint = search.endpoint if hasattr(search, 'endpoint') else 'unknown'
            query = str(search.query) if hasattr(search, 'query') else str(search)[:50]
            print(f"{i}. {endpoint}: {query[:80]}")
        
        # Analyze graph
        graph = engine.llm_coordinator.graph
        print(f"\n### GRAPH ANALYSIS ###")
        print(f"Nodes created: {len(graph.nodes)}")
        print(f"Edges created: {len(graph.edges)}")
        
        # Count node types
        node_types = {}
        for node in graph.nodes.values():
            node_type = node.node_type
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\nNode breakdown:")
        for node_type, count in node_types.items():
            print(f"  {node_type}: {count}")
        
        # Count edge types
        edge_types = {}
        for edge in graph.edges:
            edge_type = edge.edge_type
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        print("\nEdge breakdown:")
        for edge_type, count in edge_types.items():
            print(f"  {edge_type}: {count}")
        
        # Create NetworkX graph for visualization
        G = nx.DiGraph()
        
        # Add nodes with labels
        node_labels = {}
        node_colors = []
        for node_id, node in graph.nodes.items():
            # Truncate label for readability
            if node.node_type == "AnalyticQuestion":
                label = "GOAL: Debunk Herrera"
                color = 'red'
            elif node.node_type == "InvestigationQuestion":
                label = f"Q: {node.properties.get('text', '')[:30]}..."
                color = 'yellow'
            elif node.node_type == "SearchQuery":
                endpoint = node.properties.get('endpoint', 'search')
                params = node.properties.get('parameters', {})
                query_text = params.get('query', params.get('screenname', ''))[:20]
                label = f"{endpoint}: {query_text}..."
                color = 'lightblue'
            elif node.node_type == "DataPoint":
                label = f"Data: {node.properties.get('content', '')[:20]}..."
                color = 'lightgreen'
            elif node.node_type == "Insight":
                label = f"Insight: {node.properties.get('content', '')[:25]}..."
                color = 'orange'
            else:
                label = f"{node.node_type[:10]}"
                color = 'gray'
            
            G.add_node(node_id[:8], label=label)
            node_labels[node_id[:8]] = label
            node_colors.append(color)
        
        # Add edges
        for edge in graph.edges:
            if edge.source_id in graph.nodes and edge.target_id in graph.nodes:
                G.add_edge(edge.source_id[:8], edge.target_id[:8], 
                          label=edge.edge_type)
        
        # Create visualization
        plt.figure(figsize=(15, 10))
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Draw the graph
        nx.draw(G, pos, 
                node_color=node_colors,
                node_size=1500,
                with_labels=False,
                arrows=True,
                edge_color='gray',
                arrowsize=20,
                width=1.5)
        
        # Add labels
        nx.draw_networkx_labels(G, pos, node_labels, font_size=8)
        
        # Add edge labels
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6)
        
        plt.title("Investigation Knowledge Graph - Debunking Michael Herrera", fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        
        # Save the graph
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"investigation_graph_{timestamp}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n[GRAPH] Graph saved to: {filename}")
        plt.show()
        
        # Show key findings
        print("\n### KEY FINDINGS ###")
        if result.accumulated_findings:
            for i, finding in enumerate(result.accumulated_findings[:5], 1):
                print(f"{i}. {finding.content[:150]}...")
        else:
            print("No key findings extracted yet")
        
        return result, graph
        
    except Exception as e:
        print(f"[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    result, graph = run_investigation_with_graph()