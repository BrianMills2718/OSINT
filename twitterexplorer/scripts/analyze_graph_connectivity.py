"""Analyze the graph connectivity and ontology issues"""

import json
import networkx as nx

# Load the Trump investigation graph
with open('trump_investigation_graph.json', 'r') as f:
    trump_graph = json.load(f)

print("=" * 60)
print("GRAPH ONTOLOGY & CONNECTIVITY ANALYSIS")
print("=" * 60)

print(f"Investigation Topic: {trump_graph.get('investigation_topic', 'Unknown')}")
print(f"Total Nodes: {len(trump_graph['nodes'])}")
print(f"Total Edges: {len(trump_graph['edges'])}")

# Analyze the intended ontology
print(f"\n" + "=" * 60)
print("INTENDED ONTOLOGY DESIGN:")
print("=" * 60)

intended_flow = """
HIERARCHICAL INVESTIGATION FLOW (should be):
1. AnalyticQuestion (ROOT) 
   -> MOTIVATES
2. InvestigationQuestion(s) - Strategic questions
   -> OPERATIONALIZES  
3. SearchQuery - API calls
   -> GENERATES/DISCOVERED
4. DataPoint - Individual findings
   -> SUPPORTS
5. Insight - Synthesized analysis
   -> SPAWNS
6. EmergentQuestion - New questions arising

EDGE TYPES (Relationships):
- MOTIVATES: Root question -> Investigation questions
- OPERATIONALIZES: Investigation question -> Search queries  
- GENERATES: Search -> Results (generic)
- DISCOVERED: Search -> Specific datapoints
- SUPPORTS: DataPoint -> Insight
- ANSWERS: Results -> Questions
- SPAWNS: Insight -> New emergent questions
"""
print(intended_flow)

# Analyze actual structure
print(f"\n" + "=" * 60)
print("ACTUAL GRAPH STRUCTURE:")
print("=" * 60)

# Count node types
node_types = {}
nodes_by_type = {}
for node in trump_graph['nodes']:
    node_type = node['type']
    node_types[node_type] = node_types.get(node_type, 0) + 1
    if node_type not in nodes_by_type:
        nodes_by_type[node_type] = []
    nodes_by_type[node_type].append(node)

print("Node Types Found:")
for node_type, count in node_types.items():
    print(f"  {node_type}: {count}")

# Count edge types
edge_types = {}
for edge in trump_graph['edges']:
    edge_type = edge['type']
    edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

print("\nEdge Types Found:")
for edge_type, count in edge_types.items():
    print(f"  {edge_type}: {count}")

# Check for missing root node
print(f"\n" + "=" * 60)
print("CONNECTIVITY ISSUES:")
print("=" * 60)

# 1. Missing AnalyticQuestion (ROOT)
analytic_questions = [n for n in trump_graph['nodes'] if n['type'] == 'AnalyticQuestion']
print(f"1. Missing Root: Found {len(analytic_questions)} AnalyticQuestion nodes (should be 1)")

if len(analytic_questions) == 0:
    print("   [CRITICAL] PROBLEM: No root AnalyticQuestion node!")
    print("   -> This means no single entry point to connect the investigation")

# 2. Check connectivity using NetworkX
G = nx.DiGraph()

# Add nodes
for node in trump_graph['nodes']:
    G.add_node(node['id'], type=node['type'])

# Add edges  
for edge in trump_graph['edges']:
    G.add_edge(edge['source'], edge['target'], type=edge['type'])

print(f"\n2. Network Analysis:")
print(f"   Nodes in NetworkX: {G.number_of_nodes()}")
print(f"   Edges in NetworkX: {G.number_of_edges()}")

