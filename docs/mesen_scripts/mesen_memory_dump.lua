-- =============================================================
-- NES Music Lab — Mesen 2 Memory Region Dump Script
-- =============================================================
--
-- PURPOSE:
--   Dumps specific memory regions from a running ROM for
--   static analysis. Useful for extracting pointer tables,
--   song data, and driver code from known addresses.
--
-- HOW TO USE:
--   1. Load the ROM in Mesen 2
--   2. Open Script Window
--   3. Paste this script and click Run
--   4. Use the commands in the console
--
-- =============================================================

function dumpRegion(startAddr, length, filename)
    -- Reads CPU address space and writes raw bytes to a file
    local file = io.open(filename, "wb")
    if not file then
        emu.log("ERROR: Could not open file: " .. filename)
        return
    end

    local bytes = {}
    for i = 0, length - 1 do
        local addr = startAddr + i
        local val = emu.read(addr, emu.memType.cpu)
        table.insert(bytes, string.char(val))
    end

    file:write(table.concat(bytes))
    file:close()
    emu.log(string.format("Dumped %d bytes from $%04X to %s", length, startAddr, filename))
end

function dumpHex(startAddr, length)
    -- Prints a hex dump to the console (useful for quick inspection)
    local line = ""
    for i = 0, length - 1 do
        local addr = startAddr + i
        local val = emu.read(addr, emu.memType.cpu)
        if i % 16 == 0 then
            if line ~= "" then emu.log(line) end
            line = string.format("$%04X: ", addr)
        end
        line = line .. string.format("%02X ", val)
    end
    if line ~= "" then emu.log(line) end
end

function readWord(addr)
    -- Read a 16-bit little-endian word from CPU address space
    local lo = emu.read(addr, emu.memType.cpu)
    local hi = emu.read(addr + 1, emu.memType.cpu)
    local val = (hi * 256) + lo
    emu.log(string.format("[$%04X] = $%04X (lo=$%02X hi=$%02X)", addr, val, lo, hi))
    return val
end

function readPointerTable(addr, count)
    -- Read a table of 16-bit LE pointers
    emu.log(string.format("Pointer table at $%04X, %d entries:", addr, count))
    for i = 0, count - 1 do
        local ptrAddr = addr + (i * 2)
        local lo = emu.read(ptrAddr, emu.memType.cpu)
        local hi = emu.read(ptrAddr + 1, emu.memType.cpu)
        local target = (hi * 256) + lo
        emu.log(string.format("  [%2d] $%04X -> $%04X", i, ptrAddr, target))
    end
end

function findNMI()
    -- Read the NMI vector from $FFFA-$FFFB
    local lo = emu.read(0xFFFA, emu.memType.cpu)
    local hi = emu.read(0xFFFB, emu.memType.cpu)
    local nmi = (hi * 256) + lo
    emu.log(string.format("NMI vector: $%04X", nmi))
    emu.log("Dumping first 32 bytes of NMI handler:")
    dumpHex(nmi, 32)
    return nmi
end

function findReset()
    -- Read the RESET vector from $FFFC-$FFFD
    local lo = emu.read(0xFFFC, emu.memType.cpu)
    local hi = emu.read(0xFFFD, emu.memType.cpu)
    local reset = (hi * 256) + lo
    emu.log(string.format("RESET vector: $%04X", reset))
    return reset
end

function searchBytes(startAddr, endAddr, pattern)
    -- Search for a byte pattern in CPU address space
    -- pattern is a table of bytes, e.g. {0x8D, 0x15, 0x40} for STA $4015
    local patLen = #pattern
    local results = {}
    for addr = startAddr, endAddr - patLen do
        local match = true
        for i = 1, patLen do
            if emu.read(addr + i - 1, emu.memType.cpu) ~= pattern[i] then
                match = false
                break
            end
        end
        if match then
            table.insert(results, addr)
            emu.log(string.format("  Found at $%04X", addr))
        end
    end
    emu.log(string.format("Search complete: %d matches", #results))
    return results
end

-- ==========================================
-- Ready
-- ==========================================
emu.log("==============================================")
emu.log(" NES Music Lab — Memory Dump Tools Loaded")
emu.log("==============================================")
emu.log("")
emu.log("Commands:")
emu.log("  findNMI()                           - read NMI vector and dump handler")
emu.log("  findReset()                         - read RESET vector")
emu.log("  dumpHex(addr, length)               - hex dump to console")
emu.log("  readWord(addr)                      - read 16-bit LE value")
emu.log("  readPointerTable(addr, count)       - read table of pointers")
emu.log("  dumpRegion(addr, len, 'file.bin')   - dump to binary file")
emu.log("  searchBytes(start, end, {bytes})    - search for byte pattern")
emu.log("")
emu.log("Example: search for STA $4015 (APU status writes):")
emu.log("  searchBytes(0x8000, 0xFFFF, {0x8D, 0x15, 0x40})")
