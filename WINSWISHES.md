# Wins & Wishes

A retrospective on what worked, what we learned, and what we still want.
Written from the full documentation corpus (80+ files, ~500KB) produced
across the CV1, Contra, and Antigravity sessions.

---

## WINS

### 1. The Trace Changed Everything

Before we had a Mesen APU trace, we were guessing. After, we were
measuring. The entire project pivoted the moment we captured Vampire
Killer's 1792 frames and compared our extraction against hardware
ground truth. Every subsequent fix — the octave bug, the phase2_start
clamping, the EC pitch adjustment, the bounce-at-1 — came from looking
at what the hardware actually did, not reasoning about what it should do.

**Lesson:** Capture the trace BEFORE building the parser. 20 frames of
real data are worth more than 2000 words of analysis. This is now the
first gate in the workflow for every new game.

### 2. The Evidence Hierarchy Holds

We established a reliability ranking and it proved out repeatedly:

1. APU trace (catches everything, including systematic errors)
2. Annotated disassembly (explains WHY the trace looks like it does)
3. Automated trace comparison (catches most errors, misses shared bugs)
4. Ear comparison (catches gross errors, misses 1-semitone offsets)
5. Reasoning about byte meanings (least reliable, most seductive)

The octave bug is the proof: automated comparison showed zero mismatches
while every note was one octave wrong. Both the parser and the trace
converter shared the same mapping bug. Only a human ear caught it. And
the EC pitch bug is the inverse proof: the melody sounded right (just
in a slightly different key), but the trace showed every note was
exactly +1 semitone flat across all 23 unique pitches.

**Lesson:** Never trust any single layer of verification. The trace
catches what automation misses. The ear catches what the trace can't
(when both sides share the same bug). Use all of them.

### 3. One Fix at a Time Actually Works

The CV1 envelope model went through 3 wrong hypotheses before we
dumped trace data and looked at real frame values. Cost: 5 prompts.
The trace extraction that resolved it cost 1 prompt. After that we
adopted "one hypothesis, one test, measure the delta" and never
looked back.

**Lesson:** Resist the urge to fix three things at once. Change one
thing, re-run trace_compare, check if the mismatch count went down.
If it did, commit. If it didn't, revert. This discipline saved us
from the debugging hell of entangled changes.

### 4. Cross-Game Work Finds Bugs That Single-Game Testing Can't

The phase2_start clamping bug was invisible in CV1 testing. It
affected 9 notes, each off by 1 volume step on the first frame.
Nobody would ever hear that. But working on Contra forced us to
re-examine every assumption in the shared envelope code, and the
bug fell out. One-line fix: `max(1, duration - fade_step)`.
Result: 45 volume mismatches eliminated on CV1 pulse.

**Lesson:** The second game is more valuable than the first. The
first game teaches you the driver. The second game teaches you which
of your assumptions were actually driver-specific vs game-specific.
The third game will teach us which are family-specific.

### 5. Manifests Prevent Re-Discovery

Every fact about a game's ROM layout, command format, and driver
behavior goes into a JSON manifest with explicit status labels:
`verified`, `hypothesis`, `unknown`. When a new session starts,
reading the manifest tells the LLM what's known and what's uncertain.
Without this, the Contra session would have spent 3 prompts
rediscovering that DX reads 3 bytes on pulse instead of 2.

**Lesson:** Write down what you know, what you think, and what you
don't know — separately and explicitly. The manifest is the
institutional memory that survives session boundaries.

### 6. The Disassembly Shortcut Is Real

Reading the Contra annotated disassembly took one prompt. It
identified the DX byte count difference, the separate percussion
channel, the volume envelope lookup table structure, and the EC pitch
adjustment command. Doing this by scanning ROM bytes would have cost
5-10 prompts of trial and error.

**Lesson:** Always check for an existing disassembly before touching
a ROM. 10 minutes reading saves hours guessing. This is now step 3
in the new-ROM workflow, and it's not optional.

