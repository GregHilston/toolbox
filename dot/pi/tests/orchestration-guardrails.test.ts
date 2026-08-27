/**
 * The interesting half of these tests is the false positives.
 *
 * A guardrail that blocks a worker editing documentation *about* pushing gets
 * diagnosed as a broken tool and switched off, and then it protects nothing.
 * So the "must NOT block" cases below matter more than the "must block" ones.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
	DEFAULT_RULES,
	checkBash,
	checkPath,
	commandSegments,
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

test("blocks a push behind env assignments and sudo", () => {
	assert.ok(bash("GIT_SSH_COMMAND=ssh sudo -E git push --force"), "wrappers must be stripped");
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
	assert.ok(bash("/login deepseek"), "and /login changes credential resolution");
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
