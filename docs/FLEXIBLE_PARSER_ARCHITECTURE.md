# Flexible Parser Architecture

Architectural blueprint for handling multiple NES sound drivers in
NES Music Studio. Written from analysis of the CV1 and Contra
implementations as they exist today (2026-03-28).

---

## 1. Current State

### What exists

Two parsers live under `extraction/drivers/konami/`:

| File | Purpose | Lines |
|------|---------|-------|
| `parser.py` | CV1 parser + shared data structures + shared utilities | ~665 |
| `contra_parser.py` | Contra parser (imports shared types from parser.py) | ~533 |
| `frame_ir.py` | Frame IR generation + DriverCapability + envelope strategies | ~545 |
| `midi_export.py` | MIDI export from frame IR | ~355 |
| `spec.md` | Command format documentation + per-game differences | ~330 |

### What is shared vs duplicated

**Truly shared (used by both parsers):**
- Data structures: `NoteEvent`, `RestEvent`, `InstrumentChange`, `DrumEvent`,
  `OctaveChange`, `EnvelopeEnable`, `RepeatMarker`, `SubroutineCall`,
  `EndMarker`, `ChannelData`, `ParsedSong`
- `pitch_to_midi()` function
- `read_ptr_le()` utility
- `INES_HEADER_SIZE` constant
- `CHANNEL_NAMES` dict
- `PITCH_NAMES` list

**Duplicated with variation:**
- Channel parser main loop (nearly identical structure, different command
  handlers for DX, E-series, percussion)
- FE/FD/FF repeat/subroutine/end handling (identical logic, different
  `cpu_to_rom` function)
- Song-level `parse_track` (same pattern: iterate channels, create
  ChannelData, collect instruments)
- ROM loading + iNES validation (identical in both top-level parsers)

**Fully game-specific:**
- `cpu_to_rom` vs `contra_cpu_to_rom` (mapper 0 vs mapper 2 banking)
- Pointer table format and addresses
- DX instrument parsing (2 extra bytes vs 3/1)
- E-series command semantics (E8 = envelope enable vs flatten; EC = unused
  vs pitch adjust; EB = unused vs vibrato)
- Percussion model (inline E9/EA vs separate channel with DMC)
- Volume envelope extraction (`extract_envelope_tables`)
- Track address tables (ROM constants vs hardcoded dict)

### Coupling points

The `contra_parser.py` imports shared types from `parser.py`. This works
but creates an awkward dependency: `parser.py` is simultaneously the CV1
parser AND the shared type library. The `InstrumentChange` dataclass has
Contra-specific fields (`vol_env_index`, `decrescendo_mul`, `vol_duration`)
that are meaningless for CV1.

The `frame_ir.py` dispatches on `DriverCapability.volume_model` (a string
literal). This is the correct pattern. The deprecated `envelope_tables`
parameter is a compatibility shim that should eventually be removed.

---

## 2. Pluggable Game Configs (Manifest-Driven Parsing)

### Principle

The manifest JSON (`extraction/manifests/*.json`) already captures the
per-game facts that determine parsing behavior. The architecture should
be: **manifest declares, parser executes**.

### What belongs in the manifest (data)

These are facts about the ROM and driver that vary per game but do not
require new code:

```
rom_layout.mapper              → selects address resolver
rom_layout.sound_bank          → bank number for bank-switched mappers
rom_layout.resolver_method     → "linear" | "bank_switched"
pointer_table.rom_offset       → where to find track pointers
pointer_table.format           → "9_byte_entries" | "flat_sound_table" | ...
pointer_table.entry_size       → bytes per entry
pointer_table.num_tracks       → how many tracks
command_format.dx_extra_bytes_pulse    → 2 (CV1) or 3 (Contra)
command_format.dx_extra_bytes_triangle → 0 (CV1) or 1 (Contra)
command_format.c0_semantics    → "rest_with_duration" | "mute_instant"
command_format.percussion      → "inline_e9_ea" | "separate_channel_dmc"
envelope_model.type            → "two_phase_parametric" | "lookup_table"
tracks                         → per-track channel addresses (or pointer
                                 table offset if auto-discoverable)
```

