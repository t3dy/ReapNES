---
layout: default
title: "Swarm Performance Analysis — First Deployment"
---

# Swarm Performance Analysis — First Deployment

## What We Attempted

Ten parallel agents, zero file conflicts, two phases (docs + code)
running simultaneously. The goal: restructure the repo's methodology
from implicit to explicit in one parallel batch.

## Results

### Completion Rate: 7-8 out of 10

Seven agents completed their full deliverable. One (Agent 5)
completed one of two files. Two agents (9 and 10) did not produce
output and required gap-filling by the main session or follow-up
agents.

### What Worked Well

**Parallel documentation writing.** Six agents each read the same
source files (spec.md, frame_ir.py, parser.py, manifests) and
produced different output documents. No conflicts. No inconsistencies
requiring reconciliation. Each agent had a clear scope (one or two
files) with no overlap.

**Comment-only code changes.** Agent 8 added STATUS blocks to five
existing files. This is the safest kind of parallel code change —
no logic modifications, no import changes, no risk of breaking
existing behavior.

**Test file creation.** Agent 7 wrote two new test files that
import from the existing codebase. No modifications to existing
code needed. The tests encode invariants discovered during the
session (phase2_start, bounce-at-1, pitch mapping).

### What Did Not Work

**Logic changes to existing files.** Agent 9 was tasked with adding
a `--game` CLI parameter to trace_compare.py. This requires reading
the existing argument parser, understanding the control flow,
modifying conditional branches, and preserving backward compatibility.
The agent did not complete this. Likely cause: the task required too
much stateful reasoning about an existing code path for a swarm
agent working without Bash (no ability to test the change).

**Rule file with YAML front matter.** Agent 10 was supposed to
write a .claude/rules/architecture.md with specific YAML front
matter for path-specific loading. It did not produce output. This
is a simpler task than Agent 9's but still failed, suggesting
the issue may be agent capacity/timeout rather than task complexity.

### Performance Characteristics

**Strengths of the swarm pattern:**
- Zero coordination overhead (no agent needed output from another)
- Zero file conflicts (each agent owns its output files exclusively)
- Massive parallelism for write-heavy tasks (7 docs + 2 test files in ~5 minutes)
- Good at "read N files, synthesize into 1 new file" tasks
- Good at comment-only edits to existing files

**Weaknesses:**
- Cannot run tests or verify output (no Bash access)
- Cannot handle multi-step logic changes that require iterative debugging
- 20-30% failure rate on tasks at the edge of complexity
- No inter-agent communication (each works in isolation)
- Gap-filling needed for incomplete agents

### Recommendations for Future Swarms

1. **Use swarms for documentation and new file creation.**
   This is the sweet spot: read-only input, write-only output,
   no need to verify correctness at runtime.

2. **Do NOT use swarms for logic changes to existing code.**
   Agent 9's failure confirms this. Code changes need Bash for
   testing. Keep these in the main session or a single focused agent.

3. **Assign one file per agent, never more than two.**
   Agent 5 was assigned two files and completed only one.
   Agent 4 was also assigned two files but completed both —
   possibly because INVARIANTS.md and TRACE_WORKFLOW.md are more
   closely related than RESEARCH_LOG.md and UNKNOWNS.md.

4. **Expect 70-80% completion and plan for gap-filling.**
   Budget time for the main session to check results and
   complete what the swarm missed.

5. **Pre-validate that source files exist and are readable.**
   Some agent failures may be due to file path issues or
   files that changed during execution.

## What This Means for the Project

The swarm produced ~120KB of structured documentation in one batch.
Without the swarm, writing 7 docs + 2 test files + 1 rule file
sequentially would have taken 30-45 minutes of context window.
With the swarm, the writing phase took ~5 minutes wall clock,
plus ~10 minutes for gap-filling. Net savings: roughly 50%.

The real value is not speed but CONTEXT PRESERVATION. Each agent
got a fresh context window dedicated entirely to its document.
The main session's context was not consumed by writing 26KB of
COMMAND_MANIFEST.md. This leaves room for Phase 3 validation,
the user's follow-up requests, and further iteration.

## Metrics

| Metric | Value |
|--------|-------|
| Agents launched | 10 |
| Agents completed | 7-8 |
| Files produced | 10 of 12 planned |
| Total output size | ~130KB |
| Wall-clock time | ~5 minutes |
| Gap-fill time | ~10 minutes |
| File conflicts | 0 |
| Logic bugs introduced | 0 (no logic changes completed) |
| Tests passing | TBD (Phase 3) |
