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
function clickScreen(screenNumber)
    screen = hs.screen.allScreens()[screenNumber]
    hs.mouse.setRelativePosition({x=500, y=500}, screen)
    hs.eventtap.leftClick(hs.mouse.getAbsolutePosition())
end

activationCommandKeyStroke = {"cmd", "ctrl"}

 -- not sure why but sometimes the screen 3 is my second monitor
hs.hotkey.bind(activationCommandKeyStroke, "1", function()
    clickScreen(1)
end)
hs.hotkey.bind(activationCommandKeyStroke, "2", function()
    clickScreen(3)
end)
hs.hotkey.bind(activationCommandKeyStroke, "3", function()
    clickScreen(2)
end)
hs.hotkey.bind(activationCommandKeyStroke, "4", function()
    clickScreen(4)
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