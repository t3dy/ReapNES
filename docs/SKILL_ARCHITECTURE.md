# HiroPlantagenet Analysis: NES Music Studio Skill Architecture

## 1. Intent Atoms

| # | Goal | Tag |
|---|------|-----|
| 1 | Define skill inventory with inputs/outputs/contracts per pipeline layer | ONTOLOGY |
| 2 | Enforce preconditions so skills refuse to run without required inputs | META-CONTROL |
| 3 | Make manifests the single source of truth read/written by all skills | PIPELINE |
| 4 | Define the dependency graph (what blocks what, what parallelizes) | PIPELINE |
| 5 | Encode guardrails against the 6 known failure modes | META-CONTROL |
| 6 | Extract shared utilities into reusable infrastructure | PIPELINE |
| 7 | Reduce prompts to intent-only ("process Super C") | META-CONTROL |

## 2. Conflicts & Gaps

CONFLICTS:
- "Do NOT write code" vs designing skills that must eventually BE code. Resolution: this layer produces SPECS, not implementations.
- "Enforce constraints" vs "Claude Skills are markdown instructions." Skills can check for files and refuse to proceed, but they can't prevent the LLM from doing something outside the skill invocation. Enforcement = fail-fast checks at skill entry, not runtime guards.

MISSING DECISIONS:
- Where do skills live? `~/.claude/skills/nes-*` or `.claude/skills/nes-*` (project-local)?
- Should skills call other skills, or should the user invoke them in sequence?
- How does a skill "refuse to run"? (Output an error message? Prompt the user? Silently skip?)

IMPLICIT ASSUMPTIONS:
- The user has Mesen2 installed and can produce APU trace CSVs
- Python 3 is available with numpy, mido, wave, csv, struct
- The extraction/manifests/ directory exists and is the canonical config location
- All NES ROMs are accessible in AllNESRoms/ or extraction/roms/

## 3. Layer Architecture

```
Layer 1: Skill Ontology
  Purpose: Define every skill's identity, I/O contract, and classification.
  Atoms: #1, #6
  Reasoning mode: classificatory

Layer 2: Enforcement Rules
  Purpose: Define preconditions, postconditions, and hard failures per skill.
  Atoms: #2, #5
  Reasoning mode: deterministic (rule specification)
  Depends on: Layer 1

Layer 3: Manifest Schema
  Purpose: Define the JSON schema that all skills read/write.
  Atoms: #3
  Reasoning mode: ontological (schema design)
  Depends on: Layer 1

Layer 4: Dependency Graph & Prompt Design
  Purpose: Define execution order, parallelism, and minimal prompt patterns.
  Atoms: #4, #7
  Reasoning mode: analytical
  Depends on: Layers 1, 2, 3
```

## 4. Rewritten Prompts

### === LAYER 1: SKILL ONTOLOGY ===

OBJECTIVE: Define every skill in the NES extraction pipeline.

SCOPE CONSTRAINTS:
- DO: specify purpose, inputs, outputs, deterministic/probabilistic, dependencies
- DO NOT: write implementation code or explain the pipeline conceptually

OUTPUT CONTRACT:

#### Skill: `/nes-capture`
- **Purpose:** Archive a Mesen APU trace CSV into the project
- **Inputs:** User provides path to capture.csv
- **Outputs:** `extraction/traces/{game}/capture{N}.csv`
- **Type:** Deterministic (file copy + rename)
- **Dependencies:** None
- **Human input:** User must specify game name

#### Skill: `/nes-render-trace`
- **Purpose:** Render a trace CSV to listenable WAV
- **Inputs:** `extraction/traces/{game}/capture{N}.csv`
- **Outputs:** `output/{Game}/wav/{game}_capture{N}_full_v1.wav`
- **Type:** Deterministic (APU synth from register values)
- **Dependencies:** `/nes-capture`
- **Human input:** None

