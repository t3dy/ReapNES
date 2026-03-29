-- =============================================================
-- NES Music Lab — Mesen 2 APU Capture (AUTO START)
-- =============================================================
--
-- Starts capturing immediately when you run the script.
-- Saves automatically after MAX_FRAMES frames.
--
-- WORKFLOW:
--   1. Load your ROM in Mesen, navigate to the music
--   2. Open Script Window, load this script
--   3. Press Run — capture starts immediately
--   4. Wait for it to auto-save (or stop the script early)
--
-- =============================================================

local outputPath = "C:\\Dev\\NESMusicStudio\\capture_contra.csv"
local MAX_FRAMES = 4000  -- ~66 seconds at 60fps. Increase if needed.

local writes = {}
local frameCount = 0
local saved = false

-- APU state keys mapped to pseudo-register addresses
local apuKeys = {
    -- Pulse 1
    {key = "apu.square1.duty",                addr = "$4000_duty"},
    {key = "apu.square1.envelope.constantVolume", addr = "$4000_const"},
    {key = "apu.square1.envelope.volume",     addr = "$4000_vol"},
    {key = "apu.square1.timer.period",        addr = "$4002_period"},
    {key = "apu.square1.sweepEnabled",        addr = "$4001_sweep"},
    -- Pulse 2
    {key = "apu.square2.duty",                addr = "$4004_duty"},
    {key = "apu.square2.envelope.constantVolume", addr = "$4004_const"},
    {key = "apu.square2.envelope.volume",     addr = "$4004_vol"},
    {key = "apu.square2.timer.period",        addr = "$4006_period"},
    {key = "apu.square2.sweepEnabled",        addr = "$4005_sweep"},
    -- Triangle
    {key = "apu.triangle.timer.period",       addr = "$400A_period"},
    {key = "apu.triangle.linearCounter",      addr = "$4008_linear"},
    {key = "apu.triangle.lengthCounter.counter", addr = "$400B_length"},
    -- Noise
    {key = "apu.noise.envelope.volume",       addr = "$400C_vol"},
    {key = "apu.noise.envelope.constantVolume", addr = "$400C_const"},
    {key = "apu.noise.timer.period",          addr = "$400E_period"},
    {key = "apu.noise.modeFlag",              addr = "$400E_mode"},
    -- DMC
    {key = "apu.dmc.outputLevel",             addr = "$4011_dac"},
    {key = "apu.dmc.sampleAddr",              addr = "$4012_addr"},
    {key = "apu.dmc.sampleLength",            addr = "$4013_len"},
    {key = "apu.dmc.timer.period",            addr = "$4010_rate"},
}

local prevValues = {}

local function saveFile()
    if saved or #writes == 0 then return end
    saved = true
    local file = io.open(outputPath, "w")
    if file then
        file:write("frame,parameter,value\n")
        for i = 1, #writes do
            file:write(writes[i] .. "\n")
        end
        file:close()
        emu.log("")
        emu.log("======================================")
        emu.log(" SAVED: " .. outputPath)
        emu.log(" " .. #writes .. " state changes")
        emu.log(" " .. frameCount .. " frames")
        emu.log(" " .. string.format("%.1f", frameCount / 60.0) .. " seconds")
        emu.log("======================================")
    else
        emu.log("ERROR: Could not write to " .. outputPath)
    end
end

-- Capture every frame
emu.addEventCallback(function()
    if saved then return end

    frameCount = frameCount + 1

    local state = emu.getState()

    for _, entry in ipairs(apuKeys) do
        local val = state[entry.key]
        if val ~= nil then
            if type(val) == "boolean" then
                val = val and 1 or 0
            end
            if val ~= prevValues[entry.key] then
                writes[#writes + 1] = string.format("%d,%s,%s",
                    frameCount, entry.addr, tostring(val))
                prevValues[entry.key] = val
            end
        end
    end

    -- Save every 600 frames (~10 seconds) so you never lose data
    if frameCount % 600 == 0 then
        emu.log("  " .. frameCount .. " frames captured ("
            .. #writes .. " changes, "
            .. string.format("%.0f", frameCount / 60.0) .. "s)")
        saveFile()
        saved = false  -- allow re-saving with more data
    end

    -- Final save after MAX_FRAMES
    if frameCount >= MAX_FRAMES then
        saveFile()
    end
end, emu.eventType.endFrame)

emu.log("==============================================")
emu.log(" NES Music Lab — APU Capture (AUTO START)")
emu.log("==============================================")
emu.log("")
emu.log(" CAPTURING NOW — " .. MAX_FRAMES .. " frames max")
emu.log(" (~" .. string.format("%.0f", MAX_FRAMES / 60.0) .. " seconds)")
emu.log("")
emu.log(" Output: " .. outputPath)
emu.log("")
emu.log(" Status updates every 10 seconds.")
emu.log(" Stop the script early to save what you have.")
emu.log("==============================================")
