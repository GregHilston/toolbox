/**
 * What matters here: the probe runs only for the litellm provider, a live
 * gateway changes nothing, a dead gateway switches only when oMLX answers,
 * and any HTTP response (even an error status) counts as reachable.
 */

import assert from "node:assert/strict";
import { createServer } from "node:http";
import { test } from "node:test";

import { decide, looksLikeOutage, pickLocal, probeTwice, reachable } from "../.pi/agent/extensions/gateway-fallback.ts";

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

test("no local model in the registry: stranded notice, no oMLX probe", async () => {
	const out = await decide("litellm", G, undefined, only());
	assert.equal(out.action, "stranded");
	assert.match((out as { message: string }).message, /no local fallback configured/);
});

test("probeTwice retries only after a failure", async () => {
	let calls = 0;
	assert.equal(await probeTwice(G, async () => (calls++, true)), true);
	assert.equal(calls, 1);
	calls = 0;
	assert.equal(await probeTwice(G, async () => calls++ > 0), true);
	assert.equal(calls, 2);
	calls = 0;
	assert.equal(await probeTwice(G, async () => (calls++, false)), false);
	assert.equal(calls, 2);
});

test("reachable: 4xx is up, 5xx and a closed port are down", async () => {
	let status = 401;
	const server = createServer((_q, r) => r.writeHead(status).end());
	await new Promise<void>((ok) => server.listen(0, "127.0.0.1", ok));
	const { port } = server.address() as { port: number };
	const url = `http://127.0.0.1:${port}/v1`;
	assert.equal(await reachable(url), true);
	status = 404;
	assert.equal(await reachable(url), true);
	status = 502;
	assert.equal(await reachable(url), false);
	await new Promise((ok) => server.close(ok));
	assert.equal(await reachable(`http://127.0.0.1:${port}/v1`), false);
});

test("outage errors: connection and 5xx yes, 4xx no", () => {
	for (const e of ["Connection error.", "fetch failed", "502 Bad Gateway", "getaddrinfo ENOTFOUND llm.grehg2.xyz", "Request timed out"]) {
		assert.equal(looksLikeOutage(e), true, e);
	}
	for (const e of ["401 invalid api key", "400 oMLX memory guard: prompt too large", "context length exceeded", undefined]) {
		assert.equal(looksLikeOutage(e), false, String(e));
	}
});

test("pickLocal: wide profile first, :lab when it is all there is", () => {
	assert.deepEqual(pickLocal(["litellm/local-small", "omlx/Q:lab", "omlx/Q"]), { provider: "omlx", id: "Q" });
	assert.deepEqual(pickLocal(["litellm/local-small", "omlx/Q:lab", "deepseek/*"]), { provider: "omlx", id: "Q:lab" });
});

test("pickLocal: no concrete omlx entry uses the default", () => {
	for (const e of [undefined, [], ["omlx/*"], "x"]) {
		assert.deepEqual(pickLocal(e), { provider: "omlx", id: "Qwen3.6-35B-A3B-4bit" });
	}
});

test("decide names the given local model in the switch notice", async () => {
	const out = await decide("litellm", G, L, only(L), "omlx/Q:lab");
	assert.match((out as { message: string }).message, /switched to omlx\/Q:lab \(local\)/);
});