### What belongs in code (behavior)

These require actual logic and cannot be reduced to config:

- How to decode the bytes after a DX command (field meanings differ)
- E-series command dispatch (EC means nothing in CV1, pitch adjust in
  Contra; EB is unused in CV1, vibrato in Contra)
- Percussion channel parsing (different command set)
- Envelope table extraction (ROM-specific binary format)
- Address resolution logic (linear vs bank-switched formula)

### Config-driven dispatch pattern

```python
class MaezawaParser:
    """Config-driven parser for the Konami Maezawa driver family."""

    def __init__(self, rom_path: str, manifest: dict):
        self.rom = load_rom(rom_path)
        self.manifest = manifest
        self.resolver = get_resolver(manifest["rom_layout"])
        self.command_config = manifest["command_format"]
```

The manifest tells the parser HOW MANY bytes to read after DX but a
game-specific handler interprets WHAT THOSE BYTES MEAN. This is the
boundary between config and code.

---

## 3. Driver-Specific Modules

### When a separate module is needed

A new parser module is justified when ANY of these are true:

1. **Different command byte format.** The opcode space (high nibble
   meanings) is different. Example: Capcom uses different opcodes for
   notes, rests, and control flow.
2. **Different update loop architecture.** The per-frame processing
   model differs (tick rate, channel priority, SFX interaction).
3. **Different period table structure.** Not just different values
   (that is config) but different encoding (e.g., frequency instead
   of period, or indexed differently).
4. **No shared command heritage.** If you cannot map the new driver's
   commands onto the existing note/rest/DX/E-series/F-series structure,
   it is a different driver.

A new module is NOT needed when:
- Same command format, different byte counts (config)
- Same commands, different ROM addresses (manifest)
- Same driver, different mapper (address resolver)

### Module tree organization

Organize by **driver family**, not by publisher:

```
extraction/drivers/
    __init__.py
    shared/
        __init__.py
        types.py          ← NoteEvent, RestEvent, ParsedSong, etc.
        address.py        ← cpu_to_rom resolvers (linear, bank_switched)
        rom_utils.py      ← iNES parsing, read_ptr_le, etc.
        pitch.py          ← pitch_to_midi, period tables, freq conversion
    konami/
        __init__.py
        maezawa.py        ← unified config-driven parser for CV1/Contra/SuperC
        maezawa_handlers.py  ← per-game DX/E-command handler registries
        envelope.py       ← envelope strategy functions
        spec.md
    capcom/
        __init__.py
        capcom_driver.py  ← Mega Man 2 family parser
        NOTES.md
    sunsoft/
        __init__.py
        sunsoft_5b.py     ← Sunsoft 5B expansion audio driver
    nintendo/
        __init__.py
        NOTES.md
```

Why by driver family, not publisher: Konami used multiple sound drivers
across their NES catalog. CV1 and Contra share the Maezawa driver. CV2
uses the Fujio driver. Grouping by publisher would put incompatible
parsers in the same directory. Grouping by driver family keeps related
code together and unrelated code apart.

However, the current `konami/` directory is fine for now because all
implemented code IS the Maezawa family. The `capcom/`, `sunsoft/`, etc.
directories already exist as stubs. The reorganization described above
should happen when the second driver family gets real code.

---

## 4. Shared Engine Abstractions

### What can be shared across ALL drivers

**ParsedSong / ParsedNote data structures** (`shared/types.py`)

The event types (`NoteEvent`, `RestEvent`, `InstrumentChange`, etc.) are
the contract between parser and IR. They should be:
- Defined in `extraction/drivers/shared/types.py`
- Imported by every parser
- NOT extended with game-specific fields in the base types

For game-specific instrument data, use a `metadata` dict field:

