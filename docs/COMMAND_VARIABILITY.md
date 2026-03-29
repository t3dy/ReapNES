# NES Sound Driver Command Variability

How command systems differ across NES sound drivers, and what that means
for automated parsing.

## 1. Fixed vs Variable Length Commands

NES sound drivers span a spectrum from fully fixed-size to deeply
variable-length command encodings.

**Fixed-length (1 byte, self-contained):**
Notes in the Konami Maezawa driver encode both pitch and duration in a
single byte. High nibble = pitch (0-B), low nibble = duration multiplier.
Octave commands (E0-E4) and rests (C0-CF) are also single-byte. This is
the simplest case: the parser always advances by 1.

**Opcode-dependent variable length (1-4 bytes):**
The DX instrument command is where the Maezawa driver becomes variable.
In CV1, DX reads 2 extra bytes for pulse (instrument + fade) and 0 for
triangle. In Contra, DX reads 3 extra bytes for pulse (config + vol_env
+ decrescendo) and 1 for triangle. The FE repeat command always reads
3 extra bytes (count + 16-bit address). FD subroutine reads 2 extra
bytes (16-bit address).

**Context-dependent variable length:**
The DX command's byte count depends on which channel is being parsed.
Triangle channels skip the fade/envelope bytes that pulse channels read.
The parser must track channel identity as state. The optional F0 sweep
prefix in CV1 adds further conditionality: after reading the fade byte
on a pulse channel, the parser must peek at the next byte to decide
whether a sweep parameter follows.

**The full spectrum across NES drivers:**

| Driver family | Length model | Worst case |
|---------------|-------------|------------|
| Konami Maezawa (CV1) | Mostly fixed, DX variable by channel | DX + inst + fade + F0 + sweep = 5 bytes |
| Konami Maezawa (Contra) | Same opcodes, different DX byte counts | DX + config + vol_env + decrescendo = 4 bytes |
| Capcom (Mega Man) | Fixed 2-byte notes (pitch, duration separate) | Uniform, predictable |
| Sunsoft (Batman, Blaster Master) | Variable with envelope table refs | Commands carry inline table pointers |
| HAL (Kirby, EarthBound proto) | Heavily variable, multi-byte everything | Long inline parameter sequences |
| FDS/MMC5 drivers | Extension channel commands mixed in | Extra registers for expansion audio |

The key insight: even within a single driver family (Konami Maezawa),
the byte count for the same opcode (DX) differs between games. This is
not documented in the opcode itself. It is an implicit contract between
the driver code and the data.

## 2. Polymorphic Commands

A polymorphic command is one where the same opcode byte triggers
different parsing behavior depending on context that is not encoded
in the byte itself.

### DX: The canonical example

DX ($D0-$DF) in the Maezawa driver sets the tempo multiplier via its
low nibble. But the bytes that follow differ:

| Game | Channel | Extra bytes | Content |
|------|---------|-------------|---------|
| CV1 | Pulse | 2 | instrument ($4000 format), fade (start/step nibbles) |
| CV1 | Triangle | 0 | nothing |
| Contra | Pulse | 3 | channel config, vol_env index, decrescendo multiplier |
| Contra | Triangle | 1 | triangle config ($4008 value) |

The opcode byte is identical. The parser must know (a) which game it is
parsing and (b) which channel it is parsing to determine how many bytes
to consume. Get this wrong and every subsequent byte in the stream is
misaligned. There is no recovery mechanism: a 1-byte miscount corrupts
the entire remaining parse.

### E8: Same opcode, different semantics

In CV1, E8 sets a flag that enables the parametric volume fade system.
In Contra, E8 sets a "flatten note" flag with different behavioral
implications. The opcode is the same. The hardware effect differs.

### EC: Unused vs active

In CV1, EC falls into the "invalid E-command" range (E5-EF except E8-EA)
and produces silence. In Contra, EC is a pitch adjustment command that
reads an additional parameter byte. A CV1 parser encountering EC skips
1 byte. A Contra parser must read 2 bytes. Again, misidentifying the
game corrupts the parse stream.

