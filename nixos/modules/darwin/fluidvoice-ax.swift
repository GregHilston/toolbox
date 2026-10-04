// fluidvoice-ax: turn on accessibility in Electron apps.
// Usage: fluidvoice-ax <bundle-id>...
// Why and how: nixos/CLAUDE.md → "Write Mode in Electron apps".

import AppKit
import ApplicationServices

let bundleIDs = Set(CommandLine.arguments.dropFirst())
guard !bundleIDs.isEmpty else {
    FileHandle.standardError.write("usage: fluidvoice-ax <bundle-id>...\n".data(using: .utf8)!)
    exit(2)
}

// The prompt lists it under Accessibility.
let promptKey = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
if !AXIsProcessTrustedWithOptions([promptKey: true] as CFDictionary) {
    print("not trusted: allow \(CommandLine.arguments[0]) in System Settings → Privacy & Security → Accessibility")
}

// Per pid: log changes only.
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
