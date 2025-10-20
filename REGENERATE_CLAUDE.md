# REGENERATE_CLAUDE.md - Instructions for Updating CLAUDE.md

**Purpose**: How to properly regenerate CLAUDE.md from source files
**When to Use**: Rare updates to PERMANENT section (directory changes, new patterns, new principles)
**When NOT to Use**: Normal task updates (just edit CLAUDE.md TEMPORARY section directly)

---

## Understanding the Files

### CLAUDE_PERMANENT.md (Source for PERMANENT section)
- Contains core principles, patterns, and vision
- **Rarely changes** - only for significant updates:
  - Directory structure changes
  - New permanent patterns discovered
  - New principles needed (e.g., new type of systematic failure)
  - Major architectural shifts

### CLAUDE_TEMP.md (Schema/Template for TEMPORARY section)
- **This is a SCHEMA, not actual content**
- Shows structure of TEMPORARY section
- Provides template for what should be in each subsection
- **NOT a file to concatenate** - it's a guide for structure

### CLAUDE.md (Working file)
- Attached to every Claude Code API call
- Has PERMANENT section (from CLAUDE_PERMANENT.md)
- Has TEMPORARY section (current tasks, updated frequently)

---

## When to Regenerate CLAUDE.md

### ✅ Regenerate When (Rare Events):

1. **Directory Structure Changed Significantly**:
   - New top-level directories added
   - Major reorganization of modules
   - Archive structure changed
   - Example: Adding `monitoring/` directory for Phase 1

2. **New Permanent Pattern Discovered**:
   - New integration pattern that should be template
   - New testing approach that's reusable
   - New error handling pattern
   - Example: "Playwright scraping pattern" after ClearanceJobs

3. **New Principle Needed**:
   - New type of systematic failure discovered
   - New "Claude Code optimism" anti-pattern found
   - New circuit breaker condition
   - Example: "Never use max_tokens with gpt-5 models"

4. **Major Architectural Shift**:
   - Core system design changed
   - New layer added (e.g., caching layer)
   - Technology stack changed

### ❌ Do NOT Regenerate For (Normal Work):

- Task completion
- Updating current phase
- Changing next actions
- Resolving blockers
- Phase transitions
- Adding new data source (if follows existing pattern)
- Bug fixes
- Testing individual features

**For normal work**: Just edit CLAUDE.md TEMPORARY section directly

---

## Regeneration Protocol

### Step 1: Decide If Regeneration Needed

Ask these questions:

1. Is this a change to core principles? (Yes → Regenerate)
2. Is this a change to permanent patterns? (Yes → Regenerate)
3. Is this a directory structure update? (Yes → Regenerate)
4. Is this just updating current tasks? (No → Edit CLAUDE.md TEMPORARY only)

**If ANY "Yes" answer**: Proceed with regeneration
**If ALL "No" answers**: Just edit CLAUDE.md TEMPORARY section

### Step 2: Update Source Files

**Option A: Update CLAUDE_PERMANENT.md** (for principle/pattern changes):

1. Read CLAUDE_PERMANENT.md
2. Add/update the relevant section:
   - New principle? → Add to CORE PRINCIPLES with number
   - New pattern? → Add to CODE PATTERNS section
   - Directory change? → Update DIRECTORY STRUCTURE section
   - New workaround? → Add to KNOWN ISSUES section
3. Save CLAUDE_PERMANENT.md

**Option B: Update CLAUDE_TEMP.md** (for schema changes):

- **Rarely needed** - only if TEMPORARY section structure changes
- Example: Adding new top-level section like "DEPENDENCIES"

### Step 3: Read Both Source Files

Before regenerating, Claude Code should:

1. Read CLAUDE_PERMANENT.md (full file)
2. Read CLAUDE_TEMP.md (schema/template)
3. Read current CLAUDE.md TEMPORARY section (to preserve current tasks)

### Step 4: Manually Rewrite CLAUDE.md

**CRITICAL**: Do NOT concatenate files. Manually rewrite using this process:

```
CLAUDE.md =
  [CLAUDE_PERMANENT.md content]
  +
  [Divider: "END OF PERMANENT SECTION"]
  +
  [TEMPORARY section following CLAUDE_TEMP.md structure, populated with current tasks]
  +
  [Divider: "END OF TEMPORARY SECTION"]
```