### EB: Vibrato

In CV1, EB is invalid/silent (1 byte). In Contra, EB initiates vibrato
and reads 2 parameter bytes. Three bytes difference for the same opcode.

### How common is polymorphism?

Within a single driver family: very common. The Maezawa driver has at
least 4 opcodes (DX, E8, EB, EC) where the same byte means different
things or reads different byte counts depending on game and channel.

Across different driver families: universal. Every NES sound driver
defines its own command set. There is no standard. An opcode that means
"set tempo" in one driver might mean "jump to subroutine" in another.
The byte $E8 has no inherent meaning on the NES.

## 3. Channel-Dependent Semantics

The NES APU has 5 channels with different hardware capabilities:
2 pulse (square wave), 1 triangle, 1 noise, 1 DMC (sample playback).
Drivers exploit these differences.

### Instrument setup (DX) varies by channel type

Pulse channels have duty cycle, volume, and envelope parameters.
Triangle has no volume control (always max or off) and no duty cycle,
so its instrument data is shorter or absent. Noise has no pitch in the
melodic sense. DMC references sample addresses and lengths.

The DX command must dispatch differently per channel:

| Channel | CV1 DX reads | Contra DX reads |
|---------|-------------|-----------------|
| Pulse 1 | inst + fade (+ optional sweep) | config + vol_env + decrescendo |
| Pulse 2 | inst + fade (+ optional sweep) | config + vol_env + decrescendo |
| Triangle | nothing | tri_config |
| Noise | not documented (CV1 noise is inline E9/EA) | only tempo nibble, no extra bytes |

### Percussion: inline vs separate stream

CV1 embeds percussion triggers (E9 = snare, EA = hi-hat) inline within
pulse channel data, immediately following a note byte. The parser must
peek after every note to check for trailing drum triggers.

Contra uses a completely separate noise/DMC channel with its own data
stream and its own command format. In the percussion stream, the high
nibble of a non-control byte selects the sample type (kick, snare,
hi-hat, combinations) rather than a melodic pitch. The low nibble is
still a duration multiplier.

This means the same byte value $23 means "D# with duration 3" on a
pulse channel but "hi-hat with duration 3" on Contra's percussion
channel.

### Octave: irrelevant on noise

Octave commands (E0-E4) shift the period table lookup. On noise
channels, there is no period table — the noise register uses a 4-bit
value for rate selection. Octave commands in a noise stream would be
meaningless, though most drivers avoid emitting them there.

## 4. Control Flow Commands

### Loops (FE)

The Maezawa driver uses `FE count addr_lo addr_hi`:
- `count` = number of passes through the loop body
- $FF = infinite loop (song repeat point)
- The driver maintains a per-channel counter in zero-page RAM

Finite loops require stateful tracking. The parser must remember how
many times it has encountered each FE instruction (keyed by ROM offset)
and count down. The CV1 and Contra parsers share identical FE semantics.

### Subroutines (FD)

`FD addr_lo addr_hi` saves the return address and jumps to the target.
`FF` returns from the subroutine (or ends the channel if not in a sub).
The parser maintains a return stack. Subroutines can contain any command
including notes, rests, and even nested control flow.

This is powerful for data compression (shared phrases between channels
or songs) but adds complexity: the parser must follow jumps into
arbitrary ROM locations, potentially across bank boundaries in
bank-switched mappers.

### What other drivers do

| Driver | Loop mechanism | Subroutines | Conditionals |
|--------|---------------|-------------|-------------|
| Konami Maezawa | FE count+addr | FD addr, FF return | None |
| Capcom (MM series) | Repeat markers with count | Call/return | None |
| Sunsoft | Nested loops with stack | Yes, with deep nesting | Volume-conditional branches |
| Squaresoft (FF1) | Simple repeat | No subroutines | None |
| HAL | Complex loop/branch | Yes | Conditional on register state |
| FamiTracker | Pattern-based (no inline loops) | Groove tables | None (tracker model) |

