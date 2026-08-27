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
 * Flags git accepts *before* its verb. Without these, `git -C /repo push` and
 * `git --git-dir=x --work-tree=y push` sail past a rule anchored on `^git\s+push`,
 * which is the commonest real bypass rather than an exotic one.
 */
const GIT_FLAGS =
	"(?:(?:-[cC]\\s+\\S+|--(?:git-dir|work-tree|exec-path)(?:=\\S+|\\s+\\S+)|--no-pager|-p)\\s+)*";

/**
 * The defaults exist so a worktree can arm the guardrails with `{}` and still
 * get the rules that matter. Every one of these is a prohibition that was
 * previously only prose in the worker prompt.
 *
 * **Threat model: a careless worker, not an adversarial one.** These stop an
 * agent that reaches for a forbidden command in the ordinary course of its work.
 * They are not a security boundary and do not pretend to be: `bash -c "git push"`,
 * `eval`, backticks and `$(...)` all defeat them trivially, and closing that would
 * mean parsing the shell rather than reading it. Real confinement is the sandbox
 * extension's job (see docs), not this file's.
 */
export const DEFAULT_RULES: Required<Guardrails> = {
	bash: [
		{
			// GIT_FLAGS covers what may sit between `git` and its verb: `git -C /repo
			// push` and `git --git-dir=… push` reach the same place as a bare push,
			// and a rule anchored on `^git\s+push` misses both.
			pattern: `^git\\s+${GIT_FLAGS}push(\\s|$)`,
			reason:
				"Never push. A pre-push hook deploys the API, so a push is a deploy. " +
				"Stop after your last commit; the orchestrator pushes.",
			terminate: true,
		},
		{
			// `(\s|$)` not `\b`: `\b` matches before a dot, so `git checkout main.py`
			// - a real file in this repo - was refused as "leaving your branch".
			pattern: String.raw`^git\s+(checkout|switch)\s+(main|master)(\s|$)`,
			reason:
				"Never leave your branch. You are in a worktree; main is checked out " +
				"elsewhere and this cannot succeed. The orchestrator merges.",
		},
		{
			// Same trap: `\b` here refused the read-only `git merge-base` and
			// `git merge-tree`. `--abort` and `--quit` are recovery, not merging.
			pattern: String.raw`^git\s+(merge|rebase)(\s+(?!--abort|--quit|--continue)|$)`,
			reason: "Never merge or rebase. The orchestrator does that after reviewing your diff.",
		},
		{
			// Only up to the first `-m`, so a commit *message* mentioning
			// `--no-verify` or `-n` is not itself refused. Writing about the hooks
			// is exactly what a worker in this repo does.
			pattern: `^git\\s+${GIT_FLAGS}commit(\\s+(?!-m|--message)\\S+)*\\s+(--no-verify|-n)(\\s|$)`,
			reason:
				"Never bypass the hooks. They run the suites and are slow, not hung — " +
				"budget 60-90s per commit and let them finish.",
		},
		{
			pattern: String.raw`^gh\s+\w+\s+(create|edit|close|reopen|comment|merge|delete|review|ready|develop|run|set)(\s|$)`,
			reason:
				"Never write to GitHub. The orchestrator owns every gh mutation, including " +
				"the issue trailer. Read-only `gh issue view` is fine.",
		},
		{
			pattern: String.raw`^gh\s+api\b.*(-X|--method)\s*(POST|PATCH|PUT|DELETE)`,
			reason: "Never write to GitHub. `gh api` with a write method is a mutation.",
		},
		{
			pattern: String.raw`^(npx\s+)?pi\s+(install|remove|uninstall|update)(\s|$)`,
			reason:
				"Never change pi's own configuration. It would alter the next worker's behaviour.",
		},
		{
			// The shell cannot reach `.pi/` through write/edit rules, so the bash
			// side needs its own. `git config core.hooksPath` is here because it
			// defeats the --no-verify rule by another route.
			pattern: String.raw`(^|\s)(>|>>|tee\b|rm\b|mv\b|cp\b|truncate\b).*(^|/|\s)\.pi/`,
			reason:
				"`.pi/` is orchestrator scaffolding, not part of your change, and not " +
				"yours to rewrite from the shell either.",
		},
		{
			// Only the *set* forms. `git config core.hooksPath` with nothing after
			// it is a query, and so is `--get`; blocking those refused a worker
			// that was reading the hook path to understand the suite, which cost
			// it a turn and taught it nothing. A write either supplies a value
			// after the key, or is an --unset.
			pattern: String.raw`^git\s+config\b(?:.*\bcore\.hooksPath\s+\S|.*(?:^|\s)--unset(?:-all)?(?:\s|$).*\bcore\.hooksPath)`,
			reason:
				"Never repoint core.hooksPath. The hooks run the suites; disabling them " +
				"is the same as --no-verify. Reading it is fine — this blocks only writes.",
		},
	],
	paths: [
		{
			// pi's own configuration must be tested BEFORE the scaffolding rule.
			// Ordered the other way, `~/.pi/agent/settings.json` matched the generic
			// `.pi/` rule first and the model was told it had touched "orchestrator
			// scaffolding" - a misleading reason for the case that matters most.
			// Not /Users/-anchored, so it holds on Linux too.
			pattern: String.raw`(^|/)(home|Users)/[^/]+/\.pi/|^~/\.pi/`,
			reason: "Never edit pi's own configuration; it would change the next worker's behaviour.",
		},
		{
			pattern: String.raw`(^|/)\.pi/`,
			reason: "`.pi/` is orchestrator scaffolding, not part of your change.",
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
	// Several heredocs may open on one line (`cat <<A <<B`); bash consumes their
	// bodies in order, so track a queue rather than a single terminator.
	let pending: { word: string; dashed: boolean }[] = [];

	for (const line of lines) {
		if (pending.length > 0) {
			const current = pending[0];
			// Only `<<-` permits an indented terminator. Treating every heredoc as
			// dashed ended bodies early and let a body line be scanned as a command.
			const ended = current.dashed ? line.trim() === current.word : line === current.word;
			if (ended) pending = pending.slice(1);
			continue;
		}
		const openers = findHeredocOpeners(line);
		if (openers.length > 0) {
			pending = openers.map((o) => ({ word: o.word, dashed: o.dashed }));
			out.push(line.slice(0, openers[0].index));
			continue;
		}
		out.push(line);
	}

	// An unterminated heredoc means the rest of the command was swallowed. Bash
	// would not run that body either, so dropping it is right - but a *quoted*
	// `<<EOF` is not a heredoc at all, which is what findHeredocOpeners guards.
	return out.join("\n");
}

/**
 * Find heredoc openers on one line, ignoring any that sit inside quotes.
 *
 * This guard is the whole point. `grep -rn '<<EOF' docs/ && git push` has no
 * heredoc in it — but a naive match treats `<<EOF` as one, discards everything
 * after it, and the guardrails then see no `git push` at all. A worker grepping
 * documentation for heredoc examples would have silently disarmed the checker
 * for the rest of that command.
 */
function findHeredocOpeners(line: string): { word: string; dashed: boolean; index: number }[] {
	const found: { word: string; dashed: boolean; index: number }[] = [];
	let quote: string | null = null;

	for (let i = 0; i < line.length; i++) {
		const ch = line[i];
		if (quote) {
			if (ch === quote && line[i - 1] !== "\\") quote = null;
			continue;
		}
		if (ch === "'" || ch === '"') {
			quote = ch;
			continue;
		}
		if (ch !== "<" || line[i + 1] !== "<") continue;
		// `<<<` is a here-string, not a heredoc: it has no body to skip.
		if (line[i + 2] === "<") {
			i += 2;
			continue;
		}
		const rest = line.slice(i);
		const match = rest.match(/^<<(-?)\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2/);
		if (!match) continue;
		found.push({ word: match[3], dashed: match[1] === "-", index: i });
		i += match[0].length - 1;
	}
	return found;
}

/**
 * Split into the segments a shell would run as separate commands, and strip the
 * leading noise that hides the real one: `cd x && git push` must be seen as
 * `git push`, and `sudo -E git push` likewise.
 */
export function commandSegments(command: string): string[] {
	const withoutHeredocs = stripHeredocs(command);
	return withoutHeredocs
		.split(/\|\||&&|[;\n|&]/)
		.map((segment) => segment.trim())
		.filter(Boolean)
		.map(stripLeadingWrappers);
}

const WRAPPERS = /^(sudo|command|env|nohup|time|xargs|nice|then|do|else|elif)\b(\s+-\S+)*\s+/;
const ASSIGNMENT = /^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+/;
const GROUPING = /^[({]\s*/;

/**
 * Strip the leading noise that hides the real command, until nothing more comes
 * off. The loop matters: `env FOO=bar git push` needs the wrapper removed, then
 * the assignment, then nothing. Stripping assignments once before the loop - as
 * this did originally - left `FOO=bar git push` unmatched and allowed the push.
 */
function stripLeadingWrappers(segment: string): string {
	let out = segment;
	let previous: string;
	do {
		previous = out;
		out = out.replace(GROUPING, "").replace(ASSIGNMENT, "").replace(WRAPPERS, "");
	} while (out !== previous);
	return out;
}

export interface Verdict {
	block: true;
	reason: string;
	terminate?: boolean;
}

/**
 * Drop rules that cannot be trusted, loudly, rather than letting them through.
 *
 * A rule with no `pattern` compiles to `new RegExp(undefined)` — which is
 * `/(?:)/`, and matches *everything*. A hand-edited guardrails.json missing one
 * key would therefore refuse every tool call the worker made, all night, with a
 * reason that never mentions the config. An invalid regex is the mirror: it
 * throws on every bash call. Both are silent-until-you-read-the-log failures,
 * which is the exact class this extension exists to remove.
 */
export function compileRules(rules: Rule[]): { rule: Rule; regex: RegExp }[] {
	const out: { rule: Rule; regex: RegExp }[] = [];
	for (const rule of rules) {
		if (typeof rule?.pattern !== "string" || rule.pattern === "") {
			console.error("[guardrails] ignoring a rule with no pattern:", JSON.stringify(rule));
			continue;
		}
		if (typeof rule.reason !== "string" || rule.reason === "") {
			console.error(`[guardrails] ignoring rule ${rule.pattern}: it has no reason text.`);
			continue;
		}
		try {
			out.push({ rule, regex: new RegExp(rule.pattern, "i") });
		} catch (error) {
			console.error(`[guardrails] ignoring rule ${rule.pattern}: not a valid regex.`, error);
		}
	}
	return out;
}

/** Decide whether a bash command may run. Pure, so the tests can reach it. */
export function checkBash(command: string, rules: Rule[]): Verdict | null {
	const compiled = compileRules(rules);
	for (const segment of commandSegments(command)) {
		for (const { rule, regex } of compiled) {
			if (regex.test(segment)) {
				return { block: true, reason: rule.reason, terminate: rule.terminate };
			}
		}
	}
	return null;
}

/** Decide whether a write/edit may touch a path. Pure, so the tests can reach it. */
export function checkPath(path: string, rules: Rule[]): Verdict | null {
	for (const { rule, regex } of compileRules(rules)) {
		if (regex.test(path)) {
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
