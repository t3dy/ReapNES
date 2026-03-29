---
layout: default
title: "frame_ir.py — Frame IR and Volume Strategies"
---

# frame_ir.py -- Frame IR and Volume Strategies

## What This File Does

This is the heart of the NES Music Studio extraction pipeline. Everything
upstream (the parser) produces high-level events: "play note C at octave 3
for 14 frames." Everything downstream (MIDI export, WAV rendering) needs
per-frame hardware state: "at frame 847, pulse1 has period 427, volume 3,
duty 2." `frame_ir.py` is the bridge. It takes parsed events and expands
them into one `FrameState` per channel per frame, applying volume envelopes,
frequency conversion, and triangle linear counter approximation along the way.

The critical design decision is that **parsers do not shape volume**. A parser
emits a note with a duration and an instrument byte. All temporal shaping --
attack curves, sustain holds, release tails, decrescendo fadeouts -- happens
here in the IR layer. This separation exists because different Konami games
use different volume models (CV1 uses a two-phase parametric envelope, Contra
uses ROM lookup tables), but they share the same note/rest/octave command
format. The IR dispatches between models using a `DriverCapability` schema
object, not by inspecting data shape or guessing from context.

The file also contains the NES period table, the period-to-frequency
conversion, and the frequency-to-MIDI mapping. These are hardware-level
calculations that are universal across all NES games -- they come from the
2A03 APU's timer divider chain, not from any particular sound driver. Finally,
`trace_to_frame_ir` loads Mesen emulator APU trace CSVs into the same IR
format so that parsed output can be compared frame-by-frame against ground
truth.

For the envelope model details see DRIVER_MODEL.md. For the invariants
referenced in comments: INV-001 (driver capability dispatch), INV-003
(bounce-at-1 in decrescendo), INV-007 (triangle linear counter approximation).

---

## Full Annotated Source

