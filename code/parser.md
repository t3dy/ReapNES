---
layout: default
title: "parser.py — CV1 Parser and Shared Types"
---

# parser.py — Castlevania 1 Parser and Shared Event Types

## What This File Does

This is the core parser for Konami's pre-VRC sound driver, specifically the
variant written by Kinuyo Maezawa for *Castlevania* (1986). It reads raw
bytes from a NES ROM file, walks the music data as a stateful byte-stream
interpreter, and produces structured event lists (notes, rests, instrument
changes, repeats, drums) that downstream stages convert to MIDI and audio.
In the pipeline, this sits between the ROM and the frame IR: ROM bytes go in,
`ParsedSong` objects come out.

## Shared vs. CV1-Specific

The file serves double duty. The dataclasses at the top (`NoteEvent`,
`RestEvent`, `InstrumentChange`, etc.) are **shared types** imported by
other parsers such as `contra_parser.py`. The `ChannelParser` class and
`KonamiCV1Parser` are **CV1-specific** -- they hardcode CV1's pointer table
layout (9-byte entries starting at ROM offset $0825), CV1's DX byte count
(2 bytes after the DX command for pulse channels), and CV1's inline drum
format (E9/EA following a note). Other Konami games using the same driver
family require their own parser class but reuse the event types.

## Bugs Found Here

Three of the most expensive bugs in the project lived in this file.
**Octave mapping** (INV-005): `BASE_MIDI_OCTAVE4` was originally set to 24
(C1), producing notes one octave too low on pulse channels; the fix to 36
(C2) was confirmed by ear and by trace comparison. **E8 gate** (INV-001):
the envelope enable flag was checked only on Square 1, masking a bug where
Square 2 had different E8 placement. **phase2_start in the fade model**
(INV-002): the parser was shortening note durations to simulate staccato,
violating the invariant that all temporal shaping belongs to the frame IR.
The `validate_full_duration` method was added specifically to catch this
class of bug. See RESEARCH_LOG.md sessions 1-3 and INVARIANTS.md entries
INV-001, INV-002, INV-004, INV-005 for the full investigation trails.

## Annotated Source

The code below is the exact production source with `# TUTORIAL:` comments
added. No logic has been changed.

