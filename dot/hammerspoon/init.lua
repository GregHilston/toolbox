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

function alternateLaptopScreenBrightness()
  if hs.brightness.get() == 0 then
    hs.brightness.set(100)
  else
    hs.brightness.set(0)
  end
end

activationCommandKeyStroke = {"cmd", "ctrl"}
activationCommandKeyStrokeRight = {"cmd", "ctrl", "shift"}

leftSideClickX = 500
rightSideClickX = 1200

-- docked at work
-- hs.hotkey.bind(activationCommandKeyStroke, "1", function()
--    clickScreen(1, leftSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStroke, "2", function()
--    clickScreen(3, leftSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStroke, "3", function()
--    clickScreen(2, leftSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStroke, "4", function()
--    clickScreen(4, leftSideClickX)
-- end)

-- hs.hotkey.bind(activationCommandKeyStrokeRight, "1", function()
--    clickScreen(1, rightSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStrokeRight, "2", function()
--    clickScreen(3, rightSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStrokeRight, "3", function()
--    clickScreen(2, rightSideClickX)
-- end)
-- hs.hotkey.bind(activationCommandKeyStrokeRight, "4", function()
--    clickScreen(4, rightSideClickX)
-- end)

-- home w/ laptop open
--hs.hotkey.bind(activationCommandKeyStroke, "1", function()
--    clickScreen(3, leftSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStroke, "2", function()
--    clickScreen(2, leftSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStroke, "3", function()
 --   clickScreen(4, leftSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStroke, "4", function()
--    clickScreen(1, leftSideClickX)
--end)

--hs.hotkey.bind(activationCommandKeyStrokeRight, "1", function()
--    clickScreen(3, rightSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStrokeRight, "2", function()
--    clickScreen(2, rightSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStrokeRight, "3", function()
--    clickScreen(4, rightSideClickX)
--end)
--hs.hotkey.bind(activationCommandKeyStrokeRight, "4", function()
--    clickScreen(1, rightSideClickX)
--end)

-- home w/ laptop closed
hs.hotkey.bind(activationCommandKeyStroke, "1", function()
    clickScreen(3, leftSideClickX)
end)
hs.hotkey.bind(activationCommandKeyStroke, "2", function()
    clickScreen(2, leftSideClickX)
end)
hs.hotkey.bind(activationCommandKeyStroke, "3", function()
    clickScreen(1, leftSideClickX)
end)

hs.hotkey.bind(activationCommandKeyStrokeRight, "1", function()
    clickScreen(3, rightSideClickX)
end)
hs.hotkey.bind(activationCommandKeyStrokeRight, "2", function()
    clickScreen(2, rightSideClickX)
end)
hs.hotkey.bind(activationCommandKeyStrokeRight, "3", function()
    clickScreen(1, rightSideClickX)
end)


hs.hotkey.bind({"alt"}, "1", function()
  alternateLaptopScreenBrightness()
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

-- from https://blog.jverkamp.com/2016/02/08/duplicating-aerosnap-on-osx-with-hammerspoon/

-- Reload hammerspoon configs
hs.hotkey.bind({"cmd", "ctrl"}, "R", function()
    hs.reload()
end)

-- Lock
hs.hotkey.bind({"cmd", "ctrl"}, 'L', function()
    os.execute("pmset displaysleepnow")
end)

-- Aerosnap helper functions to get and set current window parameters
function aerosnap_get_parameters()
    local window = hs.window.focusedWindow()
    local frame = window:frame()
    local screen = window:screen()
    local bounds = screen:frame()

    return window, frame, bounds
end

-- Aerosnap help to move a window to a specified position
function aerosnap_move_window(x, y, w, h)
    local window, frame, bounds = aerosnap_get_parameters()

    frame.x = x
    frame.y = y
    frame.w = w
    frame.h = h

    window:setFrame(frame)
end

-- Save the current window's position so we can restore it
function aerosnap_save_window()
    local window, frame, bounds = aerosnap_get_parameters()
    saved_window_sizes = saved_window_sizes or {}
    saved_window_sizes[window:id()] = {x = frame.x, y = frame.y, w = frame.w, h = frame.h}
end

-- Aerosnap move window to the left half
hs.hotkey.bind({"cmd", "ctrl"}, "Left", function()
    local window, frame, bounds = aerosnap_get_parameters()
    aerosnap_save_window()
    aerosnap_move_window(bounds.x, bounds.y, bounds.w / 2, bounds.h)
end)

-- Aerosnap move window to the right half
hs.hotkey.bind({"cmd", "ctrl"}, "Right", function()
    local window, frame, bounds = aerosnap_get_parameters()
    aerosnap_save_window()
    aerosnap_move_window(bounds.x + bounds.w / 2, bounds.y, bounds.w / 2, bounds.h)
end)

-- Aerosnap maximize current window, saving size to restore
hs.hotkey.bind({"cmd", "ctrl"}, "Up", function()
    local window, frame, bounds = aerosnap_get_parameters()
    aerosnap_save_window()
    aerosnap_move_window(bounds.x, bounds.y, bounds.w, bounds.h)
end)

-- Restore the last saved window configuration for a window (basically, a one level undo)
hs.hotkey.bind({"cmd", "ctrl"}, "Down", function()
    local window, frame, bounds = aerosnap_get_parameters()

    old_bounds = saved_window_sizes[window:id()]
    if old_bounds ~= nil then
        aerosnap_move_window(old_bounds.x, old_bounds.y, old_bounds.w, old_bounds.h)
        saved_window_sizes[window:id()] = nil
    end
end)

hs.alert.show("Config loaded...")

-- use `hs.inspect` if you ever need to look at stuff, especially stuff I didn't make
-- ex: `hs.inspect(activationCommandKeyStroke)` in the console