#### Skill: `/nes-render-nesmdb`
- **Purpose:** Render all nesmdb tracks for a game as reference WAVs
- **Inputs:** `data/nesmdb/nesmdb24_exprsco/train/{id}_{game}_*.pkl`
- **Outputs:** `output/{Game}/wav/nesmdb/{game}_{num}_{name}.wav`
- **Type:** Deterministic (frame-level synth)
- **Dependencies:** None
- **Shared utilities:** nesmdb renderer with rate validation

#### Skill: `/nes-segment`
- **Purpose:** Split a trace WAV into individual track segments
- **Inputs:** Trace WAV + trace CSV
- **Outputs:** `output/{Game}/wav/segments/{game}_seg{NN}_v1.wav` + segment table
- **Type:** Deterministic (silence detection) + Human ear (track naming)
- **Dependencies:** `/nes-render-trace`
- **Shared utilities:** silence gap detector, melody loop comparator

#### Skill: `/nes-scan-rom`
- **Purpose:** Extract verified facts from a ROM file
- **Inputs:** ROM file at `extraction/roms/{game}.nes`
- **Outputs:** Updated `extraction/manifests/{game}.json` with verified fields
- **Type:** Deterministic (byte scanning, header parsing, period table search)
- **Dependencies:** None (but trace data improves accuracy)
- **Hard limit:** 2 search passes max. If not found, mark as UNKNOWN.

#### Skill: `/nes-find-pointer-table`
- **Purpose:** Locate the sound table / pointer table in the ROM
- **Inputs:** Manifest (with driver family, period table location), ROM file
- **Outputs:** Updated manifest `pointer_table_address` field
- **Type:** Deterministic scan (if format known) OR Probabilistic heuristic (if unknown)
- **Dependencies:** `/nes-scan-rom`
- **Hard limit:** 2 attempts. If both fail: recommend Mesen debugger, mark UNKNOWN.

#### Skill: `/nes-build-manifest`
- **Purpose:** Create or update a game manifest with all known facts
- **Inputs:** ROM scan results, trace analysis, user identifications
- **Outputs:** `extraction/manifests/{game}.json`
- **Type:** Deterministic (JSON assembly from verified data)
- **Dependencies:** `/nes-scan-rom` (minimum), optionally `/nes-capture`

#### Skill: `/nes-validate-track`
- **Purpose:** Parse one track from ROM and compare to trace
- **Inputs:** Manifest (with pointer table), trace CSV, track number
- **Outputs:** Validation report (pitch match %, volume match %, user verdict)
- **Type:** Deterministic (parse + compare) + Human ear (final verdict)
- **Dependencies:** `/nes-find-pointer-table`, `/nes-capture`
- **Gate:** Must PASS before batch extraction

#### Skill: `/nes-batch-extract`
- **Purpose:** Parse all tracks, render MIDI + WAV + REAPER projects
- **Inputs:** Validated manifest (pointer table VERIFIED)
- **Outputs:** Full output package per track
- **Type:** Deterministic (batch parse + render)
- **Dependencies:** `/nes-validate-track` MUST have passed

#### Skill: `/nes-separate-sfx`
- **Purpose:** Split a trace render into music-only and SFX-only + per-channel stems
- **Inputs:** Trace CSV, frame range
- **Outputs:** `output/{Game}/wav/separated/` (music, sfx, 4 stems)
- **Type:** Heuristic (pitch-jump detection) + Human validation
- **Dependencies:** `/nes-render-trace`

#### Skill: `/nes-rip` (ORCHESTRATOR)
- **Purpose:** Process a new game end-to-end with minimal prompting
- **Inputs:** Game name + ROM path
- **Outputs:** Invokes skills in order, tracks progress, produces final package
- **Type:** Orchestration (calls other skills in dependency order)
- **Dependencies:** All skills available
- **User interaction:** Requests trace captures, confirms track IDs, approves validation

---

### === LAYER 2: ENFORCEMENT RULES ===

OBJECTIVE: Define preconditions, postconditions, and hard failures for every skill.

SCOPE CONSTRAINTS:
- DO: specify what each skill checks before running and what it must produce
- DO NOT: implement the checks (specs only)

