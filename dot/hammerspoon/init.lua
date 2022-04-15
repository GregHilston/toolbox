-- imports
-- local Pomo = require 'pomodoro'

-- function definitions
function reloadConfig(files)
    doReload = false
    for _, file in pairs(files) do
        if file:sub(-4) == ".lua" then
            doReload = true
        end
    end
    if doReload then
        hs.reload()
    end
end

function clickScreen(screenNumber, x)
    screen = hs.screen.allScreens()[screenNumber]
    hs.mouse.setRelativePosition({x=x, y=500}, screen)
    hs.eventtap.leftClick(hs.mouse.getAbsolutePosition())
end

function alternateLaptopScreenBrightness()
  if hs.brightness.get() == 0 then
    hs.brightness.set(100)
  else
    hs.brightness.set(0)
  end
end

function testBrightnessChange()
    currentScreenWithFocus = hs.screen.mainScreen()

    for i, screen in ipairs(hs.screen.allScreens()) do
        -- We only want to modify the brightness of the non-focused monitors, so we can focus.
        if (currentScreenWithFocus ~= screen) then
            hs.alert.show(string.format("attempting to modify brightness of screen %s", screen))
            hs.alert.show(screen:setGamma(0.0, 0.0))
            -- screen:setBrightness(20) -- does nothing
        end
    end
end


-- bindings

-- pomodoro app
-- hs.hotkey.bind({"alt"}, "P", Pomo.startNew)
-- hs.hotkey.bind(, Pomo.togglePaused)
-- hs.hotkey.bind(, Pomo.toggleLatestDisplay)

-- timer
hs.hotkey.bind({"alt"}, "P", function()
    buttonPressed, timerDurationInMinutes = hs.dialog.textPrompt("Create a timer", "duration in minutes", "", "Start", "Cancel")

    if (buttonPressed == "Start") then
        hs.execute(string.format("set-timer.sh %d", timerDurationInMinutes))
        hs.alert.show(string.format("set-timer.sh %d", timerDurationInMinutes))
    end
end)

-- Automatically reload config on saved changes.
-- This doesn't seem to be working anymore.
myWatcher = hs.pathwatcher.new(os.getenv("HOME") .. "/.hammerspoon/", reloadConfig):start()

-- Reload hammerspoon config manually.
hs.hotkey.bind({"cmd", "ctrl"}, "R", function()
    hs.reload()
end)

hs.hotkey.bind({"cmd", "ctrl"}, "P", function()
    testBrightnessChange()
end)

-- Not binding, as we're running generally with three external monitors.
-- hs.hotkey.bind({"alt"}, "p", function()
--   hs.alert.show("alternating brightness")
--   alternateLaptopScreenBrightness()
-- end)

-- Display navigation hotkeys for visible windows.
hs.hotkey.bind({"alt"}, "n", function()
	-- remove the hs.window.visibleWindows()
	--   to show hints for minimized windows
    hs.hints.windowHints(hs.window.visibleWindows())
end)

-- Lock the computer.
hs.hotkey.bind({"cmd", "ctrl"}, 'L', function()
    os.execute("pmset displaysleepnow")
end)

hs.alert.show("Config loaded...")
-- use `hs.inspect` if you ever need to look at stuff, especially stuff I didn't make
-- ex: `hs.inspect(activationCommandKeyStroke)` in the console
