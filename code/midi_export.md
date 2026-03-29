---
layout: default
title: "midi_export.py — MIDI Export with CC11 Automation"
---

# midi_export.py -- MIDI Export with CC11 Automation

## How It Works

This module converts the frame IR (intermediate representation) into a standard
Type 1 MIDI file. The frame IR is a per-frame snapshot of every NES APU channel --
pitch, volume, duty cycle, sounding state -- produced by `frame_ir.py` from the
parsed song data.

### Why CC11 (Expression), not CC7 (Volume)?

MIDI has two volume controllers: CC7 (Channel Volume) and CC11 (Expression).
CC7 is meant as a static mix level -- the overall loudness of a channel.
CC11 is designed for dynamic, moment-to-moment changes within a performance.
NES APU volume changes happen every frame (1/60th of a second) as part of the
envelope model, so CC11 is the correct choice. Using CC7 would conflict with
DAW mixing workflows where CC7 controls the fader. CC11 lets the per-frame
envelope ride on top of whatever mix level the user sets.

### BPM Estimation

The NES has no concept of BPM -- it runs at a fixed 60 frames/second (NTSC).
Musical tempo comes from the driver's "tempo" byte, which sets how many frames
equal one "tick" of the music engine. `estimate_bpm()` reads the tempo values
from InstrumentChange events, finds the most common one, and converts to BPM
so the MIDI file has musically meaningful bar lines.

### Channel Mapping

The NES APU has 5 channels. This exporter maps 4 of them to MIDI:

- Pulse 1 -> MIDI channel 0 (lead melody)
- Pulse 2 -> MIDI channel 1 (harmony / countermelody)
- Triangle -> MIDI channel 2 (bass)
- Noise -> MIDI channel 3 (drums, using GM percussion mapping)

The DPCM channel is not yet exported.

## Source

