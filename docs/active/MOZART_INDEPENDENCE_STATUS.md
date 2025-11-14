# Mozart Independence Status

**Date**: 2025-11-14
**Goal**: Full independence from SignalsIntelligence's Mozart system
**Status**: Phase 1 Complete ✅

---

## Phase 1: Backup ✅ COMPLETE (Today)

- ✅ Downloaded Mozart codebase (728MB)
- ✅ Extracted to `~/mozart-backup/mozart-people-extracted/`
- ✅ All source code present (app/, scripts/, tests/)
- ✅ API keys documented
- ✅ Dependencies listed (pyproject.toml)
- ✅ Complete documentation created

**Location**: `~/mozart-backup/mozart-people-extracted/mozart-people/`

---

## Phase 2: Study and Adapt (This Weekend - 8 hours)

### Task 1: Read Key Files (2 hours)

**Critical files to study**:
```bash
cd ~/mozart-backup/mozart-people-extracted/mozart-people

# 1. Gemini extraction prompt (understand verification-aware extraction)
cat app/extraction/gemini_extractor.py | head -300

# 2. Sonnet prose prompt (understand role-aware generation)
cat app/compose/prose_sonnet.py | head -400

# 3. Fetchers (understand Perplexity + Brave Search)
cat app/ingestion/fetchers.py | head -200

# 4. Person schema (understand entity structure)
cat app/schemas/person.schema.json

# 5. MediaWiki publisher (understand API integration)
find app/publish -name "*.py" -exec cat {} \;
```

### Task 2: Build MediaWiki Publisher (2 hours)

**Create**: `integrations/publishing/mediawiki_publisher.py`

**Adapt from**: Mozart's `app/publish/`

**Test against**: SignalsIntelligence's wiki (with permission) or local MediaWiki

### Task 3: Build Biography Generator (4 hours)

**Create**: `research/biography_generator.py`

**Pattern**:
1. Use your `deep_research.py` for information gathering
2. Adapt Mozart's Gemini extraction prompts
3. Adapt Mozart's Sonnet prose prompts
4. Integrate with MediaWiki publisher

**Test**: Generate biography for "Jacques Vallée" (dry-run)

---

## Phase 3: Deploy Local Wiki (Next Weekend - 4 hours)

### Task 1: MediaWiki Docker Setup (2 hours)

```bash
mkdir ~/my-wiki-stack
cd ~/my-wiki-stack

# Use official Wikibase Docker
git clone https://github.com/wmde/wikibase-release-pipeline.git
cd wikibase-release-pipeline

# Configure
cp .env.example .env
nano .env  # Set admin credentials

# Start
docker-compose up -d

# Access: http://localhost:8181
```

### Task 2: Bot Account Setup (30 min)

1. Visit http://localhost:8181/wiki/Special:BotPasswords
2. Create bot: "ResearchBot"
3. Save credentials to your .env

### Task 3: End-to-End Test (1.5 hours)

```bash
# Generate biography
python3 apps/biography_app.py --person "Jacques Vallée"

# Publish to local wiki
python3 apps/biography_app.py \
  --person "Jacques Vallée" \
  --publish \
  --wiki-url "http://localhost:8181/api.php" \
  --wiki-user "ResearchBot" \
  --wiki-pass "your-bot-password"

# Verify: http://localhost:8181/wiki/Jacques_Vallée
```

---

## Phase 4: API Key Independence (Ongoing)

### Required Keys

**Already Have** ✅:
- Gemini API key
- Claude API key

**Need to Get** ❌:
1. **Brave Search API** (Priority: High)
   - Free tier: 2,000 queries/month
   - Sign up: https://brave.com/search/api/
   - Cost: $0

2. **Perplexity API** (Priority: Low - Optional)
   - Sign up: https://www.perplexity.ai/api
   - Cost: ~$10/month
   - Alternative: Use your deep research system instead

**Total Cost**: $0-10/month

---

## Current Capabilities

### What You Can Already Do (60% of Mozart)

**With Your Existing System**:
- ✅ Deep research across 15+ databases
- ✅ Entity extraction (Gemini 2.5 Flash)
- ✅ Report synthesis (Claude Sonnet)
- ✅ Knowledge graph generation
- ✅ Multi-source integration

### What You Need to Build (40% of Mozart)

**Missing Components**:
- ❌ MediaWiki publisher (2 hours to build)
- ❌ Brave Search integration (1 hour to build)
- ❌ Biography-specific prompts (4 hours to adapt)
- ❌ Local wiki deployment (4 hours to set up)

**Total Time**: ~10-12 hours to full independence

---

## Risk Assessment

