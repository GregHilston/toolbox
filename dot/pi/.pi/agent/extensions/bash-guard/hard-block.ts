// The hard-block floor: commands refused with no prompt.
//
// Each pattern matches anywhere in the command line, so wrappers, `sh -c`,
// aliases and `$(...)` cannot hide a catastrophe. The one exemption is a
// segment run by a read-only tool, so `grep shutdown` and `rg 'git push'`
// run: its text is dropped before matching.

export type HardRule = {
	reason: string;
	// Blocked only when headless, not in a disabled main session.
	headlessOnly?: boolean;
	pattern: RegExp;
};

// `git`, then any global options, then the subcommand.
const GIT = String.raw`\bgit(?:\s+(?:-[Cc]\s+\S+|--?[\w-]+(?:=\S*)?))*\s+`;
// A shell as a word, with or without a path.
const SH = String.raw`(?<![\w.-])(?:\S*\/)?(?:ba|z|da|k|fi)?sh(?![\w./-])`;
const rx = (source: string) => new RegExp(source);

export const HARD_RULES: HardRule[] = [
	{ reason: "recursive delete (rm -r / -rf / -Rf)", pattern: /(?<!\bgit\s+)\brm\b[^#\n]*\s-(?:[a-zA-Z]*[rR]|-recursive\b)/ },
	{ reason: "elevated privileges (sudo)", pattern: /\b(sudo|doas)\b/ },
	{ reason: "pipe to shell (runs whatever feeds it)", pattern: rx(String.raw`\|&?[^|;&\n]*` + SH) },
	{ reason: "here-string, heredoc or <(...) fed to a shell", pattern: rx(SH + String.raw`[^|;&\n]*<[<(]`) },
	{ reason: "filesystem formatting (mkfs)", pattern: /\bmkfs/ },
	{ reason: "filesystem formatting (newfs_*)", pattern: /\bnewfs_\w+/ },
	{ reason: "disk signature wipe", pattern: /\bwipefs\b/ },
	{ reason: "destructive disk operation (diskutil)", pattern: /\bdiskutil\s+(erase|zeroDisk|secureErase|reformat)/i },
	{ reason: "raw disk write (dd of=/dev/...)", pattern: /\bdd\b[^#\n]*\bof=\/dev\// },
	{ reason: "partition table management", pattern: /\b(parted|fdisk|gdisk|sgdisk)\b/ },
	{ reason: "disk encryption management", pattern: /\bcryptsetup\b/ },
	{ reason: "ZFS pool management", pattern: /\bzpool\b/ },
	{ reason: "system power operation", pattern: /\b(systemctl|launchctl)\b[^#\n]*\b(poweroff|reboot|halt|suspend)\b/ },
	{ reason: "system power operation", pattern: /\b(shutdown|reboot|halt|poweroff)\b/ },
	{ reason: "infrastructure teardown (terraform destroy)", pattern: /\bterraform\b[^#\n]*\sdestroy\b/ },
	{ reason: "Kubernetes resource deletion", pattern: /\bkubectl\b[^#\n]*\sdelete\b/ },
	{ reason: "bulk S3 deletion (aws s3 rm --recursive)", pattern: /\baws\s+s3\s+rm\b[^#\n]*--recursive/ },
	{ reason: "git commit (commits are main-session operations)", headlessOnly: true, pattern: rx(GIT + String.raw`commit(?![\w-])`) },
	{ reason: "git pull (pulls are main-session operations)", headlessOnly: true, pattern: rx(GIT + String.raw`pull(?![\w-])`) },
	{
		reason: "force push or remote branch delete (rewrites remote history)",
		pattern: rx(GIT + String.raw`push(?![\w-])[^#\n;&|]*\s(?:-[a-zA-Z]*[fd][a-zA-Z]*|--force\S*|--mirror|--delete|\+\S|:\S)`),
	},
	{ reason: "git push (pushes are main-session operations)", headlessOnly: true, pattern: rx(GIT + String.raw`push(?![\w-])`) },
	{ reason: "discard all uncommitted changes (git reset --hard)", pattern: rx(GIT + String.raw`reset\b[^#\n]*--hard\b`) },
	{ reason: "delete untracked files (git clean -f)", pattern: rx(GIT + String.raw`clean\b[^#\n]*(?:\s-[a-zA-Z]*f|--force)`) },
	{ reason: "expire reflog (removes recovery history)", pattern: rx(GIT + String.raw`reflog\s+expire\b`) },
	{ reason: "prune unreachable objects (git gc --prune)", pattern: rx(GIT + String.raw`gc\b[^#\n]*--prune\b`) },
];

const READ_ONLY = new Set(["grep", "egrep", "fgrep", "rg", "ag", "ack", "cat", "less", "head", "tail", "wc", "echo", "printf"]);
const GIT_READ_ONLY = new Set(["grep", "log", "show", "diff", "blame"]);

type Segment = { text: string; substituted: boolean };

/**
 * The command split on unquoted `;`, `&&`, `||`, `|`, `&`, newlines,
 * parentheses and backticks, each piece kept with the separator before
 * it. Null if a quote is left open. The body of a heredoc with a quoted
 * delimiter is dropped: nothing in it runs as shell.
 */
function segments(command: string): Segment[] | null {
	const out: Segment[] = [];
	let text = "";
	let quote: string | null = null;
	let backtick = false;
	const parens: boolean[] = []; // true for `$(`
	const quotedBodies: string[] = [];
	const end = (sep: string) => {
		out.push({ text, substituted: backtick || parens.includes(true) });
		text = sep;
	};
	for (let i = 0; i < command.length; i++) {
		const c = command[i];
		if (c === "\\" && quote !== "'") {
			text += c + (command[i + 1] ?? "");
			i++;
		} else if (quote) {
			if (c === quote) quote = null;
			text += c;
		} else if (c === "'" || c === '"') {
			quote = c;
			text += c;
		} else if (c === "\n") {
			end(c);
			for (const delim of quotedBodies.splice(0)) {
				const escaped = delim.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
				const close = new RegExp(`^\\t*${escaped}$`, "m").exec(command.slice(i + 1));
				i = close ? i + close.index + close[0].length : command.length;
			}
		} else if (command.startsWith("<<", i) && command[i + 2] !== "<") {
			const m = /^<<-?[ \t]*(?:(['"])([^'"\s]+)\1|\\(\S+))/.exec(command.slice(i));
			if (m) {
				quotedBodies.push(m[2] ?? m[3]);
				text += m[0];
				i += m[0].length - 1;
			} else text += c;
		} else if (["&&", "||", "|&"].includes(command.slice(i, i + 2))) {
			end(command.slice(i, i + 2));
			i++;
		} else if (c === "(") {
			const dollar = text.endsWith("$");
			end(c);
			parens.push(dollar);
		} else if (c === ")") {
			end(c);
			parens.pop();
		} else if (c === "`") {
			end(c);
			backtick = !backtick;
		} else if (c === ";" || c === "|" || c === "&") {
			end(c);
		} else text += c;
	}
	if (quote) return null;
	end("");
	return out;
}

function readOnly({ text, substituted }: Segment): boolean {
	// Output of `$(...)` or backticks becomes a command.
	if (substituted || /\$\(|`/.test(text)) return false;
	const words = text.replace(/^[;&|()`\n]+/, "").trim().split(/\s+/);
	// rg --pre, ack --pager and less +! run a command.
	if (words.some((w) => /^(--pre|--pager|\+)/.test(w))) return false;
	const cmd = words[0].split("/").pop() ?? "";
	return cmd === "git" ? GIT_READ_ONLY.has(words[1]) : READ_ONLY.has(cmd);
}

/** Why `command` is refused, or null if it may run. */
export function hardBlockReason(command: string, rules: HardRule[]): string | null {
	const segs = segments(command);
	// An exempt segment keeps its separator so the pipe before a shell stays.
	const checked = segs ? segs.map((s) => (readOnly(s) ? s.text.match(/^[;&|()`\n]*/)![0] : s.text)).join("") : command;
	return rules.find((r) => r.pattern.test(checked))?.reason ?? null;
}

export const HEADLESS_RULES = HARD_RULES;
// The user opted into autonomy, so routine git writes pass.
export const DISABLED_FLOOR_RULES = HARD_RULES.filter((r) => !r.headlessOnly);
