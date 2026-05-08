/**
 * Web search extension — gives the LLM access to SearXNG via bash.
 *
 * Pi-mono doesn't have a custom tool registration API, but it has the
 * built-in `bash` tool. This extension injects system prompt instructions
 * teaching the LLM to use `curl` against the local SearXNG instance
 * (http://localhost:8214) when it needs additional context.
 *
 * SearXNG runs as a Docker container on the home lab (see docker-compose.yaml).
 * The same instance is used by Roger's pydantic-ai agents via roger/web.py.
 *
 * Requirements:
 * - SearXNG running at http://localhost:8214 (or via Tailscale)
 * - curl and jq available in PATH
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function webSearchExtension(pi: ExtensionAPI): void {
	pi.on("before_agent_start", async (event) => {
		return {
			systemPrompt:
				event.systemPrompt +
				`

## Web Search

You can search the web using the local SearXNG instance when you need
additional context — for example, to look up documentation, verify a fact,
understand an API, or research a topic. Use the bash tool:

\`\`\`bash
curl -s "http://localhost:8214/search?q=YOUR+QUERY&format=json" | jq '.results[:5] | .[] | {title, url, content}'
\`\`\`

Tips:
- URL-encode spaces as + in the query string
- Keep queries specific and concise
- Only search when the answer isn't available in the codebase or conversation
- You can fetch a specific URL for more detail: \`curl -s "URL" | head -200\`
`,
		};
	});
}
