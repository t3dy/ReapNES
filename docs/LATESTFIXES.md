# Latest Fixes and Reverse Engineering Learnings

## The Fix Timeline

### Fix 1: Octave Off By One (v3)
**Problem**: Every note was one octave too high. A3 in the game played as A4.
**Cause**: The base MIDI note for octave E4 (no period shift) was set to 36 (C2)
instead of 24 (C1).
**Evidence**: APU trace period 511 at the first note maps to 218.5 Hz = A3 (MIDI 57).
Our formula with base=36 produced MIDI 69 (A4). With base=24: MIDI 57.
**Fix**: Changed `BASE_MIDI_OCTAVE4 = 36` to `24` in parser.py.

### Fix 2: FE Repeat Count Semantics (v4)
**Problem**: Section A played 3 times instead of 2. This caused the B section to
start at the wrong byte position, producing wrong notes from frame ~896 onward.
**Cause**: The parser treated `FE 02` as "repeat 2 more times" (3 total), but the
real driver treats it as "2 total passes."
**Evidence**: Disassembly of `_loc_0352` shows the driver increments counter $06,x
before comparing to the count byte. For count=2: counter goes 0→1 (≠2, loop back),
1→2 (==2, done). That's 2 total passes, 1 loop-back.
**Fix**: Changed first-encounter logic from `count - 1` remaining to `count - 2`
remaining loop-backs after the initial loop-back.

### Fix 3: Envelope Model (v4)
**Problem**: Notes played at constant volume for their full duration, sounding
legato/sustained instead of staccato/plucked.
**Cause**: The `fade_start` parameter was interpreted as "frames to delay before
decay starts." In reality it's the **number of volume decrements.**
**Evidence**: Instrument $F4 (vol=4, fade=4/1) in the trace shows:
frame 0: vol=4, frame 1: vol=3, frame 2: vol=2, frame 3: vol=1, frame 4: vol=0.
That's 4 decrements starting at frame 1. `fade_start=4` = 4 decrements, not
4 frames of delay.
Instrument $F3 (vol=3, fade=1/0): frame 0: vol=3, frame 1: vol=2, then holds.
1 decrement, then sustain. `fade_start=1` = 1 decrement.
**Fix**: Rewrote frame IR envelope to decrement vol by 1 per frame starting at
frame 1, for exactly `fade_start` frames. Hold at resulting volume thereafter.

### Fix 4: Channel Mapping in REAPER (v2)
**Problem**: The project generator's auto-mapper put triangle bass on the pulse track
and drums on the triangle track. Drums were silent.
**Cause**: The auto-mapper detects drums via GM channel 9, but our extracted MIDI uses
NES channel 3 for drums. Also, the auto-mapper re-analyzed already-correct channel
assignments, getting them wrong.
**Fix**: Added `--nes-native` flag to skip remapping. Created per-channel MIDI files
so each REAPER track loads only its own channel's notes.

### Fix 5: CC11/CC12 Synth Support (v3)
**Problem**: Volume dynamics and duty cycle changes in the MIDI were being ignored
by the JSFX synth.
**Cause**: The synth only handled CC1 (mod wheel) for duty. It didn't respond to
CC11 (expression/volume) or CC12 (timbre/duty in nesmdb standard).
**Fix**: Added CC11 and CC12 handlers to the @block section of ReapNES_APU.jsfx.
CC11 maps 0-127 to NES vol 0-15. CC12 maps raw 0-3 to duty cycle.

### Fix 6: Envelope Off-By-One (v5)
**Problem**: Volume mismatch at frame 4 of notes with vol=4, fade=4/1.
Our IR showed vol=1, trace showed vol=0.
**Cause**: Volume decrement was applied AFTER writing the frame state.
**Fix**: Apply decrement BEFORE writing — so frame 4 gets the decremented value.

### Fix 7: E8 Gate Removal (v5)
**Problem**: Sq2 had 1518 volume mismatches because fading wasn't applied.
**Cause**: The E8 (EnvelopeEnable) command was gating the fade system, but Sq2
has zero E8 commands. E8 does NOT gate fading.
**Fix**: Removed `envelope_enabled` check. Fading always active when fade_start > 0.

### Fix 8: fade_step Decoded (v5)
**Problem**: Instruments with fade_step > 0 showed vol=1 at the last frame of
notes where the trace showed vol=0.
**Cause**: `fade_step` was undocumented. It controls a RELEASE phase at the end
of each note: `fade_step` 1-per-frame decrements on the last `fade_step` frames.
**Evidence**: $B5 (fade=2/3) shows 3 decrements on the last 3 frames of every note.
$B4 (fade=3/1) shows 1 decrement on the last frame. $F3 (fade=1/0) holds forever.
**Fix**: Added Phase 2 release to envelope model.

### Fix 9: Triangle Linear Counter (v5)
**Problem**: Triangle had 518 sounding-state mismatches — notes sounding for
their full duration instead of silencing when the linear counter expired.
**Cause**: Triangle notes are gated by $4008 (linear counter), not volume.
The instrument byte IS the $4008 register value.
**Fix**: Model linear counter decay as `(reload + 3) // 4` sounding frames.
Control bit (bit 7) = sustain for full duration.

### Fix 10: MIDI Export Rebuilt from Frame IR (v5)
**Problem**: MIDI notes played at constant volume for full duration — too legato.
**Cause**: Export used raw parser events, not the frame IR with envelope data.
**Fix**: Complete rewrite: walks frame IR, emits shortened notes with CC11
volume automation per-frame. Staccato articulation matches game audio.

