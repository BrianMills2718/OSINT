"""
Create a demo hierarchical wave visualization with mock data showing complete wave structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'twitterexplorer'))

from twitterexplorer.graph_visualizer import InvestigationGraphVisualizer

def create_demo_hierarchy():
    """Create a demo hierarchical visualization with complete wave structure"""
    
    # Create visualizer
    visualizer = InvestigationGraphVisualizer()
    
    # Mock wave data showing complete network structure without Wave nodes
    demo_wave_data = {
        "investigation_goal": "Analyze impact of AI on employment and workforce transformation",
        "wave_count": 3,
        "nodes": [
            # Analytic Goal (root)
            {"id": "analytic_goal", "name": "Analyze AI employment impact", "type": "AnalyticGoal", "wave": 0,
             "full_text": "Analyze impact of AI on employment and workforce transformation"},
            
            # Wave 1: Initial investigation questions and searches
            {"id": "q1_1", "name": "What are AI employment impacts?", "type": "InvestigationQuestion", "wave": 1,
             "full_text": "What are the current and projected impacts of AI on employment across different sectors?"},
            {"id": "q1_2", "name": "How is workforce adapting?", "type": "InvestigationQuestion", "wave": 1,
             "full_text": "How is the workforce adapting to AI-driven changes and what trends are emerging?"},
            
            {"id": "s1_1", "name": "AI employment impact search", "type": "Search", "wave": 1, 
             "full_text": "Search for AI employment impact studies and reports", 
             "details": {"query": "AI employment impact studies", "endpoint": "search.php", "results": 45}},
            {"id": "s1_2", "name": "Workforce automation trends", "type": "Search", "wave": 1, 
             "full_text": "Search for workforce automation trends and predictions", 
             "details": {"query": "workforce automation trends", "endpoint": "search.php", "results": 38}},
            
            {"id": "d1_1", "name": "McKinsey automation report", "type": "DataPoint", "wave": 1,
             "full_text": "McKinsey report showing 375 million workers need reskilling by 2030"},
            {"id": "d1_2", "name": "MIT automation study", "type": "DataPoint", "wave": 1,
             "full_text": "MIT study on sector-specific AI adoption rates and job displacement patterns"},
            
            {"id": "i1_1", "name": "AI displaces routine jobs first", "type": "Insight", "wave": 1, 
             "full_text": "AI primarily displaces routine, predictable jobs across sectors"},
            {"id": "i1_2", "name": "Reskilling demand accelerating", "type": "Insight", "wave": 1, 
             "full_text": "Companies increasing investment in worker reskilling programs"},
             
            {"id": "eq1_1", "name": "Which sectors most vulnerable?", "type": "EmergentQuestion", "wave": 1, 
             "full_text": "Which specific sectors and job categories are most vulnerable to AI displacement?"},
            {"id": "eq1_2", "name": "How effective is reskilling?", "type": "EmergentQuestion", "wave": 1, 
             "full_text": "How effective are current reskilling programs at preventing unemployment?"},
            
            # Wave 2: Targeted investigation based on emergent questions
            {"id": "s2_1", "name": "Manufacturing automation impact", "type": "Search", "wave": 2, 
             "full_text": "Detailed search on manufacturing sector AI automation", 
             "details": {"query": "manufacturing AI automation job displacement", "driven_by": "Which sectors most vulnerable?"}},
            {"id": "s2_2", "name": "Reskilling program effectiveness", "type": "Search", "wave": 2, 
             "full_text": "Search for data on corporate reskilling program outcomes", 
             "details": {"query": "corporate reskilling program success rates", "driven_by": "How effective is reskilling?"}},
             
            {"id": "d2_1", "name": "Manufacturing job displacement data", "type": "DataPoint", "wave": 2,
             "full_text": "Data showing 40% job displacement in manufacturing from AI automation"},
            {"id": "d2_2", "name": "Corporate reskilling outcomes", "type": "DataPoint", "wave": 2,
             "full_text": "Analysis of reskilling success rates across major corporations"},
             
            {"id": "i2_1", "name": "Manufacturing leads displacement", "type": "Insight", "wave": 2, 
             "full_text": "Manufacturing sector shows 40% job displacement from AI automation"},
            {"id": "i2_2", "name": "Reskilling has 60% success rate", "type": "Insight", "wave": 2, 
             "full_text": "Corporate reskilling programs achieve ~60% success rate for job retention"},
             
            {"id": "eq2_1", "name": "What factors determine reskilling success?", "type": "EmergentQuestion", "wave": 2, 
             "full_text": "What specific factors determine whether reskilling programs succeed or fail?"},
            
            # Wave 3: Deep dive based on second wave questions  
            {"id": "s3_1", "name": "Successful reskilling factors", "type": "Search", "wave": 3, 
             "full_text": "Search for factors in successful reskilling programs", 
             "details": {"query": "factors successful worker reskilling programs", "driven_by": "What factors determine reskilling success?"}},
             
            {"id": "d3_1", "name": "Reskilling success factors analysis", "type": "DataPoint", "wave": 3,
             "full_text": "Comprehensive analysis of factors contributing to reskilling program success"},
             
            {"id": "i3_1", "name": "Early intervention key success factor", "type": "Insight", "wave": 3, 
             "full_text": "Early intervention before job displacement is critical for reskilling success"},
             
            {"id": "eq3_1", "name": "How to implement early intervention?", "type": "EmergentQuestion", "wave": 3, 
             "full_text": "How can organizations implement early intervention reskilling before displacement occurs?"}
        ],
        "edges": [
            # AnalyticGoal generates investigation questions
            {"source": "analytic_goal", "target": "q1_1", "type": "GENERATES"},
            {"source": "analytic_goal", "target": "q1_2", "type": "GENERATES"},
            
            # Investigation questions lead to searches
            {"source": "q1_1", "target": "s1_1", "type": "LEADS_TO"},
            {"source": "q1_2", "target": "s1_2", "type": "LEADS_TO"},
            
            # Searches produce data
            {"source": "s1_1", "target": "d1_1", "type": "PRODUCES"},
            {"source": "s1_1", "target": "d1_2", "type": "PRODUCES"},
            {"source": "s1_2", "target": "d1_1", "type": "PRODUCES"},
            {"source": "s1_2", "target": "d1_2", "type": "PRODUCES"},
            
            # Data supports insights
            {"source": "d1_1", "target": "i1_1", "type": "SUPPORTS"},
            {"source": "d1_2", "target": "i1_1", "type": "SUPPORTS"},
            {"source": "d1_1", "target": "i1_2", "type": "SUPPORTS"},
            {"source": "d1_2", "target": "i1_2", "type": "SUPPORTS"},
            
            # Insights spawn emergent questions
            {"source": "i1_1", "target": "eq1_1", "type": "SPAWNS"},
            {"source": "i1_2", "target": "eq1_2", "type": "SPAWNS"},
            
            # Wave 2: Emergent questions lead to new searches
            {"source": "eq1_1", "target": "s2_1", "type": "LEADS_TO"},
            {"source": "eq1_2", "target": "s2_2", "type": "LEADS_TO"},
            
            # Wave 2: Searches produce data
            {"source": "s2_1", "target": "d2_1", "type": "PRODUCES"},
            {"source": "s2_2", "target": "d2_2", "type": "PRODUCES"},
            
            # Wave 2: Data supports insights
            {"source": "d2_1", "target": "i2_1", "type": "SUPPORTS"},
            {"source": "d2_2", "target": "i2_2", "type": "SUPPORTS"},
            
            # Wave 2: Insights spawn new emergent questions
            {"source": "i2_2", "target": "eq2_1", "type": "SPAWNS"},
            
            # Wave 3: Emergent question leads to search
            {"source": "eq2_1", "target": "s3_1", "type": "LEADS_TO"},
            
            # Wave 3: Search produces data
            {"source": "s3_1", "target": "d3_1", "type": "PRODUCES"},
            
            # Wave 3: Data supports insight
            {"source": "d3_1", "target": "i3_1", "type": "SUPPORTS"},
            
            # Wave 3: Insight spawns final emergent question
            {"source": "i3_1", "target": "eq3_1", "type": "SPAWNS"}
        ]
    }
    
    # Generate hierarchical visualization
    html_file = "demo_wave_hierarchy.html"
    visualizer.save_wave_hierarchy_visualization(
        html_file,
        wave_data=demo_wave_data,
        investigation_title="Demo: AI Employment Impact Wave Investigation"
    )
    
    print(f"Demo network wave visualization created: {html_file}")
    print("\nInvestigation Flow Network:")
    print("AnalyticGoal: AI Employment Impact")
    print(" -> InvestigationQuestions: AI impacts, workforce adaptation")
    print(" -> Searches: Employment studies, automation trends")
    print(" -> DataPoints: McKinsey report, MIT study")
    print(" -> Insights: Routine jobs displaced, reskilling accelerating")
    print(" -> EmergentQuestions: Which sectors? Reskilling effectiveness?")
    print(" -> Wave 2 Searches: Manufacturing impact, reskilling outcomes")
    print(" -> Wave 2 DataPoints: Displacement data, success rates")
    print(" -> Wave 2 Insights: Manufacturing leads, 60% success rate")
    print(" -> Wave 2 EmergentQuestions: Success factors?")
    print(" -> Wave 3 Searches: Success factors analysis")
    print(" -> Wave 3 DataPoints: Reskilling factors data")
    print(" -> Wave 3 Insights: Early intervention key")
    print(" -> Wave 3 EmergentQuestions: Implementation strategies?")
    print("\nOpen the HTML file in your browser to see the interactive network visualization!")
    print("The visualization shows the complete investigation flow without Wave nodes.")
    print("Waves are computational cycles that generate the nodes, not part of the visualization.")

if __name__ == "__main__":
    create_demo_hierarchy()