**Example Process**:

1. **Write PERMANENT section**:
   - Copy all content from CLAUDE_PERMANENT.md
   - Preserve exact formatting
   - Include all sections

2. **Write divider**:
   ```
   **END OF PERMANENT SECTION**
   **Everything above this line NEVER changes**
   **Everything below this line is updated as tasks complete**

   ---
   ```

3. **Write TEMPORARY section**:
   - Use CLAUDE_TEMP.md as structure guide
   - Populate with current tasks from existing CLAUDE.md
   - Follow the schema but use real content
   - Sections to include:
     - Last Updated
     - Current Phase
     - CURRENT STATUS SUMMARY
     - RELATED STATUS & PLANNING
     - CURRENT TASK SCOPE
     - NEXT 3 ACTIONS
     - AFTER COMPLETING THESE 3 ACTIONS
     - IMMEDIATE BLOCKERS
     - CHECKPOINT QUESTIONS
     - CODE PATTERNS FOR CURRENT PHASE
     - UPDATING THIS FILE

4. **Write final divider**:
   ```
   **END OF TEMPORARY SECTION**
   ```

### Step 5: Verify Regenerated CLAUDE.md

**Checklist**:

- [ ] PERMANENT section matches CLAUDE_PERMANENT.md exactly
- [ ] TEMPORARY section follows CLAUDE_TEMP.md structure
- [ ] Current tasks preserved from old CLAUDE.md
- [ ] Next 3 actions still accurate
- [ ] Blockers still listed
- [ ] Checkpoint questions preserved
- [ ] Dividers in place ("END OF PERMANENT SECTION", "END OF TEMPORARY SECTION")
- [ ] File organization info up to date
- [ ] No content lost from old CLAUDE.md

### Step 6: Archive Old CLAUDE.md

```bash
# Create archive with date
mkdir -p archive/YYYY-MM-DD/
cp CLAUDE.md archive/YYYY-MM-DD/CLAUDE_before_regeneration.md

# Add note to archive README
echo "YYYY-MM-DD: Regenerated CLAUDE.md - [Reason for regeneration]" >> archive/YYYY-MM-DD/README.md
```

---

## Example Regeneration Scenarios

### Scenario 1: Directory Structure Changed (Phase 1 Start)

**Trigger**: Adding `monitoring/` directory for Phase 1

**Steps**:

1. **Update CLAUDE_PERMANENT.md**:
   ```
   # In DIRECTORY STRUCTURE section, update tree:
   ├── monitoring/                  # Phase 1: Boolean monitoring
   │   ├── boolean_monitor.py       # BooleanMonitor class
   │   ├── alert_manager.py         # AlertManager class
   │   └── __init__.py
   ```

2. **Read source files**:
   - Read CLAUDE_PERMANENT.md (has updated structure)
   - Read CLAUDE_TEMP.md (schema unchanged)
   - Read current CLAUDE.md TEMPORARY (preserve current tasks)

3. **Regenerate CLAUDE.md**:
   - Write PERMANENT section from CLAUDE_PERMANENT.md (with new directory structure)
   - Write TEMPORARY section following CLAUDE_TEMP.md schema
   - Populate with current tasks

4. **Archive**:
   ```bash
   cp CLAUDE.md archive/2025-10-19/CLAUDE_before_phase1_dir_structure.md
   ```

### Scenario 2: New Permanent Pattern Discovered

**Trigger**: Discovered "Playwright scraping pattern" should be permanent

**Steps**:

1. **Update CLAUDE_PERMANENT.md**:
   ```
   # In CODE PATTERNS section, add:

   ### Playwright Scraping Pattern

   **When to use**: Official API broken or doesn't exist

   **Pattern**:
   ```python
   from playwright.async_api import async_playwright

   async def scrape_with_playwright(url, selectors):
       async with async_playwright() as p:
           browser = await p.chromium.launch(headless=True)
           page = await browser.new_page()
           await page.goto(url)
           # ... scraping logic
   ```

   **After creating**: Test in headless mode, handle timeouts, respect rate limits
   ```

2. **Regenerate CLAUDE.md** following protocol

