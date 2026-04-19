/**
 * CLAUDE.md loader extension
 *
 * Walks from the session's cwd up to the git root (or filesystem root),
 * collects all CLAUDE.md files it finds, and appends their contents to
 * the system prompt — mirroring how Claude Code reads project context.
 *
 * Only project-level files are loaded; ~/.claude/CLAUDE.md is intentionally
 * skipped since it contains Claude Code-specific instructions that don't
 * apply to pi.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import * as child_process from "node:child_process";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

/** Find the git root for a directory, or null if not in a repo. */
function gitRoot(dir: string): string | null {
	try {
		const result = child_process.execSync("git rev-parse --show-toplevel", {
			cwd: dir,
			stdio: ["ignore", "pipe", "ignore"],
			encoding: "utf8",
		});
		return result.trim();
	} catch {
		return null;
	}
}

/**
 * Walk from `startDir` up to `stopDir` (inclusive) and collect any
 * CLAUDE.md files found, ordered from outermost (repo root) to innermost (cwd).
 */
function collectClaudeMd(startDir: string, stopDir: string): Array<{ filePath: string; content: string }> {
	const dirs: string[] = [];
	let current = startDir;
	while (true) {
		dirs.unshift(current); // prepend so we get root→cwd order
		if (current === stopDir) break;
		const parent = path.dirname(current);
		if (parent === current) break; // filesystem root
		current = parent;
	}

	const found: Array<{ filePath: string; content: string }> = [];
	for (const dir of dirs) {
		const candidate = path.join(dir, "CLAUDE.md");
		if (fs.existsSync(candidate)) {
			try {
				const content = fs.readFileSync(candidate, "utf8").trim();
				if (content) found.push({ filePath: candidate, content });
			} catch {
				// unreadable — skip
			}
		}
	}
	return found;
}

export default function claudeMdExtension(pi: ExtensionAPI) {
	let claudeFiles: Array<{ filePath: string; content: string }> = [];

	pi.on("session_start", async (_event, ctx) => {
		const root = gitRoot(ctx.cwd) ?? ctx.cwd;
		claudeFiles = collectClaudeMd(ctx.cwd, root);

		if (claudeFiles.length > 0) {
			const labels = claudeFiles.map((f) => path.relative(ctx.cwd, f.filePath)).join(", ");
			ctx.ui.notify(`Loaded CLAUDE.md context: ${labels}`, "info");
		}
	});

	pi.on("before_agent_start", async (event) => {
		if (claudeFiles.length === 0) return;

		const sections = claudeFiles
			.map((f) => `### ${f.filePath}\n\n${f.content}`)
			.join("\n\n---\n\n");

		return {
			systemPrompt:
				event.systemPrompt +
				`\n\n## Project Context (from CLAUDE.md)\n\n${sections}`,
		};
	});
}
