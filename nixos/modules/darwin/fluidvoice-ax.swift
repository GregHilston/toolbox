// fluidvoice-ax: turn on accessibility in Electron apps, so FluidVoice's Write
// Mode can read their selected text.
//
// Usage: fluidvoice-ax <bundle-id>...
//
// Electron apps (Slack, Obsidian, VS Code) build no accessibility tree until an
// assistive tool asks, by setting AXManualAccessibility on the app. FluidVoice
// 1.6.9 never asks: it reads kAXSelectedTextAttribute off the focused element,
// gets nothing, and Write Mode runs with no text ("Please provide the text...").
// This asks for it, for the listed apps, at startup and every time one launches
// or comes to the front. Setting it again is a no-op, and re-applying on
// activation covers an app that reset it or was not ready at launch.
//
// It needs the Accessibility permission itself; until granted, every set fails
// with kAXErrorAPIDisabled (-25211). The rationale lives in nixos/CLAUDE.md →
// "FluidVoice".

import AppKit
import ApplicationServices

let bundleIDs = Set(CommandLine.arguments.dropFirst())
guard !bundleIDs.isEmpty else {
    FileHandle.standardError.write("usage: fluidvoice-ax <bundle-id>...\n".data(using: .utf8)!)
    exit(2)
}

// The prompt adds this binary to the Accessibility list.
let promptKey = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
if !AXIsProcessTrustedWithOptions([promptKey: true] as CFDictionary) {
    print("not trusted: allow \(CommandLine.arguments[0]) in System Settings → Privacy & Security → Accessibility")
}

// Last result per pid, so the log records changes only.
var lastResult: [pid_t: AXError] = [:]

func enable(_ app: NSRunningApplication) {
    guard let id = app.bundleIdentifier, bundleIDs.contains(id) else { return }
    let element = AXUIElementCreateApplication(app.processIdentifier)
    let result = AXUIElementSetAttributeValue(element, "AXManualAccessibility" as CFString, kCFBooleanTrue)
    if lastResult[app.processIdentifier] != result {
        print("\(id) pid \(app.processIdentifier): AXManualAccessibility = true -> \(result.rawValue)")
        lastResult[app.processIdentifier] = result
    }
}

setvbuf(stdout, nil, _IOLBF, 0)
NSWorkspace.shared.runningApplications.forEach(enable)

let center = NSWorkspace.shared.notificationCenter
for name in [NSWorkspace.didLaunchApplicationNotification, NSWorkspace.didActivateApplicationNotification] {
    center.addObserver(forName: name, object: nil, queue: .main) { note in
        if let app = note.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication {
            enable(app)
        }
    }
}
center.addObserver(forName: NSWorkspace.didTerminateApplicationNotification, object: nil, queue: .main) { note in
    if let app = note.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication {
        lastResult[app.processIdentifier] = nil
    }
}

RunLoop.main.run()