Konami Maezawa sits in the middle: it has loops and subroutines but no
conditional execution. This makes it deterministic — the parse path
depends only on the data, not on runtime state. Drivers with
conditionals are much harder to parse statically because the branch
taken depends on APU register values that only exist at runtime.

## 5. Tempo and Timing Systems

### Frame-based (Konami Maezawa)

Duration in frames = `tempo * (duration_nibble + 1)`.

Tempo is set by the low nibble of the DX command (1-15). Duration
nibble is the low nibble of each note/rest byte (0-15). The smallest
unit is 1 frame (1/60s at NTSC). There is no sub-frame timing.

BPM depends on which duration value represents a quarter note. If
duration 3 (4 units) is a quarter: BPM = 3600 / (tempo * 4).

This system is simple and frame-accurate but has limited time
resolution. The finest grid is 1x tempo frames. Swing and groove are
impossible without alternating duration values manually in the data.

### Tick-based (other drivers)

Some drivers use a tick counter that subdivides frames:
- N ticks per frame (configurable)
- Duration in ticks, not frames
- Allows finer timing resolution and tempo changes mid-song

This is more flexible but harder to trace-validate because the tick
clock may drift relative to the frame counter.

### Comparison

| Aspect | Frame-based (Maezawa) | Tick-based (generic) |
|--------|----------------------|---------------------|
| Resolution | 1/60s (16.67ms) | Sub-frame (configurable) |
| Tempo encoding | DX low nibble (1-15) | Separate tempo register |
| Swing/groove | Not natively supported | Possible via tick offsets |
| Trace validation | Direct frame comparison | Requires tick-to-frame alignment |
| Parsing complexity | Low (multiply and count) | Medium (tick accumulator state) |

## 6. Note Encoding

### Pitch as index (Konami Maezawa)

The high nibble (0-B) indexes into a 12-entry period table. Combined
with the current octave (set by E0-E4), this gives the full pitch.
This is compact (1 byte per note) but limits pitch to the 12-tone
equal temperament grid.

### Direct period (some drivers)

Some drivers encode the raw 11-bit APU period value directly as 2
bytes. This allows microtonal pitch, portamento targets, and detuning
but costs twice the ROM space per note.

### Duration encoding variants

| Approach | Example | Bytes per note | Flexibility |
|----------|---------|---------------|-------------|
| Nibble-combined (Maezawa) | $47 = E, duration 7 | 1 | 16 durations only |
| Separate byte | pitch, then duration | 2 | 256 durations |
| Implicit (previous duration) | pitch only, reuse last | 1 | Requires state |
| Run-length | note + repeat count | 2-3 | Good for sustained notes |

The Maezawa approach is the most compact but the least flexible. 16
possible duration values (multiplied by tempo) cover common rhythmic
values but cannot express arbitrary lengths. Tied notes or rests must
be used to fill gaps.

## Generalized Parseability Model

What makes a command system parseable by an automated tool:

### Parseable (deterministic, static analysis sufficient)

1. **Fixed or opcode-determined length.** Given the first byte of a
   command, the parser can determine exactly how many bytes to consume
   without external state.

2. **No runtime conditionals.** The parse path depends only on the data
   stream, not on simulated hardware state.

3. **Bounded control flow.** Loops have finite counts. Subroutines do
   not recurse. The call depth is bounded.

4. **Documented or discoverable pointer table.** Track start addresses
   can be found without executing the driver code.

5. **Consistent semantics across channels.** Or, if channel-dependent,
   the channel identity is known at parse time.

### Resistant to automated parsing

1. **Context-dependent byte counts** (DX reading different amounts per
   game). Requires a per-game configuration that cannot be inferred
   from the data alone.

2. **Runtime-conditional branches.** The parser would need to simulate
   the APU to know which branch is taken.

3. **Self-modifying code.** Some drivers patch their own command stream
   at runtime. Static analysis sees different data than what executes.

