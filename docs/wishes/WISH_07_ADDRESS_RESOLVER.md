# WISH #7: Address Resolver Abstraction

## 1. What This Wish Is

Replace the two hardcoded CPU-to-ROM address conversion functions
(`cpu_to_rom` in `parser.py` and `contra_cpu_to_rom` in
`contra_parser.py`) with an `AddressResolver` abstraction that is
constructed from manifest data and injected into parsers. Each NES
mapper type gets its own resolver implementation. New mapper = new
class, not a new function scattered into a parser file.

---

## 2. Why It Matters

Every NES game stores CPU addresses in its pointer tables. Converting
those to ROM file offsets requires mapper-specific math. Today:

- **CV1** uses `cpu_to_rom()`: a one-line linear formula
  (`cpu_addr - 0x8000 + 16`).
- **Contra** uses `contra_cpu_to_rom()`: a bank-switched formula
  with hardcoded `SOUND_BANK = 1`, `NUM_PRG_BANKS = 8`,
  `BANK_SIZE = 16384`.

Adding a third game (Super C, TMNT, CV3) means writing a third
standalone function with its own hardcoded constants. This does not
scale. Worse, the constants are baked into the function rather than
read from the manifest, so the manifest's `resolver_method`,
`sound_bank`, and `prg_banks` fields are documentation-only -- they
do not drive the actual resolution logic.

The architecture docs (`FLEXIBLE_PARSER_ARCHITECTURE.md` Section 4,
`POINTER_MODELS.md` "Implications for Our Pipeline") both identify
this as Phase 1 work: extract resolvers to `shared/address.py` with
a factory driven by the manifest's `rom_layout` object.

---

## 3. Current State

### `cpu_to_rom` (parser.py, line 213)

```python
INES_HEADER_SIZE = 16

def cpu_to_rom(cpu_addr: int) -> int:
    """Convert NES CPU address to ROM file offset."""
    return cpu_addr - 0x8000 + INES_HEADER_SIZE
```

Used 7 times in `parser.py` (pointer table reads, subroutine/repeat
target resolution, channel start offsets). Implements mapper 0 / linear
resolution. Works for CV1 because its music data sits in the fixed bank
region even though the ROM is technically mapper 2.

### `contra_cpu_to_rom` (contra_parser.py, line 51)

```python
BANK_SIZE = 16384
SOUND_BANK = 1
NUM_PRG_BANKS = 8

def contra_cpu_to_rom(cpu_addr: int) -> int:
    """Convert Contra CPU address to ROM offset (bank 1 at $8000)."""
    if 0x8000 <= cpu_addr <= 0xBFFF:
        return INES_HEADER_SIZE + SOUND_BANK * BANK_SIZE + (cpu_addr - 0x8000)
    elif 0xC000 <= cpu_addr <= 0xFFFF:
        return INES_HEADER_SIZE + (NUM_PRG_BANKS - 1) * BANK_SIZE + (cpu_addr - 0xC000)
    raise ValueError(f"Invalid CPU address: ${cpu_addr:04X}")
```

Used 7 times in `contra_parser.py`. Implements mapper 2 / UNROM
bank-switched resolution with a switchable bank ($8000-$BFFF) and a
fixed last bank ($C000-$FFFF). Constants are module-level, not read
from the manifest.

### Manifest declarations (unused by code)

- `castlevania1.json`: `"resolver_method": "linear"`
- `contra.json`: `"resolver_method": "bank_switched"`,
  `"sound_bank": 1`, `"prg_banks": 8`

These values are correct but purely informational. The parsers ignore
them and use their own hardcoded constants.

---

## 4. Concrete Steps

### Step 1: Define the AddressResolver ABC

Create `extraction/drivers/shared/address.py`:

```python
from abc import ABC, abstractmethod

class AddressResolver(ABC):
    """Converts NES CPU addresses to ROM file offsets."""

    @abstractmethod
    def cpu_to_rom(self, cpu_addr: int) -> int:
        """Convert a CPU address to a ROM file offset."""
        ...

    @abstractmethod
    def rom_to_cpu(self, rom_offset: int) -> int:
        """Convert a ROM file offset back to a CPU address."""
        ...
```