```python
"""Konami pre-VRC sound driver parser (Maezawa variant).

Parses music data from Castlevania (U) and related Konami NES ROMs.
Decodes note commands, instruments, drums, repeats, and produces
structured channel data suitable for MIDI export.

Usage:
    from extraction.drivers.konami.parser import KonamiCV1Parser

    parser = KonamiCV1Parser("path/to/Castlevania (U).nes")
    song = parser.parse_track(2)  # Track 2 = Vampire Killer
    for ch in song.channels:
        print(ch.name, len(ch.events), "events")
"""
# ---------------------------------------------------------------
# STATUS: VERIFIED (CV1)
# SCOPE: cv1 + shared event types used by contra_parser
# VALIDATED: 2026-03-28
# TRACE_RESULT: 0 pitch, 0 volume, 0 sounding mismatches (CV1 pulse, 1792 frames)
# KNOWN_LIMITATIONS:
#   - pitch_to_midi uses BASE_MIDI_OCTAVE4=36, CV1-specific
#   - E5-E7 treated as invalid (may be valid in other games)
#   - Pointer table layout hardcoded for CV1 (9-byte entries, 15 tracks)
# LAYER: mixed (shared types + CV1-specific parser)
# ---------------------------------------------------------------

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# TUTORIAL: These dataclasses are the "vocabulary" of parsed music. They are
# TUTORIAL: imported by other parsers (contra_parser.py) so they must stay
# TUTORIAL: game-neutral where possible. Game-specific fields have defaults
# TUTORIAL: so that parsers that don't use them can ignore them.

@dataclass
class NoteEvent:
    """A single note in the parsed output.

    INVARIANT: duration_frames MUST be the full hardware duration
    (tempo * (nibble + 1)). Parsers must NOT shorten notes for
    staccato/envelope effects. ALL temporal volume shaping is the
    frame IR's responsibility, dispatched via DriverCapability.
    """
    # TUTORIAL: pitch is 0-11 mapping to C through B. This is the high nibble
    # TUTORIAL: of the command byte (values 0x00-0xBF). The low nibble is duration.
    pitch: int          # 0-11 (C=0 through B=11)
    octave: int         # 0-4 (E0=0 highest, E4=4 lowest)
    duration_nibble: int  # 0-15
    # TUTORIAL: duration_frames is ALWAYS tempo * (nibble + 1). If you see a
    # TUTORIAL: note whose duration_frames differs from that formula, something
    # TUTORIAL: is wrong. The validate_full_duration() method checks this.
    duration_frames: int  # actual frames = tempo * (nibble + 1)
    midi_note: int      # computed MIDI note number
    offset: int         # byte offset in ROM where this note was found


@dataclass
class RestEvent:
    """A rest (silence) in the parsed output."""
    # TUTORIAL: Rests use command bytes $C0-$CF. The low nibble is duration
    # TUTORIAL: (same formula: tempo * (nibble + 1)). In some games, $C0 might
    # TUTORIAL: mean "instantaneous mute" instead of "rest with duration 1" --
    # TUTORIAL: always check the disassembly.
    duration_nibble: int
    duration_frames: int
    offset: int


@dataclass
class InstrumentChange:
    """An instrument/tempo change (DX II FF sequence)."""
    # TUTORIAL: This is the most complex event type because it accumulates
    # TUTORIAL: fields from multiple bytes read in sequence. The DX command
    # TUTORIAL: byte itself sets the tempo (low nibble). Then the parser reads
    # TUTORIAL: the instrument byte (II), then optionally a fade byte (FF) for
    # TUTORIAL: pulse channels, then optionally a sweep command (F0 SS).
    tempo: int          # low nibble of DX command (1-15)
    raw_instrument: int  # APU register 0 value (DDLCVVVV)
    # TUTORIAL: The instrument byte encodes the NES APU $4000/$4004/$4008
    # TUTORIAL: register format: bits 7-6 = duty cycle, bit 5 = length halt,
    # TUTORIAL: bit 4 = constant volume flag, bits 3-0 = volume.
    duty_cycle: int     # 0-3
    volume: int         # 0-15
    length_halt: int    # 0-1
    constant_vol: int   # 0-1
    # TUTORIAL: fade_start and fade_step are the CV1 parametric envelope.
    # TUTORIAL: fade_start = frames of 1/frame volume decay at note start.
    # TUTORIAL: fade_step = frames of 1/frame release at note end.
    # TUTORIAL: Triangle channel ignores these (always 0).
    fade_start: int     # high nibble of FF byte (0 if triangle)
    fade_step: int      # low nibble of FF byte (0 if triangle)
    has_sweep: bool     # whether F0 SS follows
    sweep_value: int    # sweep register value (0 if no sweep)
    offset: int
    # TUTORIAL: These three fields are Contra-specific. They have defaults so
    # TUTORIAL: the CV1 parser doesn't need to set them. Contra uses lookup
    # TUTORIAL: tables for volume envelopes instead of the parametric model.
    vol_env_index: int = -1      # Contra: envelope table index (-1 = use parametric)
    decrescendo_mul: int = 0     # Contra: 3rd DX byte low nibble
    vol_duration: int = 15       # Contra: auto-decrescendo frame limit (low nibble of vol_env byte)


@dataclass
class DrumEvent:
    """A drum trigger (E9 or EA)."""
    # TUTORIAL: In CV1, drums are inline -- E9 (snare) or EA (hihat) appears
    # TUTORIAL: immediately after a note byte and shares that note's duration.
    # TUTORIAL: In Contra, drums have their own DMC channel instead. Always
    # TUTORIAL: check which percussion model the game uses.
    drum_type: str      # "snare" or "hihat"
    duration_frames: int  # from preceding note
    offset: int


@dataclass
class RepeatMarker:
    """A repeat/loop command (FE XX YYYY)."""
    # TUTORIAL: count=0xFF means infinite loop (end of song). For finite
    # TUTORIAL: repeats, count is the total number of passes through the
    # TUTORIAL: section, NOT the number of loop-backs. See the FE handler
    # TUTORIAL: in _parse_f_command for the detailed semantics.
    count: int          # repeat count ($FF = infinite)
    target_cpu: int     # CPU address to loop to
    target_rom: int     # ROM file offset
    offset: int


@dataclass
class SubroutineCall:
    """A subroutine jump (FD XX YY)."""
    # TUTORIAL: FD pushes a return address and jumps. $FF pops and returns.
    # TUTORIAL: This is how the driver reuses common musical phrases across
    # TUTORIAL: channels or tracks. The return_stack in ChannelParser tracks
    # TUTORIAL: the nesting.
    target_cpu: int
    target_rom: int
    offset: int


@dataclass
class EndMarker:
    """End of channel ($FF)."""
    # TUTORIAL: $FF has dual meaning: if the return_stack is non-empty, it is
    # TUTORIAL: a subroutine return. If the stack is empty, it is end-of-data.
    offset: int


@dataclass
class EnvelopeEnable:
    """E8 command — enable volume fade."""
    # TUTORIAL: E8 tells the frame IR to start applying the fade_start/fade_step
    # TUTORIAL: envelope from the most recent InstrumentChange. Without E8, notes
    # TUTORIAL: play at constant volume. The E8 gate bug: we initially only
    # TUTORIAL: checked Square 1's E8 state, missing that Square 2 had it in a
    # TUTORIAL: different position. Always check ALL channels.
    offset: int


@dataclass
class OctaveChange:
    """E0-E4 command — set octave."""
    # TUTORIAL: E0 = highest octave (0), E4 = lowest (4). This is inverted from
    # TUTORIAL: what you might expect -- lower command number = higher pitch.
    # TUTORIAL: Values E5-EF are not octave commands in CV1 but the parser
    # TUTORIAL: tolerates them defensively.
    octave: int
    offset: int


# Union type for all events
# TUTORIAL: This union type lets downstream code use isinstance() checks to
# TUTORIAL: dispatch on event type. The frame IR and MIDI exporter both do this.
Event = (NoteEvent | RestEvent | InstrumentChange | DrumEvent |
         RepeatMarker | SubroutineCall | EndMarker | EnvelopeEnable |
         OctaveChange)


@dataclass
class ChannelData:
    """Parsed data for one channel of a song."""
    # TUTORIAL: channel_type is the machine-readable key used everywhere
    # TUTORIAL: downstream: "pulse1", "pulse2", or "triangle". name is the
    # TUTORIAL: human-readable label for display.
    name: str           # "Square 1", "Square 2", "Triangle"
    channel_type: str   # "pulse1", "pulse2", "triangle"
    events: list[Event] = field(default_factory=list)
    start_offset: int = 0  # ROM offset where channel data begins
    start_cpu: int = 0     # CPU address


@dataclass
class ParsedSong:
    """Complete parsed song with all channels."""
    track_number: int
    channels: list[ChannelData] = field(default_factory=list)
    instruments: list[InstrumentChange] = field(default_factory=list)

    def validate_full_duration(self) -> list[str]:
        """Check that notes have full hardware durations.

        Returns list of violations. Empty = all notes are full-duration.
        This enforces the invariant that parsers emit raw durations and
        the IR handles all temporal shaping (volume envelopes, staccato).
        """
        # TUTORIAL: This method exists because of INV-002. Early versions of
        # TUTORIAL: the parser shortened note durations to simulate staccato,
        # TUTORIAL: which meant the frame IR couldn't apply its own envelope
        # TUTORIAL: model correctly. The fix: parsers ALWAYS emit the full
        # TUTORIAL: hardware duration (tempo * (nibble + 1)). The frame IR
        # TUTORIAL: decides how to shape the volume within that window.
        # TUTORIAL: Run this after parsing to catch any regressions.
        violations = []
        for ch in self.channels:
            tempo = 7  # default
            for ev in ch.events:
                if isinstance(ev, InstrumentChange):
                    tempo = ev.tempo
                elif isinstance(ev, NoteEvent):
                    expected = tempo * (ev.duration_nibble + 1)
                    if ev.duration_frames != expected:
                        violations.append(
                            f"{ch.name} offset 0x{ev.offset:X}: "
                            f"duration={ev.duration_frames} != "
                            f"tempo*nibble={expected}"
                        )
        return violations


# ---------------------------------------------------------------------------
# Note period table (from ROM at $079A)
# ---------------------------------------------------------------------------

PITCH_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# TUTORIAL: BASE_MIDI_OCTAVE4 is the MIDI note number assigned to pitch 0 (C)
# TUTORIAL: at octave 4 (E4, the lowest octave). This was the site of the most
# TUTORIAL: expensive pitch bug (INV-005): it was originally 24 (C1), making
# TUTORIAL: all pulse notes one octave too low. The trace comparison showed
# TUTORIAL: ZERO mismatches because the trace compares relative pitch, not
# TUTORIAL: absolute MIDI numbers. The bug was only caught by ear. Lesson:
# TUTORIAL: automated tests miss systematic offsets.
#
# TUTORIAL: Why 36 (C2)? The Contra disassembly confirms the base period 1017
# TUTORIAL: maps to A2 (MIDI 45). pitch_to_midi(9, 4) = 36 + 9 + 0 = 45. At
# TUTORIAL: octave E2 (2 shifts up), A becomes MIDI 69 = A4, confirmed by ear.

# Base MIDI notes at octave 4 (E4 = lowest, C2)
# Contra disassembly: base period 1017 = A2 (109.9 Hz), MIDI 45
# pitch_to_midi(9, 4) = 36 + 9 + 0 = 45 (A2) ✓
# At E2 (2 shifts): A4 (MIDI 69) — confirmed by ear against game
# The APU trace period 511 maps to 218 Hz via hardware formula,
# but the correct MIDI mapping is one octave higher (A4 not A3).
BASE_MIDI_OCTAVE4 = 36  # C2


def pitch_to_midi(pitch: int, octave: int, is_triangle: bool = False) -> int:
    """Convert CV1 pitch + octave to MIDI note number.

    pitch: 0-11 (C through B)
    octave: 0-4 (E0=highest through E4=lowest)
    is_triangle: True for triangle channel (plays 1 octave lower than
        pulse for the same period, because the APU triangle uses a
        32-step sequencer vs 16 for pulse)
    """
    # TUTORIAL: The octave numbering is inverted: E0 is the highest, E4 the
    # TUTORIAL: lowest. The formula (4 - octave) flips it so that E0 adds 4
    # TUTORIAL: octaves above the base and E4 adds 0.
    #
    # TUTORIAL: INV-004 / INV-005: Triangle subtracts 12 (one octave) because
    # TUTORIAL: the NES APU triangle channel uses a 32-step waveform while
    # TUTORIAL: pulse uses 16-step. For the same period register value, triangle
    # TUTORIAL: sounds one octave lower. If you change BASE_MIDI_OCTAVE4 and
    # TUTORIAL: forget this offset, triangle will be wrong. This has happened.

    # Clamp octave to 0-4 range (values > 4 come from misinterpreted
    # E-series commands like EC/ED which are pitch adjust, not octave)
    oct_clamped = max(0, min(4, octave))
    midi = BASE_MIDI_OCTAVE4 + pitch + (4 - oct_clamped) * 12
    if is_triangle:
        midi -= 12
    return midi


# ---------------------------------------------------------------------------
# ROM utilities
# ---------------------------------------------------------------------------

# TUTORIAL: iNES is the standard NES ROM file format. Every .nes file starts
# TUTORIAL: with a 16-byte header containing mapper info, PRG/CHR sizes, etc.
# TUTORIAL: All ROM file offsets must account for this header.
INES_HEADER_SIZE = 16


def cpu_to_rom(cpu_addr: int) -> int:
    """Convert NES CPU address to ROM file offset."""
    # TUTORIAL: The NES CPU maps PRG ROM starting at $8000. For mapper 0
    # TUTORIAL: (NROM, which CV1 uses), this is a simple linear mapping:
    # TUTORIAL: ROM offset = CPU address - $8000 + 16 (header).
    # TUTORIAL: For bank-switched mappers (2, 4, etc.), this function is
    # TUTORIAL: WRONG -- you need a bank-aware resolver. See the manifest's
    # TUTORIAL: resolver_method field.
    return cpu_addr - 0x8000 + INES_HEADER_SIZE


def rom_to_cpu(rom_offset: int) -> int:
    """Convert ROM file offset to NES CPU address."""
    return rom_offset + 0x8000 - INES_HEADER_SIZE


def read_ptr_le(data: bytes, offset: int) -> int:
    """Read a 16-bit little-endian pointer."""
    # TUTORIAL: The 6502 is little-endian, so all pointers in NES ROM data
    # TUTORIAL: are stored low byte first. This is the single most common
    # TUTORIAL: byte-reading operation in any NES parser.
    return struct.unpack_from('<H', data, offset)[0]


# ---------------------------------------------------------------------------
# Pointer table
# ---------------------------------------------------------------------------

# TUTORIAL: The pointer table is the "table of contents" for all music in the
# TUTORIAL: ROM. Each track entry contains three 16-bit CPU addresses (one per
# TUTORIAL: channel: Square 1, Square 2, Triangle) separated by single-byte
# TUTORIAL: gaps. The layout is 9 bytes per track: ptr(2) + gap(1), repeated
# TUTORIAL: three times. This layout is SPECIFIC TO CV1 -- Contra uses a
# TUTORIAL: completely different pointer table format (different offset,
# TUTORIAL: different entry size, different channel count). Never assume the
# TUTORIAL: pointer table layout transfers between games.

# Master pointer table starts at ROM offset $0825
# Each track has 3 pointers (Sq1, Sq2, Tri) at 3-byte intervals
# 9 bytes per track: ptr1(2) + gap(1) + ptr2(2) + gap(1) + ptr3(2) + gap(1)
# Actually: examining the ROM, the pointers are packed as:
# offset+0: Sq1 ptr (2 bytes LE)
# offset+2: separator byte
# offset+3: Sq2 ptr (2 bytes LE)
# offset+5: separator byte
# offset+6: Tri ptr (2 bytes LE)
# offset+8: separator byte
# Total: 9 bytes per track

POINTER_TABLE_ROM_OFFSET = 0x0825
TRACK_ENTRY_SIZE = 9
NUM_TRACKS = 15


def read_track_pointers(rom: bytes, track_num: int) -> tuple[int, int, int]:
    """Read the 3 channel CPU addresses for a track (1-indexed).

    Returns (sq1_cpu, sq2_cpu, tri_cpu).
    """
    # TUTORIAL: Tracks are 1-indexed to match how musicians refer to them
    # TUTORIAL: (Track 1 = Prologue, Track 2 = Vampire Killer, etc.).
    if track_num < 1 or track_num > NUM_TRACKS:
        raise ValueError(f"Track number must be 1-{NUM_TRACKS}, got {track_num}")

    base = POINTER_TABLE_ROM_OFFSET + (track_num - 1) * TRACK_ENTRY_SIZE
    sq1 = read_ptr_le(rom, base)
    sq2 = read_ptr_le(rom, base + 3)
    tri = read_ptr_le(rom, base + 6)
    return sq1, sq2, tri


# ---------------------------------------------------------------------------
# Channel parser
# ---------------------------------------------------------------------------

# TUTORIAL: ChannelParser is a stateful byte-stream interpreter. It maintains
# TUTORIAL: a position pointer (self.pos) into the ROM, an octave register,
# TUTORIAL: a tempo register, and a subroutine return stack. It reads one byte
# TUTORIAL: at a time, dispatches on the high nibble, and appends events.
# TUTORIAL: This is essentially a software emulation of how the NES sound
# TUTORIAL: driver reads its own data at runtime.

class ChannelParser:
    """Parses a single channel's command stream from ROM data."""

    def __init__(self, rom: bytes, start_cpu: int, channel_type: str):
        self.rom = rom
        self.start_cpu = start_cpu
        self.start_rom = cpu_to_rom(start_cpu)
        self.channel_type = channel_type  # "pulse1", "pulse2", "triangle"
        self.is_triangle = channel_type == "triangle"

        # State
        # TUTORIAL: These registers mirror the hardware driver's internal state.
        # TUTORIAL: The driver on the NES maintains the same variables in zero-page RAM.
        self.pos = self.start_rom
        self.octave = 2  # default octave E2 (middle)
        self.tempo = 7   # default tempo
        self.envelope_enabled = False
        self.events: list[Event] = []
        self.return_stack: list[int] = []
        # TUTORIAL: repeat_counters tracks how many loop-backs remain for each
        # TUTORIAL: FE command, keyed by the ROM offset of the FE byte. This is
        # TUTORIAL: needed because the parser may encounter the same FE multiple
        # TUTORIAL: times as it loops.
        self.repeat_counters: dict[int, int] = {}  # rom_offset -> remaining count

        # Safety limits
        # TUTORIAL: These prevent infinite loops from bugs or corrupted data.
        # TUTORIAL: If a track legitimately has more than 5000 events or 8000
        # TUTORIAL: bytes, raise these limits.
        self.max_events = 5000
        self.max_bytes = 8000

    def parse(self) -> list[Event]:
        """Parse the entire channel data stream. Returns list of events."""
        bytes_read = 0

        while len(self.events) < self.max_events and bytes_read < self.max_bytes:
            if self.pos >= len(self.rom):
                break

            byte = self.rom[self.pos]
            offset = self.pos
            hi = (byte >> 4) & 0xF
            lo = byte & 0xF

            # TUTORIAL: Command dispatch by high nibble:
            # TUTORIAL:   $00-$BF (hi 0-11): Note command. hi=pitch, lo=duration.
            # TUTORIAL:   $C0-$CF (hi 12):   Rest. lo=duration.
            # TUTORIAL:   $D0-$DF (hi 13):   Instrument/tempo change (DX).
            # TUTORIAL:   $E0-$EF (hi 14):   E-series (octave, drums, envelope).
            # TUTORIAL:   $F0-$FF (hi 15):   F-series (sweep, subroutine, repeat, end).

            if hi <= 0xB:
                # Note command
                # TUTORIAL: The note byte packs two values: high nibble = pitch
                # TUTORIAL: (0=C through 11=B), low nibble = duration index.
                # TUTORIAL: Actual duration in frames = tempo * (lo + 1).
                dur_frames = self.tempo * (lo + 1)
                midi = pitch_to_midi(hi, self.octave, self.is_triangle)
                self.events.append(NoteEvent(
                    pitch=hi, octave=self.octave,
                    duration_nibble=lo, duration_frames=dur_frames,
                    midi_note=midi, offset=offset,
                ))
                self.pos += 1

                # Check for drum trigger following the note
                # TUTORIAL: In CV1, drum commands (E9=snare, EA=hihat) appear
                # TUTORIAL: immediately after the note they accompany. The drum
                # TUTORIAL: shares the note's duration. This is the "inline drum"
                # TUTORIAL: model. Contra does NOT do this -- it has a separate
                # TUTORIAL: DMC channel for percussion.
                if self.pos < len(self.rom):
                    next_byte = self.rom[self.pos]
                    if next_byte == 0xE9:
                        self.events.append(DrumEvent("snare", dur_frames, self.pos))
                        self.pos += 1
                    elif next_byte == 0xEA:
                        self.events.append(DrumEvent("hihat", dur_frames, self.pos))
                        self.pos += 1

            elif hi == 0xC:
                # Rest
                dur_frames = self.tempo * (lo + 1)
                self.events.append(RestEvent(lo, dur_frames, offset))
                self.pos += 1

            elif hi == 0xD:
                # Tempo + instrument
                # TUTORIAL: DX is "the most dangerous command" because the number
                # TUTORIAL: of bytes that follow it varies by game AND by channel
                # TUTORIAL: type. In CV1: DX reads 2 bytes for pulse (instrument +
                # TUTORIAL: fade), 1 byte for triangle (instrument only). In Contra:
                # TUTORIAL: DX reads 3 bytes for pulse, 1 for triangle. Getting the
                # TUTORIAL: byte count wrong causes the parser to misalign and
                # TUTORIAL: interpret data bytes as commands (or vice versa),
                # TUTORIAL: producing garbage. Always verify DX byte count from the
                # TUTORIAL: disassembly before writing a parser for a new game.
                self._parse_instrument(offset, lo)

            elif hi == 0xE:
                self._parse_e_command(byte, offset)

            elif hi == 0xF:
                should_stop = self._parse_f_command(byte, offset)
                if should_stop:
                    break

            else:
                self.pos += 1

            bytes_read = self.pos - self.start_rom

        return self.events

    def _parse_instrument(self, offset: int, tempo_val: int):
        """Parse DX II [FF] [F0 SS] instrument sequence."""
        # TUTORIAL: The DX command sets tempo from its low nibble, then reads
        # TUTORIAL: a variable number of following bytes. The sequence is:
        # TUTORIAL:   DX          -> set tempo to X
        # TUTORIAL:   II          -> instrument byte (APU register 0 format)
        # TUTORIAL:   [FF]        -> fade parameters (pulse only, skipped for triangle)
        # TUTORIAL:   [F0 SS]     -> optional sweep (only if next byte is $F0)
        self.tempo = tempo_val
        self.pos += 1

        if self.pos >= len(self.rom):
            return

        # Read instrument byte
        # TUTORIAL: The instrument byte maps directly to NES APU register
        # TUTORIAL: $4000 (pulse1), $4004 (pulse2), or $4008 (triangle).
        # TUTORIAL: Format: DDLCVVVV where DD=duty, L=length halt,
        # TUTORIAL: C=constant volume, VVVV=volume/envelope period.
        inst_byte = self.rom[self.pos]
        self.pos += 1

        duty = (inst_byte >> 6) & 3
        lh = (inst_byte >> 5) & 1
        cv = (inst_byte >> 4) & 1
        vol = inst_byte & 0xF

        fade_start = 0
        fade_step = 0
        has_sweep = False
        sweep_val = 0

        # Read fade parameters (pulse channels only)
        # TUTORIAL: This is where triangle diverges from pulse. The hardware
        # TUTORIAL: driver skips the fade byte for triangle (confirmed in
        # TUTORIAL: disassembly). If you forget this branch, the parser reads
        # TUTORIAL: the next note byte as a fade parameter and everything
        # TUTORIAL: after that is misaligned.
        if not self.is_triangle and self.pos < len(self.rom):
            fade_byte = self.rom[self.pos]
            # Heuristic: if the next byte looks like a valid fade parameter
            # (not a note, not a control command we'd expect here)
            # The fade byte should be consumed.
            # From disassembly: triangle skips this, pulse always reads it.
            fade_start = (fade_byte >> 4) & 0xF
            fade_step = fade_byte & 0xF
            self.pos += 1

            # Check for optional F0 sweep
            # TUTORIAL: The F0 sweep command is optional. It only appears
            # TUTORIAL: when the composer wants pitch sweep on a note. The
            # TUTORIAL: parser peeks at the next byte; if it's $F0, it reads
            # TUTORIAL: the sweep parameter byte that follows.
            if self.pos < len(self.rom) and self.rom[self.pos] == 0xF0:
                self.pos += 1
                if self.pos < len(self.rom):
                    sweep_val = self.rom[self.pos]
                    has_sweep = True
                    self.pos += 1

        inst = InstrumentChange(
            tempo=tempo_val, raw_instrument=inst_byte,
            duty_cycle=duty, volume=vol,
            length_halt=lh, constant_vol=cv,
            fade_start=fade_start, fade_step=fade_step,
            has_sweep=has_sweep, sweep_value=sweep_val,
            offset=offset,
        )
        self.events.append(inst)

    def _parse_e_command(self, byte: int, offset: int):
        """Parse E-series commands."""
        lo = byte & 0xF

        # TUTORIAL: E-series command map for CV1:
        # TUTORIAL:   E0-E4: Set octave (E0=highest, E4=lowest)
        # TUTORIAL:   E5-E7: Not used in CV1 (treated as octave defensively)
        # TUTORIAL:   E8:    Enable volume envelope
        # TUTORIAL:   E9:    Snare drum trigger (standalone, rare)
        # TUTORIAL:   EA:    Hihat drum trigger (standalone, rare)
        # TUTORIAL:   EB-EF: Not used in CV1 (some may be pitch adjust in other games)

        if byte == 0xE8:
            self.envelope_enabled = True
            self.events.append(EnvelopeEnable(offset))
            self.pos += 1
        elif byte == 0xE9:
            # Standalone drum (shouldn't happen without preceding note, but handle it)
            self.events.append(DrumEvent("snare", self.tempo, offset))
            self.pos += 1
        elif byte == 0xEA:
            self.events.append(DrumEvent("hihat", self.tempo, offset))
            self.pos += 1
        elif lo <= 4:
            self.octave = lo
            self.events.append(OctaveChange(lo, offset))
            self.pos += 1
        else:
            # E5-E7, EB-EF: treat as octave set (effectively silent)
            # TUTORIAL: This is a defensive fallback. In CV1 these bytes never
            # TUTORIAL: appear in valid music data, but if corrupted data or a
            # TUTORIAL: new game uses them, the parser won't crash -- it will
            # TUTORIAL: just set a potentially out-of-range octave that gets
            # TUTORIAL: clamped in pitch_to_midi().
            self.octave = lo
            self.events.append(OctaveChange(lo, offset))
            self.pos += 1

    def _parse_f_command(self, byte: int, offset: int) -> bool:
        """Parse F-series control commands. Returns True if should stop."""
        # TUTORIAL: F-series command map for CV1:
        # TUTORIAL:   F0 SS:          Sweep (handled inside _parse_instrument)
        # TUTORIAL:   FD LL HH:       Subroutine call to address HHLL
        # TUTORIAL:   FE CC LL HH:    Repeat CC times, jump to HHLL
        # TUTORIAL:   FF:             End channel (or return from subroutine)

        if byte == 0xFD:
            # Subroutine call
            # TUTORIAL: FD reads a 16-bit pointer, pushes the current position
            # TUTORIAL: (past the 3-byte FD command) onto the return stack, and
            # TUTORIAL: jumps to the target. When $FF is encountered later with
            # TUTORIAL: a non-empty return stack, it pops and resumes here.
            if self.pos + 2 < len(self.rom):
                ptr = read_ptr_le(self.rom, self.pos + 1)
                self.events.append(SubroutineCall(ptr, cpu_to_rom(ptr), offset))
                # Save return position and jump
                self.return_stack.append(self.pos + 3)
                self.pos = cpu_to_rom(ptr)
            else:
                self.pos += 3
            return False

        elif byte == 0xFE:
            # Repeat: FE count ptr_lo ptr_hi
            # TUTORIAL: FE is the loop command. The semantics are subtle and
            # TUTORIAL: were the source of a bug (the count-2 offset). Here is
            # TUTORIAL: how the hardware driver works, from the disassembly at
            # TUTORIAL: _loc_0352:
            # TUTORIAL:
            # TUTORIAL: The driver keeps a counter per FE command (in zero-page
            # TUTORIAL: RAM at $06,x), starting at 0. Each time FE is reached:
            # TUTORIAL:   counter++ ; compare with count byte
            # TUTORIAL:   if counter == count -> done, skip past FE (4 bytes)
            # TUTORIAL:   if counter < count  -> loop back to target address
            # TUTORIAL:
            # TUTORIAL: So count=2 means: pass1 (0->1, loop back), pass2
            # TUTORIAL: (1->2, done). That's 2 total passes, 1 loop-back.
            # TUTORIAL: count=N means N total passes, N-1 loop-backs.
            # TUTORIAL:
            # TUTORIAL: The parser first encounters FE at the END of pass 1.
            # TUTORIAL: It needs (count-1) total loop-backs. The first encounter
            # TUTORIAL: does 1 loop-back, so it stores (count-2) as the remaining
            # TUTORIAL: count. This is the "count-2 offset" that caused a bug
            # TUTORIAL: when it was initially implemented as count-1.
            if self.pos + 3 < len(self.rom):
                count = self.rom[self.pos + 1]
                ptr = read_ptr_le(self.rom, self.pos + 2)
                target_rom = cpu_to_rom(ptr)

                # Infinite loop = end of song
                if count == 0xFF:
                    self.events.append(RepeatMarker(count, ptr, target_rom, offset))
                    self.pos += 4
                    return True

                # Finite repeat semantics (from disassembly _loc_0352):
                # Driver has counter at $06,x starting at 0.
                # Each FE hit: counter++, compare with count byte.
                # counter == count -> done (skip past FE)
                # counter < count -> loop back
                #
                # count=2: pass1 (0->1,loop), pass2 (1->2,done) = 2 passes, 1 loop-back
                # count=3: 3 passes, 2 loop-backs
                # count=N: N passes, N-1 loop-backs
                #
                # Parser first encounters FE at end of pass 1.
                # Need (count-1) total loop-backs. First encounter does 1,
                # so (count-2) more needed after that.
                if offset not in self.repeat_counters:
                    self.repeat_counters[offset] = max(0, count - 2)
                    self.events.append(RepeatMarker(count, ptr, target_rom, offset))
                    if count >= 2:
                        self.pos = target_rom  # loop back (loop-back #1)
                    else:
                        # count=1: 1 pass total, 0 loop-backs. Skip past.
                        del self.repeat_counters[offset]
                        self.pos += 4
                else:
                    remaining = self.repeat_counters[offset]
                    if remaining > 0:
                        self.repeat_counters[offset] = remaining - 1
                        self.pos = target_rom
                    else:
                        del self.repeat_counters[offset]
                        self.pos += 4
            else:
                self.pos += 4
            return False

        elif byte == 0xFF:
            # End or return from subroutine
            # TUTORIAL: $FF is overloaded. With a non-empty return stack, it
            # TUTORIAL: acts as a subroutine return (pop address, resume). With
            # TUTORIAL: an empty stack, it means end-of-channel. The hardware
            # TUTORIAL: driver uses the same dual-purpose logic.
            if self.return_stack:
                self.pos = self.return_stack.pop()
                return False
            else:
                self.events.append(EndMarker(offset))
                return True

        else:
            # Unknown F command — skip
            # TUTORIAL: F1-FC and F0 (outside of instrument context) are not
            # TUTORIAL: used in CV1. Skipping 1 byte is a guess -- if a future
            # TUTORIAL: game uses multi-byte F commands, this will misalign.
            self.pos += 1
            return False


# ---------------------------------------------------------------------------
# Song parser
# ---------------------------------------------------------------------------

CHANNEL_NAMES = {
    "pulse1": "Square 1",
    "pulse2": "Square 2",
    "triangle": "Triangle",
}


# TUTORIAL: KonamiCV1Parser is the top-level entry point. It loads the ROM,
# TUTORIAL: reads the pointer table, and delegates to ChannelParser for each
# TUTORIAL: of the three channels. This is the class you instantiate from
# TUTORIAL: external code. For other games, you would write a different
# TUTORIAL: top-level parser (see contra_parser.py) but reuse the event types.

class KonamiCV1Parser:
    """High-level parser for Castlevania 1 NES music."""

    def __init__(self, rom_path: str | Path):
        self.rom_path = Path(rom_path)
        with open(self.rom_path, 'rb') as f:
            self.rom = f.read()

        # Validate iNES header
        # TUTORIAL: Every valid NES ROM starts with the bytes "NES" followed
        # TUTORIAL: by $1A. If this check fails, the file is not a NES ROM
        # TUTORIAL: (or is headerless, which some old tools produced).
        if self.rom[:4] != b'NES\x1a':
            raise ValueError(f"Not a valid NES ROM: {self.rom_path}")

    def list_tracks(self) -> list[dict]:
        """List all available tracks with their pointer addresses."""
        tracks = []
        for i in range(1, NUM_TRACKS + 1):
            sq1, sq2, tri = read_track_pointers(self.rom, i)
            tracks.append({
                "track": i,
                "sq1_cpu": f"${sq1:04X}",
                "sq2_cpu": f"${sq2:04X}",
                "tri_cpu": f"${tri:04X}",
            })
        return tracks

    def parse_track(self, track_num: int) -> ParsedSong:
        """Parse all 3 channels of a track."""
        sq1_cpu, sq2_cpu, tri_cpu = read_track_pointers(self.rom, track_num)

        song = ParsedSong(track_number=track_num)

        for cpu_addr, ch_type in [(sq1_cpu, "pulse1"),
                                   (sq2_cpu, "pulse2"),
                                   (tri_cpu, "triangle")]:
            parser = ChannelParser(self.rom, cpu_addr, ch_type)
            events = parser.parse()

            channel = ChannelData(
                name=CHANNEL_NAMES[ch_type],
                channel_type=ch_type,
                events=events,
                start_offset=cpu_to_rom(cpu_addr),
                start_cpu=cpu_addr,
            )
            song.channels.append(channel)

        # Collect all instrument changes
        for ch in song.channels:
            for ev in ch.events:
                if isinstance(ev, InstrumentChange):
                    song.instruments.append(ev)

        return song

    def parse_channel(self, track_num: int, channel: str) -> ChannelData:
        """Parse a single channel of a track.

        channel: "pulse1", "pulse2", or "triangle"
        """
        sq1_cpu, sq2_cpu, tri_cpu = read_track_pointers(self.rom, track_num)
        cpu_map = {"pulse1": sq1_cpu, "pulse2": sq2_cpu, "triangle": tri_cpu}

        if channel not in cpu_map:
            raise ValueError(f"Unknown channel: {channel}")

        cpu_addr = cpu_map[channel]
        parser = ChannelParser(self.rom, cpu_addr, channel)
        events = parser.parse()

        return ChannelData(
            name=CHANNEL_NAMES[channel],
            channel_type=channel,
            events=events,
            start_offset=cpu_to_rom(cpu_addr),
            start_cpu=cpu_addr,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Parse a track and print the events."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <rom_path> [track_num]")
        print("  track_num defaults to 2 (Vampire Killer)")
        sys.exit(1)

    rom_path = sys.argv[1]
    track_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    parser = KonamiCV1Parser(rom_path)

    print(f"=== All Tracks ===")
    for t in parser.list_tracks():
        print(f"  Track {t['track']:2d}: Sq1={t['sq1_cpu']} Sq2={t['sq2_cpu']} Tri={t['tri_cpu']}")

    print(f"\n=== Parsing Track {track_num} ===\n")
    song = parser.parse_track(track_num)

    for ch in song.channels:
        notes = sum(1 for e in ch.events if isinstance(e, NoteEvent))
        rests = sum(1 for e in ch.events if isinstance(e, RestEvent))
        drums = sum(1 for e in ch.events if isinstance(e, DrumEvent))
        instruments = sum(1 for e in ch.events if isinstance(e, InstrumentChange))
        total_frames = sum(
            e.duration_frames for e in ch.events
            if isinstance(e, (NoteEvent, RestEvent))
        )

        print(f"--- {ch.name} (CPU ${ch.start_cpu:04X}) ---")
        print(f"  Events: {len(ch.events)} total ({notes} notes, {rests} rests, "
              f"{drums} drums, {instruments} instruments)")
        print(f"  Duration: {total_frames} frames ({total_frames/60:.1f} sec)")

        # Print first 30 events
        for i, ev in enumerate(ch.events[:30]):
            if isinstance(ev, NoteEvent):
                name = PITCH_NAMES[ev.pitch]
                oct_label = 6 - ev.octave  # E0=oct6, E4=oct2
                print(f"  [{i:3d}] NOTE {name}{oct_label} "
                      f"dur={ev.duration_nibble} ({ev.duration_frames}f) "
                      f"MIDI={ev.midi_note}")
            elif isinstance(ev, RestEvent):
                print(f"  [{i:3d}] REST dur={ev.duration_nibble} ({ev.duration_frames}f)")
            elif isinstance(ev, InstrumentChange):
                duty_pct = ['12.5%', '25%', '50%', '75%'][ev.duty_cycle]
                print(f"  [{i:3d}] INSTRUMENT tempo={ev.tempo} duty={duty_pct} "
                      f"vol={ev.volume} fade={ev.fade_start}/{ev.fade_step}")
            elif isinstance(ev, DrumEvent):
                print(f"  [{i:3d}] DRUM {ev.drum_type} ({ev.duration_frames}f)")
            elif isinstance(ev, OctaveChange):
                print(f"  [{i:3d}] OCTAVE E{ev.octave}")
            elif isinstance(ev, EnvelopeEnable):
                print(f"  [{i:3d}] ENVELOPE ON")
            elif isinstance(ev, RepeatMarker):
                inf = " (infinite)" if ev.count == 0xFF else ""
                print(f"  [{i:3d}] REPEAT x{ev.count}{inf} -> ${ev.target_cpu:04X}")
            elif isinstance(ev, SubroutineCall):
                print(f"  [{i:3d}] CALL ${ev.target_cpu:04X}")
            elif isinstance(ev, EndMarker):
                print(f"  [{i:3d}] END")

        if len(ch.events) > 30:
            print(f"  ... ({len(ch.events) - 30} more events)")
        print()


if __name__ == "__main__":
    main()
```

