# WISH #14: Commit Strategy for Antigravity Work

## 1. What This Wish Is

Define a clean commit strategy for the remaining untracked Antigravity
session artifacts. A large commit (`a9213ae`, 305 files, 48,982
insertions) already landed the bulk of the work -- docs, code pages,
song sets, MIDI exports, scripts, test files, and trace data. This wish
covers the ~40 files that remain untracked, plus the 5 deleted MIDI
files and 1 modified settings file that need decisions.

## 2. Why It Matters

- **106 MB of WAV files** sit untracked across three directories
  (`cv1_wav/`, `Castlevania_II/wav/`, `Castlevania_III/wav/`). WAVs are
  already gitignored by the `*.wav` glob, so they will never enter git
  unless the ignore rule is overridden or LFS is configured. This is
  correct behavior -- but it means these artifacts exist ONLY on the
  local machine.
- **20 REAPER project files** (`.rpp`) for CV1 and Contra are untracked.
  These are text files (XML-like) and represent real creative work.
- **19 remapped Bach MIDI files** in `midi_remapped/` are untracked.
  These are the NES-constrained Bach arrangements used by the mashup
  pipeline.
- **1 screenshot** (`CVscreenshot.png`) and **1 `.claude/` directory**
  inside `studio/reaper_projects/` are untracked.
- **5 v2 MIDI files** are staged as deleted from
  `extraction/exports/midi/castlevania/`. These were superseded by v4.
- If the local machine fails, everything not committed is gone.

## 3. Current State

### Already committed (a9213ae)

| Category | Count | Notes |
|----------|-------|-------|
| Jekyll site docs (swarm + follow-up) | ~35 files | All `code/*.md` and `docs/*.md` |
| Song set palettes | 49 JSON files | Full collection in `studio/song_sets/` |
| Bach mashup scripts | 3 new scripts | `bach_render_mashup.py`, `render_batch.py`, `bach_nes_mashup.py` |
| CV2/CV3 MIDI + YouTube desc | ~20 files | Output MIDI and text files |
| REAPER projects (bach_mashups/) | ~117 files | The combinatorial Fugue matrix |
| Trace data | 2 JSON files | `data/trace_diff_contra.json`, `trace_diff_cv1.json` |
| Test files | 2 files | `test_envelope_invariants.py`, `test_parser_invariants.py` |
| Adventure log + audit report | 4 files | `ANTIGRAVITYADVENTURES.md`, `CLAUDEREPORTSONANTIGRAVITY.md`, etc. |

### Still untracked

| Path | Type | Size | Action Needed |
|------|------|------|---------------|
| `output/cv1_wav/` | WAV files | 69 MB | Gitignored (*.wav). Backup manually or add to LFS. |
| `output/Castlevania_II/wav/` | WAV files | 20 MB | Gitignored (*.wav). Same. |
| `output/Castlevania_III/wav/` | WAV files | 17 MB | Gitignored (*.wav). Same. |
| `studio/reaper_projects/cv1_01_Prologue.rpp` through `cv1_15_Death_SFX.rpp` | RPP (text) | 15 files | **Commit.** Full CV1 soundtrack REAPER projects. |
| `studio/reaper_projects/Contra_Jungle.rpp` | RPP | 1 file | **Commit.** |
| `studio/reaper_projects/Contra_Jungle_v3.rpp` | RPP | 1 file | **Commit.** |
| `studio/reaper_projects/Contra_Jungle_v4.rpp` | RPP | 1 file | **Commit.** |
| `studio/reaper_projects/VampireKiller_v2.rpp` | RPP | 1 file | **Commit.** |
| `studio/reaper_projects/VampireKiller_v4.rpp` | RPP | 1 file | **Commit.** |
| `studio/reaper_projects/midi_remapped/*.mid` | MIDI | 19 files, 788 KB | **Commit.** NES-remapped Bach MIDIs. |
| `studio/reaper_projects/CVscreenshot.png` | PNG | 20 KB | **Commit.** Small enough for git. |
| `studio/reaper_projects/.claude/` | Config | unknown | **Gitignore or skip.** Session-local Claude config, not useful to others. |

### Staged deletions (working tree)

