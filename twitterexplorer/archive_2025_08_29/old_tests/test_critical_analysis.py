"""Critical analysis of the rejection feedback system"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
twitterexplorer_path = os.path.join(current_dir, 'twitterexplorer')
sys.path.insert(0, twitterexplorer_path)

from investigation_engine import InvestigationEngine, InvestigationConfig

def critical_analysis():
    """Run investigation and critically analyze the rejection feedback"""
    
    print("=== CRITICAL ANALYSIS OF REJECTION FEEDBACK ===\n")
    
    api_key = "d72bcd77e2msh76c7e6cf37f0b89p1c51bcjsnaad0f6b01e4f"
    engine = InvestigationEngine(api_key)
    
    # Track what really happens
    strategies_generated = []
    rejections_created = []
    findings_saved = []
    
    original_generate = engine._generate_strategy
    original_analyze = engine._analyze_round_results_with_llm
    
    def track_strategy(session):
        result = original_generate(session)
        
        # Check if rejection context was actually used
        rejection_context_used = False
        if session.rejection_feedback_history:
            rejection_context_used = True
            recent = session.rejection_feedback_history[-1]
            strategies_generated.append({
                'round': len(strategies_generated) + 1,
                'rejection_context_available': True,
                'rejection_rate': recent.rejection_rate,
                'searches': result.get('searches', [])
            })
        else:
            strategies_generated.append({
                'round': len(strategies_generated) + 1,
                'rejection_context_available': False,
                'searches': result.get('searches', [])
            })
        
        return result
    
    def track_analysis(session, current_round, results):
        # Count before
        findings_before = len(session.accumulated_findings)
        
        # Call original
        original_analyze(session, current_round, results)
        
        # Count after
        findings_after = len(session.accumulated_findings)
        findings_added = findings_after - findings_before
        
        # Track rejection
        if session.rejection_feedback_history:
            recent = session.rejection_feedback_history[-1]
            rejections_created.append({
                'round': current_round.round_number,
                'evaluated': recent.total_evaluated,
                'accepted': recent.total_accepted,
                'rejected': recent.total_rejected,
                'rate': recent.rejection_rate
            })
        
        findings_saved.append({
            'round': current_round.round_number,
            'findings_added': findings_added,
            'total_findings': findings_after
        })
    
    engine._generate_strategy = track_strategy
    engine._analyze_round_results_with_llm = track_analysis
    
    # Run investigation
    config = InvestigationConfig(
        max_searches=9,  # 3 rounds of 3 searches
        pages_per_search=1
    )
    
    result = engine.conduct_investigation(
        "controversial tech CEO decisions about content moderation",
        config
    )
    
    # CRITICAL ANALYSIS
    print("\n" + "="*60)
    print("CRITICAL ANALYSIS RESULTS")
    print("="*60)
    
    print("\n1. STRATEGY GENERATION:")
    print(f"   Total strategies generated: {len(strategies_generated)}")
    for s in strategies_generated:
        print(f"   Round {s['round']}: Rejection context available: {s['rejection_context_available']}")
        if s['rejection_context_available']:
            print(f"      Previous rejection rate: {s['rejection_rate']:.1%}")
    
    print("\n2. REJECTION FEEDBACK:")
    print(f"   Total rejection rounds: {len(rejections_created)}")
    for r in rejections_created:
        print(f"   Round {r['round']}: {r['evaluated']} evaluated, {r['accepted']} accepted, {r['rejected']} rejected ({r['rate']:.1%})")
    
    print("\n3. FINDINGS ACCUMULATION:")
    print(f"   Total findings rounds: {len(findings_saved)}")
    for f in findings_saved:
        print(f"   Round {f['round']}: {f['findings_added']} new findings (total: {f['total_findings']})")
    
    print("\n" + "="*60)
    print("CRITICAL ISSUES IDENTIFIED:")
    print("="*60)
    
    issues = []
    
    # Issue 1: Did rejection feedback actually get used?
    if len(strategies_generated) > 1:
        contexts_used = sum(1 for s in strategies_generated if s['rejection_context_available'])
        if contexts_used == 0:
            issues.append("Rejection context never available when generating strategies")
        elif contexts_used < len(strategies_generated) - 1:
            issues.append(f"Rejection context only used in {contexts_used}/{len(strategies_generated)-1} subsequent rounds")
    
    # Issue 2: Are findings actually being created?
    total_findings = sum(f['findings_added'] for f in findings_saved)
    if total_findings == 0:
        issues.append("NO FINDINGS CREATED despite accepting results")
    
    # Issue 3: Is rejection rate improving?
    if len(rejections_created) > 1:
        first_rate = rejections_created[0]['rate']
        last_rate = rejections_created[-1]['rate']
        if last_rate >= first_rate:
            issues.append(f"Rejection rate not improving ({first_rate:.1%} -> {last_rate:.1%})")
    
    # Issue 4: Is the system actually iterating?
    if len(strategies_generated) == 1:
        issues.append("System only generated ONE strategy (no iteration)")
    
    if issues:
        print("\nISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("\n   No major issues found")
    
    print("\n" + "="*60)
    print("FINAL VERDICT:")
    print("="*60)
    
    if total_findings == 0:
        print("   CRITICAL FAILURE: System accepts results but creates no findings")
        print("   The rejection feedback is working but the finding creation is broken")
    elif len(strategies_generated) == 1:
        print("   FAILURE: System not iterating despite max_searches allowing it")
        print("   The rejection feedback can't help if there's only one round")
    elif contexts_used < len(strategies_generated) - 1:
        print("   PARTIAL SUCCESS: Rejection feedback exists but not always used")
    else:
        print("   SUCCESS: Rejection feedback integrated and functioning")
    
    return {
        'strategies': strategies_generated,
        'rejections': rejections_created,
        'findings': findings_saved,
        'issues': issues
    }

if __name__ == "__main__":
    critical_analysis()