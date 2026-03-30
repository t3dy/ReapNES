# WISH #4: Vibrato and Pitch Envelopes (EB Command)

## 1. What This Wish Is

Implement support for the EB vibrato command in the Konami Maezawa
sound driver. EB sets up per-frame pitch modulation (LFO) on pulse
channels, causing the NES APU period register to oscillate around the
base note pitch. The parser currently reads and discards the two
parameter bytes to keep the stream aligned, but neither the parser
nor the frame IR models the pitch modulation effect.

## 2. Why It Matters

Vibrato is a standard musical expression technique. While no CV1 or
Contra music track data stream issues an EB command, the vibrato
engine code is fully present in both ROMs and the Contra disassembly
confirms it is wired into the per-frame update loop. Other games in
the Maezawa family (Super C, TMNT, Goonies II, Gradius II) may use
EB in their music data. Without EB support, any game that uses
vibrato would produce flat, lifeless sustained notes where the
original has pitch movement. This is an audible fidelity gap that
cannot be fixed by volume envelope modeling alone.

## 3. Current State (What We Know About EB)

### Command encoding (VERIFIED from Contra disassembly)

```
EB PP QQ    (3 bytes total)

PP = VIBRATO_DELAY — number of frames after note onset before
     vibrato begins. If PP == $FF, vibrato is disabled (VIBRATO_CTRL
     set to $80).

QQ = VIBRATO_AMOUNT — packed byte:
     High nibble (>> 4) = cycle length (controls how many frames
       per vibrato half-cycle; compared against a frame counter
       derived from VIBRATO_DELAY)
     Low nibble (& $0F) = pitch deviation amount (added to or
       subtracted from the base period register value)
```

### Vibrato engine behavior (from disassembly `pulse_sustain_note`)

The vibrato system operates per-frame on pulse channels only (slots
0 and 1). Triangle and noise are excluded.

1. On each frame, if `VIBRATO_CTRL != $80` (vibrato enabled),
   increment `SOUND_VOL_TIMER`.
2. When `SOUND_VOL_TIMER >= VIBRATO_DELAY`, call
   `pulse_sustain_note`.
3. Inside `pulse_sustain_note`, a 4-phase cycle runs via
   `VIBRATO_CTRL` (values 0-3):
   - Phase 0 (even): no pitch change, use base period (`PULSE_NOTE`)
   - Phase 1 (odd): pitch DOWN by `VIBRATO_AMOUNT & $0F`
   - Phase 2 (even): no pitch change, use base period
   - Phase 3 (odd): pitch UP by `VIBRATO_AMOUNT & $0F`
   - Cycle repeats (wraps from 3 back to 0)
4. Phase advances when `(VIBRATO_AMOUNT >> 4) == (negated frame
   counter)`, creating a speed-dependent cycle.

The waveform is a 4-step approximation of a sine: center, down,
center, up, repeat. The depth is symmetric (same amount up and down).
The speed is controlled by the high nibble of QQ interacting with
the delay counter.

### Parser handling today

- **CV1 parser** (`parser.py`): Treats EB as an invalid E-command.
  Falls through to `OctaveChange(0xB, offset)` and advances 1 byte.
  This is a byte-count BUG: CV1's EB handler likely also reads 2
  parameter bytes (the engine code exists in both ROMs), so the CV1
  parser would desynchronize if EB appeared in CV1 music data.

- **Contra parser** (`contra_parser.py`): Correctly consumes 3 bytes
  (EB + 2 params) but discards the parameter values. No event is
  emitted. Marked as a known limitation in the STATUS block.

### Disassembly confirmation

The Contra disassembly at `@set_vibrato_vars_adv` (the EB handler
in the E-nibble dispatch) shows:
1. Read byte 1 -> store as `VIBRATO_DELAY`
2. If byte 1 == $FF -> disable vibrato, skip byte 2
3. Read byte 2 -> store as `VIBRATO_AMOUNT`
4. Set `VIBRATO_CTRL` to 0 (vibrato active, starting at phase 0)

The disassembly comments explicitly state the vibrato code path is
never executed in Contra because no track data contains EB with a
non-$FF delay value.

## 4. Concrete Steps

### Step 1: Fix CV1 parser EB byte count (BUG FIX)

The CV1 parser treats EB as a 1-byte command. It should consume 3
bytes (EB + 2 params), same as Contra. Even though no CV1 track uses
EB, the parser must handle the byte count correctly to avoid stream
desynchronization if EB is encountered in a future game using the
CV1 parser path.

**Files:** `extraction/drivers/konami/parser.py`
**Test:** Existing trace comparison must still pass (no CV1 track
uses EB, so this is a no-op in practice).

### Step 2: Add VibratoSetup event type

Create a new event dataclass that captures the EB parameters:

```python
@dataclass
class VibratoSetup(Event):
    delay_frames: int      # PP byte (frames before vibrato starts)
    cycle_speed: int       # QQ high nibble (phase advance rate)
    depth: int             # QQ low nibble (period deviation)
    disabled: bool         # True if PP == 0xFF
    offset: int = 0
```

**Files:** `extraction/drivers/konami/parser.py` (event definition)

### Step 3: Emit VibratoSetup events from both parsers

Both the CV1 and Contra parsers should emit `VibratoSetup` when EB
is encountered, replacing the current skip-only logic.

**Files:** `parser.py`, `contra_parser.py`

### Step 4: Model vibrato in the frame IR

Add per-frame pitch modulation to `frame_ir.py`. For each sounding
frame on a pulse channel:

