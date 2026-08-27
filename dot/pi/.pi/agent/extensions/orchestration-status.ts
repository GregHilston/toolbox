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
 * Liveness was the first question. The second one, asked every time, is *what*
 * it is doing — and "phase: tool, currentTool: bash" does not answer it. So the
 * file also carries `lastText` (the last thing the worker said), the current
 * tool's interesting argument, and a short ring buffer of recent activity.
 * `bin/pi-workers.py` renders all of it; the point is that one small read
 * answers the question without opening the log at all.
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
	cacheWrite: number;
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
	/** The interesting argument of `currentTool` - the command, the path. */
	lastToolBrief?: string;
	/** The last thing the worker said out loud, flattened to one line. */
	lastText?: string;
	/** Set when a tool was refused - a blocked worker looks like a slow one. */
	lastBlocked?: string;
	/** How many refusals so far; one is a boundary, ten is a worker fighting it. */
	blockedCount: number;
	/** The last few things it did, newest last. Enough to diagnose a stall. */
	recent: string[];
	usage: StatusUsage;
}

/** Keep the file small: it is rewritten on every event and polled constantly. */
export const RECENT_LIMIT = 8;
const TEXT_LIMIT = 200;

/**
 * Tool arguments worth publishing, in preference order. A `currentTool` of
 * "bash" says nothing; "bash godot --headless ..." says everything.
 */
const ARG_KEYS = ["command", "path", "file_path", "pattern", "query", "url"] as const;

/** Collapse model prose to a single line a table can hold. */
export function flatten(value: unknown, limit = TEXT_LIMIT): string {
	if (typeof value !== "string") return "";
	const collapsed = value.split(/\s+/).filter(Boolean).join(" ");
	return collapsed.length > limit ? `${collapsed.slice(0, limit - 1)}…` : collapsed;
}

/** The one argument worth showing for a tool call. */
export function briefArgs(args: unknown): string {
	if (!args || typeof args !== "object") return "";
	const record = args as Record<string, unknown>;
	for (const key of ARG_KEYS) {
		const value = record[key];
		if (typeof value === "string" && value.trim()) return flatten(value, 120);
	}
	try {
		return flatten(JSON.stringify(record), 120);
	} catch {
		return "";
	}
}

/** The text an assistant message said, ignoring thinking and tool calls. */
export function assistantText(content: unknown): string {
	if (typeof content === "string") return flatten(content);
	if (!Array.isArray(content)) return "";
	const parts = content
		.filter(
			(block): block is { type: string; text: string } =>
				!!block &&
				typeof block === "object" &&
				(block as { type?: unknown }).type === "text" &&
				typeof (block as { text?: unknown }).text === "string",
		)
		.map((block) => block.text);
	return flatten(parts.join(" "));
}

/** Append to the ring buffer in place, oldest out. */
export function pushRecent(recent: string[], line: string, limit = RECENT_LIMIT): string[] {
	if (!line) return recent;
	recent.push(line);
	while (recent.length > limit) recent.shift();
	return recent;
}

const EMPTY_USAGE: StatusUsage = {
	input: 0,
	output: 0,
	reasoning: 0,
	cacheRead: 0,
	cacheWrite: 0,
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
		cacheWrite: total.cacheWrite + num("cacheWrite"),
		totalTokens: total.totalTokens + num("totalTokens"),
		costUsd: total.costUsd + costTotal,
	};
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
		blockedCount: 0,
		recent: [],
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
		const message = (
			event as {
				message?: { role?: string; usage?: unknown; provider?: string; model?: string };
			}
		)?.message;
		if (!message) return;
		// Assistant messages only. `message_end` also fires for toolResult messages,
		// whose `usage` is the tool's own nested-model spend and is explicitly not
		// part of main-context accounting - counting it would inflate the very
		// number this extension exists to publish.
		if (message.role !== "assistant") return;
		status.usage = accumulate(status.usage, message.usage);
		if (message.provider) status.provider = message.provider;
		if (message.model) status.model = message.model;
		// The worker's own narration of what it is doing, which is the single
		// most useful line in the file and costs nothing to keep.
		const said = assistantText((message as { content?: unknown }).content);
		if (said) {
			status.lastText = said;
			pushRecent(status.recent, `» ${said}`);
		}
		publish(status.phase === "starting" ? "thinking" : status.phase);
	});

	pi.on("tool_execution_start", async (event: unknown) => {
		const started = event as { toolName?: string; args?: unknown };
		status.toolCalls += 1;
		status.currentTool = started?.toolName;
		status.lastToolBrief = briefArgs(started?.args);
		pushRecent(status.recent, `▸ ${started?.toolName ?? "?"} ${status.lastToolBrief}`.trim());
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
			status.blockedCount += 1;
			pushRecent(status.recent, `✗ ${finished.toolName} failed`);
		}
		status.currentTool = undefined;
		status.lastToolBrief = undefined;
		publish("thinking");
	});

	pi.on("agent_settled", async () => {
		publish("settled");
	});

	pi.on("session_shutdown", async () => {
		publish("shutdown");
	});
}
