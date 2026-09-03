/**
 * Start every session without the heavy tool groups, and turn them on by hand.
 *
 * Measured 2026-09-03 on moria: the seven reddit_* tools cost 1,602 tokens on
 * every request, paid by every session for a task you know you are starting.
 * On oMLX that is window capacity rather than money, and the window is what
 * prefill scales with.
 *
 * Enabling is manual (`/enable`) rather than a model-facing gateway tool, and
 * that is deliberate. A local model is not reliable at noticing it needs a tool
 * it cannot see, and every mid-session enable changes the tools array at the
 * front of the prompt, which invalidates oMLX's prefix cache and re-prefills
 * the whole conversation once. So: enable at the start of a session, or set
 * PI_ENABLE_TOOLS=reddit (or `all`) for a worker that needs a group from its
 * first turn. Enables are additive, per pi's dynamic-tool guidance.
 *
 * The strip runs before every turn as well as at session start, so another
 * extension that restores its tools between turns loses. That is not enough
 * against pi-agent-suite's run-subagent, whose runtime composition re-applies
 * its baseline *after* this handler on every turn — which is why subagent_*
 * is not a group here and that extension is simply not loaded by default
 * (pi.nix). Only pi's own --exclude-tools beats the composition.
 *
 * Only this session is affected. A fresh session starts stripped again, which
 * is the whole point.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export const GROUPS: Record<string, readonly string[]> = {
	reddit: [
		"reddit_pack",
		"reddit_resolve_subreddits",
		"reddit_search",
		"reddit_subreddits",
		"reddit_thread",
		"reddit_trends",
		"reddit_url_extract",
	],
};

const ALL = Object.keys(GROUPS);

/** "reddit" / "all" / "" → known group names, unknown ones dropped. */
export function parseGroups(spec: string | undefined): string[] {
	const words = (spec ?? "")
		.split(/[\s,]+/)
		.map((w) => w.trim().toLowerCase())
		.filter(Boolean);
	if (words.includes("all")) return [...ALL];
	return ALL.filter((g) => words.includes(g));
}

/** Names in `spec` that are not a group, for an error message. */
export function unknownGroups(spec: string): string[] {
	return spec
		.split(/[\s,]+/)
		.map((w) => w.trim().toLowerCase())
		.filter((w) => w && w !== "all" && !(w in GROUPS));
}

function toolsOf(groups: readonly string[]): Set<string> {
	return new Set(groups.flatMap((g) => GROUPS[g] ?? []));
}

/** Active tools minus every lazy group not in `keep`. Order preserved. */
export function strip(active: readonly string[], keep: readonly string[]): string[] {
	const drop = toolsOf(ALL.filter((g) => !keep.includes(g)));
	return active.filter((t) => !drop.has(t));
}

/** Additive: current tools plus the groups' tools, no duplicates. */
export function enable(active: readonly string[], groups: readonly string[]): string[] {
	return [...new Set([...active, ...toolsOf(groups)])];
}

/** Which groups are fully active right now. */
export function activeGroups(active: readonly string[]): string[] {
	return ALL.filter((g) => GROUPS[g].every((t) => active.includes(t)));
}

export default function lazyTools(pi: ExtensionAPI) {
	const wanted = new Set(parseGroups(process.env.PI_ENABLE_TOOLS));

	const apply = () => {
		const active = pi.getActiveTools();
		const lean = strip(active, [...wanted]);
		if (lean.length < active.length) pi.setActiveTools(lean);
	};

	pi.on("session_start", async () => apply());
	pi.on("before_agent_start", async () => apply());

	const status = () => {
		const on = activeGroups(pi.getActiveTools());
		return `lazy tools on: ${on.length ? on.join(", ") : "none"} (groups: ${ALL.join(", ")}, all)`;
	};

	pi.registerCommand("enable", {
		description: "Enable a lazy tool group for this session: reddit, all",
		handler: async (args, ctx) => {
			const bad = unknownGroups(args ?? "");
			const groups = parseGroups(args);
			if (bad.length || !groups.length) {
				ctx.ui.notify(`Unknown group${bad.length ? `: ${bad.join(", ")}` : ""}. ${status()}`, "warning");
				return;
			}
			for (const g of groups) wanted.add(g);
			pi.setActiveTools(enable(pi.getActiveTools(), groups));
			ctx.ui.notify(`Enabled ${groups.join(", ")}. ${status()}`, "success");
		},
	});

	pi.registerCommand("disable", {
		description: "Disable a lazy tool group for this session: reddit, all",
		handler: async (args, ctx) => {
			const groups = parseGroups(args);
			if (!groups.length) {
				ctx.ui.notify(`Nothing matched. ${status()}`, "warning");
				return;
			}
			for (const g of groups) wanted.delete(g);
			apply();
			ctx.ui.notify(`Disabled ${groups.join(", ")}. ${status()}`, "info");
		},
	});
}
