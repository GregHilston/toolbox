// The hard-block floor: commands refused with no prompt, by command word.
//
// A regex over the raw string also matched arguments, so `grep shutdown`
// and `rg 'git push'` were refused and reviewing shell code was impossible.
// This looks at the command word of each simple command instead, and
// re-checks what runs inside `sh -c`, `eval`, `find -exec` and `$(...)`.
import { parse } from "shell-quote";

export type HardRule = {
	reason: string;
	// Blocked only when headless, not in a disabled main session.
	headlessOnly?: boolean;
	test: (cmd: string, args: string[]) => boolean;
};

const SHELLS = new Set(["sh", "bash", "zsh", "dash", "fish", "ksh"]);
// Words that run the command after them.
const WRAPPERS = new Set([
	"env", "command", "builtin", "exec", "nohup", "time", "nice", "timeout", "stdbuf", "caffeinate",
	"xargs", "then", "do", "else", "elif", "if", "while", "until", "!", "{",
]);
const CONTROL_OPS = new Set([";", "&&", "||", "&", "(", ")", ";;", "<(", ">("]);
const PIPE_OPS = new Set(["|", "|&"]);
const MAX_DEPTH = 4;

const hasShortFlag = (args: string[], letters: string) =>
	args.some((a) => /^-[A-Za-z]+$/.test(a) && [...letters].some((l) => a.includes(l)));

function gitSub(args: string[]): { sub: string | undefined; rest: string[] } {
	for (let i = 0; i < args.length; i++) {
		const a = args[i];
		if (["-C", "-c", "--git-dir", "--work-tree", "--namespace"].includes(a)) i++;
		else if (!a.startsWith("-")) return { sub: a, rest: args.slice(i + 1) };
	}
	return { sub: undefined, rest: [] };
}

const git = (sub: string, more: (rest: string[]) => boolean = () => true) => (cmd: string, args: string[]) => {
	if (cmd !== "git") return false;
	const g = gitSub(args);
	return g.sub === sub && more(g.rest);
};

export const HARD_RULES: HardRule[] = [
	{ reason: "recursive delete (rm -r / -rf / -Rf)", test: (c, a) => c === "rm" && (hasShortFlag(a, "rR") || a.includes("--recursive")) },
	{ reason: "elevated privileges (sudo)", test: (c) => c === "sudo" || c === "doas" },
	{ reason: "filesystem formatting (mkfs)", test: (c) => c.startsWith("mkfs") },
	{ reason: "filesystem formatting (newfs_*)", test: (c) => c.startsWith("newfs_") },
	{ reason: "disk signature wipe", test: (c) => c === "wipefs" },
	{ reason: "destructive disk operation (diskutil)", test: (c, a) => c === "diskutil" && /^(erase|zerodisk|secureerase|reformat)/i.test(a[0] ?? "") },
	{ reason: "raw disk write (dd of=/dev/...)", test: (c, a) => c === "dd" && a.some((x) => x.startsWith("of=/dev/")) },
	{ reason: "partition table management", test: (c) => ["parted", "fdisk", "gdisk", "sgdisk"].includes(c) },
	{ reason: "disk encryption management", test: (c) => c === "cryptsetup" },
	{ reason: "ZFS pool management", test: (c) => c === "zpool" },
	{ reason: "system power operation", test: (c) => ["shutdown", "reboot", "halt", "poweroff"].includes(c) },
	{ reason: "infrastructure teardown (terraform destroy)", test: (c, a) => c === "terraform" && a.includes("destroy") },
	{ reason: "Kubernetes resource deletion", test: (c, a) => c === "kubectl" && a.includes("delete") },
	{ reason: "bulk S3 deletion (aws s3 rm --recursive)", test: (c, a) => c === "aws" && a.includes("s3") && a.includes("rm") && a.includes("--recursive") },
	{ reason: "git commit (commits are main-session operations)", headlessOnly: true, test: git("commit") },
	{ reason: "git pull (pulls are main-session operations)", headlessOnly: true, test: git("pull") },
	{ reason: "git push (pushes are main-session operations)", headlessOnly: true, test: git("push") },
	{ reason: "force push (rewrites remote history)", test: git("push", (r) => r.some((x) => x === "-f" || x.startsWith("--force"))) },
	{ reason: "discard all uncommitted changes (git reset --hard)", test: git("reset", (r) => r.includes("--hard")) },
	{ reason: "delete untracked files (git clean -f)", test: git("clean", (r) => hasShortFlag(r, "f") || r.includes("--force")) },
	{ reason: "expire reflog (removes recovery history)", test: git("reflog", (r) => r[0] === "expire") },
	{ reason: "prune unreachable objects (git gc --prune)", test: git("gc", (r) => r.some((x) => x.startsWith("--prune"))) },
];

