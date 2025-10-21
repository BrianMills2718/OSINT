# Insight Generation Pipeline - Debugging Reference

## Overview
This document consolidates all insight-related prompts and schemas scattered across the codebase to aid in debugging Issue #2 (Untitled Insight Generation).

**Problem**: System produces insights with "No Title" and "No Confidence" despite enhanced prompts and schema definitions.

## Pipeline Flow

```
1. Investigation Query
   ↓
2. API Results → DataPoints (finding_evaluator_llm.py)
   ↓
3. DataPoint Accumulation (realtime_insight_synthesizer.py)
   ↓
4. Synthesis Decision (SynthesisDecision schema + prompt)
   ↓
5. Semantic Grouping (SemanticGrouping schema + prompt)
   ↓
6. Insight Synthesis (InsightSynthesis schema + enhanced prompt)
   ↓
7. Node Creation (investigation_graph.py InsightNode)
   ↓
8. Graph Export (JSON serialization)
```

## Key Components Analysis

### 1. InsightSynthesis Schema (realtime_insight_synthesizer.py:41)

```python
class InsightSynthesis(BaseModel):
    """Synthesized insight with structured metadata"""
    title: str = Field(description="Concise insight title")
    content: str = Field(description="Detailed insight content")  
    confidence_level: float = Field(description="Confidence 0.0-1.0")
    pattern_type: str = Field(description="Type: contradiction, trend, connection, implication")
    key_evidence: List[str] = Field(description="Supporting evidence snippets")
    investigation_relevance: float = Field(description="0-1 relevance to investigation goal")
```

**Status**: ✅ Schema properly defines title and confidence_level fields

### 2. Enhanced Insight Synthesis Prompt (realtime_insight_synthesizer.py:358)

```python
prompt = f"""
INVESTIGATION: {self.context.analytic_question}

RELATED FINDINGS:
{chr(10).join(f"- {content}" for content in content_items)}

TASK: Synthesize ONE key insight connecting these findings.

REQUIREMENTS:
- title: Create a concise, descriptive title (5-10 words) that captures the main insight
- content: Detailed explanation of the insight and its significance
- confidence_level: Rate your confidence 0.0-1.0 based on evidence strength
- pattern_type: Choose from: "contradiction", "trend", "connection", "implication" 
- key_evidence: List 2-3 specific evidence snippets supporting the insight
- investigation_relevance: Rate 0.0-1.0 relevance to investigation goal

Focus on:
- Patterns advancing understanding of: "{self.context.analytic_question}"
- Contradictions or conflicts between sources
- Significant implications for investigation goal
- Emerging themes relevant to investigation

EXAMPLES of good titles:
- "Testing Framework Adoption Accelerating"
- "API Query Patterns Show Complexity Growth"  
- "User Behavior Contradicts Stated Preferences"

IGNORE: Content unrelated to "{self.context.analytic_question}"
"""
```

**Status**: ✅ Prompt explicitly requests titles and confidence with examples

### 3. InsightNode Constructor (investigation_graph.py:149)

```python
class InsightNode(Node):
    """Insight or pattern derived from analysis of data points"""
    def __init__(self, content: str, insight_type: str, **kwargs):
        super().__init__(
            id=str(uuid.uuid4()),
            node_type="Insight",
            properties={"content": content, "insight_type": insight_type, **kwargs},
            created_at=datetime.now()
        )
```

**Status**: ✅ Constructor accepts kwargs and adds them to properties

### 4. Node Creation Call (realtime_insight_synthesizer.py:420)

```python
insight_node = self.graph.create_insight_node(
    content=insight.content,
    insight_type=insight.pattern_type,
    title=insight.title,                    # ← ADDED
    confidence=insight.confidence_level,    # ← ADDED
    investigation_relevance=insight.investigation_relevance,
    key_evidence=insight.key_evidence
)
```

**Status**: ✅ Properties passed as kwargs to constructor

## Debugging Checkpoints

### Checkpoint 1: LLM Response Structure
**Location**: `_synthesize_group_insight()` method after LLM call
**Test**: Log raw LLM response to verify structured output parsing

```python
response = self.llm.completion(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    response_format=InsightSynthesis
)

# DEBUG: Log the raw response
print(f"DEBUG - Raw LLM Response: {response.choices[0].message.parsed}")
```

### Checkpoint 2: InsightSynthesis Object
**Location**: After `response.choices[0].message.parsed` 
**Test**: Verify InsightSynthesis object has proper title and confidence

```python
insight = response.choices[0].message.parsed
print(f"DEBUG - Insight Title: '{insight.title}'")  
print(f"DEBUG - Insight Confidence: {insight.confidence_level}")
```

### Checkpoint 3: Node Property Setting
**Location**: `_create_insight_node()` method after node creation
**Test**: Verify properties are set on the node object

```python
insight_node = self.graph.create_insight_node(...)
print(f"DEBUG - Node Properties: {insight_node.properties}")
print(f"DEBUG - Node Title: {insight_node.properties.get('title', 'MISSING')}")
```

### Checkpoint 4: Graph Export
**Location**: After graph export to JSON
**Test**: Check JSON file for property persistence

```python
# In graph file:
{
  "nodes": {
    "insight_id": {
      "node_type": "Insight", 
      "properties": {
        "content": "...",
        "title": "Should be here",
        "confidence": "Should be numeric"
      }
    }
  }
}
```

## Failure Analysis

### Current Evidence
- ✅ Schema defines title/confidence fields correctly
- ✅ Prompt explicitly requests titles with examples
- ✅ Node constructor accepts kwargs
- ✅ Properties passed as kwargs to constructor
- ❌ **Graph export shows "No Title" and "No Confidence"**

### Hypothesis: Failure Points
1. **LLM Response Parsing**: Structured output not generating proper fields
2. **Property Assignment**: kwargs not reaching node properties correctly
3. **Serialization**: Properties lost during JSON export
4. **Display Logic**: CLI showing wrong property names

### Next Investigation Steps
1. Add logging at each checkpoint above
2. Run single insight synthesis with full debug output
3. Compare working vs broken insight generation
4. Validate LLM model capability for structured output

## Related Files Reference

**Schema Definitions**:
- `realtime_insight_synthesizer.py:41` - InsightSynthesis 
- `graph_aware_llm_coordinator.py:39` - EmergentQuestion
- `llm_client.py:300` - EmergentQuestion (duplicate)

**Prompt Definitions**:
- `realtime_insight_synthesizer.py:358` - Insight synthesis (enhanced)
- `realtime_insight_synthesizer.py:298` - Semantic grouping
- `realtime_insight_synthesizer.py:202` - Synthesis decision

**Node Creation**:
- `investigation_graph.py:149` - InsightNode class
- `investigation_graph.py:240` - create_insight_node method
- `realtime_insight_synthesizer.py:420` - _create_insight_node call

**Testing Tools**:
- `audit_prompts_schemas.py` - Comprehensive prompt/schema audit
- `check_insights.py` - Quick insight analysis from graph files
- `validate_fixes.py` - Issue validation framework

---

*This consolidated view enables focused debugging of the insight generation pipeline without tracing across 5 scattered files.*