```python
@dataclass
class InstrumentChange:
    tempo: int
    raw_instrument: int
    duty_cycle: int
    volume: int
    offset: int
    metadata: dict = field(default_factory=dict)
    # metadata examples:
    #   CV1: {"fade_start": 3, "fade_step": 2}
    #   Contra: {"vol_env_index": 12, "decrescendo_mul": 4, "vol_duration": 8}
```

**Frame IR generation** (`frame_ir.py`)

The frame IR is already designed for multi-driver use. The
`DriverCapability` object declares the volume model, and
`parser_to_frame_ir` dispatches on it. This pattern scales: add a new
volume_model literal, add a new strategy function, register it.

The IR itself (`FrameState`, `ChannelIR`, `SongIR`) is hardware-level
and does not change between drivers.

**MIDI export** (`midi_export.py`)

Already driver-agnostic. It consumes `SongIR` (from frame IR) and
`ParsedSong` (for drums and loop markers). No driver-specific code.
The only change needed for new drivers: the drum mapping table should
be configurable rather than hardcoded to GM snare/hihat.

**Trace comparison** (`trace_compare.py`)

Already supports `--game` parameter with per-game config dict. Adding a
new game means adding an entry to `GAME_CONFIGS`. The comparison logic
itself is pure: it compares two `SongIR` objects frame by frame.

**Address resolution** (`shared/address.py`)

Currently split between `cpu_to_rom` (in parser.py, mapper 0/linear)
and `contra_cpu_to_rom` (in contra_parser.py, mapper 2/bank-switched).
These should be extracted into a resolver module:

```python
def get_resolver(rom_layout: dict) -> Callable[[int], int]:
    method = rom_layout["resolver_method"]
    if method == "linear":
        return lambda cpu: cpu - 0x8000 + INES_HEADER_SIZE
    elif method == "bank_switched":
        bank = rom_layout["sound_bank"]
        num_banks = rom_layout["prg_banks"]
        return lambda cpu: _bank_switched_resolve(cpu, bank, num_banks)
    raise ValueError(f"Unknown resolver: {method}")
```

---

## 5. Command Dispatch Pattern

### Current approach

Both parsers use an if/elif chain on the high nibble:

```python
if hi <= 0xB:     # note
elif hi == 0xC:   # rest
elif hi == 0xD:   # instrument
elif hi == 0xE:   # e-commands
elif hi == 0xF:   # control flow
```

This is fine for 2 parsers. It becomes a maintenance problem at 5+
because the if/elif chain is duplicated in each parser with subtle
differences.

### Proposed: opcode handler registry

```python
class CommandRegistry:
    """Maps opcode ranges to handler functions."""

    def __init__(self):
        self._handlers: list[tuple[int, int, Callable]] = []

    def register(self, lo: int, hi: int, handler: Callable):
        """Register handler for opcodes in range [lo, hi] inclusive."""
        self._handlers.append((lo, hi, handler))

    def dispatch(self, opcode: int, parser_state) -> bool:
        """Find and call handler. Returns True if should stop parsing."""
        for lo, hi, handler in self._handlers:
            if lo <= opcode <= hi:
                return handler(opcode, parser_state)
        return False  # unknown opcode, skip
```

Each driver family builds its registry:

```python
def build_maezawa_registry(config: dict) -> CommandRegistry:
    reg = CommandRegistry()
    reg.register(0x00, 0xBF, handle_note)
    reg.register(0xC0, 0xCF, handle_rest)
    reg.register(0xD0, 0xDF, handle_instrument_cv1 if config["dx_bytes"] == 2
                              else handle_instrument_contra)
    reg.register(0xE0, 0xE4, handle_octave)
    reg.register(0xE8, 0xE8, handle_e8)
    # game-specific E commands:
    if config.get("has_vibrato"):
        reg.register(0xEB, 0xEB, handle_vibrato)
    if config.get("has_pitch_adjust"):
        reg.register(0xEC, 0xEC, handle_pitch_adjust)
    reg.register(0xFD, 0xFD, handle_subroutine)
    reg.register(0xFE, 0xFE, handle_repeat)
    reg.register(0xFF, 0xFF, handle_end)
    return reg
```

