/**
 * The interesting half of these tests is the false positives.
 *
 * A guardrail that blocks a worker editing documentation *about* pushing gets
 * diagnosed as a broken tool and switched off, and then it protects nothing.
 * So the "must NOT block" cases below matter more than the "must block" ones.
 */

import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import {
	DEFAULT_RULES,
	checkBash,
	checkPath,
	commandSegments,
	compileRules,
	loadRules,
	stripHeredocs,
} from "../.pi/agent/extensions/orchestration-guardrails.ts";

const bash = (command: string) => checkBash(command, DEFAULT_RULES.bash);

test("blocks a bare push, and terminates - a push is a deploy here", () => {
	const verdict = bash("git push origin main");
	assert.ok(verdict, "git push must be refused");
	assert.equal(verdict.terminate, true, "and must stop the run rather than be worked around");
	assert.match(verdict.reason, /deploy/i, "the reason must say why, so the model does not retry");
});

test("blocks a push hidden behind a cd, which is how a worker would write it", () => {
	assert.ok(bash("cd /repo/worktrees/issue-64 && git push"), "the segment after && is a command");
});

test("blocks a push behind env assignments and sudo, in BOTH orders", () => {
	assert.ok(bash("GIT_SSH_COMMAND=ssh sudo -E git push --force"), "assignment then wrapper");
	// The order that used to slip: stripping assignments once *before* the wrapper
	// loop left "FOO=bar git push" unmatched. Only this spelling catches it.
	assert.ok(bash("env FOO=bar git push"), "wrapper then assignment");
	assert.ok(bash("env GIT_SSH_COMMAND=ssh git push"), "the realistic version of it");
});

test("blocks a push wearing git's pre-verb flags", () => {
	assert.ok(bash("git -C /repo push"), "-C sits between git and its verb");
	assert.ok(bash("git --git-dir=/r/.git --work-tree=/r push"), "so do --git-dir/--work-tree");
	assert.ok(bash("git -c user.email=x commit --no-verify -m y"), "and -c, for the hook rule");
});

test("blocks a push inside shell control flow and grouping", () => {
	assert.ok(bash("if true; then git push; fi"), "`then` is not a command");
	assert.ok(bash("for r in origin; do git push $r; done"), "nor is `do`");
	assert.ok(bash("{ git push; }"), "brace grouping");
	assert.ok(bash("( git push )"), "subshell grouping");
	assert.ok(bash("echo hi & git push"), "& is a separator too");
});

test("blocks the long form of a gh api write, and npx-wrapped pi", () => {
	assert.ok(bash("gh api --method POST repos/x/y/issues"), "--method is -X spelled out");
	assert.ok(bash("npx pi install thing"), "npx is a wrapper");
});

test("blocks shell routes around the write/edit path rules", () => {
	assert.ok(bash("echo x > .pi/guardrails.json"), "redirect into scaffolding");
	assert.ok(bash("rm -f .pi/guardrails.json"), "or deleting it");
	assert.ok(bash("git config core.hooksPath /dev/null"), "which defeats --no-verify by another road");
});

test("blocks the other ways out of a worktree", () => {
	assert.ok(bash("git checkout main"), "leaving the branch");
	assert.ok(bash("git merge issue-65-run-over-close"), "merging is the orchestrator's job");
	assert.ok(bash("git rebase main"), "as is rebasing");
});

test("blocks --no-verify in both spellings", () => {
	assert.ok(bash('git commit --no-verify -m "x"'), "long form");
	assert.ok(bash('git commit -n -m "x"'), "short form");
});

test("blocks gh writes but allows gh reads", () => {
	assert.ok(bash("gh issue close 64"), "closing is a mutation");
	assert.ok(bash("gh pr create --fill"), "so is opening a PR");
	assert.ok(bash("gh api repos/x/y -X POST"), "and a write method through gh api");
	assert.equal(bash("gh issue view 64 --json body"), null, "reading an issue is explicitly fine");
	assert.equal(bash("gh api repos/x/y"), null, "a plain gh api read is fine");
});

