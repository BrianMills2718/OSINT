# Tag Formatting Standards

## Overview
This document defines the canonical formatting rules for all article tags across the Klippenstein and Bills Blackbox collections.

## Core Formatting Rules

### 1. Capitalization
- **Proper nouns**: Title Case (capitalize each significant word)
- **Common concepts**: all lowercase (no capitalization)
- **Mixed tags**: Capitalize only the proper noun parts

**Proper Nouns (Title Case):**
- Geographic regions: "Middle East", "West Africa", "Indo-Pacific"
- People: "Donald Trump", "Joe Biden", "Elon Musk"
- Organizations: "Department of Justice", "Federal Bureau of Investigation"
- Official titles: "Secretary of Defense", "Attorney General"

**Common Concepts (all lowercase):**
- Abstract concepts: "national security", "civil liberties", "surveillance"
- Generic terms: "classified documents", "military aid", "defense spending"
- Actions/processes: "election interference", "content moderation", "whistleblowing"

**Mixed Tags:**
- "Biden administration" (Biden is proper, administration is common)
- "U.S. military" (U.S. is proper, military is common)
- "Gaza protests" (Gaza is proper, protests is common)

❌ **NEVER capitalize the first word unless it's a proper noun**
- ✅ Correct: "classified documents"
- ❌ Incorrect: "Classified documents"
- ✅ Correct: "Department of Justice"
- ❌ Incorrect: "department of justice"

### 2. Spacing
- **Use spaces, not hyphens**, for multi-word tags
- ✅ Correct: "civil liberties", "national security", "Biden administration"
- ❌ Incorrect: "civil-liberties", "national-security", "Biden-administration"

### 3. Abbreviations
- **Use periods for standard U.S. abbreviations**
- ✅ Correct: "U.S.", "U.K.", "U.N."
- ❌ Incorrect: "US", "UK", "UN"

### 4. Well-Known Acronyms (No Periods)
- **Keep common acronyms without periods**
- ✅ Correct: "FBI", "CIA", "NSA", "DOJ", "DHS", "AI", "COVID-19", "9/11"
- ❌ Incorrect: "F.B.I.", "C.I.A.", "N.S.A."

## Advanced Formatting Rules

### 5. Compound Terms with Slashes
- **Split into separate tags** for better navigation
- ✅ Correct: ["Iraq", "Syria"] not "Iraq/Syria"
- ✅ Correct: ["Israel", "Palestine"] not "Israel/Palestine"
- **Exception**: Keep well-known compound terms: "9/11"

### 6. Possessives
- **Remove apostrophes**
- ✅ Correct: "Trump policies"
- ❌ Incorrect: "Trump's policies"

### 7. Leading Articles
- **Remove "The" from beginnings**
- ✅ Correct: "Pentagon", "FBI", "White House"
- ❌ Incorrect: "The Pentagon", "The FBI", "The White House"

### 8. Parentheticals
- **Use full form only** (no abbreviations in parentheses)
- ✅ Correct: "Department of Justice"
- ❌ Incorrect: "Department of Justice (DOJ)", "DOJ (Department of Justice)"
- **Note**: Use the most commonly recognized form

### 9. Ampersands
- **Spell out "and"**
- ✅ Correct: "U.S. and Iran"
- ❌ Incorrect: "U.S. & Iran"

### 10. Singular vs. Plural
- **Use singular form** for consistency
- ✅ Correct: "drone", "policy", "weapon", "surveillance program"
- ❌ Incorrect: "drones", "policies", "weapons", "surveillance programs"
- **Exception**: Terms that are inherently plural: "civil liberties", "human rights"

### 11. Special Characters
- **Remove**: Quotation marks, colons, semicolons, exclamation points
- **Keep**: Periods (for abbreviations), commas (if necessary for clarity), hyphens (only in proper nouns like "COVID-19")
- ✅ Correct: "COVID-19", "9/11", "Iran backed militia"
- ❌ Incorrect: "COVID19", "Iran-backed militia", "9-11"

## Tag Content Rules

### 12. Avoid Meta Tags
- **Do NOT create tags for**:
  - Years: "2023", "2024", "2025"
  - Newsletter mechanics: "email", "subscription", "contact", "support"
  - Administrative: "customer service", "paid subscriber"

### 13. News Roundup Detection
- **Add "news roundup" tag** for articles with multiple stories
- Detected by section markers: "Watch", "Feel Like This Should Be", "Quick Hits"

## Examples

### Good Tags
- "civil liberties"
- "U.S. military"
- "Middle East"
- "Donald Trump"
- "FBI"
- "Department of Justice"
- "surveillance"
- "national security"
- "Biden administration"
- "COVID-19"
- "9/11"

### Bad Tags (Need Normalization)
- "civil-liberties" → "civil liberties"
- "US military" → "U.S. military"
- "middle-east" → "Middle East"
- "donald trump" → "Donald Trump"
- "F.B.I." → "FBI"
- "DOJ (Department of Justice)" → "Department of Justice"
- "surveillances" → "surveillance"
- "Biden-administration" → "Biden administration"
- "COVID19" → "COVID-19"
- "9-11" → "9/11"

## Implementation Priority

1. **High Priority** (affects readability/navigation):
   - Capitalization
   - Spacing (remove hyphens)
   - Abbreviation periods (U.S., U.K., etc.)

2. **Medium Priority** (consistency):
   - Singular vs. plural
   - Leading articles
   - Possessives

3. **Low Priority** (cleanup):
   - Special characters
   - Parentheticals

## Notes

- These standards apply to **all** tags across both collections
- When in doubt, use the form that users are most likely to search for
- Geographic terms: Use commonly accepted names (e.g., "Middle East" not "Mideast")
- Organizations: Use official names (e.g., "Department of Homeland Security" not "Homeland Security Department")