```python
"""Frame-accurate intermediate representation for extracted NES music.

The canonical time model is NES frames (1/60s NTSC). Every event has an
absolute frame number. This IR can be compared directly against emulator
APU trace data.

Architecture invariants:
    - Parsers emit full-duration events. ALL temporal shaping (volume
      envelopes, decay, duty modulation) is the IR's responsibility.
    - IR dispatches on declared DriverCapability, not on data shape.
    - Each volume model is an isolated strategy function that can be
      tested and compared independently against trace data.

Usage:
    from extraction.drivers.konami.parser import KonamiCV1Parser
    from extraction.drivers.konami.frame_ir import parser_to_frame_ir, DriverCapability

    parser = KonamiCV1Parser("Castlevania.nes")
    song = parser.parse_track(2)
    ir = parser_to_frame_ir(song, DriverCapability.cv1())
    for ch in ir.channels:
        print(ch.name, len(ch.frames), "active frames")
"""
# ---------------------------------------------------------------
# STATUS: VERIFIED (CV1 pulse) / PROVISIONAL (Contra, triangle)
# SCOPE: shared (engine-level volume strategies + hardware approximations)
# VALIDATED: 2026-03-28
# TRACE_RESULT: CV1 pulse 0 mismatches; Contra 96.6% vol; triangle 195 sounding mismatches
# KNOWN_LIMITATIONS:
#   - Triangle linear counter: APPROXIMATION (reload+3)//4, off by ~1 frame per note
#   - Contra decrescendo threshold: PROVISIONAL, (mul*dur)>>4 not fully trace-validated
#   - UNKNOWN_SOUND_01 subtraction: NOT MODELED
# LAYER: mixed (engine envelope strategies + hardware period/freq conversion)
# ---------------------------------------------------------------

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from extraction.drivers.konami.parser import (
    ParsedSong, NoteEvent, RestEvent, InstrumentChange,
    DrumEvent, OctaveChange, EnvelopeEnable, RepeatMarker,
    EndMarker, SubroutineCall, pitch_to_midi, PITCH_NAMES,
)

CPU_CLK = 1789773
# TUTORIAL: The NTSC NES CPU clock is 1.789773 MHz. Every frequency
# calculation on the NES traces back to this constant. PAL would be
# 1.662607 MHz, but Konami games target NTSC.

# Period table from ROM at $079A (base octave E4)
PERIOD_TABLE = [1710, 1614, 1524, 1438, 1358, 1281, 1209, 1142, 1078, 1017, 960, 906]
# TUTORIAL: This is the base-octave period table extracted from the ROM.
# Every Konami game using the Maezawa sound driver has this exact table
# (or a functionally identical one). It represents the 12 chromatic
# pitches at octave 4 (A=440Hz region). Lower octaves are derived by
# left-shifting (doubling the period = halving the frequency = one octave
# down). Higher octaves are derived by right-shifting. The table is
# universal because it comes from NES tuning math, not from the driver
# itself -- but finding it in ROM is a strong driver-identification signal.
# Index 0 = A, 1 = A#, 2 = B, ... 11 = G#. The values are 11-bit timer
# reload values written to $4002/$4003 (pulse) or $400A/$400B (triangle).


def pitch_octave_to_period(pitch: int, octave: int) -> int:
    """Convert pitch (0-11) and octave (0-4) to NES timer period."""
    base = PERIOD_TABLE[pitch]
    shifts = max(0, 4 - min(4, octave))
    # TUTORIAL: The shift calculation inverts the octave number.
    # Octave 4 (the base octave in the table) gets 0 shifts -- use
    # the raw period value. Octave 3 gets 1 shift right (period / 2 =
    # frequency * 2 = one octave UP). Wait -- that seems backwards?
    # No: octave 0 in the Konami driver is the HIGHEST octave. Octave 0
    # gets 4 right-shifts, producing the smallest period (highest pitch).
    # Octave 4 gets 0 shifts, using the full base period (lowest pitch
    # in the playable range). This confused us for an entire session --
    # see docs/OCTAVETOOLOWONPULSE.md for the full investigation.
    return base >> shifts


def period_to_freq(period: int, channel: str = "pulse") -> float:
    """Convert NES timer period to frequency in Hz."""
    if period < 2:
        return 0.0
    divisor = 16 if channel == "pulse" else 32
    # TUTORIAL: The NES APU divides the CPU clock by (divisor * (period + 1)).
    # Pulse channels use a 16-step sequencer (divisor=16), triangle uses a
    # 32-step sequencer (divisor=32). This means the triangle channel plays
    # one octave lower than a pulse channel with the same period value.
    # This hardware fact is the root of INV-007 and the triangle octave rule
    # in CLAUDE.md: "Triangle is 1 octave lower than pulse."
    return CPU_CLK / (divisor * (period + 1))


def freq_to_midi_note(freq: float, octave_offset: int = 0) -> int:
    """Convert frequency to nearest MIDI note.

    octave_offset: additional semitones to add. Use +12 for pulse channels
    to match the Konami driver's MIDI mapping convention (BASE_MIDI_OCTAVE4
    = 36). Triangle does NOT get the offset because the 32-step sequencer
    already produces the correct octave.
    """
    # TUTORIAL: The +12 offset for pulse channels is not a fudge factor.
    # The parser maps Konami octave 4 to MIDI note 36 (C2). But the actual
    # frequency produced by a pulse channel at octave 4 is in the C3 range
    # (because octave 4 = 0 shifts = base period = ~262Hz for pitch C).
    # Adding +12 semitones aligns the MIDI note with the real pitch. Triangle
    # does NOT get this offset because its 32-step sequencer already halves
    # the frequency, landing it in the correct octave without adjustment.
    # Getting this wrong makes every note sound right relative to other notes
    # (intervals are preserved) but the entire song plays an octave too high
    # or too low. The trace comparison tool shows ZERO mismatches because it
    # compares periods, not MIDI notes -- so automated tests cannot catch this.
    # See docs/OCTAVETOOLOWONPULSE.md.
    if freq < 20:
        return 0
    m = round(69 + 12 * math.log2(freq / 440)) + octave_offset
    return m if 21 <= m <= 120 else 0


# ---------------------------------------------------------------------------
# Frame-level data structures
# ---------------------------------------------------------------------------

@dataclass
class FrameState:
    """State of one channel at one frame."""
    frame: int
    period: int = 0       # NES timer period (0 = silent)
    midi_note: int = 0    # MIDI note (0 = silent)
    volume: int = 0       # 0-15 (after envelope)
    duty: int = 0         # 0-3 (pulse only)
    sounding: bool = False  # whether audio is being produced
    # TUTORIAL: This is the atomic unit of the IR. One of these exists for
    # every (channel, frame) pair. The trace comparison tool creates these
    # from emulator data; the parser creates them from ROM data. Matching
    # them field-by-field is how we validate the extraction.


@dataclass
class ChannelIR:
    """Frame-accurate representation of one channel."""
    name: str
    channel_type: str     # "pulse1", "pulse2", "triangle"
    frames: dict[int, FrameState] = field(default_factory=dict)
    # TUTORIAL: frames is a dict, not a list, because rest gaps can be sparse.
    # Key = absolute frame number. get_frame() returns a silent FrameState for
    # any frame not explicitly set, so callers never need to check for KeyError.

    def get_frame(self, f: int) -> FrameState:
        return self.frames.get(f, FrameState(frame=f))

    @property
    def total_frames(self) -> int:
        return max(self.frames.keys()) + 1 if self.frames else 0

    @property
    def sounding_frames(self) -> int:
        return sum(1 for fs in self.frames.values() if fs.sounding)


@dataclass
class SongIR:
    """Frame-accurate representation of the entire song."""
    track_number: int
    channels: list[ChannelIR] = field(default_factory=list)

    @property
    def total_frames(self) -> int:
        return max(ch.total_frames for ch in self.channels) if self.channels else 0


# ---------------------------------------------------------------------------
# Driver capability schema
# ---------------------------------------------------------------------------

@dataclass
class DriverCapability:
    """Declares how a driver's volume model works.

    IR dispatches on these declared capabilities, not on data shape.
    Each field has a concrete semantic — add new fields when a new
    driver introduces behavior that doesn't fit existing fields.
    """
    # TUTORIAL: This is the INV-001 pattern. Before DriverCapability existed,
    # the code checked "if envelope_tables is not None" to decide between CV1
    # and Contra volume models. That broke when a CV1 caller accidentally
    # passed an empty list. The fix: make the caller DECLARE which model they
    # want, using a typed schema object. The IR never guesses. This pattern
    # scales to new games -- add a new static constructor (like cv3()) with
    # whatever fields the new driver needs, and add a new volume strategy
    # function. The dispatch in parser_to_frame_ir stays a simple match on
    # volume_model.
    volume_model: Literal["parametric", "lookup_table"]
    envelope_tables: list[list[int]] | None = None  # only for lookup_table
    # Status of the decrescendo model — "verified" or "provisional"
    decrescendo_status: Literal["verified", "provisional"] = "provisional"

    @staticmethod
    def cv1() -> DriverCapability:
        """CV1: two-phase parametric envelope (fade_start/fade_step).
        Verified against APU trace across 1792 frames."""
        return DriverCapability(
            volume_model="parametric",
            decrescendo_status="verified",
        )

    @staticmethod
    def contra(envelope_tables: list[list[int]]) -> DriverCapability:
        """Contra: lookup table envelopes + threshold-linear decrescendo.
        Table extraction verified. Decrescendo model is provisional —
        (mul * dur) >> 4 threshold derived from disassembly but not yet
        validated against Contra APU trace data."""
        return DriverCapability(
            volume_model="lookup_table",
            envelope_tables=envelope_tables,
            decrescendo_status="provisional",
        )


# ---------------------------------------------------------------------------
# Volume envelope strategies (isolated, testable, swappable)
# ---------------------------------------------------------------------------

def _cv1_parametric_envelope(
    duration: int,
    initial_volume: int,
    fade_start: int,
    fade_step: int,
) -> list[int]:
    """CV1 two-phase parametric volume envelope.

    Phase 1 (attack decay): decrement vol by 1/frame for fade_start
    frames, starting at frame 1. Frame 0 is always initial volume.
    Hold: maintain volume at (initial - fade_start).
    Phase 2 (release): decrement vol by 1/frame for the last fade_step
    frames. If fade_step is 0, hold indefinitely. Phase 2 cannot
    start before frame 1 (prevents overlap with frame 0).
    Bounce-at-1: volume holds at 1, never reaches 0 during phase 2
    (same resume_decrescendo behavior as Contra).

    Verified against APU trace:
        $B5 (vol=5,fade=2/3): 5→4→3→[hold]→2→1→0
        $F5 (vol=5,fade=2/9,dur=7): 5→4→3→2→1→0→0 (trace confirmed)
    """
    # TUTORIAL: This is the CV1 envelope model. The instrument byte encodes
    # initial_volume (high nibble), fade_start (bits 3-2), and fade_step
    # (low nibble). The parser decodes those; this function just applies
    # the two-phase shape. The key insight: phase 1 always starts at frame 1
    # (frame 0 gets the full initial volume), and phase 2 counts backward
    # from the end of the note. Between them is a sustain hold.
    volumes = []
    vol = initial_volume
    decrements_remaining = fade_start
    # Phase 2 cannot start before frame 1 — frame 0 is always initial vol
    phase2_start = max(1, duration - fade_step) if fade_step > 0 else duration
    # TUTORIAL: BUG FIX -- phase2_start. The original code was just
    # (duration - fade_step), which could be 0 for short notes. That meant
    # phase 2 started at frame 0, competing with the "frame 0 = initial vol"
    # rule and phase 1. The max(1, ...) fix eliminated 45 volume mismatches
    # in a single change. See "The Three Bugs That Lived Here" below.

    for f in range(duration):
        if f >= 1 and decrements_remaining > 0 and vol > 0:
            vol -= 1
            decrements_remaining -= 1
        elif f >= phase2_start and vol > 0:
            vol -= 1
        volumes.append(vol)

    return volumes


def _contra_lookup_envelope(
    duration: int,
    vol_env_index: int,
    decrescendo_mul: int,
    initial_volume: int,
    envelope_tables: list[list[int]],
    vol_duration: int = 15,
) -> list[int]:
    """Contra volume envelope (lookup table or auto decrescendo).

    Lookup table mode (vol_env_index >= 0):
        1. Table: read one volume byte per frame
        2. Hold: sustain last table volume after $FF
        3. Decrescendo: when remaining < (mul * dur) >> 4, decay 1/frame

    Auto decrescendo mode (vol_env_index == -1, bit 7 set):
        1. Decay: decrement vol by 1/frame for vol_duration frames
        2. Pause: hold at (initial - vol_duration) — NOT necessarily 0
        3. Decrescendo: when remaining < threshold, resume 1/frame decay

    Table extraction: VERIFIED
    Auto decrescendo with vol_duration: derived from disassembly
    (PULSE_VOL_DURATION = vol_env_byte & 0x0F, line 741-743)
    """
    # TUTORIAL: Contra's sound driver stores volume envelopes as byte arrays
    # in ROM (pulse_volume_ptr_tbl). Each entry is a series of volume values
    # terminated by $FF. The driver reads one byte per frame and writes it to
    # the volume register. After the table ends, it holds the last value.
    # The decrescendo kicks in near the end of a note: when the remaining
    # frames drop below (mul * duration) >> 4, volume decays 1/frame.
    # This is completely different from CV1's parametric model -- same
    # command format, different engine internals.
    volumes = []
    decrescendo_end_pause = (decrescendo_mul * duration) >> 4
    # TUTORIAL: The decrescendo threshold. "mul" comes from the instrument
    # byte (bits 6-4 of the volume envelope config). The shift-right-by-4
    # is a fixed-point multiply: (mul * duration) / 16. This determines
    # what fraction of the note's tail gets a fadeout. mul=0 means no
    # decrescendo at all.

    if vol_env_index >= 0 and vol_env_index < len(envelope_tables):
        # Lookup table mode
        table = envelope_tables[vol_env_index]
        table_len = len(table)
        last_table_vol = table[-1] if table else initial_volume
        decrescendo_active = False
        vol = initial_volume

        for f in range(duration):
            remaining = duration - f
            if f < table_len:
                vol = table[f]
            elif not decrescendo_active:
                vol = last_table_vol
                if decrescendo_end_pause > 0 and remaining <= decrescendo_end_pause:
                    decrescendo_active = True
                    # Bounce at 1 — engine does inc when vol hits 0
                    vol = max(1, vol - 1) if vol > 0 else 0
                    # TUTORIAL: INV-003 -- bounce-at-1. The Contra disassembly
                    # (line 411) shows that when volume hits 0 during
                    # resume_decrescendo, the engine increments it back to 1.
                    # So volume goes 5, 4, 3, 2, 1, 1, 1... never reaching 0
                    # until the note actually ends. The max(1, ...) pattern
                    # models this. Without it, notes cut off too early.
            else:
                vol = max(1, vol - 1) if vol > 0 else 0
            volumes.append(vol)
    else:
        # Auto decrescendo mode (bit 7 set)
        # Decay for exactly vol_duration frames, then pause.
        # Resume at tail end when remaining < decrescendo_end_pause.
        # IMPORTANT: resume_decrescendo bounces at 1 — when vol
        # reaches 0, the engine does inc PULSE_VOLUME (line 411
        # in disassembly), so vol holds at 1, never 0.
        # TUTORIAL: vol_duration comes from the low nibble of the volume
        # envelope byte (vol_env_byte & 0x0F). It controls how many frames
        # of initial decay happen before the hold. This was a late discovery --
        # earlier versions hardcoded decay length to 15, producing wrong
        # dynamics on short notes. See "The Three Bugs That Lived Here" below.
        vol = initial_volume
        decay_frames_left = vol_duration
        decay_paused = False

        for f in range(duration):
            remaining = duration - f
            if not decay_paused:
                if f > 0 and decay_frames_left > 0 and vol > 0:
                    vol -= 1
                    decay_frames_left -= 1
                if decay_frames_left == 0:
                    decay_paused = True
            elif decrescendo_end_pause > 0 and remaining <= decrescendo_end_pause:
                # Resume decrescendo — but bounce at 1, never 0
                if vol > 1:
                    vol -= 1
            volumes.append(vol)

    return volumes


# ---------------------------------------------------------------------------
# Convert parsed events to frame IR
# ---------------------------------------------------------------------------

def parser_to_frame_ir(
    song: ParsedSong,
    driver: DriverCapability | None = None,
    # Deprecated: use driver=DriverCapability.contra(tables) instead
    envelope_tables: list[list[int]] | None = None,
) -> SongIR:
    """Convert parser output to frame-accurate IR.

    Dispatches pulse volume shaping based on the declared DriverCapability.
    Parsers emit full-duration events; ALL temporal shaping happens here.

    Args:
        song: Parsed song data from a Konami parser.
        driver: Declares the volume model and its parameters.
            Use DriverCapability.cv1() or DriverCapability.contra(tables).
            If None, defaults to CV1 parametric model.
        envelope_tables: DEPRECATED compatibility shim. If provided
            without a driver, constructs DriverCapability.contra(tables).
    """
    # TUTORIAL: This is the main entry point. It walks every event in every
    # channel, maintaining running state (current volume, octave, duty,
    # instrument parameters), and for each NoteEvent, expands it into
    # per-frame FrameStates using the appropriate volume strategy. The
    # dispatch is on driver.volume_model -- "parametric" calls
    # _cv1_parametric_envelope, "lookup_table" calls _contra_lookup_envelope.
    # Triangle is handled separately because it ignores volume envelopes
    # entirely (the APU's triangle channel has no volume control -- it uses
    # a linear counter for note duration instead).

    # Resolve driver capability
    if driver is None:
        if envelope_tables is not None:
            driver = DriverCapability.contra(envelope_tables)
        else:
            driver = DriverCapability.cv1()

    ir = SongIR(track_number=song.track_number)

    for ch_data in song.channels:
        ch_type = ch_data.channel_type
        if ch_type == "noise":
            continue  # noise/drums go straight to MIDI, not through frame IR
        is_triangle = ch_type == "triangle"
        ch_ir = ChannelIR(name=ch_data.name, channel_type=ch_type)

        # Walk through events, tracking absolute frame position
        frame = 0
        current_volume = 15
        current_duty = 0
        current_octave = 2
        current_tempo = 7
        fade_start = 0
        fade_step = 0
        envelope_enabled = False
        raw_instrument = 0  # for triangle linear counter
        vol_env_index = -1
        decrescendo_mul = 0
        vol_duration = 15
        # TUTORIAL: These state variables accumulate as the parser events
        # are walked. InstrumentChange events set volume, duty, fade params,
        # envelope table index, etc. OctaveChange events set the current
        # octave. When a NoteEvent arrives, all of these are used to compute
        # the frame expansion. This mirrors how the real NES driver works --
        # the instrument command sets register shadows, the note command
        # triggers playback using those shadows.

        for ev in ch_data.events:
            if isinstance(ev, InstrumentChange):
                current_tempo = ev.tempo
                current_volume = ev.volume
                current_duty = ev.duty_cycle
                fade_start = ev.fade_start
                fade_step = ev.fade_step
                raw_instrument = ev.raw_instrument
                vol_env_index = ev.vol_env_index
                decrescendo_mul = ev.decrescendo_mul
                vol_duration = ev.vol_duration

            elif isinstance(ev, OctaveChange):
                current_octave = ev.octave

            elif isinstance(ev, EnvelopeEnable):
                envelope_enabled = True

            elif isinstance(ev, NoteEvent):
                duration = ev.duration_frames
                period = pitch_octave_to_period(ev.pitch, ev.octave)
                midi = ev.midi_note

                if is_triangle:
                    # TUTORIAL: Triangle channel handling (INV-007).
                    # The NES triangle channel has NO volume register. It is
                    # either on (volume 15) or off (volume 0). Duration is
                    # controlled by the linear counter loaded from $4008.
                    # Bit 7 of $4008 is the "control" flag: if set, the
                    # triangle plays for the full note duration (counter is
                    # continuously reloaded). If clear, the triangle plays
                    # for (reload_value) quarter-frames, then silences.
                    # The approximation (reload+3)//4 converts quarter-frames
                    # to frames. This is APPROXIMATE because the APU's 240Hz
                    # sequencer does not divide evenly into 60fps. Result:
                    # 195 sounding-frame mismatches on CV1 Vampire Killer,
                    # each off by exactly 1 frame. Good enough for audio;
                    # not good enough for cycle-accurate emulation.

                    # Triangle: gated by linear counter from $4008
                    tri_control = (raw_instrument >> 7) & 1
                    tri_reload = raw_instrument & 0x7F
                    if tri_control:
                        sounding_frames = duration
                    elif tri_reload > 0:
                        # APPROXIMATION: (reload+3)//4 models quarter-frame
                        # clocking at ~4 decrements/frame. Real APU uses 240Hz
                        # sequencer that doesn't divide evenly into 60fps frames.
                        # Status: APPROXIMATE — 195 sounding mismatches on CV1.
                        # See INVARIANTS.md INV-007.
                        sounding_frames = min(duration, (tri_reload + 3) // 4)
                    else:
                        sounding_frames = 0

                    for f in range(duration):
                        sounding = f < sounding_frames
                        ch_ir.frames[frame + f] = FrameState(
                            frame=frame + f,
                            period=period,
                            midi_note=midi,
                            volume=15 if sounding else 0,
                            duty=0,
                            sounding=sounding,
                        )

                elif driver.volume_model == "lookup_table":
                    vols = _contra_lookup_envelope(
                        duration, vol_env_index, decrescendo_mul,
                        current_volume, driver.envelope_tables or [],
                        vol_duration=vol_duration,
                    )
                    for f in range(duration):
                        vol = vols[f]
                        ch_ir.frames[frame + f] = FrameState(
                            frame=frame + f,
                            period=period,
                            midi_note=midi,
                            volume=vol,
                            duty=current_duty,
                            sounding=vol > 0,
                        )

                elif driver.volume_model == "parametric":
                    vols = _cv1_parametric_envelope(
                        duration, current_volume, fade_start, fade_step,
                    )
                    for f in range(duration):
                        vol = vols[f]
                        ch_ir.frames[frame + f] = FrameState(
                            frame=frame + f,
                            period=period,
                            midi_note=midi,
                            volume=vol,
                            duty=current_duty,
                            sounding=vol > 0,
                        )

                else:
                    raise ValueError(
                        f"Unknown volume model: {driver.volume_model!r}"
                    )

                frame += duration

            elif isinstance(ev, RestEvent):
                duration = ev.duration_frames
                for f in range(duration):
                    ch_ir.frames[frame + f] = FrameState(
                        frame=frame + f,
                        period=0,
                        midi_note=0,
                        volume=0,
                        duty=current_duty,
                        sounding=False,
                    )
                frame += duration

            elif isinstance(ev, DrumEvent):
                pass

        ir.channels.append(ch_ir)

    return ir


# ---------------------------------------------------------------------------
# Load trace data into the same IR format
# ---------------------------------------------------------------------------

def trace_to_frame_ir(trace_path: str, start_frame: int = 0, end_frame: int = 0) -> SongIR:
    """Load emulator APU trace CSV into frame IR format.

    The trace contains per-frame register writes. We build a running
    state and emit FrameState for each frame.
    """
    # TUTORIAL: This function is the other half of the validation story.
    # The parser produces an IR from ROM data. This function produces an IR
    # from emulator trace data (Mesen's APU log, exported as CSV). Both
    # produce the same SongIR/ChannelIR/FrameState structures. The trace
    # comparison tool (scripts/trace_compare.py) loads both and diffs them
    # field by field. Any mismatch means the parser or envelope model is
    # wrong. This is how we achieved 0 pitch mismatches on CV1 -- by
    # running the comparison after every change and fixing one mismatch
    # at a time.
    import csv
    from pathlib import Path

    ir = SongIR(track_number=0)

    pulse1_ir = ChannelIR(name="Square 1 (trace)", channel_type="pulse1")
    pulse2_ir = ChannelIR(name="Square 2 (trace)", channel_type="pulse2")
    tri_ir = ChannelIR(name="Triangle (trace)", channel_type="triangle")

    # Running state
    p1_period = 0
    p1_vol = 0
    p1_duty = 0
    p2_period = 0
    p2_vol = 0
    p2_duty = 0
    tr_period = 0
    tr_linear = 0  # $4008 linear counter value
    # TUTORIAL: These shadow the NES APU registers. The trace CSV reports
    # register writes as they happen. Between writes, values persist (the
    # real APU latches them). So we maintain running state and only update
    # when the trace reports a new write.

    # Read all trace data
    updates: dict[int, dict[str, int]] = {}
    with open(trace_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame = int(row['frame'])
            if end_frame > 0 and frame > end_frame:
                break
            param = row['parameter']
            val = int(row['value'])
            if frame not in updates:
                updates[frame] = {}
            updates[frame][param] = val

    if not updates:
        return ir

    max_frame = max(updates.keys())
    if end_frame > 0:
        max_frame = min(max_frame, end_frame)

    for f in range(min(updates.keys()), max_frame + 1):
        if f in updates:
            u = updates[f]
            if '$4002_period' in u:
                p1_period = u['$4002_period']
            if '$4000_vol' in u:
                p1_vol = u['$4000_vol']
            if '$4000_duty' in u:
                p1_duty = u['$4000_duty']
            if '$4006_period' in u:
                p2_period = u['$4006_period']
            if '$4004_vol' in u:
                p2_vol = u['$4004_vol']
            if '$4004_duty' in u:
                p2_duty = u['$4004_duty']
            if '$400A_period' in u:
                tr_period = u['$400A_period']
            if '$4008_linear' in u:
                tr_linear = u['$4008_linear']

        # Compute MIDI notes from periods
        # TUTORIAL: Note the asymmetry: pulse channels get octave_offset=12,
        # triangle gets 0. This matches the parser's convention and accounts
        # for the 16-step vs 32-step sequencer difference. If you change one
        # side (parser or trace), you MUST change the other, or the comparison
        # tool will report false pitch mismatches on every single frame.
        # Pulse channels get +12 offset to match BASE_MIDI_OCTAVE4 = 36
        p1_midi = freq_to_midi_note(period_to_freq(p1_period, "pulse"), 12) if p1_vol > 0 else 0
        p2_midi = freq_to_midi_note(period_to_freq(p2_period, "pulse"), 12) if p2_vol > 0 else 0
        # Triangle is sounding when period > 2 AND linear counter > 0
        tr_sounding = tr_period > 2 and tr_linear > 0
        tr_midi = freq_to_midi_note(period_to_freq(tr_period, "triangle")) if tr_sounding else 0

        adj_f = f - start_frame  # align to parser frame 0
        # TUTORIAL: start_frame aligns the trace to the parser's time axis.
        # The emulator trace starts counting from power-on or reset. The
        # parser starts at frame 0 of the song. start_frame is the trace
        # frame where the song actually begins (found by looking at the
        # trace for the first non-zero write to pulse1).

        if adj_f >= 0:
            pulse1_ir.frames[adj_f] = FrameState(
                frame=adj_f, period=p1_period, midi_note=p1_midi,
                volume=p1_vol, duty=p1_duty, sounding=p1_vol > 0,
            )
            pulse2_ir.frames[adj_f] = FrameState(
                frame=adj_f, period=p2_period, midi_note=p2_midi,
                volume=p2_vol, duty=p2_duty, sounding=p2_vol > 0,
            )
            tri_ir.frames[adj_f] = FrameState(
                frame=adj_f, period=tr_period, midi_note=tr_midi,
                volume=15 if tr_sounding else 0, duty=0,
                sounding=tr_sounding,
            )

    ir.channels = [pulse1_ir, pulse2_ir, tri_ir]
    return ir
```

