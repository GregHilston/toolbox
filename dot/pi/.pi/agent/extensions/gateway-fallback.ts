/**
 * Falls back to local oMLX when the litellm gateway on dungeon is down.
 * A failed litellm turn mid-session re-probes and switches too, without resending.
 * Subagents switch too: a worker on a dead gateway would only fail.
 * PI_FALLBACK_PROBE_URL forces the gateway probe target, for tests.
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const GATEWAY_PROVIDER = "litellm";
const DEFAULT_LOCAL = { provider: "omlx", id: "Qwen3.6-35B-A3B-4bit" };
const DEFAULT_LABEL = `${DEFAULT_LOCAL.provider}/${DEFAULT_LOCAL.id}`;
const PROBE_MS = 2000;

/** Any non-5xx response means up; Caddy answers 502 for a dead LiteLLM. */
export async function reachable(url: string, timeoutMs = PROBE_MS): Promise<boolean> {
	try {
		const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
		return res.status < 500;
	} catch {
		return false;
	}
}

/** A second try keeps a cold tailnet connect from flipping the model. */
export async function probeTwice(
	url: string,
	probe: (url: string) => Promise<boolean> = reachable,
): Promise<boolean> {
	return (await probe(url)) || (await probe(url));
}

/**
 * The host's own oMLX model: the first enabled omlx/* entry, the wide
 * (non-:lab) profile first. settings.json is per host, so no hostnames here.
 */
export function pickLocal(enabled: unknown): { provider: string; id: string } {
	const ids = Array.isArray(enabled)
		? enabled.filter((e): e is string => typeof e === "string" && e.startsWith("omlx/") && !e.endsWith("*"))
		: [];
	const pick = ids.find((e) => !e.endsWith(":lab")) ?? ids[0];
	return pick ? { provider: "omlx", id: pick.slice("omlx/".length) } : DEFAULT_LOCAL;
}

function configuredLocal(): { provider: string; id: string } {
	try {
		const dir = process.env.PI_CODING_AGENT_DIR ?? join(homedir(), ".pi", "agent");
		return pickLocal(JSON.parse(readFileSync(join(dir, "settings.json"), "utf8")).enabledModels);
	} catch {
		return DEFAULT_LOCAL;
	}
}

export type Outcome =
	| { action: "none" }
	| { action: "switch"; message: string }
	| { action: "stranded"; message: string };

export async function decide(
	provider: string | undefined,
	gatewayUrl: string,
	localUrl: string | undefined,
	probe: (url: string) => Promise<boolean> = probeTwice,
	localLabel = DEFAULT_LABEL,
): Promise<Outcome> {
	if (provider !== GATEWAY_PROVIDER) return { action: "none" };
	if (await probe(gatewayUrl)) return { action: "none" };
	if (!localUrl) {
		return {
			action: "stranded",
			message: "gateway on dungeon unreachable, no local fallback configured; pick with /model",
		};
	}
	if (await probe(localUrl)) {
		return {
			action: "switch",
			message: `gateway on dungeon unreachable; switched to ${localLabel} (local)`,
		};
	}
	return {
		action: "stranded",
		message: "gateway on dungeon and local oMLX both unreachable; pick another with /model",
	};
}

const CONNECTION_ERROR = /\b5\d\d\b|ECONNREFUSED|ENOTFOUND|EAI_AGAIN|fetch failed|connection|network|timed? ?out|socket|getaddrinfo/i;

/** 4xx (auth, context, oMLX guards) is the request's fault, not the gateway's. */
export function looksLikeOutage(errorMessage: string | undefined): boolean {
	if (!errorMessage) return false;
	if (/\b4\d\d\b/.test(errorMessage) && !/\b5\d\d\b/.test(errorMessage)) return false;
	return CONNECTION_ERROR.test(errorMessage);
}

export default function gatewayFallbackExtension(pi: ExtensionAPI): void {
	pi.on("session_start", async (_event, ctx) => {
		const want = configuredLocal();
		const label = `${want.provider}/${want.id}`;
		const local = ctx.modelRegistry.find(want.provider, want.id);
		const gatewayUrl = process.env.PI_FALLBACK_PROBE_URL ?? ctx.model?.baseUrl;
		if (!gatewayUrl) return;
		const outcome = await decide(ctx.model?.provider, gatewayUrl, local?.baseUrl, undefined, label);
		if (outcome.action === "none") return;
		let message = outcome.message;
		if (outcome.action === "switch" && local && !(await pi.setModel(local))) {
			message = `${label} has no API key; pick another with /model`;
		}
		ctx.ui.notify(message, "warning");
		// headless modes drop notify()
		if (ctx.mode !== "tui") console.error(message);
	});

	pi.on("message_end", async (event, ctx) => {
		const m = event.message as { role?: string; provider?: string; stopReason?: string; errorMessage?: string };
		if (m.role !== "assistant" || m.stopReason !== "error" || m.provider !== GATEWAY_PROVIDER) return;
		if (!looksLikeOutage(m.errorMessage)) return;
		const want = configuredLocal();
		const label = `${want.provider}/${want.id}`;
		const local = ctx.modelRegistry.find(want.provider, want.id);
		const gatewayUrl = process.env.PI_FALLBACK_PROBE_URL ?? ctx.model?.baseUrl;
		if (!gatewayUrl) return;
		const outcome = await decide(m.provider, gatewayUrl, local?.baseUrl, undefined, label);
		if (outcome.action === "none") return;
		let message = outcome.message;
		if (outcome.action === "switch") {
			if (local && (await pi.setModel(local))) {
				message = `gateway on dungeon went down; switched to ${label}. Say 'continue' to retry`;
			} else {
				message = `${label} has no API key; pick another with /model`;
			}
		}
		ctx.ui.notify(message, "warning");
		if (ctx.mode !== "tui") console.error(message);
	});
}
