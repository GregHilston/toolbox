/**
 * AGENTS.md is a hand-kept port of CLAUDE.md. A new CLAUDE.md heading must
 * be mapped to its AGENTS.md heading or listed as Claude-only here.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");
const headings = (md: string) => [...md.matchAll(/^## (.+)$/gm)].map((m) => m[1].trim());

const claude = headings(read("../../claude/.claude/CLAUDE.md"));
const agents = headings(read("../.pi/agent/AGENTS.md"));

const PORTED: Record<string, string> = {
	"No AI attribution, anywhere": "No AI attribution, anywhere",
	"Writing Code": "Writing code",
	Prose: "Prose",
	"Working with me": "Working with me",
	"Bash working directory — use absolute paths": "Shell gotchas",
	"Researching Reddit": "Research",
	"Agent skills": "Agent skills",
};

const CLAUDE_ONLY = [
	"Pixel 8 (Termux)",
	"Documentation Philosophy",
	"Ending a chat",
	"Picking a model for delegated work",
	"File Inspection",
	"Toolbox",
	"LLM writing for the notes vault",
];

test("every CLAUDE.md heading is ported or marked Claude-only", () => {
	const unknown = claude.filter((h) => !(h in PORTED) && !CLAUDE_ONLY.includes(h));
	assert.deepEqual(unknown, [], "add to PORTED (and AGENTS.md) or CLAUDE_ONLY");
});

test("every ported heading exists in AGENTS.md", () => {
	const missing = Object.values(PORTED).filter((h) => !agents.includes(h));
	assert.deepEqual(missing, []);
});

test("mapped lists name no stale CLAUDE.md headings", () => {
	const stale = [...Object.keys(PORTED), ...CLAUDE_ONLY].filter((h) => !claude.includes(h));
	assert.deepEqual(stale, []);
});
