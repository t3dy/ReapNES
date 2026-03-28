"""Frame-accurate intermediate representation for extracted NES music.

The canonical time model is NES frames (1/60s NTSC). Every event has an
absolute frame number. This IR can be compared directly against emulator
APU trace data.

Usage:
    from extraction.drivers.konami.parser import KonamiCV1Parser
    from extraction.drivers.konami.frame_ir import parser_to_frame_ir

    parser = KonamiCV1Parser("Castlevania.nes")
    song = parser.parse_track(2)
    ir = parser_to_frame_ir(song)
    for ch in ir.channels:
        print(ch.name, len(ch.frames), "active frames")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from extraction.drivers.konami.parser import (
    ParsedSong, NoteEvent, RestEvent, InstrumentChange,
    DrumEvent, OctaveChange, EnvelopeEnable, RepeatMarker,
    EndMarker, SubroutineCall, pitch_to_midi, PITCH_NAMES,
)

CPU_CLK = 1789773

# Period table from ROM at $079A (base octave E4)
PERIOD_TABLE = [1710, 1614, 1524, 1438, 1358, 1281, 1209, 1142, 1078, 1017, 960, 906]


def pitch_octave_to_period(pitch: int, octave: int) -> int:
    """Convert pitch (0-11) and octave (0-4) to NES timer period."""
    base = PERIOD_TABLE[pitch]
    shifts = 4 - octave
    return base >> shifts


def period_to_freq(period: int, channel: str = "pulse") -> float:
    """Convert NES timer period to frequency in Hz."""
    if period < 2:
        return 0.0
    divisor = 16 if channel == "pulse" else 32
    return CPU_CLK / (divisor * (period + 1))


def freq_to_midi_note(freq: float) -> int:
    """Convert frequency to nearest MIDI note."""
    if freq < 20:
        return 0
    m = round(69 + 12 * math.log2(freq / 440))
    return m if 21 <= m <= 108 else 0


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


@dataclass
class ChannelIR:
    """Frame-accurate representation of one channel."""
    name: str
    channel_type: str     # "pulse1", "pulse2", "triangle"
    frames: dict[int, FrameState] = field(default_factory=dict)

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
# Convert parsed events to frame IR
# ---------------------------------------------------------------------------

def parser_to_frame_ir(song: ParsedSong) -> SongIR:
    """Convert parser output to frame-accurate IR.

    Expands each note into per-frame states including volume envelope decay.
    """
    ir = SongIR(track_number=song.track_number)

    for ch_data in song.channels:
        ch_type = ch_data.channel_type
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

        for ev in ch_data.events:
            if isinstance(ev, InstrumentChange):
                current_tempo = ev.tempo
                current_volume = ev.volume
                current_duty = ev.duty_cycle
                fade_start = ev.fade_start
                fade_step = ev.fade_step

            elif isinstance(ev, OctaveChange):
                current_octave = ev.octave

            elif isinstance(ev, EnvelopeEnable):
                envelope_enabled = True

            elif isinstance(ev, NoteEvent):
                duration = ev.duration_frames
                period = pitch_octave_to_period(ev.pitch, ev.octave)
                midi = ev.midi_note

                if is_triangle:
                    # Triangle: no volume control, no envelope
                    for f in range(duration):
                        ch_ir.frames[frame + f] = FrameState(
                            frame=frame + f,
                            period=period,
                            midi_note=midi,
                            volume=15,
                            duty=0,
                            sounding=True,
                        )
                else:
                    # Pulse: apply parametric volume envelope
                    # Verified against trace: decay by 1 per frame for
                    # exactly fade_start frames, then hold at remainder.
                    # fade_start = number of volume decrements (not a delay)
                    # Decay starts at frame 1 (not frame 0 — attack frame).
                    vol = current_volume
                    decrements_remaining = fade_start if envelope_enabled else 0
                    for f in range(duration):
                        sounding = vol > 0
                        ch_ir.frames[frame + f] = FrameState(
                            frame=frame + f,
                            period=period,
                            midi_note=midi,
                            volume=vol,
                            duty=current_duty,
                            sounding=sounding,
                        )
                        # Apply envelope: decrement vol by 1 each frame
                        # until fade_start decrements are used up
                        if f >= 1 and decrements_remaining > 0 and vol > 0:
                            vol -= 1
                            decrements_remaining -= 1

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
                # Drums don't advance the frame counter — they share
                # timing with the preceding note on the triangle channel.
                # Just mark the drum trigger at the current frame.
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

        # Compute MIDI notes from periods
        p1_midi = freq_to_midi_note(period_to_freq(p1_period, "pulse")) if p1_vol > 0 else 0
        p2_midi = freq_to_midi_note(period_to_freq(p2_period, "pulse")) if p2_vol > 0 else 0
        tr_midi = freq_to_midi_note(period_to_freq(tr_period, "triangle")) if tr_period > 2 else 0

        adj_f = f - start_frame  # align to parser frame 0

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
                volume=15 if tr_period > 2 else 0, duty=0,
                sounding=tr_period > 2,
            )

    ir.channels = [pulse1_ir, pulse2_ir, tri_ir]
    return ir