### 7. The Mistake-Baking Strategy Works

Every bug that cost 2+ prompts got written as a warning into the
system files that Claude reads at session start. "Same period table
does NOT prove same driver" is positioned to fire when starting a
new game. "Dump trace data before modeling" fires when debugging.
"Check all channels, not just one" fires when testing.

These aren't documentation — they're tripwires. They intercept the
mistake BEFORE it happens because they're positioned at the exact
decision point where the mistake would occur.

**Lesson:** Don't just fix bugs. Write the warning where the next
person (or the next LLM session) will read it at the moment they're
about to make the same mistake.

### 8. Swarm Agents Are Documentation Machines

10 agents, 5 minutes wall clock, 130KB of structured documentation,
zero file conflicts. The swarm pattern works beautifully for
read-many-write-one tasks where each agent produces a single file
from shared source material. 70-80% completion rate with the rest
gap-filled manually.

**Lesson:** Use swarms for documentation, taxonomy, and analysis —
never for logic changes to existing code. Plan for 20-30% failure.
Assign one file per agent, not two. The value isn't 100% automation;
it's 70% automation plus preserved context in the main session.

### 9. The Bach Mashups Proved the Pipeline End-to-End

Taking Bach MIDI files and rendering them through NES instrument
envelopes from 8 different games was the ultimate integration test.
It exercised the preset bank (54,000 entries), the song set
extraction, the project generator, and a custom Python NES APU
synth — all in one creative workflow. 28 rendered WAVs, 188 REAPER
projects, 49 song set palettes.

**Lesson:** Creative side-quests aren't distractions. They stress-test
the pipeline in ways that unit tests never will, and they produce
artifacts that demonstrate the system's value to others.

### 10. CV2 and CV3 Extractions Worked (Partially)

Despite HANDOVER.md calling CV2 a "dead end" (different driver), the
Antigravity session extracted 7 of ~15 tracks. CV3 yielded 10 of ~25.
Both produced full MIDI/WAV/MP4 pipelines. The partial success
suggests more driver overlap than we previously concluded — or that
some tracks happen to be coincidentally parseable.

**Lesson:** Try it anyway. The worst case is you learn exactly where
and why it breaks. The best case is you get partial results that
inform the next round of investigation.

### 11. Context Engineering Is the Meta-Skill

CLAUDE.md (31 lines, compressed from 120), path-specific rules that
auto-load, manifests, handover docs, NEXT_SESSION_PROMPT.md — the
entire context engineering stack exists because each new LLM session
starts with zero memory. The prompts saved per session compound:
3 prompts saved x 8 sessions = 24 prompts = roughly a full session
of wasted work avoided.

**Lesson:** The most valuable code in the project isn't the parser
or the frame IR. It's the system of files that ensures every session
starts from the right baseline and doesn't repeat known mistakes.

---

## WISHES

### 1. Contra Trace Capture

The single highest-value action never completed. We have a Contra
parser at 96.6% volume accuracy, but the trace that would push it
to CV1-level perfection hasn't been captured. Every remaining Contra
gap (decrescendo timing, UNKNOWN_SOUND_01, triangle precision) is
blocked on this.

**What it would unlock:** Frame-level validation of all 54 envelope
tables, decrescendo onset timing, DMC sample timing, noise register
values. The 3.4% volume gap would either close or become precisely
characterized.

### 2. Triangle Linear Counter Precision

195 sounding mismatches on CV1, labeled APPROXIMATE. The current
formula `(reload+3)//4` is off by 1 frame on ~8 notes per loop.
Fixing this requires modeling the APU's 240Hz quarter-frame sequencer
— a hardware-level project that's fascinating but non-trivial.
Estimated 3-5 sessions.

### 3. The Third Konami Game

Super C is the natural next target: same driver family, mapper 2,
9 of 15 tracks already parsed with the CV1 parser. It would be the
third data point that reveals which assumptions are truly universal
vs game-specific. The unified Maezawa parser (FLEXIBLE_PARSER_
ARCHITECTURE Phase 2) should wait for this game.

