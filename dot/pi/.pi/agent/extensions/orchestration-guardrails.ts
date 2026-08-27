/**
 * Enforce an unattended worker's prohibitions, instead of asking it nicely.
 *
 * `/orchestrate-pi` spawns pi workers that must never push (a pre-push hook
 * deploys the API, so a push is a deploy), never merge, never write to GitHub,
 * never `--no-verify` past the suites, and never edit pi's own configuration.
 * Until this existed those were English sentences in a 141-line prompt — which
 * is a request, not a boundary, and nobody is awake at 3am to notice one being
 * ignored. `tool_call` can block, so they are boundaries now.
 *
 * Off unless asked for. A global extension runs in every interactive session
 * too, and blocking `git push` at a keyboard would be maddening. It arms when
 * `<cwd>/.pi/guardrails.json` exists — the orchestrator already scaffolds a
 * `.pi/` per worktree — or when PI_GUARDRAILS=1 is set.
 *
 * The hard part is not the blocking, it is not blocking the wrong thing. A
 * worker that edits documentation *about* pushing writes the words "git push"
 * into a file, and a naive substring match blocks that and teaches the worker
 * that the tool is broken. So the command is split into segments the shell
 * would actually execute, with heredoc bodies removed first. That is what the
 * tests are mostly about.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export interface Rule {
	/** Case-insensitive regex, tested against one command segment. */
	pattern: string;
	/** Shown to the model verbatim. Say what to do instead, not just "no". */
	reason: string;
	/** Stop the run rather than letting it improvise around the refusal. */
	terminate?: boolean;
}

export interface Guardrails {
	bash?: Rule[];
	/** Path globs the write/edit tools may not touch, as regexes. */
	paths?: Rule[];
}

/**
 * The defaults exist so a worktree can arm the guardrails with `{}` and still
 * get the rules that matter. Every one of these is a prohibition that was
 * previously only prose in the worker prompt.
 */
export const DEFAULT_RULES: Required<Guardrails> = {
	bash: [
		{
			pattern: String.raw`^git\s+push\b`,
			reason:
				"Never push. A pre-push hook deploys the API, so a push is a deploy. " +
				"Stop after your last commit; the orchestrator pushes.",
			terminate: true,
		},
		{
			pattern: String.raw`^git\s+(checkout|switch)\s+(main|master)\b`,
			reason:
				"Never leave your branch. You are in a worktree; main is checked out " +
				"elsewhere and this cannot succeed. The orchestrator merges.",
		},
		{
			pattern: String.raw`^git\s+(merge|rebase)\b`,
			reason: "Never merge or rebase. The orchestrator does that after reviewing your diff.",
		},
		{
			pattern: String.raw`^git\s+commit\b.*(--no-verify|(^|\s)-n(\s|$))`,
			reason:
				"Never bypass the hooks. They run the suites and are slow, not hung — " +
				"budget 60-90s per commit and let them finish.",
		},
		{
			pattern: String.raw`^gh\s+\w+\s+(create|edit|close|reopen|comment|merge|delete|review)\b`,
			reason:
				"Never write to GitHub. The orchestrator owns every gh mutation, including " +
				"the issue trailer. Read-only `gh issue view` is fine.",
		},
		{
			pattern: String.raw`^gh\s+api\b.*-X\s*(POST|PATCH|PUT|DELETE)`,
			reason: "Never write to GitHub. `gh api` with a write method is a mutation.",
		},
		{
			pattern: String.raw`^pi\s+(install|remove|uninstall|update)\b`,
			reason:
				"Never change pi's own configuration. It would alter the next worker's behaviour.",
		},
		{
			pattern: String.raw`(^|\s)/login\b`,
			reason:
				"Never /login. This worker's provider is deepseek, billed to its own key, " +
				"and that is deliberate.",
		},
	],
	paths: [
		{
			pattern: String.raw`(^|/)\.pi/`,
			reason: "`.pi/` is orchestrator scaffolding, not part of your change.",
		},
		{
			pattern: String.raw`^([~]|/Users/[^/]+)/\.pi/`,
			reason: "Never edit pi's own configuration; it would change the next worker's behaviour.",
		},
	],
};

/**
 * Remove heredoc bodies, so their contents are never mistaken for commands.
 *
 * This is the whole false-positive story: a worker documenting the push rule
 * writes `cat > docs.md <<'EOF'` ... `git push` ... `EOF`, and without this the
 * guardrail blocks a documentation edit and looks broken.
 */