## Key Concepts

- **The parser is a stateful byte-stream interpreter.** It mirrors the NES hardware driver's own logic: read a byte, dispatch on the high nibble, update internal registers (octave, tempo), advance the position pointer. If you have the game's disassembly, you can trace the parser's behavior against the driver's source almost line-for-line.

- **Command byte encoding: high nibble = type, low nibble = parameter.** Bytes $00-$BF are notes (high nibble = pitch 0-11, low nibble = duration index). $C0-$CF are rests. $D0-$DF are instrument changes. $E0-$EF are control commands. $F0-$FF are flow control. This single-byte dispatch is compact but means any misaligned read produces plausible-looking garbage.

- **DX (instrument) is the most dangerous command.** It reads a variable number of trailing bytes depending on the game AND the channel type. CV1 pulse reads 2 bytes (instrument + fade), CV1 triangle reads 1 (instrument only). Contra pulse reads 3. Getting this wrong misaligns the parser for the rest of the channel. Always verify from the disassembly.

- **FE (repeat) uses count-2, not count-1.** The repeat count byte specifies the total number of passes, not loop-backs. The parser first encounters FE at the end of pass 1, performs 1 loop-back on that encounter, and stores `count - 2` as remaining loop-backs. This was a bug when initially implemented as `count - 1`.