```python
# TUTORIAL: Module docstring. The "nesmdb CC11/CC12 encoding standard" refers to
# a convention from the NES Music Database project where CC11 carries volume
# automation and CC12 carries duty cycle (timbre) information. This lets
# downstream tools (REAPER, synthesizers) reconstruct NES-accurate playback.
"""Export parsed Konami CV1 song data to MIDI via the frame IR.

Produces a 4-channel MIDI file conforming to REQUIREMENTSFORMIDI.md
and the nesmdb CC11/CC12 encoding standard.

The frame IR provides per-frame volume envelopes, so MIDI notes are
shortened to match the actual sounding duration (not the full driver
duration). This gives proper staccato articulation matching the real
game audio.

Usage:
    from extraction.drivers.konami.parser import KonamiCV1Parser
    from extraction.drivers.konami.midi_export import export_to_midi

    parser = KonamiCV1Parser("Castlevania.nes")
    song = parser.parse_track(2)
    export_to_midi(song, "vampire_killer.mid")
"""
# ---------------------------------------------------------------
# STATUS: VERIFIED
# SCOPE: shared
# VALIDATED: 2026-03-28
# TRACE_RESULT: N/A (MIDI export, not directly trace-comparable)
# KNOWN_LIMITATIONS:
#   - CC11 automation quantized to MIDI ticks (slight timing rounding)
#   - Drum mapping uses GM percussion (approximate timbral match)
# LAYER: data (export format, not engine or hardware)
# ---------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

import mido

from extraction.drivers.konami.parser import (
    ParsedSong, NoteEvent, RestEvent, InstrumentChange,
    DrumEvent, RepeatMarker, PITCH_NAMES,
)
from extraction.drivers.konami.frame_ir import (
    parser_to_frame_ir, SongIR, ChannelIR, FrameState,
)


# TUTORIAL: PPQ (Pulses Per Quarter note) = 480 is a standard high-resolution
# MIDI timebase. Higher PPQ means finer timing granularity. At 480, each
# 16th note is 120 ticks, giving us sub-frame precision for most tempos.
# FRAMES_PER_SEC = 60 because NTSC NES runs at 60.0988 Hz (we round to 60).
# MIDI constants
PPQ = 480           # ticks per quarter note
FRAMES_PER_SEC = 60  # NTSC

# TUTORIAL: CC_VELOCITY=11 is CC11 (Expression), NOT CC7 (Volume).
# CC_TIMBRE=12 carries the pulse duty cycle (0/1/2/3 on NES, mapped to 0-127).
# Triangle has no duty cycle, so CC12 is skipped for that channel.
# nesmdb CC standard
CC_VELOCITY = 11    # mid-note volume changes
CC_TIMBRE = 12      # duty cycle

# TUTORIAL: MIDI channels 0-2 for melodic voices, channel 3 for drums.
# Note: MIDI convention puts General MIDI drums on channel 10 (index 9),
# but we use channel 3 because we only have 4 channels and this simplifies
# the mapping. DAWs like REAPER can remap as needed.
# Channel mapping
CHANNEL_MAP = {
    "pulse1": 0,
    "pulse2": 1,
    "triangle": 2,
}
DRUM_CHANNEL = 3

# Drum MIDI note mapping
DRUM_NOTES = {
    "snare": 38,    # GM Acoustic Snare
    "hihat": 42,    # GM Closed Hi-Hat
}

# TUTORIAL: GM program numbers give DAWs a hint about the intended sound.
# 80 = "Lead 1 (square)" is apt for pulse channels.
# 38 = "Synth Bass 1" works for the triangle's bass role.
# These are cosmetic -- the real sound comes from NES APU synth plugins.
# GM program numbers for channel identification
GM_PROGRAMS = {
    "pulse1": 80,   # Lead 1 (square)
    "pulse2": 81,   # Lead 2 (sawtooth)
    "triangle": 38,  # Synth Bass 1
}


# TUTORIAL: Frame-to-tick conversion. This is the core timing bridge between
# NES world (frames at 60 Hz) and MIDI world (ticks at PPQ-dependent rate).
# Formula: frames -> seconds -> ticks.
#   seconds = frames / 60
#   ticks_per_second = PPQ * BPM / 60
#   ticks = seconds * ticks_per_second
# The +0.5 before int() provides rounding instead of truncation.
# max(1, ...) ensures we never emit a zero-duration note.
def frames_to_ticks(frames: int, bpm: float = 120.0) -> int:
    """Convert NES frame count to MIDI ticks."""
    seconds = frames / FRAMES_PER_SEC
    ticks_per_second = PPQ * bpm / 60.0
    return max(1, int(seconds * ticks_per_second + 0.5))


def frame_to_tick(frame: int, bpm: float = 120.0) -> int:
    """Convert a single frame number to absolute MIDI tick."""
    seconds = frame / FRAMES_PER_SEC
    ticks_per_second = PPQ * bpm / 60.0
    return int(seconds * ticks_per_second + 0.5)


# TUTORIAL: BPM estimation. The NES driver uses a "tempo" byte that sets the
# number of frames per driver tick. A driver tick of 4 frames means one
# sixteenth-note lasts 4 frames. beat_frames = tempo * 4 gives us the quarter
# note length in frames. Then BPM = 60 * 60 / beat_frames.
# When multiple tempos exist (tempo changes mid-song), we pick the most
# frequently used one as the "primary" tempo for the MIDI file header.
def estimate_bpm(song: ParsedSong) -> float:
    """Estimate BPM from the song's tempo and note patterns."""
    tempos = set()
    for ch in song.channels:
        for ev in ch.events:
            if isinstance(ev, InstrumentChange):
                tempos.add(ev.tempo)

    if not tempos:
        return 120.0

    primary_tempo = max(tempos, key=lambda t: sum(
        1 for ch in song.channels for ev in ch.events
        if isinstance(ev, InstrumentChange) and ev.tempo == t
    ))

    beat_frames = primary_tempo * 4
    bpm = 60.0 * FRAMES_PER_SEC / beat_frames
    return round(bpm, 1)


# TUTORIAL: Volume mapping. NES APU volume is 4-bit (0-15). MIDI velocity
# and CC values are 7-bit (0-127). Linear scaling: midi = nes * 127 / 15.
# Two separate functions because velocity 0 means note-off in MIDI (so we
# clamp to min 1 for audible notes), while CC11 value 0 is a valid "silent
# but note still on" state.
def nes_vol_to_velocity(vol: int) -> int:
    """Convert NES 4-bit volume (0-15) to MIDI velocity (0-127)."""
    if vol <= 0:
        return 0
    return min(127, max(1, int(vol * 127 / 15 + 0.5)))


def nes_vol_to_cc(vol: int) -> int:
    """Convert NES 4-bit volume (0-15) to CC11 value (0-127)."""
    return min(127, max(0, int(vol * 127 / 15 + 0.5)))


# TUTORIAL: _build_track_from_ir -- THE MAIN LOOP.
# This function walks through every frame of the IR (one frame = 1/60th second)
# and emits MIDI events when state changes occur:
#
# The algorithm tracks three pieces of state: current_note, current_vol, current_duty.
# On each frame it checks:
#   1. Is the channel sounding with a valid note?
#      - If the note changed: emit note_off for old note, note_on for new note, CC11
#      - If only volume changed: emit CC11 (this is the per-frame envelope automation)
#      - If duty changed: emit CC12
#   2. Is the channel silent?
#      - If we had an active note: emit note_off
#
# Events are collected as (absolute_tick, message) pairs, then sorted and converted
# to delta times at the end. This avoids accumulating rounding errors from repeated
# frame-to-tick conversions.
def _build_track_from_ir(ch_ir: ChannelIR, midi_ch: int,
                          bpm: float) -> mido.MidiTrack:
    """Build a MIDI track from frame IR data.

    Walks the frame IR and emits:
    - note_on when a note starts sounding (or pitch changes)
    - CC11 when volume changes mid-note
    - CC12 when duty cycle changes
    - note_off when note stops sounding
    """
    track = mido.MidiTrack()

    role = {"pulse1": "lead", "pulse2": "harmony", "triangle": "bass"}[ch_ir.channel_type]
    track.append(mido.MetaMessage('track_name',
                                   name=f'{ch_ir.name} [{role}]', time=0))
    track.append(mido.Message('program_change',
                               channel=midi_ch,
                               program=GM_PROGRAMS[ch_ir.channel_type], time=0))

    if not ch_ir.frames:
        return track

    max_frame = max(ch_ir.frames.keys())

    # TUTORIAL: We collect events as (absolute_tick, message) pairs rather than
    # computing delta times on the fly. This is critical because frame_to_tick()
    # rounds independently for each frame, and accumulating deltas would drift.
    # Sorting by absolute tick then differencing gives correct delta times.
    # Collect all MIDI events as (abs_tick, message) pairs
    events: list[tuple[int, mido.Message]] = []

    current_note = -1
    current_vol = -1
    current_duty = -1
    note_start_vol = 0

    for f in range(max_frame + 1):
        fs = ch_ir.get_frame(f)
        tick = frame_to_tick(f, bpm)

        # TUTORIAL: fs.sounding means the channel is actively producing audio.
        # fs.midi_note > 0 filters out the "sounding but no pitch" edge case.
        # When a new note starts (or pitch changes mid-hold), we close the old
        # note and open a new one. The initial velocity comes from the current
        # frame's volume, and we also emit CC11 so that DAWs with expression-
        # based playback get the correct starting level.
        if fs.sounding and fs.midi_note > 0:
            if fs.midi_note != current_note:
                # New note (or pitch change)
                if current_note >= 0:
                    events.append((tick, mido.Message(
                        'note_off', channel=midi_ch,
                        note=current_note, velocity=0, time=0)))

                vel = nes_vol_to_velocity(fs.volume)
                events.append((tick, mido.Message(
                    'note_on', channel=midi_ch,
                    note=fs.midi_note, velocity=vel, time=0)))
                current_note = fs.midi_note
                note_start_vol = fs.volume
                current_vol = fs.volume

                # Emit CC11 for initial volume
                events.append((tick, mido.Message(
                    'control_change', channel=midi_ch,
                    control=CC_VELOCITY,
                    value=nes_vol_to_cc(fs.volume), time=0)))

            # TUTORIAL: This is where per-frame volume automation happens.
            # If the note is the same but volume changed (envelope decay, for
            # example), we emit a CC11 message. In a typical Vampire Killer note,
            # volume might go 15, 14, 13, 12... over successive frames, producing
            # a smooth fade that matches the NES APU's hardware envelope.
            elif fs.volume != current_vol:
                # Volume change mid-note -- emit CC11
                events.append((tick, mido.Message(
                    'control_change', channel=midi_ch,
                    control=CC_VELOCITY,
                    value=nes_vol_to_cc(fs.volume), time=0)))
                current_vol = fs.volume

            # TUTORIAL: Duty cycle changes are less frequent but musically
            # important -- they change the timbre (tone color) of pulse channels.
            # Triangle has no duty cycle, so we skip it.
            # Duty cycle change
            if fs.duty != current_duty and ch_ir.channel_type != "triangle":
                events.append((tick, mido.Message(
                    'control_change', channel=midi_ch,
                    control=CC_TIMBRE, value=fs.duty, time=0)))
                current_duty = fs.duty

        else:
            # TUTORIAL: Channel is silent. If we had an active note, close it.
            # Setting current_note = -1 means the next sounding frame will
            # trigger a fresh note_on even if it is the same pitch.
            # Not sounding -- end any active note
            if current_note >= 0:
                events.append((tick, mido.Message(
                    'note_off', channel=midi_ch,
                    note=current_note, velocity=0, time=0)))
                current_note = -1
                current_vol = -1

    # Final note off
    if current_note >= 0:
        tick = frame_to_tick(max_frame + 1, bpm)
        events.append((tick, mido.Message(
            'note_off', channel=midi_ch,
            note=current_note, velocity=0, time=0)))

    # TUTORIAL: Convert absolute ticks to delta times. MIDI files store each
    # event's time as "ticks since the previous event on this track." Sorting
    # ensures correct ordering when multiple events land on the same tick
    # (e.g., note_off + note_on at a pitch change).
    # Sort by tick, then convert to delta times
    events.sort(key=lambda x: x[0])
    last_tick = 0
    for abs_tick, msg in events:
        msg.time = abs_tick - last_tick
        track.append(msg)
        last_tick = abs_tick

    return track


# TUTORIAL: export_to_midi -- THE ASSEMBLY FUNCTION.
# This is the public API. It:
#   1. Estimates BPM from the parsed song
#   2. Builds the frame IR (the per-frame volume/pitch/duty snapshot)
#   3. Creates a Type 1 MIDI file (multiple simultaneous tracks)
#   4. Writes Track 0 (tempo, time signature, metadata text events)
#   5. Writes Tracks 1-3 from the frame IR (pulse1, pulse2, triangle)
#   6. Writes Track 4 from the parser's drum events (noise channel)
#   7. Adds loop point metadata if the song has a repeat marker
#
# The envelope_tables parameter is for Contra, which uses lookup-table-based
# volume envelopes instead of CV1's parametric model.
def export_to_midi(song: ParsedSong, output_path: str | Path,
                   game_name: str = "Castlevania",
                   song_name: str = "",
                   envelope_tables: list[list[int]] | None = None) -> Path:
    """Export a parsed song to a Type 1 MIDI file via frame IR.

    Creates 5 tracks:
    - Track 0: Tempo/meta (tempo, time signature, metadata)
    - Track 1: Pulse 1 (channel 0)
    - Track 2: Pulse 2 (channel 1)
    - Track 3: Triangle (channel 2)
    - Track 4: Drums (channel 3)
    """
    output_path = Path(output_path)
    bpm = estimate_bpm(song)
    tempo_us = int(60_000_000 / bpm)

    # Build frame IR from parsed song
    ir = parser_to_frame_ir(song, envelope_tables=envelope_tables)

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)

    # Track 0: Meta
    meta_track = mido.MidiTrack()
    mid.tracks.append(meta_track)
    meta_track.append(mido.MetaMessage('set_tempo', tempo=tempo_us, time=0))
    meta_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Game: {game_name}', time=0))
    if song_name:
        meta_track.append(mido.MetaMessage('text', text=f'Song: {song_name}', time=0))
    meta_track.append(mido.MetaMessage('text', text='Source: ROM static extraction (frame IR)', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Driver: Konami Pre-VRC (Maezawa)', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Track: {song.track_number}', time=0))
    meta_track.append(mido.MetaMessage('text', text=f'Tempo: {bpm} BPM (estimated)', time=0))

    # Build melodic tracks from frame IR
    for ch_ir in ir.channels:
        midi_ch = CHANNEL_MAP[ch_ir.channel_type]
        track = _build_track_from_ir(ch_ir, midi_ch, bpm)
        mid.tracks.append(track)

    # TUTORIAL: Drum track building. Drums are NOT in the frame IR because the
    # noise channel does not have meaningful pitch or envelope data in the same
    # way melodic channels do. Instead, we walk the parser's event list directly
    # and emit short note_on/note_off pairs using GM percussion note numbers.
    # Duration is shortened to 1/4 of the original to avoid overlapping hits.
    # Drum track from parser events (drums aren't in the frame IR)
    drum_track = mido.MidiTrack()
    drum_track.append(mido.MetaMessage('track_name', name='Noise [drums]', time=0))
    drum_events: list[tuple[int, mido.Message]] = []

    for ch_data in song.channels:
        abs_frame = 0
        for ev in ch_data.events:
            if isinstance(ev, DrumEvent):
                abs_tick = frame_to_tick(abs_frame, bpm)
                dur_ticks = frames_to_ticks(ev.duration_frames, bpm)
                drum_note = DRUM_NOTES.get(ev.drum_type, 38)
                drum_events.append((abs_tick, mido.Message(
                    'note_on', channel=DRUM_CHANNEL,
                    note=drum_note, velocity=100, time=0)))
                drum_off_tick = abs_tick + max(1, dur_ticks // 4)
                drum_events.append((drum_off_tick, mido.Message(
                    'note_off', channel=DRUM_CHANNEL,
                    note=drum_note, velocity=0, time=0)))
                # TUTORIAL: Contra's noise channel is a dedicated drum track
                # (unlike CV1 where drums are inline events on melodic channels).
                # When processing Contra's noise channel, we advance abs_frame
                # by the drum event's duration. For CV1's inline drums, the
                # melodic NoteEvent/RestEvent handles the timeline advancement.
                # Contra's noise channel has drums with their own
                # timeline -- advance the frame counter
                if ch_data.channel_type == "noise":
                    abs_frame += ev.duration_frames
            elif isinstance(ev, (NoteEvent, RestEvent)):
                abs_frame += ev.duration_frames

    drum_events.sort(key=lambda x: x[0])
    drum_abs = 0
    for abs_t, msg in drum_events:
        msg.time = abs_t - drum_abs
        drum_track.append(msg)
        drum_abs = abs_t

    mid.tracks.append(drum_track)

    # TUTORIAL: Loop point metadata. NES songs typically loop forever.
    # RepeatMarker with count=0xFF signals "loop to beginning." We record
    # the total duration as a LOOP_END text event so that downstream tools
    # (REAPER project generator, WAV renderer) know where to loop.
    # Loop point metadata
    for ch in song.channels:
        for ev in ch.events:
            if isinstance(ev, RepeatMarker) and ev.count == 0xFF:
                total_frames = sum(
                    e.duration_frames for e in ch.events
                    if isinstance(e, (NoteEvent, RestEvent))
                )
                loop_tick = frames_to_ticks(total_frames, bpm)
                meta_track.append(mido.MetaMessage('text',
                                                    text='LOOP_END', time=loop_tick))
                break
        break

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python midi_export.py <rom_path> <output.mid> [track_num]")
        sys.exit(1)

    rom_path = sys.argv[1]
    output_path = sys.argv[2]
    track_num = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    from extraction.drivers.konami.parser import KonamiCV1Parser

    parser = KonamiCV1Parser(rom_path)
    song = parser.parse_track(track_num)

    result = export_to_midi(song, output_path,
                            game_name="Castlevania",
                            song_name=f"Track {track_num}")

    # Build IR for stats
    ir = parser_to_frame_ir(song)

    print(f"Exported to {result}")
    print(f"  Channels: {len(song.channels)} melodic + drums")
    for ch_ir in ir.channels:
        sounding = ch_ir.sounding_frames
        total = ch_ir.total_frames
        print(f"  {ch_ir.name}: {sounding}/{total} sounding frames")


if __name__ == "__main__":
    main()
```