test("blocks a worker reconfiguring pi for the next worker", () => {
	assert.ok(bash("pi install some-extension"), "installing changes the next run");
	assert.ok(bash("pi update"), "as does updating it underneath the run");
});

test("does NOT try to police /login, which the bash tool cannot reach", () => {
	// /login is a pi *slash command*, typed in the TUI - it never arrives as a
	// shell command, so a rule for it protected nothing and refused `rg /login`
	// in any repo with a login route. The prompt still forbids it.
	assert.equal(bash("rg /login src/"), null, "searching for a login route is ordinary work");
});

// --- the false positives, which are the point ---

test("does NOT block writing documentation that mentions the forbidden commands", () => {
	const command = [
		"cat > docs/workflow.md <<'EOF'",
		"## Publishing",
		"Run `git push` when the review is done.",
		"Never use git commit --no-verify.",
		"EOF",
	].join("\n");
	assert.equal(bash(command), null, "a heredoc body is data, not commands");
});

test("does NOT block an indented heredoc terminator (<<- form)", () => {
	const command = ["cat <<-EOF > out.txt", "git push", "\tEOF", "echo done"].join("\n");
	assert.equal(bash(command), null, "<<- allows the terminator to be indented");
});

test("a quoted << does not open a heredoc and swallow the rest of the line", () => {
	// The worst hole found in review: `<<EOF` inside quotes was treated as a real
	// heredoc opener, so everything after it became invisible and the trailing
	// push was allowed. Silent, and self-inflicted by a worker grepping docs.
	assert.ok(bash("grep -rn '<<EOF' docs/ && git push"), "the push after a fake opener");
	assert.ok(bash('echo "a << b" && git push'), "and after a quoted shift-looking token");
});

test("does NOT treat a here-string as a heredoc", () => {
	assert.equal(bash("cat <<<'some text'"), null, "<<< has no body to skip");
});

test("does NOT block grepping for the forbidden command", () => {
	assert.equal(bash('grep -rn "git push" docs/'), null, "the argument is not the command");
	assert.equal(bash("rg 'gh issue close' ."), null, "nor here");
});

test("does NOT block commands that merely start with the same letters", () => {
	assert.equal(bash("git pushd-not-a-real-command"), null, "word boundary must hold");
	assert.equal(bash("gh issue view 1 --comments"), null, "--comments is a flag, not `comment`");
});

test("does NOT block ordinary work", () => {
	assert.equal(bash("git commit -m 'fix: a thing'"), null);
	assert.equal(bash("bash run_tests.sh"), null);
	assert.equal(bash("cd godot-client && bash run_tests.sh && git add -A"), null);
});

test("does NOT block checking out a file that merely starts with 'main'", () => {
	// Real paths in the repo this guards: main.py, main.gd, main.tscn. `\b`
	// matched before the dot and refused restoring any of them.
	assert.equal(bash("git checkout main.py"), null, "a file, not the branch");
	assert.equal(bash("git checkout godot-client/scenes/main/main.gd"), null);
	assert.equal(bash("git checkout -- main.tscn"), null);
});

test("does NOT block read-only merge plumbing, or recovery from a rebase", () => {
	assert.equal(bash("git merge-base --is-ancestor main HEAD"), null, "read-only and idiomatic");
	assert.equal(bash("git merge-tree a b"), null, "also read-only");
	assert.equal(bash("git rebase --abort"), null, "the only way out of a rebase");
});

test("does NOT block a commit message that talks about the hooks", () => {
	// The rule used to run `.*` into the message body, so writing *about*
	// --no-verify was refused - which is exactly what a worker in this repo does.
	assert.equal(bash("git commit -m 'chore: pass -n to xargs'"), null);
	assert.equal(bash("git commit -m 'feat: document the --no-verify escape hatch'"), null);
});

// --- segmentation, which everything above rests on ---

test("splits on every separator a shell would", () => {
	assert.deepEqual(commandSegments("a && b || c; d | e"), ["a", "b", "c", "d", "e"]);
});

test("strips heredoc bodies but keeps the command that opened them", () => {
	const stripped = stripHeredocs("cat > f <<'EOF'\ngit push\nEOF\necho after");
	assert.match(stripped, /cat > f/, "the opening command survives");
	assert.doesNotMatch(stripped, /git push/, "the body does not");
	assert.match(stripped, /echo after/, "and the script continues after the terminator");
});

