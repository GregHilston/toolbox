/**
 * Loads API keys from ~/.pi/agent/secrets.json into process.env.
 *
 * Extensions that need a key read it from the environment — pi-brave-search does
 * `process.env.BRAVE_API_KEY` at tool-call time — so why not just export it?
 *
 * Two other places could hold it, and both are worse:
 *
 *   ~/.zshrc.local  Does not work under PI WEB. Its launchd agents run
 *                   `/usr/bin/env zsh -lc <cmd>` (dist/nativeServices/serviceRendering.js),
 *                   which is a *login* shell but not an *interactive* one — so
 *                   ~/.zshenv and ~/.zprofile are sourced and ~/.zshrc is not.
 *                   ~/.zshrc.local is sourced by ~/.zshrc, so it never runs.
 *
 *   ~/.zshenv       Would work, and is the tempting one-liner. But it exports the
 *                   key into *every* process on the machine rather than just pi,
 *                   and this repo does not manage ~/.zshenv — the nix-generated
 *                   shell file is ~/.zshrc.local, which is the one that does not
 *                   get sourced. Broader exposure, less declarative.
 *
 * Injecting the key into the launchd plists directly is not an option either: they
 * are regenerated from PI WEB's own plan on every `pi-web install`, which is also
 * the documented upgrade path, so anything hand-added there is wiped.
 *
 * Reading a file from inside pi is scoped to pi, survives PI WEB upgrades, and is
 * one code path for both the terminal and the browser.
 *
 * The file is generated from secrets.json.tpl by `just secrets` (1Password) and is
 * gitignored. A missing file is not an error — pi should still start on a host that
 * has never run `just secrets`, and the extensions that want a key already report
 * their own "no key found" message.
 *
 * A real environment variable always wins, so `BRAVE_API_KEY=... pi` still overrides
 * the file for a one-off.
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

	// Throw rather than write to stdio. pi's extension loader catches whatever a
	// factory throws and surfaces it in its own UI, whereas a bare console.error
	// lands mid-frame when `/reload` re-runs the factories while the TUI owns the
	// terminal. No other extension here writes to stdio either.
	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch (error) {
		throw new Error(`pi-secrets: ${SECRETS_PATH} is not valid JSON: ${error}`);
	}

	if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
		throw new Error(`pi-secrets: ${SECRETS_PATH} must be a JSON object of NAME -> value.`);
	}

	for (const [name, value] of Object.entries(parsed as Record<string, unknown>)) {
		if (typeof value !== "string" || value === "") continue;
		if (process.env[name] !== undefined) continue; // a real export wins
		process.env[name] = value;
	}
}