### Step 2: Implement concrete resolvers

**LinearResolver** (mapper 0 / NROM, and mapper 2 games where data
is in the fixed region):

```python
class LinearResolver(AddressResolver):
    def __init__(self, header_size: int = 16):
        self.header_size = header_size

    def cpu_to_rom(self, cpu_addr: int) -> int:
        return cpu_addr - 0x8000 + self.header_size

    def rom_to_cpu(self, rom_offset: int) -> int:
        return rom_offset + 0x8000 - self.header_size
```

**BankSwitchedResolver** (mapper 2 / UNROM, mapper 1 mode 3):

```python
class BankSwitchedResolver(AddressResolver):
    def __init__(self, sound_bank: int, num_prg_banks: int,
                 bank_size: int = 16384, header_size: int = 16):
        self.sound_bank = sound_bank
        self.num_prg_banks = num_prg_banks
        self.bank_size = bank_size
        self.header_size = header_size

    def cpu_to_rom(self, cpu_addr: int) -> int:
        if 0x8000 <= cpu_addr <= 0xBFFF:
            return (self.header_size
                    + self.sound_bank * self.bank_size
                    + (cpu_addr - 0x8000))
        elif 0xC000 <= cpu_addr <= 0xFFFF:
            return (self.header_size
                    + (self.num_prg_banks - 1) * self.bank_size
                    + (cpu_addr - 0xC000))
        raise ValueError(f"Invalid CPU address: ${cpu_addr:04X}")

    def rom_to_cpu(self, rom_offset: int) -> int:
        # Inverse for the switchable bank region
        adjusted = rom_offset - self.header_size
        bank = adjusted // self.bank_size
        offset_in_bank = adjusted % self.bank_size
        if bank == self.sound_bank:
            return 0x8000 + offset_in_bank
        elif bank == self.num_prg_banks - 1:
            return 0xC000 + offset_in_bank
        raise ValueError(f"ROM offset {rom_offset} not in sound or fixed bank")
```

**MultiWindowResolver** (mapper 4 / MMC3 -- stub for future use):

```python
class MultiWindowResolver(AddressResolver):
    def __init__(self, bank_map: dict, num_8k_banks: int,
                 header_size: int = 16):
        self.bank_map = bank_map
        self.num_8k_banks = num_8k_banks
        self.header_size = header_size

    def cpu_to_rom(self, cpu_addr: int) -> int:
        # Dispatch to correct 8KB window
        ...
```

### Step 3: Build a factory function

```python
def get_resolver(rom_layout: dict) -> AddressResolver:
    """Create an AddressResolver from a manifest's rom_layout section."""
    method = rom_layout["resolver_method"]
    header = rom_layout.get("header_size", 16)

    if method == "linear":
        return LinearResolver(header_size=header)

    elif method == "bank_switched":
        return BankSwitchedResolver(
            sound_bank=rom_layout["sound_bank"],
            num_prg_banks=rom_layout["prg_banks"],
            header_size=header,
        )

    raise ValueError(f"Unknown resolver method: {method}")
```

### Step 4: Migrate parsers

In `parser.py`:
- Import `get_resolver` (or `LinearResolver` directly).
- Replace all 7 calls to the module-level `cpu_to_rom()` with
  `self.resolver.cpu_to_rom()`, where `self.resolver` is constructed
  from the manifest or defaults to `LinearResolver()`.
- Keep the old `cpu_to_rom` function as a deprecated re-export for
  any external callers.

