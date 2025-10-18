# AI Research Assistant Guide

## 🤖 Overview

The AI Research Assistant is a new feature that allows you to ask natural language questions and have AI automatically:
1. Generate appropriate search queries for ClearanceJobs, DVIDS, and SAM.gov
2. Execute those queries across all relevant databases
3. Summarize the results in the context of your original research question

## ✨ Key Features

- **Natural Language Input**: Ask questions in plain English
- **Multi-Database Search**: Automatically searches across all 3 databases
- **Intelligent Query Generation**: AI determines the best search parameters for each database
- **Contextual Summarization**: Results are summarized in relation to your research question
- **Detailed Results**: Access full results from each database
- **Export Capabilities**: Download results from each database as CSV

## 🔑 Requirements

### OpenAI API Key
You need an OpenAI API key to use this feature:

1. Go to: https://platform.openai.com/api-keys
2. Create a new API key
3. Add it to your `.env` file:

```bash
OPENAI_API_KEY=sk-proj-...your-key-here...
```

### Other API Keys (Optional)
- **DVIDS API Key**: Required for DVIDS searches
- **SAM.gov API Key**: Required for SAM.gov searches
- **ClearanceJobs**: No API key needed

If you don't provide DVIDS or SAM.gov API keys, the AI will still search ClearanceJobs and inform you that those databases couldn't be accessed.

## 📖 How to Use

### 1. Access the AI Research Tab

Run the unified search app:
```bash
streamlit run unified_search_app.py
```

Navigate to the **🤖 AI Research** tab.

### 2. Ask Your Research Question

Type your research question in natural language. Examples:

**Good Research Questions:**
- "What cybersecurity job opportunities are available for cleared professionals?"
- "Find recent military operations in the Middle East and related government contracts"
- "Show me AI security positions and relevant DoD contracts"
- "What government contracting opportunities exist for small businesses in cloud computing?"

**Tips for Better Results:**
- Be specific about what you're looking for
- Include relevant keywords (e.g., "cybersecurity", "DoD", "Top Secret clearance")
- Mention time frames if relevant (e.g., "recent", "in the last 30 days")
- Specify scope (e.g., "small business set-aside contracts")

### 3. Review the Search Strategy

After you click **🚀 Research**, the AI will:
- Display the overall search strategy
- Show which databases are relevant to your question
- Explain the reasoning for each database search

Example output:
```
Overall Strategy: Search for cybersecurity jobs requiring clearances,
related military cyber news, and government cyber security contracts.

🏢 ClearanceJobs: Keywords: cybersecurity security
   Reasoning: Searching for cleared cybersecurity positions

📸 DVIDS: Keywords: cyber security operations
   Reasoning: Looking for recent military cyber security news

📋 SAM.gov: Keywords: cybersecurity
   Reasoning: Finding active government cybersecurity contracts
```

### 4. View the AI Summary

The AI will analyze all results and provide a comprehensive summary that:
- Directly answers your research question
- Highlights key findings from each database
- Notes patterns and connections across databases
- Identifies gaps or areas needing further investigation
- Provides specific examples from the results

### 5. Explore Detailed Results

Below the summary, you can expand each database's results to see:
- Full result listings
- Links to original sources
- Metadata (dates, organizations, etc.)
- Export options (CSV download)

## 🎯 Example Use Cases

### Use Case 1: Job + Contract Research
**Question:** "What opportunities exist for cleared professionals working on AI security?"

**What the AI does:**
- Searches ClearanceJobs for AI security positions requiring clearances
- Searches DVIDS for military AI security initiatives
- Searches SAM.gov for AI security contracts
- Summarizes how the jobs, news, and contracts relate to each other

### Use Case 2: Market Research
**Question:** "What small business opportunities exist in cloud computing for the DoD?"

**What the AI does:**
- Searches SAM.gov specifically for small business set-aside contracts
- Filters for DoD contracts in cloud computing
- Summarizes the types of work, agencies involved, and deadlines

### Use Case 3: Threat Intelligence Research
**Question:** "What recent developments have there been in military cyber operations?"

**What the AI does:**
- Searches DVIDS for recent cyber operations news
- Looks for related job openings in ClearanceJobs
- Finds government contracts related to cyber operations
- Provides a comprehensive overview of the current landscape

## ⚙️ Configuration

### Results Per Database
You can control how many results are fetched from each database (5-50 results).
- **Lower values (5-10)**: Faster, more focused results
- **Higher values (25-50)**: More comprehensive, but slower

