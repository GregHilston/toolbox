/**
 * What matters here: the probe runs only for the litellm provider, a live
 * gateway changes nothing, a dead gateway switches only when oMLX answers,
 * and any HTTP response (even an error status) counts as reachable.
 */

import assert from "node:assert/strict";
import { createServer } from "node:http";
import { test } from "node:test";

import { decide, reachable } from "../.pi/agent/extensions/gateway-fallback.ts";

const G = "https://gateway.test/v1";
const L = "http://localhost:8000/v1";
const only = (...up: string[]) => async (url: string) => up.includes(url);

test("non-litellm provider is never probed", async () => {
	const probe = async () => assert.fail("probed");
	assert.deepEqual(await decide("omlx", G, L, probe), { action: "none" });
	assert.deepEqual(await decide(undefined, G, L, probe), { action: "none" });
});

test("gateway up: nothing happens", async () => {
	assert.deepEqual(await decide("litellm", G, L, only(G, L)), { action: "none" });
	assert.deepEqual(await decide("litellm", G, L, only(G)), { action: "none" });
});

test("gateway down, oMLX up: switch with the notice", async () => {
	assert.deepEqual(await decide("litellm", G, L, only(L)), {
		action: "switch",
		message: "gateway on dungeon unreachable; switched to omlx/Qwen3.6-35B-A3B-4bit (local)",
	});
});

test("both down: stranded, points at /model", async () => {
	const out = await decide("litellm", G, L, only());
	assert.equal(out.action, "stranded");
	assert.match((out as { message: string }).message, /\/model/);
});

test("reachable: an error status is up, a closed port is down", async () => {
	const server = createServer((_q, r) => r.writeHead(401).end());
	await new Promise<void>((ok) => server.listen(0, "127.0.0.1", ok));
	const { port } = server.address() as { port: number };
	assert.equal(await reachable(`http://127.0.0.1:${port}/v1`), true);
	await new Promise((ok) => server.close(ok));
	assert.equal(await reachable(`http://127.0.0.1:${port}/v1`), false);
});