- **$FF is overloaded: end-of-channel OR subroutine return.** The parser checks the return stack. If non-empty, $FF pops and resumes. If empty, $FF ends parsing. This matches the hardware driver exactly.

- **Triangle is one octave lower than pulse for the same period value.** The NES APU triangle channel uses a 32-step waveform vs. pulse's 16-step, so it sounds one octave lower for the same period register. The parser subtracts 12 from the MIDI note for triangle. If you change `BASE_MIDI_OCTAVE4`, you must account for this offset or triangle will be wrong.

- **Octave numbering is inverted.** E0 is the highest octave, E4 is the lowest. The formula `(4 - octave) * 12` flips this so that lower E-numbers produce higher MIDI notes.

- **cpu_to_rom only works for mapper 0 (NROM).** CV1 uses mapper 0, so the linear formula `cpu_addr - $8000 + 16` is correct. For bank-switched games (mapper 2, 4, etc.), you need a bank-aware address resolver. The manifest's `resolver_method` field tells you which to use.

- **validate_full_duration catches parser-level envelope bugs.** If any note's `duration_frames` differs from `tempo * (nibble + 1)`, the parser is incorrectly shortening notes. All volume shaping (staccato, fade, envelope) belongs to the frame IR layer, not the parser. Run this check after parsing.

- **Automated trace comparison misses systematic pitch offsets.** The trace compares relative pitch correctness (period ratios), not absolute MIDI note numbers. An octave-wide systematic error produces zero mismatches. The only way to catch it is to listen and compare to the game. This burned 3 prompts before it was understood.
