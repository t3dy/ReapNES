#!/usr/bin/env python3
"""Generate REAPER projects (.RPP) for NES-style music production.

Creates ready-to-open .RPP files with:
- Named tracks with ReapNES JSFX instruments loaded
- MIDI input configured (all devices, all channels, monitoring ON)
- Optional inline MIDI items from .mid files
- Correct RPP v7 format (tested with REAPER v7.27)

Usage:
    python generate_project.py --generic                     # Blank NES session
    python generate_project.py --song-set smb1_overworld     # Game palette
    python generate_project.py --midi file.mid               # MIDI import
    python generate_project.py --list-sets                   # List palettes
    python generate_project.py --all                         # Rebuild all
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SONG_SETS_DIR = REPO_ROOT / "studio" / "song_sets"
PRESETS_DIR = REPO_ROOT / "studio" / "presets"
PROJECTS_DIR = REPO_ROOT / "studio" / "reaper_projects"

# Track colors (REAPER PEAKCOL format)
COLORS = {
    "pulse1": 16576606,
    "pulse2": 10092441,
    "triangle": 16744192,
    "noise": 11184810,
}

CHANNEL_LABELS = {
    "pulse1": "NES - Pulse 1",
    "pulse2": "NES - Pulse 2",
    "triangle": "NES - Triangle",
    "noise": "NES - Noise / Drums",
}

MIDI_CHANNELS = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}

# ReapNES_APU slider defaults (sequential 1-15, no gaps):
#  1: P1 Duty (2=50%)      2: P1 Volume (15)     3: P1 Enable (1)
#  4: P2 Duty (1=25%)      5: P2 Volume (15)     6: P2 Enable (1)
#  7: Tri Enable (1)
#  8: Noise Period (0)     9: Noise Mode (0)    10: Noise Vol (15)   11: Noise Enable (1)
# 12: Master Gain (0.8)
# 13: Channel Mode: 0=P1 Only, 1=P2 Only, 2=Tri Only, 3=Noise Only, 4=Full APU
# 14: Live Patch: 0=Off, 1=NES Sustain, 2=NES Decay
# 15: Debug Overlay: 0=Off, 1=On
FULL_APU_DEFAULTS = [
    2, 15, 1,       # P1: duty=50%, vol=15, enable=on
    1, 15, 1,       # P2: duty=25%, vol=15, enable=on
    1,              # Tri: enable=on
    0, 0, 15, 1,    # Noise: period=0, mode=long, vol=15, enable=on
    0.8,            # Master gain
    4,              # Channel Mode: Full APU (for keyboard play)
    0,              # Live Patch: Off (MIDI files carry their own CC automation)
    0,              # Debug Overlay: Off
]

# Per-channel mode values for slider13
CHANNEL_MODES = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}


def make_guid() -> str:
    """Generate a REAPER-style GUID."""
    return "{" + str(uuid.uuid4()).upper() + "}"


def fmt_slider_values(values: list[float], total: int = 64) -> str:
    """Format slider values as 64 space-separated fields (dash for unused)."""
    parts = []
    for i in range(total):
        if i < len(values):
            v = values[i]
            if isinstance(v, float) and v != int(v):
                parts.append(f"{v:.6f}")
            else:
                parts.append(f"{int(v)}" if v == int(v) else f"{v}")
        else:
            parts.append("-")
    return " ".join(parts)


# ---------------------------------------------------------------------------
#  RPP building blocks
# ---------------------------------------------------------------------------

def rpp_header(tempo: float = 120.0, title: str = "") -> str:
    return f"""<REAPER_PROJECT 0.1 "7.27/win64" 1707000000
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 129
  TEMPO {tempo} 4 4
  PLAYRATE 1 0 0.25 4
  MASTERAUTOMODE 0
  MASTER_VOLUME 1 0 -1 -1 1
  MASTER_NCH 2 2
  <NOTES
    |ReapNES Studio Project
    |{title}
  >"""


def rpp_track(
    name: str,
    color: int,
    slider_values: list[float] | None = None,
    midi_file: str = "",
    midi_length: float = 0,
    armed: bool = True,
) -> str:
    """Generate a complete track block.

    Args:
        name: Track display name
        color: PEAKCOL color value
        slider_values: JSFX slider values (defaults used if None)
        midi_file: Absolute path to .mid file for SOURCE MIDI FILE reference
        midi_length: Length of MIDI item in seconds
        armed: Whether to arm track for MIDI recording with monitoring
    """
    vals = slider_values if slider_values is not None else list(FULL_APU_DEFAULTS)
    params = fmt_slider_values(vals)
    track_guid = make_guid()

    # REC field: armed input monitor mode monitor_media preserve_pdc path
    # 6112 = 4096 + (63 << 5) + 0 = MIDI, all devices, all channels
    if armed:
        # 5088 = 4096 (MIDI) + (31 << 5) (all devices) + 0 (all channels)
        # Device 31 = "All MIDI Inputs" in REAPER v7.27
        rec_line = "    REC 1 5088 1 0 0 0 0 0"
    else:
        rec_line = "    REC 0 0 1 0 0 0 0 0"

    lines = []
    lines.append(f"  <TRACK {track_guid}")
    lines.append(f'    NAME "{name}"')
    lines.append(f"    PEAKCOL {color}")
    lines.append(f"    BEAT -1")
    lines.append(f"    AUTOMODE 0")
    lines.append(f"    VOLPAN 1 0 -1 -1 1")
    lines.append(f"    MUTESOLO 0 0 0")
    lines.append(f"    IPHASE 0")
    lines.append(f"    PLAYOFFS 0 1")
    lines.append(f"    ISBUS 0 0")
    lines.append(f"    BUSCOMP 0 0 0 0 0")
    lines.append(f"    NCHAN 2")
    lines.append(f"    FX 1")
    lines.append(f"    TRACKID {track_guid}")
    lines.append(f"    PERF 0")
    lines.append(f"    MIDIOUT -1")
    lines.append(f"    MAINSEND 1 0")
    lines.append(rec_line)
    lines.append(f"    VU 2")
    # FX chain
    lines.append(f"    <FXCHAIN")
    lines.append(f"      SHOW 0")
    lines.append(f"      LASTSEL 0")
    lines.append(f"      DOCKED 0")
    lines.append(f"      BYPASS 0 0 0")
    lines.append(f'      <JS "ReapNES Studio/ReapNES_APU.jsfx" ""')
    lines.append(f"        {params}")
    lines.append(f"      >")
    lines.append(f"      FLOATPOS 0 0 0 0")
    lines.append(f"      FXID {make_guid()}")
    lines.append(f"      WAK 0 0")
    lines.append(f"    >")

    # MIDI item via external file reference
    if midi_file:
        item_guid = make_guid()
        midi_path_fwd = midi_file.replace("\\", "/")
        lines.append(f"    <ITEM")
        lines.append(f"      POSITION 0")
        lines.append(f"      LENGTH {midi_length}")
        lines.append(f"      LOOP 0")
        lines.append(f"      ALLTAKES 0")
        lines.append(f"      FADEIN 0 0 0 0 0 0 0")
        lines.append(f"      FADEOUT 0 0 0 0 0 0 0")
        lines.append(f"      MUTE 0 0")
        lines.append(f"      SEL 0")
        lines.append(f"      IGUID {item_guid}")
        lines.append(f'      <SOURCE MIDI')
        lines.append(f'        FILE "{midi_path_fwd}"')
        lines.append(f"      >")
        lines.append(f"    >")

    lines.append(f"  >")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  MIDI file conversion
# ---------------------------------------------------------------------------

def midi_track_to_events(track) -> list[str]:
    """Convert a mido track to RPP E/X event lines."""
    lines = []
    for msg in track:
        delta = msg.time
        if msg.is_meta:
            if msg.type == "end_of_track":
                continue
            raw = msg.bin()
            hex_data = " ".join(f"{b:02x}" for b in raw)
            lines.append(f"X {delta} {len(raw)} {hex_data}")
        elif msg.type in ("note_on", "note_off", "control_change", "program_change",
                          "pitchwheel", "aftertouch", "polytouch", "channel_pressure"):
            raw = msg.bin()
            hex_data = " ".join(f"{b:02x}" for b in raw)
            lines.append(f"E {delta} {hex_data}")
    return lines


def analyze_midi(midi_path: Path) -> dict:
    """Analyze MIDI file for auto-mapping.

    Detects which channels have notes, assigns them to NES roles
    (pulse1, pulse2, triangle, noise), and creates a remapped copy
    of the MIDI with channels reassigned to 0-3 for our plugin.
    """
    import mido
    mid = mido.MidiFile(str(midi_path))

    tempo_us = 500000
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                tempo_us = msg.tempo
                break

    # Collect per-channel statistics across all tracks
    channel_stats: dict[int, dict] = {}
    for i, track in enumerate(mid.tracks):
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                ch = msg.channel
                if ch not in channel_stats:
                    channel_stats[ch] = {
                        "notes": [], "note_count": 0, "is_drum": ch == 9,
                    }
                channel_stats[ch]["notes"].append(msg.note)
                channel_stats[ch]["note_count"] += 1

    for ch, stats in channel_stats.items():
        stats["note_min"] = min(stats["notes"])
        stats["note_max"] = max(stats["notes"])
        stats["note_avg"] = sum(stats["notes"]) / len(stats["notes"])

    return {
        "channel_stats": channel_stats,
        "duration_seconds": mid.length,
        "tempo_bpm": 60_000_000 / tempo_us,
        "ticks_per_beat": mid.ticks_per_beat,
        "mid": mid,
    }


def auto_map_channels(midi_info: dict) -> dict[str, int | None]:
    """Auto-map MIDI channels to NES roles.

    Returns dict mapping NES role -> original MIDI channel number.
    Example: {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 9}
    """
    stats = midi_info["channel_stats"]
    drums = [(ch, s) for ch, s in stats.items() if s["is_drum"]]
    melodic = sorted(
        [(ch, s) for ch, s in stats.items() if not s["is_drum"]],
        key=lambda x: x[1]["note_avg"],
    )

    mapping: dict[str, int | None] = {
        "pulse1": None, "pulse2": None, "triangle": None, "noise": None,
    }

    # Drums -> noise channel
    if drums:
        mapping["noise"] = drums[0][0]

    # Melodic: lowest avg pitch -> triangle (bass), rest -> pulses by note count
    if melodic:
        mapping["triangle"] = melodic[0][0]
        rest = sorted(melodic[1:], key=lambda x: x[1]["note_count"], reverse=True)
        if rest:
            mapping["pulse1"] = rest[0][0]
        if len(rest) >= 2:
            mapping["pulse2"] = rest[1][0]
        # If only 1-2 melodic channels, assign the busiest to pulse1 if triangle is only one
        if len(melodic) == 1:
            # Single channel - use as pulse1 instead (more musical default)
            mapping["pulse1"] = melodic[0][0]
            mapping["triangle"] = None

    return mapping


def create_remapped_midi(midi_path: Path, channel_map: dict[int, int], output_dir: Path) -> Path:
    """Create a copy of the MIDI with channels remapped to 0-3.

    Args:
        midi_path: Source MIDI file
        channel_map: Dict mapping original_channel -> new_channel (0-3)
        output_dir: Directory for remapped files

    Returns:
        Path to the remapped MIDI file
    """
    import mido
    mid = mido.MidiFile(str(midi_path))

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{midi_path.stem}_nes.mid"

    for track in mid.tracks:
        for msg in track:
            if hasattr(msg, "channel") and msg.channel in channel_map:
                msg.channel = channel_map[msg.channel]

    mid.save(str(out_path))
    return out_path


# ---------------------------------------------------------------------------
#  Project generation
# ---------------------------------------------------------------------------

def generate_generic_project(output_path: Path) -> None:
    """Generic NES session - all defaults, armed for keyboard play."""
    lines = [rpp_header(tempo=120, title="Generic NES Session")]
    for ch in ["pulse1", "pulse2", "triangle", "noise"]:
        lines.append(rpp_track(
            name=CHANNEL_LABELS[ch], color=COLORS[ch], armed=True,
        ))
    lines.append(">")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {output_path}")


def generate_song_set_project(song_set_path: Path, output_path: Path) -> None:
    """Generate from a song set JSON."""
    with open(song_set_path, encoding="utf-8") as f:
        song_set = json.load(f)

    game = song_set["game"]["title"]
    song = song_set["song"]["title"]
    tempo = song_set["song"].get("tempo_bpm", 120)

    lines = [rpp_header(tempo=tempo, title=f"{game} - {song}")]
    for ch in ["pulse1", "pulse2", "triangle", "noise"]:
        ch_info = song_set.get("channels", {}).get(ch, {})
        role = ch_info.get("role", "")
        name = CHANNEL_LABELS.get(ch, ch)
        if role:
            name += f" [{role}]"
        # Set each track to its own channel mode
        vals = list(FULL_APU_DEFAULTS)
        vals[12] = CHANNEL_MODES[ch]  # slider13 = channel-specific mode
        lines.append(rpp_track(name=name, color=COLORS[ch], slider_values=vals, armed=True))
    lines.append(">")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {output_path}")
    print(f"  {game} - {song} ({tempo} BPM)")


def generate_midi_project(midi_path: Path, output_path: Path,
                          song_set_path: Path | None = None,
                          nes_native: bool = False) -> None:
    """Generate project with MIDI items, optionally remapping channels to 0-3.

    Creates a remapped MIDI copy where active channels are assigned to
    NES roles (0=Pulse1, 1=Pulse2, 2=Triangle, 3=Noise) and references
    that file from each track via SOURCE MIDI FILE.

    If nes_native=True, skip remapping — MIDI already uses channels 0-3
    in NES standard format (from ROM extraction). Channel 3 = drums.
    """
    midi_info = analyze_midi(midi_path)
    tempo = midi_info["tempo_bpm"]
    duration = midi_info["duration_seconds"]
    stats = midi_info["channel_stats"]

    title = f"MIDI Import - {midi_path.stem}"
    if song_set_path:
        with open(song_set_path, encoding="utf-8") as f:
            ss = json.load(f)
        title = f"{ss['game']['title']} - {ss['song']['title']}"

    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}

    if nes_native:
        # NES-native MIDI: channels already at 0-3, no remapping needed
        role_map = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3}
        ch_remap = {0: 0, 1: 1, 2: 2, 3: 3}  # identity
        remapped_path = midi_path  # use original file directly
    else:
        role_map = auto_map_channels(midi_info)
        ch_remap = {}
        for role, orig_ch in role_map.items():
            if orig_ch is not None:
                ch_remap[orig_ch] = nes_ch[role]
        # Create remapped MIDI
        remapped_dir = output_path.parent / "midi_remapped"
        remapped_path = create_remapped_midi(midi_path, ch_remap, remapped_dir)

    print(f"  MIDI: {midi_path.name} ({duration:.0f}s, {tempo:.0f} BPM)")
    print(f"  Channel mapping:")

    lines = [rpp_header(tempo=tempo, title=title)]

    for role in ["pulse1", "pulse2", "triangle", "noise"]:
        orig_ch = role_map.get(role)
        name = CHANNEL_LABELS[role]

        # Set channel mode so this track only plays its own oscillator
        vals = list(FULL_APU_DEFAULTS)
        vals[12] = CHANNEL_MODES[role]  # slider13 = channel-specific mode

        has_midi = False
        if orig_ch is not None and orig_ch in stats:
            has_midi = True
            s = stats[orig_ch]
            note_count = s["note_count"]
            drum_tag = " (drums)" if s["is_drum"] else ""
            print(f"    {role:<10s} <- MIDI ch {orig_ch} -> NES ch {nes_ch[role]} ({note_count} notes{drum_tag})")
            name += f" [ch{orig_ch}{drum_tag}]"
        else:
            print(f"    {role:<10s} <- (none)")

        midi_file_str = str(remapped_path.resolve()).replace("\\", "/") if has_midi else ""
        lines.append(rpp_track(
            name=name, color=COLORS[role], slider_values=vals,
            midi_file=midi_file_str, midi_length=duration,
            armed=(not has_midi),  # arm tracks without MIDI items for live play
        ))

    lines.append(">")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {output_path}")


def generate_all() -> None:
    """Rebuild all projects."""
    sets = sorted(SONG_SETS_DIR.glob("*.json"))
    sets = [s for s in sets if s.name != "song_set_schema.json"]
    for ss in sets:
        out = PROJECTS_DIR / f"{ss.stem}.rpp"
        generate_song_set_project(ss, out)
    generate_generic_project(PROJECTS_DIR / "generic_nes.rpp")


def list_song_sets() -> None:
    sets = sorted(SONG_SETS_DIR.glob("*.json"))
    sets = [s for s in sets if s.name != "song_set_schema.json"]
    if not sets:
        print("No song sets found.")
        return
    print("Available song sets:\n")
    for ss in sets:
        with open(ss, encoding="utf-8") as f:
            d = json.load(f)
        print(f"  {ss.stem:<30s} {d['game']['title']} - {d['song']['title']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REAPER projects for NES music")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--generic", action="store_true", help="Generic NES project")
    group.add_argument("--song-set", metavar="NAME", help="Song set name")
    group.add_argument("--midi", metavar="PATH", help="Import MIDI file into project")
    group.add_argument("--list-sets", action="store_true", help="List song sets")
    group.add_argument("--all", action="store_true", help="Rebuild all")
    parser.add_argument("-o", "--output", metavar="PATH", help="Output .RPP path")
    parser.add_argument("--palette", metavar="NAME", help="Song set to use with --midi")
    parser.add_argument("--nes-native", action="store_true",
                        help="MIDI already uses NES channels 0-3 (skip remapping)")

    args = parser.parse_args()

    if args.list_sets:
        list_song_sets()
    elif args.generic:
        out = Path(args.output) if args.output else PROJECTS_DIR / "generic_nes.rpp"
        generate_generic_project(out)
    elif args.song_set:
        ss = SONG_SETS_DIR / f"{args.song_set}.json"
        if not ss.exists():
            print(f"Not found: {ss}", file=sys.stderr)
            sys.exit(1)
        out = Path(args.output) if args.output else PROJECTS_DIR / f"{args.song_set}.rpp"
        generate_song_set_project(ss, out)
    elif args.midi:
        midi = Path(args.midi)
        if not midi.exists():
            print(f"Not found: {midi}", file=sys.stderr)
            sys.exit(1)
        ss = SONG_SETS_DIR / f"{args.palette}.json" if args.palette else None
        out = Path(args.output) if args.output else PROJECTS_DIR / f"{midi.stem}_nes.rpp"
        generate_midi_project(midi, out, ss, nes_native=args.nes_native)
    elif args.all:
        generate_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