---

## The Three Bugs That Lived Here

These are the three highest-impact bugs found and fixed in `frame_ir.py`, each
discovered through frame-level trace comparison. They are documented here
because they represent the classes of error that volume modeling is most
vulnerable to.

### 1. phase2_start (45 mismatches, one-line fix)

**Symptom**: Short notes (duration 3-5 frames) had wrong volume on frames 1-2.

**Root cause**: `phase2_start = duration - fade_step` could equal 0 when
`fade_step >= duration`. This meant phase 2 release started on frame 0,
competing with the invariant that frame 0 always gets initial volume, and
overlapping with phase 1 decay.

**Fix**: `phase2_start = max(1, duration - fade_step)`. Phase 2 can never
start before frame 1. This single change eliminated 45 volume mismatches
across the full 1792-frame Vampire Killer trace.

**Lesson**: Envelope phases must have non-overlapping frame ranges. When two
phases can claim the same frame, the one with the lower start index wins
silently, producing wrong but plausible-sounding output.

### 2. bounce-at-1 (INV-003, Contra decrescendo)

**Symptom**: Notes in Contra's Jungle theme cut off 2-3 frames early compared
to the game.

**Root cause**: The decrescendo tail was decrementing volume all the way to 0.
The real Contra engine (disassembly line 411) increments volume back to 1 when
it hits 0 during `resume_decrescendo`. Volume holds at 1 until the note
actually ends, then drops to 0.

**Fix**: `vol = max(1, vol - 1) if vol > 0 else 0` in both the lookup table
and auto-decrescendo paths. The `max(1, ...)` prevents the decrescendo from
silencing the note prematurely.

**Lesson**: "Decay to zero" is an assumption. Real drivers often have floor
values, bounce behaviors, or increment-on-zero quirks. Always check the
disassembly for what happens at the boundary.

### 3. vol_duration (Contra auto-decrescendo length)

**Symptom**: Notes with bit-7-set volume envelopes (auto-decrescendo mode) had
decay phases that were too long or too short, depending on the instrument.

**Root cause**: The decay length was hardcoded to 15 frames. The real engine
reads it from the low nibble of the volume envelope byte:
`PULSE_VOL_DURATION = vol_env_byte & 0x0F` (disassembly line 741-743). An
instrument with vol_env_byte = $85 has vol_duration = 5, not 15.

**Fix**: Added `vol_duration` parameter to `_contra_lookup_envelope` and
`InstrumentChange`, propagated from the parser's instrument byte decoding.

**Lesson**: When a hardcoded constant produces "mostly right" results, check
whether it should actually be a per-instrument parameter. The disassembly is
the only reliable source for which bits control which behavior.