### Scenario 3: New Principle (Circuit Breaker)

**Trigger**: Discovered new systematic failure pattern

**Steps**:

1. **Update CLAUDE_PERMANENT.md**:
   ```
   # In CORE PRINCIPLES, add new numbered section:

   ### 9. CIRCUIT BREAKERS - HARD STOP CONDITIONS

   **When ANY of these occur, STOP immediately**:
   - Import errors on entry points
   - Repeated timeouts (3+ consecutive)
   - Scope drift
   - ... [details]
   ```

2. **Regenerate CLAUDE.md** following protocol

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Concatenating Files

**WRONG**:
```bash
cat CLAUDE_PERMANENT.md CLAUDE_TEMP.md > CLAUDE.md
```

**Why Wrong**: CLAUDE_TEMP.md is a schema, not content. You'd get placeholder text instead of actual tasks.

**RIGHT**: Read both files, manually write CLAUDE.md using PERMANENT content + TEMP structure + current tasks.

### ❌ Mistake 2: Losing Current Tasks

**WRONG**: Overwrite TEMPORARY section with empty template

**RIGHT**: Preserve current tasks from old CLAUDE.md when regenerating

### ❌ Mistake 3: Regenerating Too Often

**WRONG**: Regenerate every time tasks change

**RIGHT**: Only regenerate for PERMANENT section changes. For task updates, just edit CLAUDE.md TEMPORARY directly.

### ❌ Mistake 4: Not Archiving

**WRONG**: Overwrite CLAUDE.md without backup

**RIGHT**: Always archive old version with dated directory and README note

---

## Quick Reference Commands

```bash
# Read source files
cat CLAUDE_PERMANENT.md    # Get PERMANENT content
cat CLAUDE_TEMP.md         # Get TEMPORARY structure
cat CLAUDE.md | tail -300  # Get current tasks

# Archive old CLAUDE.md
mkdir -p archive/$(date +%Y-%m-%d)/
cp CLAUDE.md archive/$(date +%Y-%m-%d)/CLAUDE_before_regeneration.md

# After regenerating, verify
diff CLAUDE_PERMANENT.md CLAUDE.md | head -50  # Should match at start
wc -l CLAUDE.md            # Should be ~600-800 lines
grep "END OF PERMANENT SECTION" CLAUDE.md  # Should exist
grep "END OF TEMPORARY SECTION" CLAUDE.md  # Should exist
```

---

## Checklist for Regeneration

Use this checklist every time you regenerate:

**Pre-Regeneration**:
- [ ] Confirmed regeneration is necessary (not just task update)
- [ ] Updated CLAUDE_PERMANENT.md with changes
- [ ] Read CLAUDE_PERMANENT.md
- [ ] Read CLAUDE_TEMP.md (schema)
- [ ] Read current CLAUDE.md TEMPORARY section
- [ ] Archived old CLAUDE.md with date

**During Regeneration**:
- [ ] Wrote PERMANENT section from CLAUDE_PERMANENT.md
- [ ] Wrote divider ("END OF PERMANENT SECTION")
- [ ] Wrote TEMPORARY section following CLAUDE_TEMP.md structure
- [ ] Populated TEMPORARY with current tasks (not placeholder text)
- [ ] Wrote final divider ("END OF TEMPORARY SECTION")

**Post-Regeneration Verification**:
- [ ] PERMANENT section matches CLAUDE_PERMANENT.md exactly
- [ ] TEMPORARY section has all required subsections
- [ ] Current tasks preserved
- [ ] Next 3 actions still accurate
- [ ] Blockers listed
- [ ] No content lost
- [ ] Dividers in place
- [ ] Archive created with README note

---

## When in Doubt

**Ask these questions**:

1. **Is this updating core principles?** → Regenerate
2. **Is this updating current tasks?** → Just edit CLAUDE.md TEMPORARY
3. **Is this updating directory structure?** → Regenerate
4. **Is this a new pattern for all future work?** → Regenerate
5. **Is this a one-time task change?** → Just edit CLAUDE.md TEMPORARY

**Golden Rule**: If you're not sure, just edit CLAUDE.md TEMPORARY section. Regeneration is for rare, significant changes to PERMANENT content.