---

## What We Learned About the ROM Structure

### The Konami Maezawa Driver Architecture

Castlevania 1 uses the Konami pre-VRC sound driver (Maezawa variant, ~1986).
The same driver family is used in Contra, Super C, TMNT, Goonies II, and
Gradius II.

**It is NOT a data format. It is a virtual machine.**

The driver runs as a frame-based interpreter:
- Every NMI (60Hz), each of 6 channel slots is processed
- Each slot has its own data pointer, duration counter, and state variables
- When the duration counter expires, the next byte is read and interpreted
- The same byte can mean different things depending on execution context

### The Command Set

| Byte Range | Meaning |
|-----------|---------|
| $00-$BF | Note: high nibble = pitch (C-B), low nibble = duration |
| $C0-$CF | Rest: low nibble = duration |
| $D0-$DF | Tempo + instrument: sets speed, reads instrument byte + fade params |
| $E0-$E4 | Set octave (0=highest, 4=lowest) |
| $E8 | Enable volume envelope processing |
| $E9 | Trigger snare drum |
| $EA | Trigger hi-hat |
| $FD | Jump to subroutine (with return stack) |
| $FE | Repeat section (counter-based) |
| $FF | End channel / return from subroutine |

### The Instrument System

Each "instrument" is the raw APU register 0 value (DDLCVVVV):
- DD (bits 7-6) = duty cycle: 0=12.5%, 1=25%, 2=50%, 3=75%
- L (bit 5) = length counter halt
- C (bit 4) = constant volume flag
- VVVV (bits 3-0) = volume (0-15)

There are NO envelope tables in ROM. Envelopes are two-phase parametric:
- Phase 1: `fade_start` = number of volume decrements (1/frame from frame 1)
- Hold: volume maintains at `(initial_vol - fade_start)`
- Phase 2: `fade_step` = number of 1/frame decrements on the LAST frames
- If `fade_step=0`, hold indefinitely (no release)
- E8 command does NOT gate fading — fading is always active

For triangle: the instrument byte IS $4008 (linear counter register):
- Bit 7: control (1=sustain/reload, sounds full duration)
- Bits 6-0: reload value; triangle sounds ~(reload/4) frames

### The Note Period Table

12 entries at ROM $079A, one per semitone (C through B).
Base octave E4 periods verified against NTSC CPU clock (1789773 Hz):

| Note | Period | Frequency |
|------|--------|-----------|
| C | 1710 | 65.4 Hz |
| A | 1017 | 109.9 Hz |
| B | 906 | 123.3 Hz |

Higher octaves: period = base >> (4 - octave_value).
E0 shifts 4 times (highest). E4 shifts 0 times (base/lowest).

### The Pointer Table

15 tracks x 3 channels (Sq1, Sq2, Tri) at ROM $0825.
Each entry is 9 bytes: 3 x (2-byte LE pointer + 1-byte separator).
Noise/drums are embedded as E9/EA triggers within the melodic channel data.

### The Repeat System (FE)

The driver uses a per-channel counter at $06,x:
- Counter starts at 0
- Each FE encounter: increment counter, compare with count byte
- Equal → done (skip past FE, reset counter to 0, set duration=1)
- Less → loop back to target address

The "set duration=1" after FE resolve is critical — it means the driver
spends one frame doing nothing before reading the next command byte.

---

## What We Learned About Reverse Engineering Method

### 1. The Trace Is Ground Truth
We wasted time reasoning about what bytes "should" mean. The trace tells you
what they DO mean. When the trace says C#3 and our parser says D3, the parser
is wrong — full stop. Don't rationalize the discrepancy.

### 2. State Context Matters More Than Byte Values
The same byte ($D7) can be a tempo command, a rest, or part of a note depending
on which code path the driver is executing. The driver is a VM with multiple
entry points. You cannot decode bytes without knowing which handler is active.

### 3. Structural Errors Cascade
The repeat count bug (off by one iteration) didn't just add extra notes —
it shifted the data pointer so that ALL subsequent bytes were read at the wrong
offset. One state error at a control flow boundary corrupted everything after it.

### 4. Fix In Priority Order: Pitch → Timing → Volume → Sound Design
Pitch errors are the most audible and easiest to verify against the trace.
Timing errors (wrong note durations) are next. Volume/envelope errors affect
feel but not melodic accuracy. Sound design (duty cycle, synth behavior) is
last because it only matters when the notes and timing are right.

### 5. Frame-Based Comparison Is Non-Negotiable
The `trace_compare.py` tool compares at frame resolution — there is no
ambiguity. A pitch mismatch at frame 896 means something specific went wrong
at that exact moment. Comparing by ear or by MIDI event count is too coarse
to catch these bugs.

### 6. Disassembly + Trace = Complete Understanding
Neither source alone is sufficient:
- The disassembly tells you HOW the driver works (code paths, state variables)
- The trace tells you WHAT the driver actually does (ground truth output)
Cross-referencing both is what caught the repeat count bug: the disassembly
showed the counter increments before comparing, the trace proved the B section
started at the right address when the count was fixed.

---

## Current State

**Vampire Killer extraction: 0 pitch mismatches across all 3 channels for the
full 1792-frame song.** Verified frame-by-frame against emulator APU trace.

Remaining work is volume envelope accuracy (687-1728 frame mismatches per
channel) and rebuilding MIDI export from the frame IR for proper articulation.