test("handles a command with no heredoc unchanged", () => {
	assert.equal(stripHeredocs("echo hi && ls"), "echo hi && ls");
});

// --- paths ---

test("blocks edits to orchestrator scaffolding and pi's own config", () => {
	assert.ok(checkPath(".pi/guardrails.json", DEFAULT_RULES.paths), "worktree scaffolding");
	assert.ok(checkPath("/Users/someone/.pi/agent/settings.json", DEFAULT_RULES.paths), "pi config");
});

test("does NOT block ordinary source paths", () => {
	assert.equal(checkPath("godot-client/scenes/game/game_screen.gd", DEFAULT_RULES.paths), null);
	assert.equal(checkPath("docs/pi-notes.md", DEFAULT_RULES.paths), null, "'pi' in a name is fine");
});

// --- loadRules: the arming decision, previously untested entirely ---

test("stays inert with no config and no env - interactive sessions must not be policed", () => {
	const dir = mkdtempSync(join(tmpdir(), "guardrails-"));
	try {
		assert.equal(loadRules(dir, {}), null, "absent config means absent guardrails");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("arms on an empty config file, and still gets every default", () => {
	const dir = mkdtempSync(join(tmpdir(), "guardrails-"));
	try {
		mkdirSync(join(dir, ".pi"));
		writeFileSync(join(dir, ".pi", "guardrails.json"), "{}");
		const rules = loadRules(dir, {});
		assert.ok(rules, "the file's presence is what arms it");
		assert.equal(rules.bash.length, DEFAULT_RULES.bash.length, "`echo '{}'` is documented; honour it");
		assert.ok(checkBash("git push", rules.bash), "and the defaults actually apply");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("arms on PI_GUARDRAILS=1 with no file at all", () => {
	const dir = mkdtempSync(join(tmpdir(), "guardrails-"));
	try {
		assert.ok(loadRules(dir, { PI_GUARDRAILS: "1" }), "the env var is the other documented switch");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("merges project rules onto the defaults rather than replacing them", () => {
	const dir = mkdtempSync(join(tmpdir(), "guardrails-"));
	try {
		mkdirSync(join(dir, ".pi"));
		writeFileSync(
			join(dir, ".pi", "guardrails.json"),
			JSON.stringify({ bash: [{ pattern: "^\\./export_macos\\.sh", reason: "Interactive; it hangs." }] }),
		);
		const rules = loadRules(dir, {});
		assert.ok(rules);
		assert.ok(checkBash("./export_macos.sh", rules.bash), "the project rule applies");
		assert.ok(checkBash("git push", rules.bash), "and the default it did not restate still does");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("malformed JSON falls back to the defaults instead of disarming", () => {
	const dir = mkdtempSync(join(tmpdir(), "guardrails-"));
	try {
		mkdirSync(join(dir, ".pi"));
		writeFileSync(join(dir, ".pi", "guardrails.json"), "{ this is not json");
		const rules = loadRules(dir, {});
		assert.ok(rules, "a typo must not silently switch the guardrails off");
		assert.ok(checkBash("git push", rules.bash), "the defaults still hold");
	} finally {
		rmSync(dir, { recursive: true, force: true });
	}
});

test("a rule with no pattern is dropped, not treated as match-everything", () => {
	// new RegExp(undefined) is /(?:)/, which matches any string - so one missing
	// key in a hand-edited config would have refused every tool call all night.
	const compiled = compileRules([{ reason: "no pattern here" } as never]);
	assert.deepEqual(compiled, [], "dropped");
	assert.equal(checkBash("ls", [{ reason: "no pattern" } as never]), null, "and `ls` still runs");
});

test("a rule whose regex will not compile is dropped, not thrown", () => {
	assert.equal(checkBash("ls", [{ pattern: "(", reason: "unclosed group" }]), null);
	assert.ok(
		checkBash("git push", [{ pattern: "(", reason: "bad" }, ...DEFAULT_RULES.bash]),
		"and a bad rule does not take the good ones down with it",
	);
});