# Check connected components
if G.number_of_nodes() > 0:
    # Convert to undirected for component analysis
    G_undirected = G.to_undirected()
    components = list(nx.connected_components(G_undirected))
    
    print(f"   Connected components: {len(components)}")
    
    if len(components) > 1:
        print("   [CRITICAL] PROBLEM: Graph is not fully connected!")
        print("   -> Multiple disconnected subgraphs")
        
        for i, component in enumerate(components, 1):
            print(f"   Component {i}: {len(component)} nodes")
            component_types = {}
            for node_id in component:
                node_type = G.nodes[node_id]['type']
                component_types[node_type] = component_types.get(node_type, 0) + 1
            print(f"     Types: {component_types}")
    else:
        print("   [SUCCESS] Graph is connected")
        
    # Check for isolated nodes
    isolated = list(nx.isolates(G_undirected))
    if isolated:
        print(f"   [CRITICAL] Isolated nodes: {len(isolated)}")
        for node_id in isolated:
            node_type = G.nodes[node_id]['type'] 
            print(f"     {node_id[:20]}... ({node_type})")
    else:
        print("   [SUCCESS] No isolated nodes")

# 3. Examine why DataPoints weren't created
print(f"\n3. DataPoint Creation Issue:")
datapoints = [n for n in trump_graph['nodes'] if n['type'] == 'DataPoint']
print(f"   DataPoints found: {len(datapoints)}")

if len(datapoints) == 0:
    print("   [CRITICAL] PROBLEM: No DataPoints created from searches!")
    print("   -> This suggests:")
    print("     - API returned no results, OR")
    print("     - Finding evaluator filtered everything out, OR") 
    print("     - DataPoint creation failed")
    
    # Check SearchQuery nodes for clues
    searches = [n for n in trump_graph['nodes'] if n['type'] == 'SearchQuery']
    print(f"\n   Search queries performed: {len(searches)}")
    for i, search in enumerate(searches, 1):
        params = search['properties'].get('parameters', {})
        query = params.get('query', params.get('screenname', 'unknown'))
        endpoint = search['properties'].get('endpoint', 'unknown')
        print(f"     {i}. {endpoint}: {query[:50]}...")

# 4. Check for proper hierarchical flow
print(f"\n4. Hierarchical Flow Issues:")

investigation_questions = [n for n in trump_graph['nodes'] if n['type'] == 'InvestigationQuestion']
search_queries = [n for n in trump_graph['nodes'] if n['type'] == 'SearchQuery']

print(f"   InvestigationQuestions: {len(investigation_questions)}")
print(f"   SearchQueries: {len(search_queries)}")

# Check if investigation questions are connected to searches
operationalizes_edges = [e for e in trump_graph['edges'] if e['type'] == 'OPERATIONALIZES']
print(f"   OPERATIONALIZES edges: {len(operationalizes_edges)} (should connect questions -> searches)")

if len(operationalizes_edges) != len(search_queries):
    print("   [CRITICAL] PROBLEM: Not all searches are connected to questions!")

# Summary
print(f"\n" + "=" * 60)
print("SUMMARY OF ISSUES:")
print("=" * 60)
print("1. Missing AnalyticQuestion root node -> disconnected forest")
print("2. No DataPoints created -> empty results")  
print("3. Limited connectivity -> isolated subgraphs")
print("4. Investigation -> Search -> DataPoint flow broken")

print(f"\n" + "=" * 60)
print("WHAT THE ONTOLOGY SHOULD LOOK LIKE:")
print("=" * 60)
print("""
                    [AnalyticQuestion]
                           |
                    "Donald Trump Health?"
                           |
                     MOTIVATES
                           |
                           v
    [InvestigationQuestion] -> [InvestigationQuestion] -> [InvestigationQuestion]
     "Check rumors"          "Verify with news"        "Monitor trends"
           |                        |                        |
     OPERATIONALIZES          OPERATIONALIZES          OPERATIONALIZES  
           |                        |                        |
           v                        v                        v
    [SearchQuery]              [SearchQuery]            [SearchQuery]
    search.php                 from:CNN                 trends.php
           |                        |                        |
     GENERATES                 GENERATES                GENERATES
           |                        |                        |
           v                        v                        v
    [DataPoint]               [DataPoint]               [DataPoint]
    Individual tweets         News articles            Trending topics
           |                        |                        |
           +------ SUPPORTS --------+------ SUPPORTS -------+
                              |
                              v
                        [Insight]
                   "Rumors unsubstantiated"
                              |
                        SPAWNS (optional)
                              v
                   [EmergentQuestion]
                 "Why do rumors persist?"
""")