### Variable-length command reading

The trickiest part of NES sound drivers is variable-length commands.
DX reads 2 extra bytes in CV1, 3 in Contra pulse, 1 in Contra triangle.
The handler function signature should be:

```python
def handle_instrument(opcode: int, state: ParserState) -> bool:
    """Read instrument command. Advances state.pos past all consumed bytes."""
    state.tempo = opcode & 0xF
    state.pos += 1
    if state.is_triangle:
        # read 1 byte
        ...
    else:
        # read N bytes based on config
        ...
    return False  # don't stop
```

The handler owns how many bytes it reads. The main loop just calls
dispatch and trusts the handler to advance `state.pos`. This is already
how the current parsers work internally; the registry just makes the
dispatch explicit.

---

## 6. DriverCapability System

### Current state

`DriverCapability` in `frame_ir.py` has three fields:

```python
volume_model: Literal["parametric", "lookup_table"]
envelope_tables: list[list[int]] | None
decrescendo_status: Literal["verified", "provisional"]
```

### Proposed extension

```python
@dataclass
class DriverCapability:
    # Volume envelope
    volume_model: Literal["parametric", "lookup_table", "constant", "custom"]
    envelope_tables: list[list[int]] | None = None
    decrescendo_status: Literal["verified", "provisional"] = "provisional"

    # Percussion
    percussion_model: Literal["inline_triggers", "separate_channel", "none"]
    drum_map: dict[str, int] | None = None  # drum_type -> GM note

    # Channel configuration
    channel_count: int = 3  # melodic channels (excluding noise/DMC)
    has_noise_channel: bool = True
    has_dmc_channel: bool = False

    # Expansion audio
    expansion: Literal["none", "vrc6", "vrc7", "mmc5", "n163", "fds", "s5b"] = "none"
    expansion_channels: int = 0

    # Timing
    tick_rate: Literal["ntsc_60", "pal_50", "variable"] = "ntsc_60"
```

### How dispatch works

The IR already dispatches on `volume_model`. Extend this to other
dimensions:

```python
def parser_to_frame_ir(song: ParsedSong, driver: DriverCapability) -> SongIR:
    for ch_data in song.channels:
        if ch_data.channel_type == "noise":
            if driver.percussion_model == "separate_channel":
                # process as separate percussion timeline
                ...
            elif driver.percussion_model == "inline_triggers":
                # skip, handled inline during melodic channel processing
                ...
```

### Factory methods per game

```python
@staticmethod
def cv1() -> DriverCapability:
    return DriverCapability(
        volume_model="parametric",
        percussion_model="inline_triggers",
        drum_map={"snare": 38, "hihat": 42},
        channel_count=3,
        decrescendo_status="verified",
    )

@staticmethod
def contra(envelope_tables) -> DriverCapability:
    return DriverCapability(
        volume_model="lookup_table",
        envelope_tables=envelope_tables,
        percussion_model="separate_channel",
        drum_map={"kick": 36, "snare": 38, "hihat": 42,
                  "kick_snare": 38, "kick_hihat": 42},
        channel_count=3,
        has_dmc_channel=True,
        decrescendo_status="provisional",
    )
```

### Expansion audio

CV3 (Castlevania III) uses MMC5 mapper with 2 extra pulse channels.
VRC6 games (Akumajou Densetsu, the Japanese CV3) add 2 pulse + 1 saw.
The `expansion` and `expansion_channels` fields let the IR allocate
additional `ChannelIR` objects without special-casing game names.

---

## 7. Manifest Evolution

### Current schema (v1, implicit)

The manifests for CV1 and Contra have similar structure but no version
field. The fields were added organically.

