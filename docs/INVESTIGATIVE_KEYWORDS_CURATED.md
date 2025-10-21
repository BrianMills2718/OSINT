# Investigative Keywords - Manually Curated from Ken Klippenstein & Bill's Black Box

**Source**: Analysis of 1,101 articles (3,300 tags) + 1,216 automated keyword extractions
**Date**: 2025-10-19
**Purpose**: These are the RARE DIAMONDS - specific terminology, programs, and concepts that investigative journalists monitor

---

## Tier 1: High-Value Investigative Terms (Specific Programs & Classifications)

### Domestic Extremism Programs
- **"Nihilistic Violent Extremism"** - FBI threat classification (rare, specific)
- **"Black Identity Extremists"** - Controversial FBI designation
- **"Domestic Violent Extremism"** - Official DHS terminology
- **"National Security Presidential Memorandum 7"** - Specific directive
- **NVE** - Nihilistic Violent Extremism acronym
- **DVE** - Domestic Violent Extremism acronym
- **BIE** - Black Identity Extremists acronym

### Intelligence Operations & Classifications
- **"classified program"** - Reveals redacted/secret operations
- **"covert operation"** - CIA/DoD secret activities
- **"counterintelligence"** - Spy vs spy operations
- **"declassification"** - FOIA revelations
- **"intelligence leak"** - Whistleblower/unauthorized disclosures
- **"information warfare"** - Psychological operations
- **"influence operations"** - Foreign/domestic propaganda campaigns

### Military Special Operations
- **"Operation Excalibur"** - Specific military operation
- **Joint Special Operations Command** - JSOC (elite forces)
- **"special operations forces"** - SOF missions
- **"submarine operation"** - Underwater missions
- **Joint All-Domain Operations (JADO)** - New military doctrine

### Surveillance & Civil Liberties
- **"surveillance state"** - Government overreach
- **"mass surveillance"** - NSA/intelligence collection
- **"FISA warrant"** - Foreign Intelligence Surveillance Act
- **"backdoor search"** - Warrantless surveillance
- **"parallel construction"** - Law enforcement evidence laundering

---

## Tier 2: Medium-Value Terms (Agencies, Concepts, Bureaucratic Terminology)

### Government Agencies (Tags from articles)
- Department of Homeland Security (45 mentions)
- National Counterterrorism Center (12 mentions)
- Joint Terrorism Task Force
- National Guard (13 mentions)
- U.S. Immigration and Customs Enforcement (11 mentions)
- Customs and Border Protection (17 mentions)

### Key Concepts (High frequency in investigative journalism)
- **national security** (130x) - But combine with specific terms
- **civil liberties** (92x) - Constitutional violations
- **surveillance** (54x) - Monitoring programs
- **domestic terrorism** (29x) - Threat designations
- **counterterrorism** (14x) - CT operations
- **press freedom** (15x) - First Amendment issues
- **media censorship** (10x) - Government suppression
- **congressional oversight** (8x) - Legislative accountability
- **Leaks and whistleblowers** (8x) - Unauthorized disclosures

### Specific Officials/Figures (When tied to scandals/programs)
- Kash Patel (10x) - Intelligence official
- Christopher Wray - FBI Director
- William Burns - CIA Director
- Alejandro Mayorkas - DHS Secretary
- Mark Milley - Former Joint Chiefs Chair

---

## Tier 3: Context-Dependent Terms (Useful when combined)

### Document Types to Search For
- "threat assessment"
- "intelligence bulletin"
- "operational memo"
- "after-action report"
- "inspector general report"
- "classified memo"
- "internal directive"

### Foreign Policy/Conflicts
- **Iran** (40x) - But focus on: "Iran-backed militia", "Iran nuclear program"
- **Gaza** (22x) - Focus on: "humanitarian crisis", "civilian casualties"
- **Israel** (42x) - Focus on: "arms transfers", "military aid"
- **Houthi movement** (10x) - Yemen conflict
- **Ukraine** (16x) - Military aid tracking

### Technology & Surveillance
- **cybersecurity** (6x)
- **biometrics** - Surveillance technology
- **facial recognition** - AI surveillance
- **social media moderation** - Censorship
- **encryption** - Privacy technology

---

