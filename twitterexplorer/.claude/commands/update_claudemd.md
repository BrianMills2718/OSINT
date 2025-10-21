# CLAUDE.md Update Command - Evidence-Based Development Workflow

## Overview
Update CLAUDE.md to clear out resolved tasks and populate it with instructions for resolving the next tasks using evidence-based and TDD development practices. The instructions should be detailed enough for a new LLM to implement with no context beyond CLAUDE.md and referenced files.

## Core CLAUDE.md Requirements
### dont include any production readiness i.e. Docker or enterprise features
### always use litellm with real structured output with gemini-2.5-flash with api keys here C:\Users\Brian\projects\twitterexplorer\twitterexplorer\.streamlit\secrets.toml
### Always use a test driven design approach whenever possible

### 1. Coding Philosophy Section (Mandatory)

Every CLAUDE.md must include:
- **NO LAZY IMPLEMENTATIONS**: No mocking/stubs/fallbacks/pseudo-code/simplified implementations
- **FAIL-FAST PRINCIPLES**: Surface errors immediately, don't hide them
- **EVIDENCE-BASED DEVELOPMENT**: All claims require raw evidence in structured evidence files

### 2. Codebase Structure Section (Mandatory)  
Concisely document:
- Key entry points and main orchestration files
- Module organization and responsibilities
- Important integration points (ResourceOrchestrator, healing_integration.py, etc.)

### 3. Evidence Structure Requirements
**CURRENT PRACTICE**: Use structured evidence organization instead of single Evidence.md:

```
evidence/
├── current/
│   └── Evidence_[PHASE]_[TASK].md     # Current development phase only
├── completed/  
│   └── Evidence_[PHASE]_[TASK].md     # 
Completed phases (archived)
└── doublecheck/
    └── doublecheck_results/      # doublecheck outputs
```

**CRITICAL**: 
- Evidence files must contain ONLY current phase work
- Raw execution logs required for all claims
- No success declarations without demonstrable proof
- Archive completed phases to avoid chronological confusion

## Workflow Process

### Task Implementation Order
1. **Implement tasks** following CLAUDE.md instructions
2. **Document evidence** in `evidence/current/Evidence_[PHASE]_[TASK].md`
3. **Include raw logs** for all validation steps
4. **Test thoroughly** - assume nothing works until proven

**CRITICAL**: 
- Evidence files must contain ONLY current phase work
- Raw execution logs required for all claims
- No success declarations without demonstrable proof
- Archive completed phases to avoid chronological confusion