### Proposed schema with version

```json
{
  "schema_version": 2,
  "game": "Super C",
  "rom_aliases": ["Super C (U)"],
  "status": "IN_PROGRESS",

  "driver": {
    "family": "konami_maezawa",
    "family_status": "verified",
    "variant": "super_c",
    "variant_notes": "Same as Contra with minor ROM layout differences"
  },

  "rom_layout": {
    "mapper": 2,
    "prg_banks": 8,
    "sound_bank": 1,
    "resolver_method": "bank_switched"
  },

  "pointer_table": {
    "rom_offset": "0x...",
    "format": "flat_sound_table",
    "entry_size": 3,
    "num_tracks": 15
  },

  "commands": {
    "dx_extra_bytes": {"pulse": 3, "triangle": 1},
    "c0_semantics": "rest_with_duration",
    "percussion": "separate_channel_dmc",
    "e_commands": {
      "E8": "flatten_note",
      "EB": {"type": "vibrato", "param_bytes": 2},
      "EC": {"type": "pitch_adjust", "param_bytes": 1}
    }
  },

  "envelope": {
    "type": "lookup_table",
    "table_rom_offset": "0x...",
    "total_entries": 54
  },

  "tracks": { },
  "validation": { },
  "anomalies": [ ]
}
```

### Key changes from v1

1. **`schema_version`** field enables forward-compatible reading. Loaders
   check version and apply defaults for missing fields.
2. **`driver` object** replaces flat `driver_family` + `driver_family_status`.
   Adds `variant` for games that share a driver family but differ in
   details.
3. **`commands.e_commands`** map replaces implicit assumptions about what
   E-series commands do. Each game declares which E commands it uses and
   how many parameter bytes they consume.
4. **`commands.dx_extra_bytes`** is a dict keyed by channel type, not
   two separate fields.

### Migration

Existing manifests continue to work. The parser checks for
`schema_version`; if absent, it applies v1 interpretation (read the
flat fields directly). New manifests use v2 schema.

```python
def load_manifest(path: Path) -> dict:
    with open(path) as f:
        m = json.load(f)
    if m.get("schema_version", 1) == 1:
        m = migrate_v1_to_v2(m)
    return m
```

---

## 8. Concrete Example: Adding a Capcom Game

For a new Capcom game (e.g., Mega Man 2), you would:

### Step 1: Identify

```bash
PYTHONPATH=. python scripts/rom_identify.py "AllNESRoms/.../Mega Man 2 (U).nes"
```

This reports: mapper 1 (MMC1), period table not found (different table
format), no Maezawa DX/FE/FD signature. Conclusion: different driver.

### Step 2: Create manifest

Create `extraction/manifests/megaman2.json` with what you know:

```json
{
  "schema_version": 2,
  "game": "Mega Man 2",
  "status": "INVESTIGATION",
  "driver": {
    "family": "capcom_nes",
    "family_status": "hypothesis"
  },
  "rom_layout": {
    "mapper": 1,
    "prg_banks": 16,
    "resolver_method": "bank_switched"
  }
}
```

### Step 3: Research the driver

Check `references/` for a disassembly. Search community resources.
Read `extraction/drivers/capcom/NOTES.md` for any prior research.

### Step 4: Write the parser module

Since the Capcom driver has a completely different command format, create:

```
extraction/drivers/capcom/
    capcom_driver.py    ← new parser
    envelope.py         ← Capcom envelope system
```

Import shared types from `extraction.drivers.shared.types`:

```python
from extraction.drivers.shared.types import (
    ParsedSong, ChannelData, NoteEvent, RestEvent,
    InstrumentChange, RepeatMarker, EndMarker,
)
```

### Step 5: Build DriverCapability

```python
@staticmethod
def megaman2() -> DriverCapability:
    return DriverCapability(
        volume_model="custom",  # Capcom has its own envelope system
        percussion_model="separate_channel",
        channel_count=3,
        has_dmc_channel=True,
    )
```