4. **Implicit state carry-over.** If a command's meaning depends on a
   flag set by a previous command in a different channel, the parser
   must simulate multi-channel interleaving.

5. **Undocumented or computed pointer tables.** If track addresses are
   computed by the driver at runtime (e.g., indirect through multiple
   tables), finding them requires reverse engineering the driver code.

### Scorecard

| Factor | CV1 | Contra | Hypothetical "hard" driver |
|--------|-----|--------|---------------------------|
| Command length determinism | High (DX varies by channel only) | High (same, different counts) | Low (runtime-dependent) |
| Runtime conditionals | None | None | Yes (volume-gated branches) |
| Control flow complexity | Low (1-deep sub, finite loops) | Low (same) | High (nested, recursive) |
| Pointer table accessibility | Direct ROM offset | Disassembly-documented | Computed at runtime |
| Channel consistency | DX varies, rest is uniform | DX + percussion differ | Every opcode differs |
| **Overall parseability** | **High** | **High (with correct config)** | **Low** |

## Comparison Table: CV1 vs Contra vs Other Patterns

| Feature | CV1 | Contra | Capcom (Mega Man) | Sunsoft (Batman) |
|---------|-----|--------|-------------------|-----------------|
| Note encoding | 1 byte (pitch+dur nibbles) | Same | 2 bytes (pitch, duration) | 1-2 bytes variable |
| Tempo system | Frame-based (DX nibble) | Same | Tick-based | Tick-based |
| DX extra bytes (pulse) | 2 | 3 | N/A (separate instrument cmd) | Variable |
| DX extra bytes (triangle) | 0 | 1 | N/A | Variable |
| Envelope model | Parametric (3 params) | Lookup table (54 entries) | Predefined table | Multi-stage ADSR table |
| Percussion | Inline E9/EA triggers | Separate DMC channel | Separate noise stream | Separate channel |
| Subroutines | FD/FF (1-deep) | Same | Similar | Nested |
| Loops | FE count+addr | Same | Pattern-based | Stack-based nested |
| Pitch adjustment | None (E5-EF invalid) | EC + parameter byte | Pitch slide commands | Portamento + vibrato |
| Vibrato | None | EB + 2 params | Built-in per-instrument | Table-driven |
| Sweep | Optional F0+param after DX | Not used | Not exposed | Not exposed |
| Bank switching | N/A (mapper 0 linear) | Mapper 2 (bank 1) | Mapper 1/4 | Mapper 1/4 |
| Pointer table | 9-byte entries at fixed ROM offset | Flat 3-byte entries | Per-bank tables | Indirect through header |

## Implications for Our Pipeline

### The parser architecture must handle:

1. **Per-game DX byte counts.** The manifest JSON must declare
   `dx_extra_bytes_pulse` and `dx_extra_bytes_triangle`. The parser
   must read these values, not assume them. This is already implemented
   via separate parser classes (KonamiCV1Parser vs ContraParser), but
   a future generic Maezawa parser should dispatch on manifest config.

2. **Per-game E-command interpretation.** The set of valid E-commands
   and their parameter byte counts must be declared per game. EB reads
   0 extra bytes in CV1 but 2 in Contra. EC reads 0 in CV1 but 1 in
   Contra. A table mapping opcode to byte count per game would
   eliminate this class of bug.

3. **Channel-aware parsing.** The parser must know the channel type
   before it begins parsing a stream. This determines DX byte count,
   whether percussion decoding applies, and whether triangle-specific
   rules (no fade bytes, octave offset) are active.

4. **Bank-switched address resolution.** The `cpu_to_rom` function
   differs between CV1 (linear) and Contra (bank-switched). The
   manifest's `resolver_method` field already captures this. Every
   address conversion in the parser must go through the correct
   resolver, especially for FD subroutine targets and FE loop targets.