| Path | Action |
|------|--------|
| `extraction/exports/midi/castlevania/vampire_killer_v2.mid` | **Commit the deletion.** Superseded by v4. |
| `extraction/exports/midi/castlevania/vk_v2_ch0_pulse1.mid` | Same. |
| `extraction/exports/midi/castlevania/vk_v2_ch1_pulse2.mid` | Same. |
| `extraction/exports/midi/castlevania/vk_v2_ch2_triangle.mid` | Same. |
| `extraction/exports/midi/castlevania/vk_v2_ch3_noise.mid` | Same. |

### Modified tracked files

| Path | Action |
|------|--------|
| `.claude/settings.local.json` | **Do not commit.** Local IDE settings. |

## 4. Concrete Steps

### Step A: Commit the REAPER projects and remapped MIDIs

```bash
git add studio/reaper_projects/cv1_*.rpp
git add studio/reaper_projects/Contra_Jungle*.rpp
git add studio/reaper_projects/VampireKiller_*.rpp
git add studio/reaper_projects/midi_remapped/
git add studio/reaper_projects/CVscreenshot.png
git commit -m "Add CV1/Contra REAPER projects and NES-remapped Bach MIDIs"
```

This is ~20 RPP files + 19 MIDI files + 1 PNG. All are small text/binary
files appropriate for git.

### Step B: Commit the v2 MIDI deletions

```bash
git add extraction/exports/midi/castlevania/vampire_killer_v2.mid
git add extraction/exports/midi/castlevania/vk_v2_ch*.mid
git commit -m "Remove superseded v2 MIDI exports (replaced by v4)"
```

### Step C: Gitignore the REAPER Claude config

Add to `.gitignore`:

```
# REAPER project Claude session config
studio/reaper_projects/.claude/
```

### Step D: Handle WAV files (choose one)

The 106 MB of WAVs are already gitignored by `*.wav`. Three options:

1. **Do nothing** -- WAVs are regenerable from the committed MIDI +
   scripts + song sets. Accept the risk that re-rendering takes time.
2. **Manual backup** -- Copy to an external drive or cloud storage.
3. **Git LFS** -- Track `output/*/wav/*.wav` in LFS. Adds complexity
   but keeps everything in one repo. Only worth it if the repo will be
   shared or if local backup discipline is weak.

Recommendation: Option 1 (do nothing). The WAVs are deterministically
reproducible from committed artifacts. The render scripts and song set
JSONs are already committed.

### Step E: Verify completeness

```bash
git status -s
```

After steps A-D, the only remaining items should be:
- `.claude/settings.local.json` (modified, never commit)
- `output/*/wav/` directories (gitignored)
- `studio/reaper_projects/.claude/` (newly gitignored)

## 5. Estimated Effort

| Step | Time |
|------|------|
| A: Commit RPP + MIDI | 2 minutes |
| B: Commit v2 deletions | 1 minute |
| C: Gitignore update | 1 minute |
| D: WAV decision | 0 minutes (if option 1) |
| E: Verify | 1 minute |
| **Total** | **5 minutes** |

## 6. Dependencies

- None. All steps are independent of any code changes.
- Steps A and B can be done in either order.
- Step C should happen before or with step A to avoid accidentally
  staging the `.claude/` directory.

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| WAV loss from disk failure | Low | Medium (re-renderable but time-consuming) | Manual backup or LFS |
| Committing `.claude/settings.local.json` | Low | Low (noise in diff) | Already in awareness; do not stage |
| RPP files contain absolute local paths | High | Low (REAPER resolves gracefully) | Document that RPP paths assume `C:\Dev\NESMusicStudio` |
| Large repo size from MIDI/RPP accumulation | Low | Low (current total is modest) | Monitor; LFS if repo exceeds 500 MB |

## 8. Success Criteria

- `git status -s` shows zero actionable untracked files (only gitignored
  items and `.claude/settings.local.json` remain).
- All 15 CV1 REAPER projects, 3 Contra REAPER projects, and 2
  VampireKiller REAPER projects are tracked.
- All 19 NES-remapped Bach MIDIs are tracked.
- The 5 superseded v2 MIDI files are deleted from the repo.
- WAV files remain gitignored (regenerable from committed sources).
- No secrets, ROM files, or copyrighted material committed.

## 9. Priority Ranking

**Priority: P3 (Low) -- but should be done immediately anyway.**

This is pure housekeeping with near-zero risk and 5 minutes of effort.
The large commit already landed the important work. What remains is
cleanup that prevents future confusion ("why are these RPP files not
tracked?") and protects against data loss for the remapped Bach MIDIs,
which represent non-trivial creative curation work.

Do it now, before the next feature session creates more untracked files
and the cleanup scope grows.
