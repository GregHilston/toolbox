/**
 * Loads API keys from ~/.pi/agent/secrets.json into process.env.
 *
 * This looks like pointless indirection until you try to run pi under PI WEB.
 *
 * Extensions that need a key read it from the environment — pi-brave-search
 * does `process.env.BRAVE_API_KEY` at tool-call time — so the obvious fix is an
 * `export` in ~/.zshrc.local. That works in the TUI and *silently* does not
 * work in PI WEB: its session daemon is a launchd agent, launchd agents never
 * source a shell rc, and agent processes inherit the daemon's environment. The
 * daemon's plist environment is a modeled set that `pi-web doctor` validates
 * against the canonical file, so we cannot smuggle a key in there either.
 *
 * Setting it from inside pi sidesteps both: one code path, identical behavior
 * in the terminal and in the browser.
 *
 * The file is generated from secrets.json.tpl by `just secrets` (1Password) and
 * is gitignored. A missing or malformed file is not an error — the extensions
 * that want a key already report their own "no key found" message, and pi
 * should still start on a host that has never run `just secrets`.
 *
 * A real environment variable always wins, so `BRAVE_API_KEY=... pi` still
 * overrides the file for a one-off.
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const SECRETS_PATH = join(homedir(), ".pi", "agent", "secrets.json");

export default function piSecretsExtension(_pi: ExtensionAPI): void {
	let raw: string;
	try {
		raw = readFileSync(SECRETS_PATH, "utf8");
	} catch {
		return; // no secrets file on this host — nothing to do
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch (error) {
		console.error(`pi-secrets: ${SECRETS_PATH} is not valid JSON: ${error}`);
		return;
	}

	if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
		console.error(`pi-secrets: ${SECRETS_PATH} must be a JSON object of NAME -> value.`);
		return;
	}

	for (const [name, value] of Object.entries(parsed as Record<string, unknown>)) {
		if (typeof value !== "string" || value === "") continue;
		if (process.env[name] !== undefined) continue; // a real export wins
		process.env[name] = value;
	}
}