### If SignalsIntelligence Cuts Off Access Tomorrow

**You Have**:
- ✅ Complete Mozart codebase
- ✅ All documentation (84KB across 3 files)
- ✅ API configuration examples
- ✅ 60% of functionality already built
- ✅ Their API keys (for emergency testing only)

**You Need**:
- Build MediaWiki publisher (2 hours)
- Build biography generator (4 hours)
- Get Brave Search API key (15 min)
- Deploy local wiki (4 hours)

**Recovery Time**: 1-2 weeks to full independence

**Likelihood of Total Loss**: Near zero
- Even if they delete everything, you have the backup
- Even if they revoke API keys, you can get your own
- Even if you lose the backup, you have the documentation to rebuild

---

## Collaboration Strategy

### Maintain Friendly Relations (Recommended)

**Benefits of Collaboration**:
- Access to 130+ entities in their Wikibase
- SPARQL queries against their knowledge graph
- Shared development of verification frameworks
- Community curation improving quality

**How to Help Them** (from WIKIDISC_LOCAL_INDEPENDENCE_PLAN.md):
1. Share your government database integrations
2. Contribute verification framework patterns
3. Build WikiDisc integration for your system
4. Share Gemini 2.5 Flash optimization patterns

**But Also Maintain Independence**:
- Keep your own wiki as backup
- Use your own API keys
- Can operate standalone if needed
- Own all critical infrastructure

---

## Timeline to Full Independence

### Week 1 (This Weekend)
- ✅ Day 1: Backup complete
- [ ] Day 2: Study Mozart code (4 hours)
- [ ] Day 3: Build MediaWiki publisher (2 hours)
- [ ] Day 4: Build biography generator (4 hours)

### Week 2 (Next Weekend)
- [ ] Day 1: Get Brave Search API key (15 min)
- [ ] Day 2: Deploy local MediaWiki (4 hours)
- [ ] Day 3: End-to-end test (2 hours)
- [ ] Day 4: Generate 5-10 test biographies

### Week 3+ (Optional)
- [ ] Deploy to cloud VPS
- [ ] Domain name and SSL
- [ ] Bulk biography generation
- [ ] Integration with your deep research

---

## Success Metrics

**Phase 1 Complete** ✅:
- Mozart codebase backed up locally
- Documentation complete
- Inventory created

**Phase 2 Complete** (This Weekend):
- MediaWiki publisher built and tested
- Biography generator working (dry-run)
- Can generate professional biographies locally

**Phase 3 Complete** (Next Weekend):
- Local MediaWiki deployed
- Can publish biographies to local wiki
- End-to-end pipeline working

**Full Independence** (2 weeks):
- Own API keys obtained
- Local wiki operational
- Can generate + publish biographies without any SignalsIntelligence infrastructure
- Entire process documented and reproducible

---

## Next Actions

### TODAY (Done) ✅
- [x] Download Mozart backup
- [x] Extract and verify backup
- [x] Create documentation
- [x] Create action plan

### TOMORROW (Optional - 2 hours)
- [ ] Read Gemini extraction code
- [ ] Read Sonnet prose code
- [ ] Read MediaWiki publisher code

### THIS WEEKEND (8-10 hours)
- [ ] Build MediaWiki publisher (2 hours)
- [ ] Build biography generator (4 hours)
- [ ] Test biography generation (2 hours)

### NEXT WEEKEND (4-6 hours)
- [ ] Get Brave Search API key (15 min)
- [ ] Deploy local MediaWiki (2-3 hours)
- [ ] End-to-end test (1-2 hours)

---

## Resources

**Documentation Created**:
1. `docs/reference/WIKIDISC_MOZART_RESEARCH_BOT.md` (45KB)
   - Complete architecture documentation
   - LLM prompts and configurations
   - Integration opportunities

2. `docs/reference/MOZART_BACKUP_INVENTORY.md` (8KB)
   - What's in the backup
   - How to use it
   - Key files to study

3. `docs/reference/WIKIDISC_LOCAL_INDEPENDENCE_PLAN.md` (30KB)
   - Complete independence plan
   - Step-by-step build instructions
   - Deployment options

4. `docs/active/MOZART_INDEPENDENCE_STATUS.md` (This file)
   - Current status
   - Action plan
   - Timeline

**Total Documentation**: ~90KB

**Backup Location**: `~/mozart-backup/mozart-people-extracted/mozart-people/`

---

**Status**: Phase 1 Complete, Ready for Phase 2
**Next Step**: Study Mozart code (read key files)
**Timeline**: Full independence in 2 weeks
**Risk Level**: Low (complete backup + documentation)