OUTPUT CONTRACT:

| Skill | Precondition | Postcondition | Hard Failure |
|-------|-------------|---------------|-------------|
| `/nes-capture` | capture.csv exists at user path | File copied to traces/{game}/ | File not found → STOP |
| `/nes-render-trace` | traces/{game}/capture{N}.csv exists | WAV file created, duration > 0 | Empty trace → STOP |
| `/nes-render-nesmdb` | nesmdb pkl files exist for game | WAVs created, rate field validated | Median pitch > MIDI 80 on pulse → WARN |
| `/nes-segment` | Trace WAV exists | Segment WAVs + segment table | No silence gaps found → single segment, WARN |
| `/nes-scan-rom` | ROM file exists at extraction/roms/ | Manifest created/updated with VERIFIED fields | ROM header invalid → STOP |
| `/nes-find-pointer-table` | Manifest exists with mapper field | pointer_table_address updated | 2 failed attempts → mark UNKNOWN, recommend debugger, STOP |
| `/nes-build-manifest` | ROM scan completed | Valid JSON with all required fields | Missing required field → STOP |
| `/nes-validate-track` | Manifest has pointer_table (verified or candidate), trace exists | Validation report with pitch match % | No trace → REFUSE TO RUN. Pitch < 90% → FAIL |
| `/nes-batch-extract` | `/nes-validate-track` PASSED | Full output package | Validation not passed → REFUSE TO RUN |
| `/nes-separate-sfx` | Trace CSV exists | 6 WAV files (music, sfx, 4 stems) | No audio in range → WARN |

**Enforcement pattern for every skill:**
```
1. Check preconditions. If ANY fails: print what's missing, STOP.
2. Execute deterministic work.
3. Check postconditions. If ANY fails: print what went wrong, STOP.
4. Update manifest with results (never overwrite VERIFIED fields).
5. Print summary of what was produced.
```

---

### === LAYER 3: MANIFEST SCHEMA ===

OBJECTIVE: Define the canonical JSON schema for game manifests.

OUTPUT CONTRACT:

```json
{
  "game": "string (required)",
  "rom_file": "string (path, required)",
  "mapper": "integer (required, VERIFIED by rom header)",
  "prg_banks": "integer (required, VERIFIED)",
  "chr_banks": "integer (VERIFIED)",
  "driver_family": "string: maezawa | contra_variant | fujio | unknown (required)",
  "driver_family_confidence": "string: verified | high | medium | low | rejected",
  "driver_family_evidence": "string: disassembly | rom_scan | trace | hypothesis",

  "period_table": {
    "address": "string: hex or NOT_FOUND",
    "format": "string: contiguous_16bit | split_lohi | extended | computed | unknown",
    "tuning": "string: maezawa_exact | contra_variant | cv3_variant | unknown",
    "entry_count": "integer",
    "status": "string: verified | candidate | not_found"
  },

  "pointer_table": {
    "address": "string: hex or UNKNOWN",
    "format": "string: grouped_9byte | triple_3byte | nested_pairs | flat | unknown",
    "bank": "integer or null",
    "track_count": "integer or null",
    "status": "string: verified | candidate | unknown"
  },

  "sound_bank": "integer or null",
  "vibrato_detected": "boolean",
  "dx_byte_count": "integer or null (2 for CV1, 3 for Contra)",
  "envelope_model": "string: parametric | lookup_table | unknown",
  "percussion_model": "string: inline | dmc_channel | unknown",

  "traces": [
    {
      "file": "string (path)",
      "frames": "integer",
      "duration_sec": "number",
      "track_identified": "string or null",
      "identified_by": "string: user | nesmdb_match | unidentified"
    }
  ],

  "tracks_extracted": [
    {
      "number": "integer",
      "name": "string",
      "validated_against_trace": "boolean",
      "pitch_match_pct": "number or null",
      "output_version": "string (v1, v2...)"
    }
  ],

  "status": "string: new | scanning | parsing | validated | complete | dead_end",
  "notes": "string (free-form observations)"
}
```