1. If `vibrato_enabled` and `frames_since_note_start >= delay`:
   - Compute current phase (0-3) from frame counter and cycle speed
   - Phase 1: subtract depth from base period
   - Phase 3: add depth to base period
   - Phases 0, 2: use base period unchanged
2. Convert modulated period to a pitch bend value

This requires the frame IR to track per-channel vibrato state
(delay, speed, depth, current phase, frame counter).

**Files:** `extraction/drivers/konami/frame_ir.py`

### Step 5: Express vibrato in MIDI output

Map the per-frame pitch deviation to MIDI pitch bend messages.
The NES period modulation maps to cents deviation from the base
note. MIDI pitch bend with a +/-2 semitone range should cover
typical NES vibrato depths.

**Files:** `extraction/drivers/konami/midi_export.py`

### Step 6: Validate against a game that uses EB

Find a Maezawa-family game where EB appears in music data. Scan
ROM data streams for the byte pattern. Capture a Mesen APU trace
and compare the period register oscillation against our model.

**Files:** New game manifest, trace comparison scripts.

## 5. Estimated Effort

| Step | Effort | Notes |
|------|--------|-------|
| Fix CV1 parser byte count | 15 min | Trivial: add EB case to E-command handler |
| VibratoSetup event type | 15 min | New dataclass, add to imports |
| Emit events from parsers | 30 min | Modify both parser E-command handlers |
| Frame IR vibrato model | 2-3 hours | Core work: per-frame state machine, phase cycling, period modulation |
| MIDI pitch bend output | 1-2 hours | Map period deviation to pitch bend, write CC messages |
| Find and validate a test game | 2-4 hours | Scanning ROMs, capturing traces, comparing |

**Total: 6-10 hours** (mostly in steps 4-6).

Steps 1-3 can be done immediately with no test game. Steps 4-6
require a game that actually uses EB to validate against.

## 6. Dependencies

### Hard dependency: a game that uses EB in its music data

Without real EB usage in a track, the vibrato model cannot be
validated. The Contra disassembly confirms EB is unused there.
CV1 usage is unconfirmed but unlikely (the CV1 spec lists EB-EF
as invalid/silent).

**Candidate games to scan:**
- Super C (same driver family, may use EB for boss music)
- TMNT (Konami, likely Maezawa variant)
- Goonies II (Konami, same era)
- Gradius II (Konami, same era)

The scan is mechanical: parse each channel's data stream and check
for $EB bytes in E-command position. This can be done with the
existing parser infrastructure by adding a counter.

### Soft dependency: render_wav.py pitch modulation

The Python WAV renderer would need to support per-frame period
changes to audibly reproduce vibrato. Currently it sets the period
once per note. This is a rendering enhancement, not a data
extraction issue.

## 7. Risks

### Risk 1: No test game available (HIGH)

If none of the candidate games use EB, the implementation cannot
be validated. Mitigation: implement steps 1-3 (correct byte count
and event emission) regardless, since these are defensive fixes.
Defer steps 4-6 until a test game is found.

### Risk 2: Vibrato parameter interpretation is wrong (MEDIUM)

The cycle speed derivation involves a subtraction and comparison
that is not fully intuitive from the disassembly. The relationship
between `VIBRATO_AMOUNT >> 4` and the frame counter may produce
unexpected cycle lengths. Mitigation: trace-level validation
against a real game is mandatory before marking as verified.

### Risk 3: MIDI pitch bend granularity (LOW)

NES vibrato operates on raw 11-bit period values. The pitch
deviation in cents is nonlinear (depends on the base period).
MIDI pitch bend is linear in cents. Very deep vibrato at low
pitches may not map cleanly. Mitigation: compute cents from
period ratio, not from a linear approximation.

### Risk 4: CV1 parser EB byte count is already wrong (LOW)

If any future game uses the CV1 parser path and contains EB, the
current 1-byte handling will desynchronize the entire parse. This
is a latent bug. The fix (step 1) eliminates it.

## 8. Success Criteria

1. **Byte count correctness**: Both parsers consume exactly 3 bytes
   for EB (command + 2 params). Verified by trace comparison
   showing zero regressions on CV1 and Contra.

2. **Event emission**: `VibratoSetup` events appear in the parsed
   song data when EB is present in the data stream, with correct
   delay, speed, and depth values.

3. **Frame-level pitch accuracy**: For a game that uses EB, the
   per-frame period values produced by the frame IR match the Mesen
   APU trace `$4002/$4003` period registers within +/-1 (hardware
   rounding). Measured across at least one full vibrato cycle.

4. **MIDI fidelity**: Playing the MIDI output in a DAW produces
   audible pitch wobble that matches the character of the original
   game's vibrato (same speed, similar depth). User ear-confirms.

5. **No regressions**: CV1 trace comparison (1792 frames) and
   Contra trace comparison (2976 frames) show zero new mismatches
   after all changes.

## 9. Priority Ranking

**Priority: LOW (P3)**

Rationale:
- No currently supported game (CV1, Contra) uses EB.
- The vibrato engine code exists but is dormant in both games.
- The byte-count fix (step 1) is worth doing immediately as a
  defensive measure, but the full vibrato model (steps 4-6) is
  blocked on finding a test game.
- Other checklist items with higher fidelity impact (noise period
  values, DMC sample extraction, mid-note duty changes) should be
  addressed first.
- This becomes P1 the moment a new game is added that uses EB.

**Recommended approach**: Do steps 1-3 now (30-60 minutes, fixes a
latent parser bug and prepares the event pipeline). Park steps 4-6
until a Maezawa-family game with active EB usage is identified.