## MIDI Output Quality

### What MIDI can represent from NES audio

- **Pitch**: Exact. The NES period-to-MIDI-note lookup gives semitone-accurate pitch
  for all standard notes. MIDI note numbers map 1:1 to NES period register values
  via the NTSC period table.

- **Per-frame volume envelopes**: High fidelity. CC11 automation at 60 Hz (one message
  per frame when volume changes) captures the NES APU's 4-bit volume decay curves.
  The 4-bit to 7-bit scaling (0-15 to 0-127) is linear and lossless in practice
  since 15 distinct levels map cleanly.

- **Note timing and articulation**: Very close. Frame-level start/stop from the IR
  means notes begin and end within 1/60th of a second of the real hardware. The
  frame-to-tick conversion introduces sub-millisecond rounding that is inaudible.

- **Duty cycle / timbre**: Encoded as CC12. The NES pulse channels have 4 duty
  settings (12.5%, 25%, 50%, 75%) that dramatically affect tone color. CC12
  preserves this information for NES-aware synthesizers (like the included
  ReapNES_APU.jsfx plugin). Standard MIDI playback ignores CC12.

- **Loop points**: Stored as LOOP_END text events. Not part of the MIDI standard,
  but recognized by the project's REAPER generator and WAV renderer.

### What MIDI cannot represent

- **Raw waveform character**: The NES APU's pulse waves, triangle wave, and noise
  generator have a distinctive lo-fi sound from the 2A03 chip's DAC nonlinearity,
  aliasing, and limited bit depth. MIDI is note-level data; actual audio
  synthesis depends on the playback engine.

- **Sub-frame timing**: The NES APU updates registers mid-frame in some edge cases
  (particularly the triangle channel's pop artifacts). MIDI's minimum resolution
  is one frame (1/60s at the rates used here).

- **Hardware mixing and interference**: The 2A03 mixes channels through a nonlinear
  DAC. Channel interactions (especially triangle + noise bleed) are lost in the
  per-channel MIDI representation.

- **DPCM channel**: The delta-PCM sample playback channel is not exported. It would
  require either audio samples or a specialized MIDI encoding.

- **Sweep unit effects**: Pitch sweeps on pulse channels (used for sound effects,
  rarely for music) are not captured in the current frame IR.