5. **Envelope strategy dispatch.** The frame IR must select the correct
   volume model based on `DriverCapability`, not on parser class
   identity. CV1 uses parametric fade. Contra uses lookup tables. A
   future game might use a third model. The IR's `isinstance` checks
   (if any remain) are a scaling liability.

### What the manifest must declare for any new game:

```
command_format.dx_extra_bytes_pulse
command_format.dx_extra_bytes_triangle
command_format.c0_semantics
command_format.percussion
command_format.e_command_table  (NEW: opcode -> param byte count)
rom_layout.resolver_method
envelope_model.type
```

The `e_command_table` field does not exist yet. Adding it would make
E-command parsing data-driven rather than code-branched.

## Failure Risks If Misunderstood

### 1. DX byte count mismatch (CATASTROPHIC)

If the parser reads 2 extra bytes after DX but the game sends 3, every
byte after the first DX command is misaligned. Notes become rests,
rests become control commands, and control commands consume note data.
The output is garbage with no obvious error signal — just wrong music.

This happened during the CV1-to-Contra transition. The parser assumed
CV1's 2-byte DX format. Contra sends 3 bytes. The result: mangled
output that took 3 prompts to diagnose. Cost: 3 prompts.

### 2. E-command parameter count mismatch (CATASTROPHIC)

Same mechanism as DX but harder to detect. If EB reads 0 extra bytes
(CV1 assumption) but the game sends 2 (Contra reality), the two
vibrato parameter bytes are interpreted as the next two commands. This
silently corrupts the parse from that point forward.

### 3. Wrong address resolver (SILENT CORRUPTION)

Using `cpu_to_rom()` (linear, mapper 0) on a bank-switched ROM
produces valid-looking but incorrect ROM offsets. The parser reads
data from the wrong location. It may still parse without errors (the
byte patterns can look like valid commands) but the music is wrong.

### 4. Channel type confusion (SUBTLE)

Parsing a triangle stream as pulse causes the parser to read 2 extra
bytes after DX that do not exist. Parsing a pulse stream as triangle
causes it to skip 2 bytes it should have read. Both corrupt the
remaining parse.

Parsing Contra's separate percussion channel as a melodic channel
turns drum sample selectors into note pitches. The output plays a
melody where there should be a drum pattern.

### 5. Assuming same driver from same period table (WASTED EFFORT)

CV2 (Simon's Quest) has an identical period table to CV1 — the same
12 frequency values at the same relative positions. But CV2 uses a
completely different sound engine (Fujio variant). The pointer table
format, command set, and envelope system are all different. Scanning
for the period table and concluding "same driver" led to 4 wasted
prompts trying to find CV1-style pointer tables in CV2's ROM.

The period table is a hardware-derived constant (equal temperament
tuning for the NES APU). Every NES game that plays music in tune has
some version of it. It proves nothing about the driver.

### 6. Infinite loop misdetection (HANG)

FE $FF = infinite loop (song repeat). If the parser fails to detect
this and follows the jump, it loops forever. The safety limit
(max_events / max_bytes) catches this but produces truncated output
that silently drops the song's ending or repeat structure.

### 7. Subroutine target in wrong bank (GARBAGE)

FD jumps to a CPU address. If the address resolver maps it to the
wrong ROM bank, the subroutine reads random data. The parser may
not crash (the data might happen to contain $FF which terminates the
sub) but the musical content is wrong.

## Summary

NES sound driver command systems are compact, stateful, and
context-dependent. Even within the Konami Maezawa family — two games
sharing the same codebase lineage — at least 4 opcodes have different
byte counts or semantics. The parser cannot assume anything about a
new game from the driver family alone. Every game needs its own
manifest declaring the exact command format, and the parser must be
configured by that manifest rather than by hardcoded assumptions.

The highest-risk failure mode is byte count mismatch on variable-length
commands (DX, EB, EC). A single miscount corrupts the entire remaining
byte stream with no error signal. The defense is: read the disassembly
(or trace the driver in an emulator) before writing any parser code,
and validate against an APU trace before trusting the output.