### Model Used
The AI Research Assistant uses OpenAI's **gpt-5-mini** model via litellm for:
- Query generation
- Result summarization

This model provides a good balance of:
- Speed (fast responses)
- Cost (economical)
- Quality (structured outputs)

## 💡 Tips for Best Results

### 1. Be Specific But Not Too Narrow
❌ **Too Broad:** "Show me jobs"
✅ **Good:** "Show me cybersecurity jobs requiring Top Secret clearance"

### 2. Include Context
❌ **Lacks Context:** "Find contracts"
✅ **Good:** "Find DoD contracts for cloud migration in the last 30 days"

### 3. Combine Multiple Aspects
✅ **Good:** "What job opportunities and government contracts exist for cleared professionals working on quantum computing?"

### 4. Ask Follow-Up Questions
After reviewing results, you can ask more specific follow-up questions to drill down further.

## 📊 Understanding the Results

### Search Strategy Section
- Shows which databases were searched and why
- Displays the keywords used for each database
- Explains the reasoning behind each search

### AI Summary Section
- High-level overview of findings
- Key insights across all databases
- Patterns and connections
- Recommendations for further research

### Detailed Results Section
- Expandable sections for each database
- Full result listings with metadata
- Links to original sources
- CSV export for each database

## 🔧 Troubleshooting

### "OpenAI API Key Required" Error
**Problem:** The AI Research tab shows an error about missing OpenAI API key.

**Solution:**
```bash
# Create or edit .env file
echo "OPENAI_API_KEY=your-key-here" > .env
```

### No Results from DVIDS or SAM.gov
**Problem:** ClearanceJobs works but DVIDS/SAM.gov show errors.

**Solution:** Add your API keys to the sidebar:
- DVIDS API Key
- SAM.gov API Key

### AI Summary is Too Generic
**Problem:** The summary doesn't provide enough detail.

**Solution:**
- Increase "Results per database" to get more data
- Make your research question more specific
- Include more context in your question

### Query Generation Fails
**Problem:** AI fails to generate queries.

**Solution:**
- Check your OpenAI API key is valid
- Verify you have sufficient OpenAI credits
- Check your internet connection
- Try a simpler research question

## 💰 Cost Considerations

### OpenAI API Usage
Each research query makes 2 API calls:
1. **Query Generation**: Generates search parameters (~500-1000 tokens)
2. **Result Summarization**: Summarizes results (~2000-5000 tokens depending on results)

**Estimated Cost per Query:**
- With gpt-5-mini: ~$0.01-0.05 per research query
- Cost varies based on:
  - Complexity of question
  - Number of results returned
  - Length of result data

**Cost Optimization Tips:**
- Start with lower "Results per database" (5-10)
- Use specific questions to reduce token usage
- Review search strategy before executing to ensure relevance

## 🛠️ Technical Details

### Architecture
```
User Question
    ↓
AI Query Generator (gpt-5-mini)
    ↓
Structured Search Parameters
    ↓
Parallel Database Searches
    ├─→ ClearanceJobs
    ├─→ DVIDS
    └─→ SAM.gov
    ↓
Combined Results
    ↓
AI Summarizer (gpt-5-mini)
    ↓
Final Summary + Detailed Results
```

### Code Structure
- **`ai_research.py`**: Main AI research module
  - `generate_search_queries()`: Converts question → search parameters
  - `execute_clearancejobs_search()`: ClearanceJobs search
  - `execute_dvids_search()`: DVIDS search
  - `execute_sam_search()`: SAM.gov search
  - `summarize_results()`: AI result summarization
  - `render_ai_research_tab()`: Streamlit UI

### Dependencies
```python
litellm>=1.0.0        # OpenAI API wrapper
python-dotenv>=1.0.0  # Environment variable management
```

## 📚 Related Documentation

- **User Guide:** `README.md` - Full application documentation
- **Quick Start:** `QUICK_START.md` - Getting started quickly
- **Technical Docs:** `INTEGRATION_ANALYSIS.md` - API integration details
- **UX Improvements:** `UI_IMPROVEMENTS.md` - UI/UX design decisions

## 🚀 Future Enhancements

Potential improvements for future versions:
- [ ] Support for additional databases
- [ ] Query refinement suggestions
- [ ] Result caching to reduce API costs
- [ ] Advanced filtering of AI-generated results
- [ ] Export combined results across all databases
- [ ] Natural language filtering (e.g., "only show recent results")
- [ ] Multi-turn conversations for iterative research

## 📝 Feedback

If you encounter issues or have suggestions for improving the AI Research Assistant, please provide feedback through the project's issue tracker.
