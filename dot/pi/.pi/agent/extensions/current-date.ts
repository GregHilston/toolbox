/**
 * Injects the current date into the system prompt.
 *
 * Local models don't know today's date. This small extension appends it
 * so the model can answer date-relative questions ("what day is it",
 * "how long ago was X") without hallucinating.
 *
 * Follows pi's "less is more" system prompt philosophy — one line, ~20 tokens.
 * Reference: https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function currentDateExtension(pi: ExtensionAPI): void {
	pi.on("before_agent_start", async () => {
		const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD
		return {
			message: {
				content: `Today's date is ${today}.`,
				display: false,
			},
		};
	});
}
