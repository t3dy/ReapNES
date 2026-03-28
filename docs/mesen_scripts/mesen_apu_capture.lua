-- =============================================================
-- NES Music Lab — Mesen 2 APU Capture Script (v7)
-- =============================================================
--
-- Uses endFrame callback to snapshot APU state each frame.
-- Mesen 2 exposes full decoded APU state via emu.getState()
-- with flat string keys like "apu.square1.timer.period".
--
-- This is BETTER than register writes — we get decoded values
-- (period, duty, volume, etc.) directly from the emulator.
-- No interference with audio. No write callbacks at all.
--
-- CONTROLS:
--   [  = Start capture
--   ]  = Stop capture and save
--   \  = Check status
--
-- =============================================================

local outputPath = "C:\\Users\\PC\\Documents\\Mesen2\\capture.csv"

local capturing = false
local writes = {}
local frameCount = 0
local captureStartFrame = 0
local startHeld = false
local stopHeld = false
local statusHeld = false

-- APU state keys we care about, mapped to pseudo-register addresses
-- so our pipeline can process them
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

-- Previous values for change detection
local prevValues = {}

local function resetPrev()
    for _, entry in ipairs(apuKeys) do
        prevValues[entry.key] = nil
    end
end

-- Each frame, snapshot APU state and log changes
emu.addEventCallback(function()
    frameCount = frameCount + 1
    if not capturing then return end

    local state = emu.getState()
    local relativeFrame = frameCount - captureStartFrame

    for _, entry in ipairs(apuKeys) do
        local val = state[entry.key]
        if val ~= nil then
            -- Convert booleans to 0/1
            if type(val) == "boolean" then
                val = val and 1 or 0
            end
            if val ~= prevValues[entry.key] then
                writes[#writes + 1] = string.format("%d,%s,%s",
                    relativeFrame, entry.addr, tostring(val))
                prevValues[entry.key] = val
            end
        end
    end
end, emu.eventType.endFrame)

-- Keyboard controls
emu.addEventCallback(function()
    local startKey = emu.isKeyPressed("[")
    if startKey and not startHeld then
        if not capturing then
            writes = {}
            captureStartFrame = frameCount
            resetPrev()
            capturing = true
            emu.log("")
            emu.log("======================================")
            emu.log(" CAPTURE STARTED at frame " .. frameCount)
            emu.log(" Press ] to stop and save")
            emu.log("======================================")
        end
    end
    startHeld = startKey

    local stopKey = emu.isKeyPressed("]")
    if stopKey and not stopHeld then
        if capturing then
            capturing = false
            local duration = frameCount - captureStartFrame
            emu.log("")
            emu.log("======================================")
            emu.log(" CAPTURE STOPPED")
            emu.log(" " .. #writes .. " state changes")
            emu.log(" " .. duration .. " frames")
            emu.log(" " .. string.format("%.1f", duration / 60.0988) .. " seconds")
            emu.log("======================================")

            if #writes > 0 then
                local file = io.open(outputPath, "w")
                if file then
                    file:write("frame,parameter,value\n")
                    for i = 1, #writes do
                        file:write(writes[i] .. "\n")
                    end
                    file:close()
                    emu.log("")
                    emu.log(" SAVED: " .. outputPath)
                else
                    emu.log(" ERROR: Could not write to " .. outputPath)
                end
            end
        end
    end
    stopHeld = stopKey

    local statusKey = emu.isKeyPressed("\\")
    if statusKey and not statusHeld then
        if capturing then
            local elapsed = frameCount - captureStartFrame
            emu.log("CAPTURING: " .. #writes .. " changes, "
                .. elapsed .. " frames ("
                .. string.format("%.1f", elapsed / 60.0988) .. "s)")
        else
            emu.log("NOT CAPTURING. " .. #writes .. " changes stored.")
        end
    end
    statusHeld = statusKey
end, emu.eventType.inputPolled)

emu.log("==============================================")
emu.log(" NES Music Lab — APU Capture v7 (state poll)")
emu.log("==============================================")
emu.log("")
emu.log(" [  = Start capture")
emu.log(" ]  = Stop capture and save")
emu.log(" \\  = Check status")
emu.log("")
emu.log(" Output: " .. outputPath)
emu.log("")
emu.log(" Polls decoded APU state each frame.")
emu.log(" No write callbacks — zero audio interference.")
emu.log("")
emu.log(" Ready. Press [")
emu.log("==============================================")