Add a `capcom_envelope` strategy function in `frame_ir.py` (or in
`capcom/envelope.py` if it is complex enough to warrant its own module).

### Step 6: Wire into pipeline

Add a `"megaman2"` entry to `GAME_CONFIGS` in `trace_compare.py`.
Update `full_pipeline.py` to accept a `--driver` flag or auto-detect
from the manifest.

---

## 9. Migration Path

How to get from current state to proposed architecture without breaking
CV1 or Contra.

### Phase 1: Extract shared types (low risk)

1. Create `extraction/drivers/shared/types.py` with the event dataclasses
   currently in `parser.py`.
2. Create `extraction/drivers/shared/address.py` with `cpu_to_rom`,
   `contra_cpu_to_rom`, and `get_resolver`.
3. Create `extraction/drivers/shared/pitch.py` with `pitch_to_midi`,
   `PITCH_NAMES`, `PERIOD_TABLE`, `BASE_MIDI_OCTAVE4`.
4. Make `parser.py` and `contra_parser.py` import from shared.
5. Keep backward-compatible re-exports in `parser.py` so existing
   imports do not break.
6. Run `trace_compare.py --frames 1792` after each move. Must show
   0 pitch mismatches.

### Phase 2: Unify Maezawa parsers (medium risk)

1. Create `maezawa.py` with a config-driven `MaezawaParser` that reads
   the manifest to determine DX byte count, E-command set, percussion
   model, and address resolver.
2. Implement `CommandRegistry` with per-game handler registrations.
3. Test: parse CV1 track 2 through both old `KonamiCV1Parser` and new
   `MaezawaParser`. Diff the `ParsedSong` output. Must be identical.
4. Repeat for Contra Jungle.
5. Mark old parsers as deprecated. Keep them until new parser passes
   full trace comparison.

### Phase 3: Extend DriverCapability (low risk)

1. Add `percussion_model`, `channel_count`, `expansion` fields.
2. Update `parser_to_frame_ir` to use new fields.
3. Update `export_to_midi` drum mapping to use `driver.drum_map`.
4. No behavioral change for existing games (new fields have defaults
   matching current behavior).

### Phase 4: Pipeline generalization (medium risk)

1. `full_pipeline.py` currently hardcodes `KonamiCV1Parser`. Change it
   to load the manifest, select the parser class, and pass the
   `DriverCapability`.
2. `trace_compare.py` already supports `--game`. Refactor `GAME_CONFIGS`
   to load from manifest + a small registry of parser classes.
3. `rom_identify.py` already detects mapper and period table. Add
   driver signature detection for Capcom, Sunsoft, etc.

---

## 10. Implications for the Pipeline

What changes in each stage when a new driver is added:

| Stage | Current | With architecture | Change needed for new driver |
|-------|---------|-------------------|------------------------------|
| ROM identify | Detects Maezawa signature | Detects multiple signatures | Add signature pattern |
| Manifest | Per-game JSON, informal schema | Versioned schema, loaded by parser | Create manifest JSON |
| Parser | Game-specific class | Config-driven or new module | Config (same family) or new module (new family) |
| Frame IR | Dispatches on DriverCapability | Same, more fields | Add volume strategy if new model |
| MIDI export | Hardcoded drum map | Reads from DriverCapability | Nothing (if drum_map provided) |
| Trace compare | `--game` switch, hardcoded configs | Manifest-driven configs | Add manifest entry |
| WAV render | Consumes SongIR | Same | Nothing |
| Full pipeline | Hardcoded to CV1 parser | Auto-selects parser from manifest | Nothing (once generalized) |
| REAPER project | Consumes MIDI | Same | Nothing |

The key insight: once Phase 4 is complete, adding a game with an
existing driver family requires ONLY a manifest JSON and an ear-check.
Adding a new driver family requires a parser module + envelope strategy.

---

## 11. Failure Risks If Misunderstood

