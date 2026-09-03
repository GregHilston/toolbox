/**
 * What matters here: a fresh session never carries a lazy group unless asked
 * for it by name, an enable never drops a tool that was already active (pi's
 * dynamic-tool rule: additive changes keep the prompt prefix), an enable
 * survives another extension re-adding its tools before the next turn, and a
 * typo in a group name is refused rather than silently enabling nothing.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import lazyTools, {
	GROUPS,
	activeGroups,
	enable,
	parseGroups,
	strip,
	unknownGroups,
} from "../.pi/agent/extensions/lazy-tools.ts";

const BUILTINS = ["read", "bash", "edit", "write", "grep", "find", "ls"];
const FULL = [...BUILTINS, "web_search", ...GROUPS.reddit, "fff"];
const LEAN = [...BUILTINS, "web_search", "fff"];

test("strip removes every lazy group and nothing else", () => {
	assert.deepEqual(strip(FULL, []), LEAN);
});

test("strip keeps a group named in PI_ENABLE_TOOLS", () => {
	assert.deepEqual(strip(FULL, ["reddit"]), FULL);
	assert.deepEqual(strip(FULL, parseGroups("all")), FULL);
});

test("parseGroups accepts commas or spaces, ignores case and unknowns", () => {
	assert.deepEqual(parseGroups("Reddit, bogus"), ["reddit"]);
	assert.deepEqual(parseGroups(undefined), []);
	assert.deepEqual(unknownGroups("reddit bogus all"), ["bogus"]);
});

test("enable is additive and idempotent", () => {
	const once = enable(LEAN, ["reddit"]);
	assert.deepEqual(once.slice(0, LEAN.length), LEAN, "nothing already active moves or disappears");
	assert.deepEqual(once.slice(LEAN.length), GROUPS.reddit);
	assert.deepEqual(enable(once, ["reddit"]), once);
});

/** Records what the extension asked pi to do, instead of a real pi. */
function fakePi(active: string[]) {
	const handlers: Record<string, () => Promise<void>> = {};
	const commands: Record<string, { handler: (args: string, ctx: unknown) => Promise<void> }> = {};
	return {
		handlers,
		commands,
		on(event: string, h: () => Promise<void>) {
			handlers[event] = h;
		},
		registerCommand(name: string, cmd: { handler: (args: string, ctx: unknown) => Promise<void> }) {
			commands[name] = cmd;
		},
		getActiveTools: () => active,
		setActiveTools(names: string[]) {
			active = names;
		},
		get current() {
			return active;
		},
	};
}

const fakeCtx = () => {
	const notes: string[] = [];
	return { notes, ui: { notify: (m: string) => notes.push(m) } };
};

test("session_start strips lazy groups; PI_ENABLE_TOOLS keeps one", async () => {
	delete process.env.PI_ENABLE_TOOLS;
	const pi = fakePi([...FULL]);
	lazyTools(pi as never);
	await pi.handlers.session_start();
	assert.deepEqual(pi.current, LEAN);

	process.env.PI_ENABLE_TOOLS = "reddit";
	const worker = fakePi([...FULL]);
	lazyTools(worker as never);
	delete process.env.PI_ENABLE_TOOLS;
	await worker.handlers.session_start();
	assert.deepEqual(activeGroups(worker.current), ["reddit"]);
});

test("another extension re-adding a group's tools before a turn is stripped again", async () => {
	delete process.env.PI_ENABLE_TOOLS;
	const pi = fakePi([...FULL]);
	lazyTools(pi as never);
	await pi.handlers.session_start();
	pi.setActiveTools(enable(pi.current, ["reddit"]));
	await pi.handlers.before_agent_start();
	assert.deepEqual(pi.current, LEAN);
});

test("/enable adds a group and it survives the next turn; a typo is refused; /disable removes it", async () => {
	delete process.env.PI_ENABLE_TOOLS;
	const pi = fakePi([...LEAN]);
	lazyTools(pi as never);
	const ctx = fakeCtx();

	await pi.commands.enable.handler("redit", ctx);
	assert.deepEqual(pi.current, LEAN, "a typo must not enable anything");
	assert.match(ctx.notes.at(-1)!, /Unknown group: redit/);

	await pi.commands.enable.handler("reddit", ctx);
	assert.deepEqual(activeGroups(pi.current), ["reddit"]);
	await pi.handlers.before_agent_start();
	assert.deepEqual(activeGroups(pi.current), ["reddit"], "an enable is for the session, not one turn");

	await pi.commands.disable.handler("all", ctx);
	assert.deepEqual(pi.current, LEAN);
});