In `contra_parser.py`:
- Remove `BANK_SIZE`, `SOUND_BANK`, `NUM_PRG_BANKS` constants.
- Remove `contra_cpu_to_rom` function.
- Accept a resolver in the parser constructor (or build one from
  the manifest's `rom_layout`).
- Replace all 7 calls to `contra_cpu_to_rom()` with
  `self.resolver.cpu_to_rom()`.

### Step 5: Add unit tests

Create `tests/test_address_resolver.py`:
- Test `LinearResolver` with known CV1 addresses.
- Test `BankSwitchedResolver` with known Contra addresses (both
  switchable and fixed bank regions).
- Test `get_resolver` factory with both manifest `rom_layout` dicts.
- Test round-trip: `rom_to_cpu(cpu_to_rom(addr)) == addr` for all
  resolver types.
- Test error cases: invalid CPU addresses, unknown resolver methods.

### Step 6: Validate

- Run `PYTHONPATH=. python scripts/trace_compare.py --frames 1792`
  (CV1 pulse validation). Must show 0 pitch mismatches.
- Run Contra parsing and verify output matches pre-migration output.
- Run existing test suite.

---

## 5. Estimated Effort

| Step | Effort |
|------|--------|
| ABC + LinearResolver + BankSwitchedResolver | 30 min |
| Factory function | 10 min |
| Migrate parser.py (7 call sites) | 20 min |
| Migrate contra_parser.py (7 call sites) | 20 min |
| Unit tests | 30 min |
| Trace validation + ear check | 15 min |
| **Total** | **~2 hours** |

This is a small, well-scoped refactoring. The risk is low because
the math does not change -- only where it lives and how it is
parameterized.

---

## 6. Dependencies

- **Manifest schema**: The `rom_layout` section of
  `castlevania1.json` and `contra.json` already contains
  `resolver_method`, `sound_bank`, and `prg_banks`. No manifest
  changes are needed for the two existing games.
- **shared/ package**: The `extraction/drivers/shared/` directory
  must exist (or be created). This is also identified in
  `FLEXIBLE_PARSER_ARCHITECTURE.md` Phase 1.
- **No downstream dependencies**: `frame_ir.py`, `midi_export.py`,
  `trace_compare.py`, and `full_pipeline.py` do not call address
  resolution functions directly. They consume `ParsedSong` objects
  where addresses are already resolved.

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Off-by-one in migration (replacing function calls) | Low | High (silent wrong notes) | Trace comparison before and after; diff ParsedSong output |
| Breaking import paths for external scripts | Low | Medium | Keep deprecated re-exports in parser.py |
| Over-engineering MultiWindowResolver before it is needed | Medium | Low (wasted time) | Implement only LinearResolver and BankSwitchedResolver now; stub MMC3/MMC5 |
| Manifest `rom_layout` missing fields for future games | Low | Low | Factory raises clear ValueError for missing keys |

The biggest real risk is **silent corruption from wrong bank math**.
The existing functions are tested and correct. The new implementations
must produce byte-identical results. The mitigation is mechanical:
run both old and new functions on the same inputs and assert equality
before removing the old code.

---

## 8. Success Criteria

1. `extraction/drivers/shared/address.py` exists with
   `AddressResolver` ABC, `LinearResolver`, `BankSwitchedResolver`,
   and `get_resolver` factory.
2. `parser.py` and `contra_parser.py` use injected resolvers instead
   of module-level functions.
3. Old `cpu_to_rom` and `contra_cpu_to_rom` are either removed or
   kept as deprecated thin wrappers.
4. `get_resolver(manifest["rom_layout"])` produces the correct
   resolver for both CV1 and Contra manifests.
5. `trace_compare.py --frames 1792` shows 0 pitch mismatches (CV1).
6. Contra Jungle parse output is byte-identical to pre-migration.
7. Unit tests cover both resolver types, the factory, round-trips,
   and error cases.
8. Adding a new UNROM game (e.g., Super C) requires zero new
   address functions -- only a manifest entry with `sound_bank` and
   `prg_banks`.

---

## 9. Priority Ranking

**Priority: Medium (do during Phase 1 shared extraction)**

This is the lowest-risk piece of the Phase 1 refactoring described
in `FLEXIBLE_PARSER_ARCHITECTURE.md`. It touches only address math,
not parsing logic or envelope models. It should be done:

- **Before** adding a third Maezawa game (Super C, TMNT). Without
  this, the third game means a third hardcoded function with a third
  set of baked-in constants.
- **Before** or **alongside** extracting shared types to
  `shared/types.py` (both are Phase 1 and independent of each other).
- **After** the current Contra volume envelope work is complete
  (do not interrupt an active investigation with a refactoring).

It blocks nothing today but prevents accumulation of per-game
address functions as the game count grows. The two-hour effort is
small enough to slot into any session gap.