### 4. Vibrato and Pitch Envelopes

The EB vibrato command is documented with parameter encoding but
never implemented because no CV1 or Contra track uses it. We need
a game that does — TMNT and Gradius are likely candidates. Without
this, the parser silently skips EB bytes, which is fine for current
games but will corrupt output on games that use vibrato.

### 5. DMC Sample Decoding

Contra has 283 DAC changes in Jungle alone. Two physical samples
(81 bytes hi-hat, 593 bytes snare) sit at $FC00 in bank 7. We
know where they are, we know the format, we just haven't decoded
them. The render_wav.py synthesizer uses white noise for all
percussion. Real DPCM samples would transform the drum sound.

### 6. Expansion Audio

CV3 JP (Akumajou Densetsu) has the best Castlevania soundtrack on
NES and it uses VRC6 (2 extra pulse + sawtooth). CV3 US uses MMC5
(2 extra pulse, no sawtooth — a downgrade). Neither is supported.
Priority ranking from HARDWARE_VARIANTS: MMC5 first (trivial synth,
enables CV3 US), VRC6 second (enables the superior CV3 JP).

### 7. Address Resolver Abstraction

Two hardcoded functions (`cpu_to_rom` for mapper 0, `contra_cpu_to_rom`
for mapper 2). Every new mapper type currently requires a new function.
The FLEXIBLE_PARSER_ARCHITECTURE proposes an AddressResolver ABC with
implementations for Linear, BankSwitched, MMC3, MMC5. This is the
highest-priority infrastructure for scaling to new games.

### 8. Runtime Manifest Loading

Manifests exist as reference documents but parsers don't load them at
runtime. Addresses, byte counts, and track lists are still hardcoded
in parser source. Moving to manifest-driven parsing would mean adding
a new game requires only a JSON file and an ear-check, not code changes
(for games within the same driver family).

### 9. Website Deployment

The Antigravity session built an entire Jekyll site: annotated source
code (3,701 lines), LLM methodology paper (543 lines), research log,
invariants registry, open problems bounty board, game matrix, trace
tutorials, and the Bach mashup collection. The content exists. The
`_config.yml` exists (hacker theme). It's not deployed. The user said
"go build and deploy the website" and then the session apparently moved
on to other things.

### 10. The Combinatorial Fugue Matrix

117 REAPER projects in `studio/reaper_projects/bach_mashups/` — Fugues
1, 2, 5, 7 crossed with every CV1 and Contra instrument palette. Zero
WAV files. The crash likely interrupted the batch render. Running
`render_batch.py` on this folder would complete the collection.

### 11. CV2 Investigation Revisited

7 tracks extracted despite the "dead end" label. Which tracks parsed
correctly? Which are garbled? Is the Fujio driver actually closer to
Maezawa than we concluded? A focused listening session comparing the
WAVs against the game would settle this and potentially re-open CV2
as a viable target.

### 12. Non-Konami Drivers

The taxonomy identifies Capcom (Mega Man series) as the second-best
pipeline ROI after finishing Konami. The Capcom driver covers 10-15
games from one parser. Sunsoft (Batman, Blaster Master, Journey to
Silius) is third. Neither has been touched. The onboarding workflow
and failure mode catalog were written specifically to make the first
non-Konami game feasible without repeating every Konami mistake.

### 13. Noise Channel Modeling

Every percussion hit in the pipeline uses the same white noise synth.
Real NES noise has 16 rate presets and 2 modes (long/short sequence)
that produce dramatically different timbres. Snare, hi-hat, kick, and
tom sounds come from different period+mode combinations. Extracting
and applying these per-drum parameters would improve percussion realism
significantly.

### 14. Committing the Antigravity Work

None of it is in git. The scripts, song sets, Bach mashups, CV2/CV3
extractions, 36 new docs, annotated source code, trace data JSONs,
and the session prompt are all sitting untracked in the working
directory. One crash away from gone.