## Tier 4: Acronyms (Always Useful for Boolean Searches)

**Intelligence/Security**:
- NSA, CIA, DHS, FBI, DOJ, DOD
- JSOC, CENTCOM, SOCOM
- NCTC (National Counterterrorism Center)
- ODNI (Office of Director of National Intelligence)

**Immigration**:
- ICE, CBP, USCIS

**Military**:
- NORAD, NATO

**Classifications**:
- TS/SCI (Top Secret/Sensitive Compartmented Information)
- FOIA (Freedom of Information Act)

---

## What NOT to Search For (Too Generic)

❌ "Donald Trump" - Too broad, returns news cycle
❌ "Joe Biden" - Same issue
❌ "Israel" alone - Need specifics
❌ "United States" - Useless
❌ "news" - Not investigative
❌ "report" - Too generic

---

## Boolean Query Templates (Investigative Focus)

### Template 1: Specific Programs
```
("Nihilistic Violent Extremism" OR "NVE") AND ("threat assessment" OR "intelligence bulletin" OR "classified")
```

### Template 2: Surveillance Revelations
```
("FISA warrant" OR "backdoor search" OR "mass surveillance") AND ("leak" OR "whistleblower" OR "FOIA")
```

### Template 3: Military Operations
```
("JSOC" OR "Joint Special Operations Command" OR "covert operation") AND site:(.gov OR .mil)
```

### Template 4: Agency Misconduct
```
("inspector general report" OR "congressional oversight") AND ("FBI" OR "DHS" OR "ICE") AND ("misconduct" OR "violation")
```

### Template 5: Domestic Extremism Classifications
```
("domestic terrorism" OR "domestic extremism") AND ("threat assessment" OR "intelligence product" OR "bulletin") AND NOT ("news" OR "opinion")
```

---

## Key Insight: Klippenstein & Bill's Focus

**They write about**:
1. **Government overreach** (surveillance, civil liberties violations)
2. **Secret programs** (classified operations, intelligence programs)
3. **Controversial classifications** (extremism designations, threat assessments)
4. **Military operations** (special ops, covert actions, drone strikes)
5. **Whistleblower revelations** (leaks, FOIA documents, insider disclosures)
6. **Agency misconduct** (FBI overreach, DHS abuses, ICE violations)
7. **Foreign policy secrets** (arms transfers, military aid, covert support)

**They DON'T write about**:
- Generic political news
- Press releases
- Opinion pieces
- Election horse race coverage
- Celebrity politics

---

## Recommended Monitors (Based on This Analysis)

### Monitor 1: Domestic Extremism Designations
```yaml
keywords:
  - "Nihilistic Violent Extremism"
  - "Black Identity Extremists"
  - "Domestic Violent Extremism"
  - "NVE"
  - "DVE"
  - "BIE"
  - "extremism threat assessment"
sources: [dvids, federal_register, sam, usajobs]
```

### Monitor 2: Surveillance & FISA
```yaml
keywords:
  - "FISA warrant"
  - "Section 702"
  - "backdoor search"
  - "mass surveillance"
  - "warrantless surveillance"
sources: [federal_register, dvids]
```

### Monitor 3: Special Operations & Covert Programs
```yaml
keywords:
  - "Joint Special Operations Command"
  - "JSOC"
  - "covert operation"
  - "classified program"
  - "special operations forces"
sources: [dvids, sam]
```

### Monitor 4: Inspector General Reports & Oversight
```yaml
keywords:
  - "inspector general report"
  - "OIG report"
  - "congressional oversight"
  - "whistleblower complaint"
sources: [federal_register, sam]
```

### Monitor 5: Immigration Enforcement Abuses
```yaml
keywords:
  - "ICE detention"
  - "CBP misconduct"
  - "immigration enforcement"
  - "detention facility"
  - "deportation"
sources: [federal_register, dvids, usajobs]
```

---

## Next Steps

1. **Archive** the automated 1,200 keyword database (has quality issues)
2. **Use THIS curated list** for monitor creation
3. **Test each monitor** to ensure it returns investigative content, not news
4. **Iterate** - Add specific program names as they emerge from articles
5. **Combine keywords** - "JSOC" + "Yemen" is better than "JSOC" alone
