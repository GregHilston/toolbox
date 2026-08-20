/**
 * Web search for the model, via our self-hosted SearXNG.
 *
 * Registers a real `web_search` tool rather than teaching the model to curl.
 * The previous version of this file injected bash instructions pointing at
 * http://localhost:8214, which only ever worked on dungeon — SearXNG is a
 * container there, so on moria and citadel pi had no working web search at all,
 * and the failure looked like the model choosing not to search.
 *
 * The endpoint is NOT a literal here. Only nix knows each host's answer
 * (localhost on dungeon, the tailnet address everywhere else), so
 * `custom.programs.pi.searxngBaseUrl` writes ~/.pi/agent/searxng.json and this
 * reads it. PI_SEARXNG_URL overrides for a one-off.
 *
 * Token efficiency is the point. SearXNG's JSON is enormous — engine metadata,
 * scores, parsed_url arrays, positions — and almost none of it helps the model.
 * We return `n. title\n   url\n   snippet` and nothing else, capped, because
 * this replaced a paid Brave tool that was chosen for exactly that discipline.
 */

import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

const CONFIG_PATH = join(homedir(), ".pi", "agent", "searxng.json");

// Enough for the model to judge relevance and decide what to read in full;
// past this, results are near-duplicates and just burn context.
const MAX_RESULTS = 8;
const MAX_SNIPPET_CHARS = 280;
const MAX_OUTPUT_CHARS = 6000;
const REQUEST_TIMEOUT_MS = 15000;

function resolveBaseUrl(): string {
	const fromEnv = process.env.PI_SEARXNG_URL;
	if (fromEnv) return fromEnv.replace(/\/+$/, "");
	// nix writes this file on every host that enables pi. If it is missing, the
	// host was configured by hand — say so rather than guessing an endpoint.
	const raw = readFileSync(CONFIG_PATH, "utf8");
	const parsed = JSON.parse(raw) as { searxngBaseUrl?: string };
	if (!parsed.searxngBaseUrl) {
		throw new Error(`${CONFIG_PATH} has no "searxngBaseUrl".`);
	}
	return parsed.searxngBaseUrl.replace(/\/+$/, "");
}

interface SearxResult {
	title?: string;
	url?: string;
	content?: string;
}

// SearXNG reports per-engine failures here as [engine, reason] and still returns
// HTTP 200 with an empty `results`. Without surfacing it, an instance whose
// engines are all CAPTCHA'd is indistinguishable from a query with no matches —
// which is exactly how this instance sat broken.
type UnresponsiveEngine = [string, string];

function compact(text: string): string {
	return text.replace(/\s+/gu, " ").trim();
}

function formatResults(query: string, results: SearxResult[], unresponsive: UnresponsiveEngine[]): string {
	if (results.length === 0) {
		if (unresponsive.length > 0) {
			const detail = unresponsive.map(([engine, reason]) => `${engine} (${reason})`).join(", ");
			return `No results for "${query}", and ${unresponsive.length} search engine(s) failed: ${detail}. This is an instance problem, not an empty web — do not conclude the topic has no coverage. Enable a working engine in home-lab's searxng/settings.yml.`;
		}
		return `No results for "${query}". Try fewer or less specific terms — SearXNG returns nothing for over-quoted queries.`;
	}
	const lines = results.map((r, i) => {
		const title = compact(r.title ?? "(untitled)");
		const url = r.url ?? "";
		const snippet = compact(r.content ?? "").slice(0, MAX_SNIPPET_CHARS);
		return `${i + 1}. ${title}\n   ${url}${snippet ? `\n   ${snippet}` : ""}`;
	});
	const out = `Results for "${query}":\n\n${lines.join("\n\n")}`;
	if (out.length <= MAX_OUTPUT_CHARS) return out;
	return `${out.slice(0, MAX_OUTPUT_CHARS - 80).trimEnd()}\n\n[truncated; narrow the query]`;
}

export default function webSearchExtension(pi: ExtensionAPI): void {
	pi.registerTool({
		name: "web_search",
		label: "Web Search",
		description:
			"Search the web through a private SearXNG metasearch instance. Returns ranked title/URL/snippet results. Use for documentation, current facts, error messages, and anything outside the codebase or conversation.",
		promptSnippet: "Search the web via SearXNG",
		promptGuidelines: [
			"Use web_search when the answer is not in the codebase, the conversation, or your own knowledge — especially for current facts and library documentation.",
			"Keep queries short and specific. Do not wrap the whole query in quotes; SearXNG often returns nothing for quoted queries.",
			"To read a result in full, fetch its URL with the bash tool afterwards.",
		],
		// Plain JSON Schema on purpose. TypeBox's Type.Object() produces exactly
		// this at runtime, but `typebox` ships inside pi's own node_modules and is
		// not resolvable from ~/.pi/agent/extensions — importing it would make this
		// file's loadability depend on pi's install layout.
		parameters: {
			type: "object",
			properties: {
				query: {type: "string", description: "Search query. Short and specific; no surrounding quotes."},
				count: {
					type: "number",
					description: `Maximum results to return. Default ${MAX_RESULTS}, max ${MAX_RESULTS}.`,
				},
				categories: {
					type: "string",
					description: 'Optional SearXNG category filter, e.g. "it", "news", "science".',
				},
			},
			required: ["query"],
		} as never,
		executionMode: "parallel",
		async execute(_toolCallId: string, params: {query: string; count?: number; categories?: string}, signal?: AbortSignal) {
			const baseUrl = resolveBaseUrl();
			const limit = Math.max(1, Math.min(Number(params.count) || MAX_RESULTS, MAX_RESULTS));

			const url = new URL(`${baseUrl}/search`);
			url.searchParams.set("q", params.query);
			url.searchParams.set("format", "json");
			if (params.categories) url.searchParams.set("categories", params.categories);

			// SearXNG can hang on a slow upstream engine. Without our own timeout the
			// tool call blocks the agent loop indefinitely.
			const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
			const abort = signal ? AbortSignal.any([signal, timeout]) : timeout;

			let response: Response;
			try {
				response = await fetch(url, {signal: abort, headers: {Accept: "application/json"}});
			} catch (error) {
				throw new Error(
					`SearXNG request to ${baseUrl} failed: ${error}. Is the instance reachable from this host?`,
				);
			}
			if (!response.ok) {
				// A 403 here almost always means `json` is missing from `search.formats`
				// in SearXNG's settings.yml, which is its default.
				throw new Error(
					`SearXNG returned HTTP ${response.status}. If 403, enable the json format in search.formats in settings.yml.`,
				);
			}

			const body = (await response.json()) as {
				results?: SearxResult[];
				unresponsive_engines?: UnresponsiveEngine[];
			};
			const results = (body.results ?? []).slice(0, limit);
			const text = formatResults(params.query, results, body.unresponsive_engines ?? []);
			return {
				content: [{type: "text" as const, text}],
				details: {query: params.query, count: results.length, baseUrl},
			};
		},
	});
}