### Over-abstraction: the registry-of-everything trap

The command registry pattern is useful for the Maezawa family (CV1,
Contra, Super C, TMNT, Goonies II) because they share 80% of their
command set. It is NOT useful as a universal abstraction across all NES
sound drivers.

A Capcom parser should NOT be forced to register its commands in the
same `CommandRegistry` as Maezawa. Different drivers have fundamentally
different byte-stream architectures. The shared layer is the OUTPUT
types (`ParsedSong`, `NoteEvent`, etc.), not the input parsing.

**Rule: share outputs, not inputs.** All parsers produce the same event
types. How they read the ROM is their own business.

### Premature generalization: abstracting before the second case

Do not refactor `parser.py` into a config-driven system until a third
Maezawa game (Super C or TMNT) actually needs it. The current two-file
approach (parser.py + contra_parser.py) is ugly but correct and tested.
Refactoring it before the third case means guessing at which dimensions
of variation matter. The third case reveals the true variation axes.

The correct sequence:
1. CV1 parser: write it.
2. Contra parser: copy and modify. Note what changed.
3. Super C parser: now you have three data points. Extract the pattern.

We are at step 2. Step 3 has not happened. The shared type extraction
(Phase 1) is safe now. The unified parser (Phase 2) should wait for
the third game.

### Config-in-code vs config-in-JSON: the blurry line

The manifest should declare WHAT the driver does (byte counts, command
semantics). The code should implement HOW (parsing logic, envelope
math). If you find yourself putting if/elif chains in JSON, you have
crossed the line.

Bad: `"dx_handler": "contra_style"` (code smell in JSON)
Good: `"dx_extra_bytes": {"pulse": 3, "triangle": 1}` (declarative fact)

The manifest is a data sheet, not a program.

### The triangle octave bug: why shared pitch code needs tests

`pitch_to_midi` is shared by all Maezawa parsers and handles the
triangle -12 offset. If a future driver uses a different octave mapping,
do NOT parameterize `pitch_to_midi` — write a new function. The -12
offset is a hardware fact (32-step vs 16-step sequencer) that applies
to ALL NES games equally, but the base octave mapping and the
`BASE_MIDI_OCTAVE4` constant are driver-specific conventions.

### The "works on one channel" trap

From MISTAKEBAKED.md: the E8 envelope gate looked correct on pulse 1
but was wrong for pulse 2. Any architectural change MUST be validated
across all channels of at least two games. Running `trace_compare.py`
on just pulse1 of CV1 is not enough. The minimum validation matrix:

| Game | pulse1 | pulse2 | triangle |
|------|--------|--------|----------|
| CV1 | trace_compare (1792 frames) | trace_compare | ear check |
| Contra | trace_compare (2976 frames) | trace_compare | ear check |

If a refactoring changes shared types or pitch logic, BOTH rows of
this matrix must pass before the change is committed.

---

## 12. Summary of Recommendations

**Do now (Phase 1):**
- Extract shared types to `extraction/drivers/shared/types.py`
- Extract address resolvers to `extraction/drivers/shared/address.py`
- Keep backward-compatible re-exports

**Do when the third Maezawa game arrives (Phase 2):**
- Build config-driven `MaezawaParser` with `CommandRegistry`
- Unify CV1 and Contra into one parser with game-specific handlers
- Deprecate `parser.py` and `contra_parser.py` as standalone parsers

**Do when the first non-Maezawa driver arrives (Phase 3-4):**
- Extend `DriverCapability` with percussion, expansion, channel fields
- Generalize `full_pipeline.py` to auto-select parser from manifest
- Add driver signature detection to `rom_identify.py`

**Do not do:**
- Do not build a universal command registry across driver families
- Do not add config fields for things that require code (envelope math)
- Do not refactor working parsers until the third case reveals the pattern
- Do not change `pitch_to_midi` or `BASE_MIDI_OCTAVE4` without running
  the full trace validation matrix
