-- Quick test script to figure out Mesen 2's Lua API
-- Load this, press F5, check the log for output

-- Test 1: What does emu.getState() look like?
local state = emu.getState()
emu.log("=== STATE KEYS ===")
for k, v in pairs(state) do
    emu.log("  " .. tostring(k) .. " = " .. type(v))
end

-- Test 2: If state.cpu exists, what's in it?
if state.cpu then
    emu.log("=== CPU STATE ===")
    for k, v in pairs(state.cpu) do
        emu.log("  cpu." .. tostring(k) .. " = " .. tostring(v))
    end
end

-- Test 3: Try other possible paths
if state.nes then
    emu.log("=== NES STATE ===")
    for k, v in pairs(state.nes) do
        emu.log("  nes." .. tostring(k) .. " = " .. type(v))
    end
end

-- Test 4: Check what memCallbackType values exist
emu.log("=== CALLBACK TYPES ===")
for k, v in pairs(emu.callbackType) do
    emu.log("  " .. tostring(k) .. " = " .. tostring(v))
end

-- Test 5: Check memType values
emu.log("=== MEM TYPES ===")
for k, v in pairs(emu.memType) do
    emu.log("  " .. tostring(k) .. " = " .. tostring(v))
end

-- Test 6: Try a cpuExec callback on a small range and log what we get
local testCount = 0
emu.addMemoryCallback(function(address, value)
    if testCount < 5 then
        emu.log(string.format("cpuExec: addr=$%04X value=%d", address, value))
        local s = emu.getState()
        if s.cpu then
            emu.log(string.format("  cpu.a=%s cpu.x=%s cpu.y=%s",
                tostring(s.cpu.a), tostring(s.cpu.x), tostring(s.cpu.y)))
        else
            emu.log("  no s.cpu — dumping top keys:")
            for k, v in pairs(s) do
                emu.log("    " .. tostring(k) .. " = " .. type(v))
            end
        end
        testCount = testCount + 1
    end
end, emu.callbackType.cpuExec, 0x8000, 0x8010)

emu.log("")
emu.log("Debug test loaded. Check output above.")
