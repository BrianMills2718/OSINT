# Development Instructions - TwitterExplorer Comprehensive Streamlit Interface
# YOU MUST FOLLOW THESE EXACT INSTRUCTIONS

## CRITICAL DEVELOPMENT PRINCIPLES (MANDATORY)
- **NO LAZY IMPLEMENTATIONS**: No mocking/stubs/fallbacks/pseudo-code/simplified implementations
- **FAIL-FAST PRINCIPLES**: Surface errors immediately, don't hide them  
- **EVIDENCE-BASED DEVELOPMENT**: All claims require raw evidence in structured evidence files
- **TEST-DRIVEN DESIGN**: Write tests first, then implementation to pass tests

## API Configuration
- **LLM Model**: User-configurable via models.yaml (OpenAI/Gemini switching)
- **API Keys Location**: `C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml`
  - GEMINI_API_KEY: For LLM operations
  - RAPIDAPI_KEY: For Twitter API calls
  - OPENAI_API_KEY: For OpenAI operations

## Current System Status (EVIDENCE-BASED)

### ✅ COMPLETED COMPONENTS (All Working)
- **Complete architectural integration** with bridge pattern working
- **LiteLLM multi-provider support** at client level  
- **Full investigation pipeline**: API Results → DataPoints → Insights → EmergentQuestions
- **Graph state working**: 6 node types, 5 edge types, SPAWNS edges
- **Model configuration system**: User-configurable OpenAI/Gemini switching via YAML
- **Bridge integration**: ConcreteInvestigationBridge connecting dual intelligence systems
- **Comprehensive reporting**: KnowledgeBuilder + SatisfactionAssessor for final reports

### ❌ CURRENT PROBLEM: Outdated Streamlit Interface
- **Streamlit app**: Written months ago, missing all architectural improvements
- **Missing components**: Bridge integration, complete 6-node ontology, model configuration
- **Visualization**: Basic pyvis (static) instead of interactive D3.js hierarchical graphs
- **User experience**: No real-time updates, manual provider switching requires code changes

## TASK: Build New Comprehensive Streamlit App from Scratch

### Technical Requirements Analysis

**✅ D3.js Integration**: Validated feasible via `streamlit.components.v1.html()`
**✅ Real-time Updates**: Multiple proven patterns (`st.empty()`, update loops, session state)
**✅ Model Configuration**: Existing LLMModelManager system ready for UI integration  
**✅ Investigation Engine**: Current investigation_engine.py with all improvements ready

### New Streamlit App Architecture

**Comprehensive Interface Design**:
```
streamlit_app_modern.py
├── 🔧 Configuration Panel
│   ├── Model Provider Selection (OpenAI/Gemini/Custom)
│   ├── Investigation Settings (max_searches, satisfaction_threshold)
│   ├── Real-time Display Options
│   └── Export/Import Settings
│
├── 🎯 Investigation Control Center  
│   ├── Query Input & Validation
│   ├── Start/Stop/Pause Controls
│   ├── Progress Indicators
│   └── Session Management
│
├── 📊 Live D3.js Visualization Panel
│   ├── Real-time Graph Updates (st.empty() + custom component)
│   ├── Interactive Node Dragging/Zooming
│   ├── Edge Hover Information
│   ├── Hierarchical Layout Engine
│   └── Export Graph Functionality
│
├── 📈 Real-time Progress Stream
│   ├── Search Attempt Details
│   ├── Finding Evaluations  
│   ├── Insight Generation Tracking
│   ├── EmergentQuestion Detection
│   └── Satisfaction Score Updates
│
└── 📋 Final Results Dashboard
    ├── Comprehensive Knowledge Summary
    ├── Satisfaction Analysis Report
    ├── Cross-Reference Analysis
    ├── Investigation Recommendations
    └── Export Options (JSON/Markdown/HTML)
```

### Implementation Plan

#### Phase 1: Foundation & Configuration UI (Day 1)

**Core App Structure**:
- Create new `streamlit_app_modern.py` using current investigation_engine.py
- Implement model configuration UI with real-time provider switching
- Set up basic investigation runner with progress tracking
- Test end-to-end with current architectural improvements

**Key Components**:
```python
# Model Configuration UI
def render_model_config_panel():
    st.sidebar.header("🤖 Model Configuration")
    
    provider = st.sidebar.selectbox(
        "Provider", ["openai", "gemini", "custom"],
        help="Select LLM provider for investigation"
    )
    
    if provider == "custom":
        # Allow manual model specification
        pass
    else:
        # Use predefined configurations
        pass
        
# Investigation Control
def render_investigation_controls():
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        query = st.text_input("Investigation Query")
    
    with col2:
        if st.button("🔍 Start Investigation"):
            run_investigation(query)
    
    with col3:
        if st.button("⏹️ Stop"):
            stop_investigation()
```

#### Phase 2: D3.js Integration & Real-time Updates (Day 1-2)

**D3.js Component Integration**:
```python
def render_investigation_graph(graph_data, height=600):
    # Port our existing interactive_ontology_graph.html to Streamlit component
    d3_html = f"""
    <div id="investigation-graph" style="height: {height}px;"></div>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const graphData = {json.dumps(graph_data)};
        // Hierarchical D3.js graph with drag, zoom, hover tooltips
        // (Use our proven interactive_ontology_graph.html implementation)
    </script>
    """
    components.html(d3_html, height=height)

# Real-time Updates Pattern
def run_live_investigation():
    graph_container = st.empty()
    progress_container = st.empty()
    
    while session.is_active:
        with graph_container.container():
            render_investigation_graph(session.graph.to_dict())
        
        with progress_container.container():
            display_investigation_progress(session)
            
        time.sleep(1)  # Update every second
```

