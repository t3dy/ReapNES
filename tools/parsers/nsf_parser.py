"""nsf_parser.py — Parse NSF (NES Sound Format) file headers and metadata.

NSF files contain 6502 code and data for NES music playback.
This module extracts the header metadata and provides a foundation
for future register-log extraction.

Reference: https://www.nesdev.org/wiki/NSF
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# NSF header is exactly 128 bytes
NSF_HEADER_SIZE = 128
NSF_MAGIC = b"NESM\x1a"


@dataclass
class NSFHeader:
    """Parsed NSF file header."""

    version: int
    total_songs: int
    starting_song: int
    load_address: int
    init_address: int
    play_address: int
    song_name: str
    artist: str
    copyright: str
    ntsc_speed: int  # play speed in microseconds (NTSC)
    bankswitch: tuple[int, ...]  # 8 bankswitch init values
    pal_speed: int
    region: str  # "NTSC", "PAL", or "Dual"
    extra_sound_chips: int  # bitfield for expansion audio

    @property
    def uses_vrc6(self) -> bool:
        return bool(self.extra_sound_chips & 0x01)

    @property
    def uses_vrc7(self) -> bool:
        return bool(self.extra_sound_chips & 0x02)

    @property
    def uses_fds(self) -> bool:
        return bool(self.extra_sound_chips & 0x04)

    @property
    def uses_mmc5(self) -> bool:
        return bool(self.extra_sound_chips & 0x08)

    @property
    def uses_namco163(self) -> bool:
        return bool(self.extra_sound_chips & 0x10)

    @property
    def uses_sunsoft5b(self) -> bool:
        return bool(self.extra_sound_chips & 0x20)

    @property
    def expansion_chips_str(self) -> str:
        chips = []
        if self.uses_vrc6:
            chips.append("VRC6")
        if self.uses_vrc7:
            chips.append("VRC7")
        if self.uses_fds:
            chips.append("FDS")
        if self.uses_mmc5:
            chips.append("MMC5")
        if self.uses_namco163:
            chips.append("Namco 163")
        if self.uses_sunsoft5b:
            chips.append("Sunsoft 5B")
        return ", ".join(chips) if chips else "None (2A03 only)"


def parse_nsf(filepath: Path) -> NSFHeader:
    """Parse an NSF file and return its header metadata.

    Args:
        filepath: Path to the .nsf file.

    Returns:
        Populated NSFHeader dataclass.

    Raises:
        ValueError: If the file is not a valid NSF.
        FileNotFoundError: If the file does not exist.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        msg = f"NSF file not found: {filepath}"
        raise FileNotFoundError(msg)

    with filepath.open("rb") as f:
        header_bytes = f.read(NSF_HEADER_SIZE)

    if len(header_bytes) < NSF_HEADER_SIZE:
        msg = f"File too small for NSF header ({len(header_bytes)} bytes)"
        raise ValueError(msg)

    magic = header_bytes[0:5]
    if magic != NSF_MAGIC:
        msg = f"Invalid NSF magic: {magic!r} (expected {NSF_MAGIC!r})"
        raise ValueError(msg)

    version = header_bytes[5]
    total_songs = header_bytes[6]
    starting_song = header_bytes[7]

    load_address = struct.unpack_from("<H", header_bytes, 8)[0]
    init_address = struct.unpack_from("<H", header_bytes, 10)[0]
    play_address = struct.unpack_from("<H", header_bytes, 12)[0]

    song_name = header_bytes[14:46].split(b"\x00")[0].decode("ascii", errors="replace")
    artist = header_bytes[46:78].split(b"\x00")[0].decode("ascii", errors="replace")
    copyright_str = header_bytes[78:110].split(b"\x00")[0].decode("ascii", errors="replace")

    ntsc_speed = struct.unpack_from("<H", header_bytes, 110)[0]
    bankswitch = struct.unpack_from("8B", header_bytes, 112)
    pal_speed = struct.unpack_from("<H", header_bytes, 120)[0]

    region_byte = header_bytes[122]
    if region_byte == 0:
        region = "NTSC"
    elif region_byte == 1:
        region = "PAL"
    else:
        region = "Dual"

    extra_sound_chips = header_bytes[123]

    return NSFHeader(
        version=version,
        total_songs=total_songs,
        starting_song=starting_song,
        load_address=load_address,
        init_address=init_address,
        play_address=play_address,
        song_name=song_name,
        artist=artist,
        copyright=copyright_str,
        ntsc_speed=ntsc_speed,
        bankswitch=bankswitch,
        pal_speed=pal_speed,
        region=region,
        extra_sound_chips=extra_sound_chips,
    )


def scan_nsf_directory(root: Path) -> list[NSFHeader]:
    """Scan a directory for .nsf files and parse all headers.

    Args:
        root: Directory to scan.

    Returns:
        List of parsed NSFHeader objects.
    """
    root = Path(root)
    results: list[NSFHeader] = []
    for nsf_path in sorted(root.rglob("*.nsf")):
        try:
            results.append(parse_nsf(nsf_path))
        except (ValueError, OSError) as e:
            print(f"  Skipping {nsf_path.name}: {e}")
    return results


def main() -> None:
    """CLI entry point for NSF header inspection."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse and display NSF file headers.")
    parser.add_argument("path", type=Path, help="NSF file or directory to scan")
    args = parser.parse_args()

    path = Path(args.path)

    if path.is_file():
        headers = [parse_nsf(path)]
    elif path.is_dir():
        headers = scan_nsf_directory(path)
    else:
        print(f"Error: {path} is not a file or directory")
        return

    for h in headers:
        print(f"{'Song:':<18} {h.song_name}")
        print(f"{'Artist:':<18} {h.artist}")
        print(f"{'Copyright:':<18} {h.copyright}")
        print(f"{'Tracks:':<18} {h.total_songs} (starts at {h.starting_song})")
        print(f"{'Region:':<18} {h.region}")
        print(f"{'Load/Init/Play:':<18} ${h.load_address:04X} / ${h.init_address:04X} / ${h.play_address:04X}")
        print(f"{'NTSC speed:':<18} {h.ntsc_speed} us")
        print(f"{'Expansion:':<18} {h.expansion_chips_str}")
        print(f"{'Bankswitch:':<18} {h.bankswitch}")
        print("-" * 60)


if __name__ == "__main__":
    main()