**Update rules:**
- Never overwrite a field with status VERIFIED using a field with status candidate/hypothesis
- Append to traces array, never replace
- Increment output_version, never overwrite files
- status field progresses: new → scanning → parsing → validated → complete
- status can regress to dead_end from any state

---

### === LAYER 4: DEPENDENCY GRAPH & PROMPT DESIGN ===

OBJECTIVE: Define execution order, parallelism, and minimal prompt patterns.

OUTPUT CONTRACT:

**Dependency graph:**
```
/nes-capture ─────────────→ /nes-render-trace → /nes-segment
                                                      │
/nes-render-nesmdb (parallel) ──────────────────────── │ (cross-ref)
                                                      │
/nes-scan-rom ──→ /nes-find-pointer-table ────────────┤
       │                                               │
       └──→ /nes-build-manifest ←──────────────────────┘
                    │
                    ▼
            /nes-validate-track ← (GATE: trace + pointer table required)
                    │
                    ▼ (GATE: validation PASSED)
            /nes-batch-extract

/nes-separate-sfx (independent, runs after /nes-render-trace)
```

**Parallel execution:**
- `/nes-capture` + `/nes-scan-rom` + `/nes-render-nesmdb` can all run in parallel
- `/nes-render-trace` and `/nes-segment` are sequential (render before segment)
- `/nes-find-pointer-table` blocks on `/nes-scan-rom`
- `/nes-validate-track` blocks on BOTH pointer table AND trace

**Human input required at:**
- `/nes-capture`: user must capture in Mesen and provide CSV path
- `/nes-segment`: user must identify which segment is which track
- `/nes-validate-track`: user must listen and give PASS/FAIL verdict

**Minimal prompt patterns (post-skill-system):**

| User says | System does |
|-----------|------------|
| "new game: Super C" | `/nes-rip` orchestrator: create manifest, scan ROM, prompt for trace |
| "SAVED: capture.csv" | `/nes-capture` → `/nes-render-trace` → `/nes-segment` |
| "that's Thunder Landing" | Update manifest traces[].track_identified |
| "find the pointer table" | `/nes-find-pointer-table` (2 attempts, then recommend debugger) |
| "validate" | `/nes-validate-track` (refuses if no trace or no pointer table) |
| "extract all" | `/nes-batch-extract` (refuses if validation hasn't passed) |

---

## 5. Execution Notes

**Deterministic skills (build once, trust always):**
- `/nes-capture`, `/nes-render-trace`, `/nes-render-nesmdb`, `/nes-scan-rom`, `/nes-build-manifest`, `/nes-batch-extract`

**Judgment-required skills (always validate output):**
- `/nes-find-pointer-table` (heuristic scoring), `/nes-separate-sfx` (pitch-jump threshold)

**Human-gated skills:**
- `/nes-segment` (track naming), `/nes-validate-track` (listening test)

**Shared infrastructure (implement as python modules, not per-skill):**
- `utils/trace_renderer.py` — trace CSV → WAV (any game)
- `utils/nesmdb_renderer.py` — exprsco pkl → WAV (with rate validation)
- `utils/silence_detector.py` — frame volumes → gap list
- `utils/melody_comparator.py` — compare note sequences across segments
- `utils/period_converter.py` — period ↔ frequency ↔ MIDI
- `utils/bank_resolver.py` — mapper + bank + CPU addr → ROM offset
- `utils/manifest_io.py` — read/write/validate manifest JSON

**Caching:** Manifests persist across sessions. nesmdb renders persist per game. Trace renders are versioned and never overwritten.

**Implementation priority:**
1. Manifest schema + `/nes-build-manifest` (anchors everything)
2. `/nes-capture` + `/nes-render-trace` (immediate value, game-agnostic)
3. `/nes-scan-rom` (replaces ad-hoc ROM scanning scripts)
4. `/nes-rip` orchestrator (ties it together)
5. Everything else follows from usage
