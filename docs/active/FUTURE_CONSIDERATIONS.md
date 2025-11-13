# Future Considerations

## Structured Entity Output
- Idea: replace the current flat entity list with a generic node schema `{name, type, properties}` and optional edges.  
- Benefits: richer graphs, easier downstream consumption, and per-query flexibility.  
- Risks: touches extraction prompts, aggregation logic, reporting, and any downstream tooling. Needs a dedicated refactor + migration plan.
