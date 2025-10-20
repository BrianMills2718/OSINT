# CLAUDE.md - Temporary Section (Schema/Template)

**Last Updated**: [YYYY-MM-DD HH:MM]
**Current Phase**: [Phase Name] ([Phase Description]) - [X]% complete
**Next Phase**: [Next Phase Name] ([Next Phase Description])

---

## CURRENT STATUS SUMMARY

**[Phase Name] Progress**: [X of Y] [component type] complete

**Working** ([PASS]):
- [Component 1 name]
- [Component 2 name]
- [Component 3 name]
- [Infrastructure component]
- [Infrastructure component]

**Blocked** ([BLOCKED]):
- [Component name] ([Reason for blocker])

**Full Status**: See STATUS.md for detailed component status table

---

## RELATED STATUS & PLANNING

**Status & Evidence** (Reality Check):
- See STATUS.md for component-by-component status with evidence
- What's [PASS], what's [FAIL], what's [BLOCKED]
- Evidence: command outputs, limitations, unverified claims

**Phase Plans** (Where This Fits):
- See ROADMAP.md for phase objectives and success criteria
- Current phase goals and deliverables
- Next phase preview

**Long-Term Vision** (Why We're Doing This):
- See INVESTIGATIVE_PLATFORM_VISION.md (75 pages)
- Full architectural target and requirements

---

## CURRENT TASK SCOPE

**SCOPE**: [Exactly what you will verify this session]

**NOT IN SCOPE**:
- [What you will NOT verify - item 1]
- [What you will NOT verify - item 2]
- [What you will NOT verify - item 3]

**SUCCESS CRITERIA**:
1. Command: `[exact command to run]`
   Expected: [exact expected output]
   Time: < [N] seconds

2. Command: `[exact command to run]`
   Expected: [exact expected output]
   Time: < [N] seconds

3. [Other success criteria]
   Expected: [what success looks like]

**ESTIMATED IMPACT**: [Impact description] ([X of Y] [unit])

---

## NEXT 3 ACTIONS (Priority Order)

### Action 1: [Action Name]

**Prerequisites**: [None | Action dependencies]

**Steps**:
```bash
# [Step 1 description]
[command]

# [Step 2 description]
[command]

# [Step 3 description]
[command]
```

**Success Criteria**:
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**Evidence Required**:
- [Evidence type 1]
- [Evidence type 2]
- [Evidence type 3]

**On Failure**:
- [Debugging step 1]
- [Debugging step 2]
- [Debugging step 3]

**Current Status**: [PENDING | IN PROGRESS | BLOCKED] - [Brief status description]

---

### Action 2: [Action Name]

**Prerequisites**: [Action dependencies]

**Entry Point** (MUST use this):
```bash
[exact command for user-facing entry point]
```

**Expected Output**:
```
[Show exact expected output format with placeholders]
```

**Success Criteria**:
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**Evidence Required**:
- [Evidence type 1]
- [Evidence type 2]
- [Evidence type 3]

**On Failure**:
- [Debugging step 1]
- [Debugging step 2]
- [Debugging step 3]

**What This DOES NOT Test** (must state explicitly):
- [Unverified aspect 1]
- [Unverified aspect 2]
- [Unverified aspect 3]

---

### Action 3: [Action Name]

**Prerequisites**: [Action dependencies]

**Entry Point** (MUST use this):
```bash
[exact command for user-facing entry point]
```

**Expected Output**:
```
[Show exact expected output format with placeholders]
```

**Success Criteria**:
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**Evidence Required**:
- [Evidence type 1]
- [Evidence type 2]
- [Evidence type 3]

**On Failure**:
- [Debugging step 1]
- [Debugging step 2]
- [Debugging step 3]

**What This DOES NOT Test** (must state explicitly):
- [Unverified aspect 1]
- [Unverified aspect 2]
- [Unverified aspect 3]

---

## AFTER COMPLETING THESE 3 ACTIONS

**[Phase Name] Status**: [COMPLETE | PARTIALLY COMPLETE]

**Update Documentation**:
1. **STATUS.md**: [What to update with evidence]
2. **ROADMAP.md**: [What to update with actual results]
3. **CLAUDE.md TEMPORARY**: [What to update - next actions or phase transition]
4. **README.md**: [What to update if needed]

**Transition to Next Phase** (if phase complete):
1. Read ROADMAP.md for [Next Phase Name] objectives and success criteria
2. Read relevant sections of INVESTIGATIVE_PLATFORM_VISION.md for [Next Phase Name] details
3. Update CLAUDE.md TEMPORARY with [Next Phase Name] scope and next 3 actions
4. Begin [Next Phase Name] work following new scope declaration

**[Next Phase Name] Preview**:
- Objectives: See ROADMAP.md [Next Phase Name] section
- Key deliverables: [Deliverable 1], [Deliverable 2], [Deliverable 3]
- Success criteria: [High-level success description]

---

## IMMEDIATE BLOCKERS

| Blocker | Impact | Status | Next Action |
|---------|--------|--------|-------------|
| [Blocker description] | [Impact description] | [Current status] | [What to do next] |

**[Additional blocker notes if needed]**

---

## CHECKPOINT QUESTIONS (Answer Every 15 Min)

**Last Checkpoint**: [YYYY-MM-DD HH:MM | Not started]

**Questions**:
1. What have I **proven** with command output?
   - Answer: [Fill during work]

2. What am I **assuming** without evidence?
   - Answer: [Fill during work]

3. What would break if I'm wrong?
   - Answer: [Fill during work]

4. What **haven't I tested** yet?
   - Answer: [Fill during work]

**Update this section during work to track progress and catch drift.**

---

## CODE PATTERNS FOR CURRENT PHASE

**For current phase, see PATTERNS.md**

Key patterns needed for Actions 1-3:
- [Pattern 1 name] (see [location])
- [Pattern 2 name] (see [location])
- [Pattern 3 name] (see [location])

---

**END OF TEMPORARY SECTION**

---

## UPDATING THIS FILE

**When tasks complete** (normal workflow):
1. Update "CURRENT STATUS SUMMARY" with latest progress
2. Update "NEXT 3 ACTIONS" with new actions
3. Update "CHECKPOINT QUESTIONS" with your latest answers
4. Update "IMMEDIATE BLOCKERS" as blockers resolve
5. Cross-reference with STATUS.md and ROADMAP.md for consistency

**When phase changes**:
1. Archive old CLAUDE.md: `archive/YYYY-MM-DD/CLAUDE_phase[N].md`
2. Read ROADMAP.md for new phase objectives
3. Rewrite TEMPORARY section with new phase scope
4. Update "RELATED STATUS & PLANNING" section

**PERMANENT section updates** (rare):
- Follow REGENERATE_CLAUDE.md instructions
- Edit CLAUDE_PERMANENT.md first
- Then regenerate full CLAUDE.md
