# Code Story Generator - Immediate Action Plan (2 Weeks)

## Week 1: Real-World Testing & Discovery

### Day 1-2: Test Repository Setup
**Goal:** Build a diverse test suite to find failure modes

**Tasks:**
- [ ] Clone 5 test repositories:
  1. **Large, mature project**: Linux kernel subsystem or PostgreSQL (complex history)
  2. **Modern TypeScript**: Next.js or Remix (recent, well-maintained)
  3. **Solo/small team**: Pick from our workshop/substansive_synth projects
  4. **Different language**: Rust project (servo or ripgrep)
  5. **Library with API evolution**: lodash or axios

- [ ] For each repo, identify 2-3 "interesting" files:
  - Core module with long history
  - File that had major refactor
  - File with known bug fix cycle

**Deliverable:** `test-repos.md` with repo list and target files

---

### Day 3-4: Run Analysis & Document Results
**Goal:** Find patterns in what works and what doesn't

**Tasks:**
- [ ] Run code-story on all test files (~15 analyses)
- [ ] For each analysis, document:
  - ✅ What insights were valuable
  - ❌ What was missed or wrong
  - 🤔 What was confusing or unclear
  - 💡 Ideas for improvement

- [ ] Create issues template:
  ```markdown
  ## Analysis Quality Issue

  **File:** path/to/file
  **Repo:** repo-name
  **Pattern:** [feature/refactor/bug-fix/etc]

  **What happened:**
  [Description of poor/missing analysis]

  **What should happen:**
  [Ideal output]

  **Possible fix:**
  [Ideas for improvement]
  ```

**Deliverable:** `testing-results.md` with findings

---

### Day 5: Analyze Findings & Prioritize
**Goal:** Identify the top 3 quick wins

**Tasks:**
- [ ] Review all testing results
- [ ] Group issues by theme:
  - Prompt quality issues
  - Missing context issues
  - Pattern detection failures
  - Performance/UX issues

- [ ] Pick top 3 improvements based on:
  - Impact (how much better does analysis get?)
  - Effort (can we do it in 1-2 days?)
  - Frequency (how often does this issue occur?)

**Deliverable:** `priority-fixes.md` with rationale

---

## Week 2: Quick Wins Implementation

### Day 6-7: Add Commit Hash References
**Goal:** Make narratives actionable with direct code links

**Tasks:**
- [ ] Update `StorySegment` type to include commit hashes:
  ```typescript
  interface StorySegment {
    // ... existing fields
    commitRefs: {
      hash: string;
      shortHash: string;
      url?: string; // if GitHub repo
    }[];
  }
  ```

- [ ] Modify narrative generation to include references:
  ```
  Phase 2 - Aggressive Optimization (b0523a4, e122899, 7ef6f4c):
  - ~75x speedup through architectural changes
  - Replaced Array.reduce with for loops
  ```

- [ ] Add `--show-commits` flag to display full commit info
- [ ] If repo is on GitHub, include clickable links in output

**Deliverable:** PR with commit references feature

---

### Day 8-9: Implement Basic Caching
**Goal:** Make second runs instant

**Tasks:**
- [ ] Create cache directory structure:
  ```
  ~/.code-story-cache/
    ├── {repo-hash}/
    │   └── {file-hash}.json
  ```

- [ ] Cache schema:
  ```typescript
  interface CacheEntry {
    version: string;
    repoPath: string;
    filePath: string;
    lastCommitHash: string;
    commits: CommitInfo[];
    story: CodeStory;
    createdAt: Date;
  }
  ```

- [ ] Invalidation logic:
  ```typescript
  // Check if file has new commits since cache
  const latestCommit = await getLatestCommit(repo, file);
  if (cache.lastCommitHash !== latestCommit) {
    // Re-analyze only new commits
    // Merge with existing story
  }
  ```

- [ ] Add cache commands:
  - `--no-cache`: Force fresh analysis
  - `--cache-stats`: Show cache usage
  - `--clear-cache`: Delete all cached data

**Deliverable:** PR with caching system

---

### Day 10: Improve Pattern-Specific Prompts
**Goal:** Better analysis for common change types

**Tasks:**
- [ ] Create prompt templates for patterns:

  **Performance Optimization:**
  ```
  Analyze this performance-focused change:
  1. What was the bottleneck? (include metrics if in commit msg)
  2. What solution was implemented? (show key code changes)
  3. What was the performance gain?
  4. What trade-offs were made?
  ```

  **Security Fix:**
  ```
  Analyze this security-related change:
  1. What vulnerability existed?
  2. How was it exploited? (if mentioned)
  3. How was it fixed?
  4. What preventive measures were added?
  ```

  **API Change:**
  ```
  Analyze this API modification:
  1. What changed in the public interface?
  2. Was this breaking? What's the migration path?
  3. Why was this change necessary?
  4. What's deprecated or removed?
  ```

- [ ] Update segment generation to use appropriate template based on detected pattern
- [ ] Add pattern confidence scoring

**Deliverable:** PR with enhanced prompts

---

### Day 11: Documentation & Polish
**Goal:** Make the tool easy to use and contribute to

**Tasks:**
- [ ] Update README with:
  - Clear installation instructions
  - Usage examples from real repos
  - Performance tips (caching, API vs local)
  - Troubleshooting guide

- [ ] Create CONTRIBUTING.md:
  - How to add new patterns
  - How to improve prompts
  - Testing guidelines
  - Code structure explanation

- [ ] Add examples directory:
  - Sample outputs from test repos
  - Before/after of improvements
  - Edge cases handled

**Deliverable:** Complete documentation

---

## Success Metrics (End of Week 2)

**Quantitative:**
- [ ] Cache hit rate >70% on repeated analyses
- [ ] Analysis includes commit references 100% of time
- [ ] 3+ pattern-specific prompts implemented
- [ ] Test suite covers 5+ diverse repositories

**Qualitative:**
- [ ] Narratives consistently include "why" not just "what"
- [ ] Code examples appear in deep dives when relevant
- [ ] User can jump from analysis to actual code easily
- [ ] Tool feels fast and responsive

**Decision Criteria (End Week 2):**

Ask: "Is this tool now useful enough for daily use?"

If **YES** → Plan Week 3-4: Cross-file analysis
If **NO** → What's still missing? Iterate on immediate fixes

---

## Resources Needed

**Time:**
- ~2-3 hours/day of focused development
- ~1 hour/day of testing and documentation

**API Costs:**
- ~$5-10 for testing (15 files × 2-3 iterations)
- Can use local LLM for most testing

**Help Needed:**
- Feedback on test results
- Real-world use cases to validate
- Ideas for which repos to test on

---

## How to Get Started (Right Now)

1. **Create test repos list**: Pick 5 diverse repositories
2. **Run first analysis**: Try on one file, document everything you notice
3. **Open issues**: Create GitHub issues for each problem found
4. **Pick one quick win**: Start with commit references or caching

Then iterate based on what we learn!
