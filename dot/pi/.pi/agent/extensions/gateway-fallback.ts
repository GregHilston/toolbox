/**
 * Falls back to local oMLX when the litellm gateway on dungeon is down.
 * Only the startup model is checked; a mid-session outage is not handled.
 * Subagents switch too: a worker on a dead gateway would only fail.
 * PI_FALLBACK_PROBE_URL forces the gateway probe target, for tests.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const GATEWAY_PROVIDER = "litellm";
const LOCAL = { provider: "omlx", id: "Qwen3.6-35B-A3B-4bit" };
const LOCAL_LABEL = `${LOCAL.provider}/${LOCAL.id}`;
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

export type Outcome =
	| { action: "none" }
	| { action: "switch"; message: string }
	| { action: "stranded"; message: string };

export async function decide(
	provider: string | undefined,
	gatewayUrl: string,
	localUrl: string | undefined,
	probe: (url: string) => Promise<boolean> = probeTwice,
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
			message: `gateway on dungeon unreachable; switched to ${LOCAL_LABEL} (local)`,
		};
	}
	return {
		action: "stranded",
		message: "gateway on dungeon and local oMLX both unreachable; pick another with /model",
	};
}

export default function gatewayFallbackExtension(pi: ExtensionAPI): void {
	pi.on("session_start", async (_event, ctx) => {
		const local = ctx.modelRegistry.find(LOCAL.provider, LOCAL.id);
		const gatewayUrl = process.env.PI_FALLBACK_PROBE_URL ?? ctx.model?.baseUrl;
		if (!gatewayUrl) return;
		const outcome = await decide(ctx.model?.provider, gatewayUrl, local?.baseUrl);
		if (outcome.action === "none") return;
		let message = outcome.message;
		if (outcome.action === "switch" && local && !(await pi.setModel(local))) {
			message = `${LOCAL_LABEL} has no API key; pick another with /model`;
		}
		ctx.ui.notify(message, "warning");
		// headless modes drop notify()
		if (ctx.mode !== "tui") console.error(message);
	});
}
