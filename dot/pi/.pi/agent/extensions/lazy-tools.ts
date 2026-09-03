/**
 * Heavy tool groups start off and are enabled by hand (`/enable`), never by
 * the model: a local model misses tools it cannot see, and a mid-session
 * enable re-prefills the whole conversation on oMLX. The strip repeats before
 * every turn so an extension that restores its tools between turns loses.
 *
 * subagent_* is not a group: pi-agent-suite re-applies its baseline after
 * this handler, so pi.nix does not load it. dot/pi/CLAUDE.md -> "Lazy tools".
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
const USAGE = `usage: /enable <${ALL.join("|")}|all>`;

/** "reddit, all" → known groups in GROUPS order, plus whatever was not one. */
export function parse(spec: string | undefined): { groups: string[]; unknown: string[] } {
	const words = (spec ?? "")
		.split(/[\s,]+/)
		.map((w) => w.toLowerCase())
		.filter(Boolean);
	const unknown = words.filter((w) => w !== "all" && !(w in GROUPS));
	const groups = words.includes("all") ? [...ALL] : ALL.filter((g) => words.includes(g));
	return { groups, unknown };
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
	const wanted = new Set(parse(process.env.PI_ENABLE_TOOLS).groups);

	const apply = () => {
		const active = pi.getActiveTools();
		const lean = strip(active, [...wanted]);
		if (lean.length < active.length) pi.setActiveTools(lean);
	};

	pi.on("session_start", async () => apply());
	pi.on("before_agent_start", async () => apply());

	const status = () => {
		const on = activeGroups(pi.getActiveTools());
		return `lazy tools on: ${on.length ? on.join(", ") : "none"}`;
	};

	pi.registerCommand("enable", {
		description: `Enable a lazy tool group for this session: ${ALL.join(", ")}, all`,
		handler: async (args, ctx) => {
			const { groups, unknown } = parse(args);
			if (unknown.length || !groups.length) {
				const why = unknown.length ? `Unknown group: ${unknown.join(", ")}. ` : "";
				ctx.ui.notify(`${why}${USAGE}. ${status()}`, "warning");
				return;
			}
			for (const g of groups) wanted.add(g);
			pi.setActiveTools(enable(pi.getActiveTools(), groups));
			ctx.ui.notify(`Enabled ${groups.join(", ")}. ${status()}`, "success");
		},
	});

	pi.registerCommand("disable", {
		description: `Disable a lazy tool group for this session: ${ALL.join(", ")}, all`,
		handler: async (args, ctx) => {
			const { groups } = parse(args);
			if (!groups.length) {
				ctx.ui.notify(`${USAGE.replace("/enable", "/disable")}. ${status()}`, "warning");
				return;
			}
			for (const g of groups) wanted.delete(g);
			apply();
			ctx.ui.notify(`Disabled ${groups.join(", ")}. ${status()}`, "info");
		},
	});
}