**State Management**:
```python
# Session State for Investigation Persistence
if 'investigation_engine' not in st.session_state:
    st.session_state.investigation_engine = InvestigationEngine()
    st.session_state.current_session = None
    st.session_state.model_config = load_model_config()
    st.session_state.graph_data = None
```

#### Phase 3: Advanced Reporting & Features (Day 2-3)

**Comprehensive Final Reports**:
- Integrate existing KnowledgeBuilder.generate_knowledge_summary()  
- Use SatisfactionAssessor.generate_satisfaction_report()
- Add investigation recommendations and cross-reference analysis
- Implement multiple export formats (JSON, Markdown, HTML)

**Session Management**:
- Save/load investigation sessions
- Investigation history browser  
- Resume interrupted investigations
- Export/import investigation data

#### Step 4: Polish & Testing (Day 3)

**Performance & UX**:
- Real-time update optimization
- Error handling and edge cases
- User experience refinements  
- Integration testing with real investigations

### Success Criteria (Evidence-Based)

**Required Outcomes**:
- ✅ **Unified Interface**: Single comprehensive app for all TwitterExplorer functionality  
- ✅ **Real-time Visualization**: Live D3.js hierarchical graph updates during investigation
- ✅ **Model Configuration UI**: User-friendly provider switching (no code changes required)
- ✅ **Complete Pipeline**: Uses current investigation_engine.py with all architectural improvements
- ✅ **Comprehensive Reports**: Integration of KnowledgeBuilder and SatisfactionAssessor systems
- ✅ **Session Management**: Save/load/resume investigations with persistent state
- ✅ **Export Functionality**: Multiple formats (JSON/Markdown/HTML) for sharing results

### Expected User Experience Improvements

1. **Single Interface**: Everything in one place (no separate HTML files)
2. **Live Updates**: Watch investigation progress in real-time with interactive graph
3. **Easy Configuration**: Switch providers/models via UI dropdowns 
4. **Better Visualization**: D3.js interactivity integrated within Streamlit interface
5. **Complete Analysis**: Built-in comprehensive final reports and recommendations
6. **Session Persistence**: Save investigations and resume later
7. **Professional Export**: Share results in multiple formats

### Evidence Requirements

**Must demonstrate**:
1. **Real-time D3.js integration** working in Streamlit environment
2. **Model configuration UI** successfully switching providers without restart
3. **Complete investigation pipeline** using all current architectural components  
4. **Live progress updates** showing search attempts, findings, insights, emergent questions
5. **Comprehensive final reporting** matching or exceeding existing analysis capabilities
6. **Session management** with save/load/resume functionality working

### Current System Integration

**Existing Components to Use**:
```python
# Use current working components directly
from investigation_engine import InvestigationEngine, InvestigationConfig
from llm_model_manager import LLMModelManager
from knowledge_builder import KnowledgeBuilder  
from satisfaction_assessor import SatisfactionAssessor
from investigation_bridge import ConcreteInvestigationBridge
from graph_aware_llm_coordinator import GraphAwareLLMCoordinator
from realtime_insight_synthesizer import RealTimeInsightSynthesizer
```

**Current Configuration Working**:
```yaml  
# config/models.yaml (already exists and working)
default_provider: openai
models:
  strategic_coordinator: "gpt-4o-mini"
  finding_evaluator: "gpt-4o-mini"
  insight_synthesizer: "gpt-4o-mini"
  emergent_questions: "gpt-4o-mini"
  cross_reference: "gpt-4o-mini"
  temporal_analysis: "gpt-4o-mini"
  fallback_primary: "gpt-3.5-turbo"
  fallback_secondary: "gemini/gemini-2.5-flash"
```

### Validation Commands

**Test current system integration**:
```bash
# Test investigation engine with current improvements
python -c "
from twitterexplorer.investigation_engine import InvestigationEngine
from twitterexplorer.llm_model_manager import LLMModelManager

# Test model configuration loading
manager = LLMModelManager()
print('Model manager loaded:', manager.get_current_config_summary())

# Test investigation engine initialization  
engine = InvestigationEngine()
print('Investigation engine initialized with bridge:', hasattr(engine, 'integration_bridge'))
print('✅ All components ready for Streamlit integration')
"
```

**Test D3.js component generation**:
```bash
# Test D3.js HTML component generation
python -c "
import json
from twitterexplorer.investigation_graph import InvestigationGraph

# Test graph data export for D3.js
graph = InvestigationGraph()
test_data = {
    'nodes': [{'id': 'test', 'type': 'AnalyticQuestion', 'label': 'Test Node'}],
    'edges': [{'source': 'test', 'target': 'test2', 'type': 'MOTIVATES'}]
}
print('Graph data ready for D3.js:', json.dumps(test_data, indent=2))
print('✅ D3.js integration data format validated')
"
```

**Streamlit development server test**:
```bash
# Test Streamlit development environment
streamlit --version
echo '✅ Streamlit ready for development'
```

## DO NOT
❌ Use old outdated Streamlit app as base
❌ Skip real-time D3.js integration  
❌ Hardcode model configurations in new app
❌ Miss any current architectural improvements
❌ Skip comprehensive final reporting integration

## DO  
✅ Build completely new Streamlit app from scratch
✅ Integrate all current working components (investigation engine, bridge, model manager)
✅ Implement real-time D3.js hierarchical graph visualization
✅ Create user-friendly model configuration interface
✅ Include comprehensive reporting (KnowledgeBuilder, SatisfactionAssessor)
✅ Add session management and export functionality
✅ Test end-to-end with real investigations to validate all improvements
