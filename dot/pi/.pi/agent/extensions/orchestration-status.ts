/**
 * Publish a worker's liveness and cost, so an orchestrator never has to guess.
 *
 * The failure this removes: a pi worker spawned into the background writes a
 * JSONL log, and a worker that died on startup writes a **0-byte** one. A
 * worker thinking hard for four minutes also writes nothing new. From outside
 * the two are identical, and in the 2026-08-27 run two dead workers were
 * reported as "still running" twice before anyone thought to check `ps`.
 * Unattended overnight that is an empty slot for hours.
 *
 * So the worker says so itself. One small JSON file, rewritten on every turn
 * and every tool call, holding the things an orchestrator actually asks: is it
 * alive, what is it doing, how far in, what has it spent. Polling one directory
 * of these answers "dead or thinking" in one read — and a *missing* file
 * answers "it never started at all", which is the case that fooled us.
 *
 * It also retires log-scraping for telemetry. Usage totals came out of 13MB
 * JSONL files three times that day; they are published here per turn instead.
 *
 * Off unless asked for: writes only when PI_STATUS_FILE names a path. A global
 * extension loads in every interactive session too, and those have a human
 * looking at them who does not need a heartbeat file.
 *
 * Writes are atomic (temp + rename) because the orchestrator polls this while
 * it is being written, and a half-written JSON read as "malformed" would look
 * exactly like the corruption it is meant to rule out.
 */

import { renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export interface StatusUsage {
	input: number;
	output: number;
	reasoning: number;
	cacheRead: number;
	totalTokens: number;
	costUsd: number;
}

export interface Status {
	/** "starting" | "thinking" | "tool" | "settled" | "shutdown" */
	phase: string;
	pid: number;
	cwd: string;
	provider?: string;
	model?: string;
	startedAt: string;
	/** The field that answers "is it stuck": compare against now. */
	lastActivityAt: string;
	turn: number;
	toolCalls: number;
	/** What it is doing right now, when phase is "tool". */
	currentTool?: string;
	/** Set when a tool was refused - a blocked worker looks like a slow one. */
	lastBlocked?: string;
	usage: StatusUsage;
}

const EMPTY_USAGE: StatusUsage = {
	input: 0,
	output: 0,
	reasoning: 0,
	cacheRead: 0,
	totalTokens: 0,
	costUsd: 0,
};

/**
 * Sum one turn's usage into the running total.
 *
 * Deliberately additive over `message_end` events rather than reading a running
 * total off the last one: pi reports usage per assistant message, so the last
 * message knows about itself and nothing before it.
 */
export function accumulate(total: StatusUsage, usage: unknown): StatusUsage {
	const u = (usage ?? {}) as Record<string, unknown>;
	const num = (key: string): number => {
		const value = u[key];
		return typeof value === "number" && Number.isFinite(value) ? value : 0;
	};
	const cost = (u.cost ?? {}) as Record<string, unknown>;
	const costTotal = typeof cost.total === "number" && Number.isFinite(cost.total) ? cost.total : 0;
	return {
		input: total.input + num("input"),
		output: total.output + num("output"),
		reasoning: total.reasoning + num("reasoning"),
		cacheRead: total.cacheRead + num("cacheRead"),
		totalTokens: total.totalTokens + num("totalTokens"),
		costUsd: total.costUsd + costTotal,
	};
}

/** Seconds since the status was last touched. The orchestrator's staleness test. */
export function secondsSince(lastActivityAt: string, now: Date = new Date()): number {
	const then = Date.parse(lastActivityAt);
	if (Number.isNaN(then)) return Number.POSITIVE_INFINITY;
	return (now.getTime() - then) / 1000;
}

export function writeStatusAtomic(path: string, status: Status): void {
	// Same directory, so the rename cannot cross a filesystem boundary and fall
	// back to a non-atomic copy.
	const temp = join(dirname(path), `.status.${process.pid}.tmp`);
	writeFileSync(temp, `${JSON.stringify(status, null, 2)}\n`, "utf8");
	renameSync(temp, path);
}

export default function orchestrationStatus(pi: ExtensionAPI): void {
	const path = process.env.PI_STATUS_FILE;
	if (!path) return;

	const status: Status = {
		phase: "starting",
		pid: process.pid,
		cwd: process.cwd(),
		startedAt: new Date().toISOString(),
		lastActivityAt: new Date().toISOString(),
		turn: 0,
		toolCalls: 0,
		usage: { ...EMPTY_USAGE },
	};

	// Never let a status write take the worker down with it. A full disk or a
	// removed worktree must cost visibility, not the run.
	const publish = (phase: string): void => {
		status.phase = phase;
		status.lastActivityAt = new Date().toISOString();
		try {
			writeStatusAtomic(path, status);
		} catch {
			/* visibility is best-effort */
		}
	};

	publish("starting");

	pi.on("turn_start", async () => {
		status.turn += 1;
		publish("thinking");
	});

	pi.on("turn_end", async () => {
		publish("thinking");
	});

	pi.on("message_end", async (event: unknown) => {
		const message = (event as { message?: { usage?: unknown; provider?: string; model?: string } })
			?.message;
		if (!message) return;
		status.usage = accumulate(status.usage, message.usage);
		if (message.provider) status.provider = message.provider;
		if (message.model) status.model = message.model;
		publish(status.phase === "starting" ? "thinking" : status.phase);
	});

	pi.on("tool_execution_start", async (event: unknown) => {
		status.toolCalls += 1;
		status.currentTool = (event as { toolName?: string })?.toolName;
		publish("tool");
	});

	// A refused tool call is the other thing that looks like slowness from
	// outside, and the guardrails extension makes refusals a normal event. This
	// reads `isError` rather than the block verdict itself, because one
	// extension cannot see another's return value.
	pi.on("tool_execution_end", async (event: unknown) => {
		const finished = event as { toolName?: string; isError?: boolean };
		if (finished?.isError && finished.toolName) {
			status.lastBlocked = `${finished.toolName} @ turn ${status.turn}`;
		}
		status.currentTool = undefined;
		publish("thinking");
	});

	pi.on("agent_settled", async () => {
		publish("settled");
	});

	pi.on("session_shutdown", async () => {
		publish("shutdown");
	});
}
