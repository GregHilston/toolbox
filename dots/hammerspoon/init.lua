-- reload on changes to config
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
myWatcher = hs.pathwatcher.new(os.getenv("HOME") .. "/.hammerspoon/", reloadConfig):start()

-- config
function clickScreen(screenNumber, x)
    screen = hs.screen.allScreens()[screenNumber]
    hs.mouse.setRelativePosition({x=x, y=500}, screen)
    hs.eventtap.leftClick(hs.mouse.getAbsolutePosition())
end

activationCommandKeyStroke = {"cmd", "ctrl"}
activationCommandKeyStrokeRight = {"cmd", "ctrl", "shift"}

hs.hotkey.bind(activationCommandKeyStroke, "1", function()
    hs.alert.show("clickScreen 1 500")
    clickScreen(2, 500)
end)
hs.hotkey.bind(activationCommandKeyStroke, "2", function()
    clickScreen(3, 500)
end)
hs.hotkey.bind(activationCommandKeyStroke, "3", function()
    clickScreen(4, 500)
end)
hs.hotkey.bind(activationCommandKeyStroke, "4", function()
    clickScreen(1, 500)
end)

hs.hotkey.bind(activationCommandKeyStrokeRight, "1", function()
    hs.alert.show("clickScreen 1 1200")
    clickScreen(2, 1200)
end)
hs.hotkey.bind(activationCommandKeyStrokeRight, "2", function()
    clickScreen(3, 1200)
end)
hs.hotkey.bind(activationCommandKeyStrokeRight, "3", function()
    clickScreen(4, 1200)
end)
hs.hotkey.bind(activationCommandKeyStrokeRight, "4", function()
    clickScreen(1, 1200)
end)


hs.hotkey.bind(activationCommandKeyStroke, "left", function()
    hs.window.focusedWindow():moveOneScreenWest()
end)

hs.hotkey.bind(activationCommandKeyStroke, "right", function()
    hs.window.focusedWindow():moveOneScreenEast()
end)

hs.hotkey.bind(activationCommandKeyStroke, "f", function()
	-- show hint keys for visible windows.
	-- remove the hs.window.visibleWindows()
	--   to show hints for minimized windows
    hs.hints.windowHints(hs.window.visibleWindows())
end)
hs.alert.show("Config loaded...")

-- use `hs.inspect` if you ever need to look at stuff, especially stuff I didn't make
-- ex: `hs.inspect(activationCommandKeyStroke)` in the console