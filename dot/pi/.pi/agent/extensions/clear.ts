/**
 * Clear Command Extension
 *
 * Adds a /clear command that clears the current session and starts a fresh chat.
 * Place in ~/.pi/agent/extensions/clear.ts (or .pi/extensions/clear.ts for project-local).
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerCommand("clear", {
    description: "Clear the current session and start a new chat",
    handler: async (_args, ctx) => {
      const ok = await ctx.ui.confirm("Clear Session", "Clear the current session and start fresh?");
      if (ok) {
        await ctx.newSession({});
        ctx.ui.notify("Started a new session!", "success");
      } else {
        ctx.ui.notify("Aborted.", "info");
      }
    },
  });
}
