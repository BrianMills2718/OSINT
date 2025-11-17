# Test Data for Stage 1 Manual Validation

## Purpose

This directory holds 2-3 **public investigative reports** used for Stage 1 manual entity extraction validation.

**Standalone approach**: We use publicly available investigative journalism, not outputs from other tools.

## Requirements

For Stage 1 validation to work, we need:

1. **2-3 public investigative reports** on thematically related topics
2. **Thematic overlap** to test cross-document entity recurrence
3. **Sufficient depth** to extract 10-15 entity-rich snippets per report

## Recommended Public Sources

### Option A: Bellingcat Investigations (Recommended)

**MH17 Investigation Series** (3 reports, related theme):
- https://www.bellingcat.com/news/uk-and-europe/2014/11/08/origin-of-the-separatists-buk-a-bellingcat-investigation/
- https://www.bellingcat.com/news/uk-and-europe/2015/05/31/mh17-the-open-source-evidence/
- https://www.bellingcat.com/news/uk-and-europe/2016/09/28/mh17-russian-gru-commander-orion-identified-oleg-ivannikov/

**Why these**:
- Rich entity sets: military units, commanders, equipment, locations
- Cross-document recurrence: same entities appear across multiple reports
- Investigative journalism depth (not just news summaries)
- Entity types: people (commanders), organizations (military units), equipment (Buk system), locations (Ukraine, Russia)

### Option B: ProPublica Investigations

**Machine Bias Series** (3 reports, related theme):
- https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing
- https://www.propublica.org/article/how-we-analyzed-the-compas-recidivism-algorithm
- https://www.propublica.org/article/breaking-the-black-box-what-facebook-knows-about-you

**Why these**:
- Entities: companies (Northpointe, Facebook), concepts (algorithms, bias), people (researchers), organizations (courts)
- Cross-report themes: algorithmic bias, criminal justice, technology companies
- Academic + investigative depth

### Option C: Intelligence/Defense Investigations

**NSA/Intelligence Community** (use CIA FOIA reading room):
- CIA: Operation Mockingbird documents
- NSA: PRISM/Snowden-related declassified reports
- Military: Psychological operations manuals (publicly available via FOIA)

**Why these**:
- Matches v3 design examples (J-2, psyops, intelligence programs)
- Entity types: offices, programs, people, codewords
- True investigative journalism use case

### Option D: Long-Form NYT/WaPo Investigations

**Any long-form investigation** (5000+ words) with:
- Multiple named entities (people, orgs, programs)
- Cross-references between entities
- Investigative depth (not breaking news)

## File Organization

Save reports as:
```
test_data/
├── report1_bellingcat_mh17_origin.md  (or .pdf, .html)
├── report2_bellingcat_mh17_evidence.md
├── report3_bellingcat_mh17_commander.md
└── README.md (this file)
```

**Format**: Markdown preferred (easier to extract snippets), but PDF/HTML acceptable

## Usage

Once you have 2-3 reports here:

1. Read `./poc/STAGE1_SPEC.md`
2. Follow manual extraction process (10-15 snippets per report)
3. Test entity pivoting across reports
4. Document findings in `./poc/stage1_manual_test.md`

## Quick Start

**Fastest path to Stage 1**:

1. Pick Bellingcat MH17 series (Option A)
2. Download 3 reports as markdown or save HTML
3. Start Stage 1: extract entities from first report, then second, then third
4. Test cross-report pivoting (e.g., "Buk" entity appears in all 3 reports)

**Time estimate**: 2-3 hours total for Stage 1 with these sources