export function stripHeredocs(command: string): string {
	const lines = command.split("\n");
	const out: string[] = [];
	let terminator: string | null = null;

	for (const line of lines) {
		if (terminator !== null) {
			// A heredoc terminator may be indented when <<- was used.
			if (line.trim() === terminator) terminator = null;
			continue;
		}
		// <<EOF, <<-EOF, <<'EOF', <<"EOF"
		const open = line.match(/<<-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1/);
		if (open) {
			terminator = open[2];
			out.push(line.slice(0, open.index));
			continue;
		}
		out.push(line);
	}
	return out.join("\n");
}

/**
 * Split into the segments a shell would run as separate commands, and strip the
 * leading noise that hides the real one: `cd x && git push` must be seen as
 * `git push`, and `sudo -E git push` likewise.
 */
export function commandSegments(command: string): string[] {
	const withoutHeredocs = stripHeredocs(command);
	return withoutHeredocs
		.split(/\|\||&&|[;\n|]/)
		.map((segment) => segment.trim())
		.filter(Boolean)
		.map(stripLeadingWrappers);
}

const WRAPPERS = /^(sudo|command|env|nohup|time|xargs|nice)\b(\s+-\S+)*\s+/;

function stripLeadingWrappers(segment: string): string {
	let out = segment.replace(/^\(\s*/, "");
	// Leading VAR=value assignments precede the command they apply to.
	out = out.replace(/^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+/, "");
	let previous: string;
	do {
		previous = out;
		out = out.replace(WRAPPERS, "");
	} while (out !== previous);
	return out;
}

export interface Verdict {
	block: true;
	reason: string;
	terminate?: boolean;
}

/** Decide whether a bash command may run. Pure, so the tests can reach it. */
export function checkBash(command: string, rules: Rule[]): Verdict | null {
	for (const segment of commandSegments(command)) {
		for (const rule of rules) {
			if (new RegExp(rule.pattern, "i").test(segment)) {
				return { block: true, reason: rule.reason, terminate: rule.terminate };
			}
		}
	}
	return null;
}

/** Decide whether a write/edit may touch a path. Pure, so the tests can reach it. */
export function checkPath(path: string, rules: Rule[]): Verdict | null {
	for (const rule of rules) {
		if (new RegExp(rule.pattern, "i").test(path)) {
			return { block: true, reason: rule.reason, terminate: rule.terminate };
		}
	}
	return null;
}

/**
 * Merged rather than replaced: a worktree that wants one extra rule should not
 * have to restate the eight that ship here, because the one it forgets is the
 * one that matters at 3am.
 */
export function loadRules(cwd: string, env: NodeJS.ProcessEnv): Required<Guardrails> | null {
	const configPath = join(cwd, ".pi", "guardrails.json");
	const armed = existsSync(configPath) || env.PI_GUARDRAILS === "1";
	if (!armed) return null;

	let configured: Guardrails = {};
	if (existsSync(configPath)) {
		try {
			configured = JSON.parse(readFileSync(configPath, "utf8")) as Guardrails;
		} catch (error) {
			// A malformed config must not silently disarm the guardrails - that is
			// the failure mode this whole extension exists to remove.
			console.error(`[guardrails] ${configPath} is not valid JSON; using defaults only.`, error);
			configured = {};
		}
	}
	return {
		bash: [...DEFAULT_RULES.bash, ...(configured.bash ?? [])],
		paths: [...DEFAULT_RULES.paths, ...(configured.paths ?? [])],
	};
}

export default function orchestrationGuardrails(pi: ExtensionAPI): void {
	const rules = loadRules(process.cwd(), process.env);
	if (!rules) return;

	pi.on("tool_call", async (event) => {
		if (event.toolName === "bash") {
			const command = (event.input as { command?: string })?.command;
			if (typeof command === "string") {
				const verdict = checkBash(command, rules.bash);
				if (verdict) return verdict;
			}
			return;
		}
		if (event.toolName === "write" || event.toolName === "edit") {
			const path = (event.input as { path?: string })?.path;
			if (typeof path === "string") {
				const verdict = checkPath(path, rules.paths);
				if (verdict) return verdict;
			}
		}
	});
}
