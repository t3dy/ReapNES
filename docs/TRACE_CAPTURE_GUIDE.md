# Trace Capture Guide

## Overview

NES Music Lab's pipeline begins with APU register write traces — timestamped logs of every value written to the NES sound hardware during emulation. This guide covers how to capture these traces from supported emulators.

## Supported Emulators

### Mesen (Recommended)

Mesen has the best APU debugging and Lua scripting support for automated capture.

**Manual capture via Debug → APU Viewer:**
1. Load the ROM in Mesen.
2. Open **Debug → APU Viewer** to verify audio channels are active.
3. Open **Debug → Script Window**.
4. Load the Lua script below to capture APU writes.
5. Play the game to the desired music.
6. Stop the script and save the output.

**Mesen Lua capture script (`docs/scripts/mesen_apu_capture.lua`):**

```lua
-- Mesen APU register write capture script for NES Music Lab
-- Captures all writes to $4000-$4017 with frame numbers.

local output = {}
local frame = 0

function onFrame()
    frame = frame + 1
end

function onWrite(addr, value)
    if addr >= 0x4000 and addr <= 0x4017 then
        table.insert(output, string.format('%d,$%04X,%d', frame, addr, value))
    end
end

emu.addEventCallback(onFrame, emu.eventType.endFrame)
emu.addMemoryCallback(onWrite, emu.callbackType.cpuWrite, 0x4000, 0x4017)

-- To stop and save: call saveOutput() from the script console
function saveOutput()
    local file = io.open("apu_trace.csv", "w")
    file:write("frame,address,value\n")
    for _, line in ipairs(output) do
        file:write(line .. "\n")
    end
    file:close()
    emu.log("Saved " .. #output .. " APU writes to apu_trace.csv")
end
```

### FCEUX

FCEUX supports trace logging but with less APU-specific granularity.

**Manual capture:**
1. Load the ROM.
2. Open **Debug → Trace Logger**.
3. Configure to log CPU writes.
4. Filter for addresses $4000-$4017 in post-processing.

### NSFPlay / NSFe

For NSF files (ripped music without the full ROM):
1. Load the NSF in NSFPlay.
2. Use the built-in register logger.
3. Export as CSV or text.

## Converting Traces to NES Music Lab Format

Raw emulator output needs conversion to the NES Music Lab JSON trace format.

**From Mesen CSV:**
```bash
PYTHONPATH=src python -m nesml.trace_convert mesen_csv apu_trace.csv --rom-name "Game Name" --output traces/game_name/capture_001.json
```

**Expected JSON format:**
```json
{
  "schema_version": "0.1.0",
  "metadata": {
    "source": "mesen",
    "rom_name": "Game Name",
    "rom_sha256": "...",
    "region": "ntsc"
  },
  "writes": [
    {"frame": 0, "address": "$4000", "value": 191},
    {"frame": 0, "address": "$4002", "value": 253}
  ]
}
```

## Capture Best Practices

1. **Isolate the music.** Start capture after the title screen loads but before gameplay adds SFX. Alternatively, use NSFs to capture music without SFX interference.

2. **Capture at least 2 full loops.** Most NES songs loop. Capture enough to detect the loop point reliably.

3. **Note the song ID.** Record which in-game location or menu triggered this music.

4. **Record the region.** NTSC (60Hz) vs PAL (50Hz) affects timing calculations.

5. **Hash the ROM.** Use the manifest SHA-256 to ensure trace-ROM correspondence.

## Trace File Organization

```
traces/
  castlevania/
    capture_001_stage1.json    # Stage 1 BGM
    capture_002_boss.json      # Boss BGM
    capture_003_title.json     # Title screen
  darkwing_duck/
    capture_001_stage1.json
```

## Next Steps

Once you have a trace file:
1. Run `/apu-trace-analysis` to ingest and normalize.
2. Review the channel activity summary.
3. Run `/sequence-reconstruction` for symbolic analysis.
