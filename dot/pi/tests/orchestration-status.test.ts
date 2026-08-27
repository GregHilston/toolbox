/**
 * What matters here is that the status file can always be trusted by a reader
 * that polls it mid-write, and that the numbers are a running total rather than
 * whatever the last message happened to say.
 */

import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import {
	type Status,
	type StatusUsage,
	accumulate,
	writeStatusAtomic,
} from "../.pi/agent/extensions/orchestration-status.ts";

const ZERO: StatusUsage = {
	input: 0,
	output: 0,
	reasoning: 0,
	cacheRead: 0,
	cacheWrite: 0,
	totalTokens: 0,
	costUsd: 0,
};

test("accumulates across turns rather than replacing", () => {
	const first = accumulate(ZERO, {
		input: 100,
		output: 10,
		reasoning: 4,
		cacheRead: 900,
		totalTokens: 1010,
		cost: { total: 0.5 },
	});
	const second = accumulate(first, {
		input: 50,
		output: 5,
		reasoning: 1,
		cacheRead: 500,
		totalTokens: 555,
		cost: { total: 0.25 },
	});
	assert.equal(second.input, 150, "a running total, not the latest message");
	assert.equal(second.cacheRead, 1400, "cache reads dominate cost here, so they must be summed");
	assert.equal(second.totalTokens, 1565);
	assert.equal(second.cacheWrite, 0, "absent cacheWrite must sum to zero, not NaN");
	assert.equal(second.costUsd, 0.75, "cost comes from pi's own per-turn object");
});

test("sums cacheWrite, which was silently dropped before review", () => {
	const out = accumulate(ZERO, { cacheWrite: 128, cost: { total: 0 } });
	assert.equal(out.cacheWrite, 128, "a real field on Usage; leaving it out understated the run");
});

test("survives a message with no usage at all", () => {
	assert.deepEqual(accumulate(ZERO, undefined), ZERO, "a usage-less message must not corrupt");
	assert.deepEqual(accumulate(ZERO, {}), ZERO);
});

test("ignores non-finite and non-numeric fields instead of producing NaN", () => {
	const out = accumulate(ZERO, {
		input: "lots",
		output: Number.NaN,
		totalTokens: Number.POSITIVE_INFINITY,
		cost: { total: null },
	});
	assert.deepEqual(out, ZERO, "a NaN here would poison every later sum");
});

test("writes valid JSON and leaves no temp file behind", () => {
	const dir = mkdtempSync(join(tmpdir(), "pi-status-"));
	try {
		const path = join(dir, "status.json");
		const status: Status = {
			phase: "tool",
			pid: 4242,
			cwd: "/repo/worktrees/issue-64",
			startedAt: "2026-08-27T12:00:00Z",
			lastActivityAt: "2026-08-27T12:00:10Z",
			turn: 7,
			toolCalls: 3,
			currentTool: "bash",
			usage: { ...ZERO },
		};
		writeStatusAtomic(path, status);

		const parsed = JSON.parse(readFileSync(path, "utf8")) as Status;
		assert.equal(parsed.pid, 4242, "the pid is how the orchestrator confirms liveness");
		assert.equal(parsed.currentTool, "bash", "and currentTool is what it is doing right now");

		const leftovers = readdirSync(dir).filter((name) => name.includes("tmp"));
		assert.deepEqual(leftovers, [], "the temp file must be renamed away, not accumulated");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("overwrites in place, so a poller always sees one whole document", () => {
	const dir = mkdtempSync(join(tmpdir(), "pi-status-"));
	try {
		const path = join(dir, "status.json");
		const base: Status = {
			phase: "thinking",
			pid: 1,
			cwd: "/x",
			startedAt: "2026-08-27T12:00:00Z",
			lastActivityAt: "2026-08-27T12:00:00Z",
			turn: 1,
			toolCalls: 0,
			usage: { ...ZERO },
		};
		writeStatusAtomic(path, base);
		writeStatusAtomic(path, { ...base, turn: 2, phase: "settled" });

		const parsed = JSON.parse(readFileSync(path, "utf8")) as Status;
		assert.equal(parsed.turn, 2, "the second write wins");
		assert.equal(parsed.phase, "settled");
		assert.equal(readdirSync(dir).length, 1, "and does not leave a second file");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});