type Token = string | { op?: string; pattern?: string; comment?: string };

// shell-quote joins lines into one command, so split them first.
function newlinesToSemicolons(s: string): string {
	let out = "";
	let quote: string | null = null;
	for (let i = 0; i < s.length; i++) {
		const c = s[i];
		if (c === "\\" && quote !== "'") {
			out += c + (s[++i] ?? "");
			continue;
		}
		if (quote) {
			if (c === quote) quote = null;
		} else if (c === "'" || c === '"') {
			quote = c;
		} else if (c === "\n") {
			out += ";";
			continue;
		}
		out += c;
	}
	return out;
}

/** Simple commands as word lists, grouped into pipelines. */
function pipelines(command: string): string[][][] {
	const tokens = parse(newlinesToSemicolons(command), (name: string) => `$${name}`) as Token[];
	const out: string[][][] = [];
	let pipeline: string[][] = [];
	let words: string[] = [];
	const endCommand = () => {
		if (words.length) pipeline.push(words);
		words = [];
	};
	const endPipeline = () => {
		endCommand();
		if (pipeline.length) out.push(pipeline);
		pipeline = [];
	};
	for (let i = 0; i < tokens.length; i++) {
		const t = tokens[i];
		if (typeof t === "string") words.push(t);
		else if (t.op === "glob") words.push(t.pattern ?? "");
		else if (t.op && PIPE_OPS.has(t.op)) endCommand();
		else if (t.op && CONTROL_OPS.has(t.op)) endPipeline();
		else if (t.op) i++; // a redirect: its target is not a command
	}
	endPipeline();
	return out;
}

function commandWord(words: string[]): { cmd: string; args: string[] } | null {
	let i = 0;
	let wrapped = false;
	while (i < words.length) {
		const w = words[i];
		if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(w)) i++;
		else if (WRAPPERS.has(w)) {
			wrapped = true;
			i++;
		} else if (wrapped && (w.startsWith("-") || /^\d+(\.\d+)?[smhd]?$/.test(w))) i++;
		else break;
	}
	if (i >= words.length) return null;
	return { cmd: words[i].split("/").pop() ?? "", args: words.slice(i + 1) };
}

// Command strings that a simple command runs in turn.
function innerCommands(cmd: string, args: string[]): string[] {
	if (SHELLS.has(cmd)) {
		const c = args.indexOf("-c");
		return c >= 0 && args[c + 1] !== undefined ? [args[c + 1]] : [];
	}
	if (cmd === "eval") return [args.join(" ")];
	if (cmd === "find") {
		const inner: string[] = [];
		args.forEach((a, i) => {
			if (["-exec", "-execdir", "-ok", "-okdir"].includes(a)) {
				const end = args.findIndex((x, j) => j > i && (x === ";" || x === "+"));
				inner.push(args.slice(i + 1, end < 0 ? undefined : end).join(" "));
			}
		});
		return inner;
	}
	return [];
}

/** Why `command` is refused, or null if it may run. */
export function hardBlockReason(command: string, rules: HardRule[], depth = 0): string | null {
	if (depth > MAX_DEPTH) return "command nested too deeply to check";
	// Substitutions run wherever they sit, even inside double quotes.
	for (const m of command.matchAll(/\$\(([^()]*)\)|`([^`]*)`/g)) {
		const inner = hardBlockReason(m[1] ?? m[2], rules, depth + 1);
		if (inner) return inner;
	}
	let parsed: string[][][];
	try {
		parsed = pipelines(command);
	} catch {
		return "a command that could not be parsed";
	}
	for (const pipeline of parsed) {
		const words = pipeline.map(commandWord);
		for (const [i, w] of words.entries()) {
			if (!w) continue;
			const rule = rules.find((r) => r.test(w.cmd, w.args));
			if (rule) return rule.reason;
			const fetched = words.slice(0, i).some((u) => u && (u.cmd === "curl" || u.cmd === "wget"));
			if (fetched && SHELLS.has(w.cmd) && !w.args.includes("-c")) return "pipe to shell (remote code execution)";
			for (const inner of innerCommands(w.cmd, w.args)) {
				const reason = hardBlockReason(inner, rules, depth + 1);
				if (reason) return reason;
			}
		}
	}
	return null;
}

export const HEADLESS_RULES = HARD_RULES;
// The user opted into autonomy, so routine git writes pass.
export const DISABLED_FLOOR_RULES = HARD_RULES.filter((r) => !r.headlessOnly);
