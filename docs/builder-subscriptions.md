# Cheap subscriptions and free tiers for pi builders

Researched 2026-11-16. The question: is there something that beats what we pay
now for cheap builder models, called by pi with Opus orchestrating? We pay for
Claude Max ($100), ChatGPT Plus ($20, Luna via Codex OAuth) and OpenCode Go
($10, DeepSeek V4.1 Flash), then fall back to the DeepSeek API.

Starting point: the r/DeepSeek thread
[Which subscriptions give the most usage?](https://www.reddit.com/r/DeepSeek/comments/1xvh1hb/)
(read through the Arctic Shift archive, because Reddit blocked dungeon). Three
Sonnet researchers then checked its claims against vendor pages. Plan limits
change monthly, so check the date before you rely on a number.

## Verdict

**Stack two $10 Flash plans, then send overflow to a zero-retention host.**
On 2026-11-16, Go's monthly Flash limit ran out with 14 days still to go, so we
use about $190 a month of Flash at DeepSeek list prices. DeepSeek's own API had
$3.56 left in it.

Cheapest ways to get Flash, per typical builder request (750 uncached, 82,000
cached and 290 output tokens), at DeepSeek's off-peak list price = 1x:

| Route | Cost vs DeepSeek off-peak | Trains? | Cap |
|---|---:|---|---|
| OpenCode Go $10 | 0.1x ($100 for $10) | No (ZDR, renews monthly) | $20 / 5 h, $50 / week, $100 / month |
| Command Code GOAT $10 | 0.1x ($100 for $10) | No with ZDR on | same shape |
| Go Plus $40 | 0.2x ($200 for $40) | No | double Go |
| Ollama Cloud Pro $20 | 0.33x ($60 for $20) | No | monthly credit |
| OpenRouter → DeepInfra Flex | 0.86x (0.43x vs peak) | No (ZDR endpoint) | pay as you go |
| OpenRouter → CoreWeave | 0.84x | No (ZDR endpoint) | pay as you go |
| DeepSeek API | 1x off-peak, 2x peak | **Yes**, China | pay as you go |
| OpenCode Zen / Go Extra Usage | 2x (peak price at all hours) | No | pay as you go |

- **Go Plus gives 2x the Flash for 4x the price.** It is 4x only for V4 Pro
  and Kimi K3, and 8x for GLM-5.3. Go plus GOAT gives the same $200 of Flash for
  $20 rather than $40 ([Go docs](https://opencode.ai/docs/go/)).
- **GOAT from the gateway:**
  - Base URL `https://api.commandcode.ai/provider/v1`, Bearer key, OpenAI
    `/chat/completions`.
  - Send `x-cmd-zdr: 1` for no retention or training. It answers 422
    `cmd_zdr_no_providers` rather than leak.
  - **Unknown: whether Flash under ZDR keeps the $100 boost.** "Extra"-cost ZDR
    models meter at the default $20. The docs don't classify Flash, and the
    public `/models` list has no ZDR field. Only a paid key can tell: send
    `x-cmd-zdr: 1` and watch what the allowance shows. Model id
    `deepseek/deepseek-v4.1-flash`.
  - One blog saw about 50% cache hits for DeepSeek via Command Code from
    OpenCode, which puts a timestamp at the front of the prompt
    ([post](https://www.80aj.com/2026/09/02/opencode-deepseek-cache-issue/),
    snippet only). Check pi's hit rate in the first hour.
  - [Terms](https://commandcode.ai/terms) (2026-10-29) neither allow nor ban
    orchestrated agents. The FAQ says "integrate GOAT with any other agent".
  - The status code at a cap is undocumented.
  - Docs: [GOAT](https://commandcode.ai/docs/plans/goat),
    [provider API](https://commandcode.ai/docs/provider),
    [ZDR](https://commandcode.ai/docs/resources/zdr).
- **Don't hold two Go accounts.** Go's terms ban "multiple accounts to
  circumvent usage limits" ([ToS](https://opencode.ai/legal/terms-of-service)).
- **Leave Go's Extra Usage off.** It bills Zen's flat rate, which is DeepSeek's
  peak price even off-peak.
- **Replace `cloud-deepseek` with DeepInfra Flex.** It costs less than DeepSeek
  even off-peak, keeps no data, and runs fp8. Prices come from
  `https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash/endpoints`,
  and zero retention from `https://openrouter.ai/api/v1/endpoints/zdr`.
- **OpenRouter does hose the cache unless you pin it.** By default it picks a
  provider at random, weighted by price and speed, and every provider keeps its
  own cache. "Sticky routing" holds a warm provider for 60 idle minutes, but it is
  dropped on any failure and turned off by `provider.order`
  ([prompt caching](https://openrouter.ai/docs/features/prompt-caching),
  [routing](https://openrouter.ai/docs/features/provider-routing)). One write-up
  measured 39x cost from that drift. To pin it, set
  `provider: {only: ["deepinfra/fp8/flex"], allow_fallbacks: false, zdr: true}`
  through LiteLLM's `extra_body`, so an outage returns 502 or 503 and LiteLLM's
  chain takes over.
- **Simpler: call DeepInfra directly.** It charges the same list price, so we
  save OpenRouter's 5.5% credit fee and remove the routing layer. Caching is
  automatic by prefix, with a TTL it doesn't publish
  ([caching](https://docs.deepinfra.com/chat/prompt-caching)). Its privacy page
  says "We will not store, sell, or train using this data unless we have your
  explicit consent" ([privacy](https://deepinfra.com/privacy)). How to request
  the Flex tier directly is unverified. Measure `cached_tokens` over a 20-turn
  session before switching.
- **Go's 10x applies only to Flash.** V4 Pro, GLM-5.3 and Kimi K3 get $15
  each on Go, about 1.5x. `cloud-go` already pins Flash. Every limit has its own
  windows: 20% per 5 hours, 50% per week, 100% per month.
- **No free tier can carry a builder.** Long multi-turn calls at 50–200k
  tokens blow through every free limit. The free catalogs have also shrunk to
  weaker models in 2026, and most of them log or train. Free tiers suit side jobs on
  public code at best.
- **The DeepSeek API trains on inputs by default, and stores them in China.**
  Its privacy policy lists model training as a use
  ([policy](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html)).
  platform.deepseek.com has no opt-out setting. The policy's only route is an
  email to privacy@deepseek.com. The chat app's "Improve the model for everyone"
  toggle is documented for chat only. The
  [API terms](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html)
  say nothing about training. Go routes the same model under a zero-retention deal, so Go first is
  also the private order. That deal is "renewed monthly", currently through
  2026-11-30 ([Go docs](https://opencode.ai/docs/go/)).

## Paid plans compared

"x per $1" is the vendor's own quota divided by the price, at its list rates.
Treat it as an upper bound: our 95–99% cache hit on DeepSeek's own API may not
hold on a reseller.

| Service | $/mo | Usage per $1 | Third-party harness | Trains? | Verdict |
|---|---:|---|---|---|---|
| **OpenCode Go** | 10 | Flash 10x; Pro, GLM, Kimi 1.5x | pi validated; needs `x-opencode-session` | No by default | **Keep** |
| **Command Code GOAT** | 10 | up to 10x, cheap models only | Provider API, "any other agent" | No where the provider allows | Trial if Go binds |
| DeepSeek API | metered | 1x (baseline) | yes | **Yes, opt-out** | Overflow; opt out |
| NanoGPT | 12 | 60M input tokens/week, output free | API | unverified | Maybe for bulk reading |
| Ollama Cloud Pro | 20 | 3x (credits at its token rates) | standard API, 3 concurrent | No | Skip |
| Z.ai GLM Lite | 18 | credits, not convertible to $ | FAQ: "officially supported tools" only | Probably not | Only to get GLM-5.3 |
| Mistral Pro | 15 | 1x verified ($15 credit) | Vibe key outside Vibe unconfirmed | **Yes, opt-out** | Skip |
| Kimi Code | 19–39 | unpublished | API key for named tools | consumer terms: yes; China | Skip |
| MiniMax M Plan | 22+ | unpublished | "interactive developer use" | no policy found | Skip |
| Alibaba Coding Plan | ~50 | ~1,800 requests per $1 | **bans non-interactive use** | **Yes** | Skip |
| Synthetic | 9–90 | weekly credits | not stated | No | Unclear quantization |
| Copilot Pro | 10 | 1,500 credits | OpenCode only, officially | n/a | Skip |
| Chutes | — | pay-as-you-go only now | | No | Not a subscription |
| Deeprelay / Openrelay | 1 | claims 500M tokens | | | **Red flag: relay resale** |

Claims from the thread that did not hold up:

- **Mistral's "$300 Vibe limit via OAuth".** Mistral's pricing page lists $15
  of shared API credit and no OAuth
  ([pricing](https://mistral.ai/en/pricing),
  [subscriptions](https://docs.mistral.ai/admin/billing-usage/subscriptions)).
  Harness issues say the subscription is meant for Vibe only
  ([omnigent#1141](https://github.com/omnigent-ai/omnigent/issues/1141)), or
  that it works mechanically with the ToS unanswered
  ([nebuko#1155](https://github.com/nebuko/nebuko/issues/1155)). Several thread
  commenters say they use it. Until Mistral says so in writing, treat it as a ban risk.
- **Deeprelay at $1 for 500M tokens.** No legitimate source sells that. Relay
  markets resell grey or stolen credits
  ([write-up](https://dev.to/jamilxt/the-013-api-token-inside-the-underground-relay-market-for-ai-access-4034)).
  Never send code through one.
- **"Go is slower and caches worse."** No vendor source confirms or denies
  it. Commenters report 40–100 tok/s. Measure it in pi before believing either side.

## Free tiers

| Provider | Free models worth having | Limits | Trains? | Builder? |
|---|---|---|---|---|
| **OpenCode Zen free** | GLM-5.3-Flash, V4.1 Flash, MiniMax M3.1 Flash | unpublished; promotional | No for these | No: refuses non-OpenCode clients (429, tested) |
| **OpenRouter `:free`** | mostly Nemotron, ERNIE, Cohere North Mini Code | 20 RPM; 1,000/day after $10 lifetime credit | per provider; account switch excludes trainers | Side jobs |
| Cerebras trial | gpt-oss-120b, Qwen3.8-27B | $5, expires in 30 days, card needed | No (secondary source) | Side jobs |
| Groq | gpt-oss-120b, Qwen3.8-27B | 8K TPM | not retained by default | No: context too big |
| Gemini API free | 3.8 Flash and older | ~20 RPD reported | **Yes, human review** | Public code only |
| NVIDIA NIM trial | GLM-5.3-Flash, MiniMax M3.1 Flash | ~40 RPM, no production use | logged; no confidential data | Public code only |
| Mistral Experiment | Devstral, Codestral | ~1 RPS | **Yes, opt-out** | Side jobs |
| Cloudflare Workers AI | strong models are paid | 10k neurons/day | not checked | No |

### Free promos at the front of the `cloud` chain

The gateway's chain is one LiteLLM rule, `fallbacks: cloud: [cloud-luna,
cloud-deepseek]` in home-lab's `litellm/config.yaml`, so a free route would be
one more entry. The test is "does not train". Keeping data, such as 30-day abuse
logs, is acceptable. Checked 2026-11-16:

| Route | Model | Trains? | Callable from the gateway? |
|---|---|---|---|
| **Zro free plan** | DeepSeek V4.1 Flash | No, and keeps no requests ([privacy](https://zro.moonmath.ai/docs/privacy)) | Yes. OpenAI API at `https://zro.moonmath.ai/v1`, and pi is a listed integration. Daily allowance unpublished |
| OpenRouter `particle-ai/particle-1:free` | post-trained on V4.1 Flash | No, and ZDR by default ([policy](https://particle.ai/privacy/)) | Yes. 50/day, or 1,000/day after $10 credit. No benchmarks |
| OpenRouter `inclusionai/ling-3.2-flash:free` | Ling 3.2 Flash, 1M context | No ([Ant policy](https://maas-global.oss-ap-southeast-1.aliyuncs.com/Privacy%20Policy%20Legal.pdf)). The only free model with a ZDR endpoint | Yes. Same limits. Unproven on coding |
| Kilo `reflection/beam-free` | Beam | No, keeps 30 days (per Zen) | Yes. 200 requests/hour/IP ([Kilo](https://kilo.ai/docs/gateway/usage-and-billing)) |
| OpenCode Zen free Flash and GLM-5.3-Flash | | No | **No.** Our key got HTTP 429 `FreeUsageLimitError` "Free models work in OpenCode" on its first call |

Excluded because they train or say nothing: the NVIDIA Nemotron free models
(NVIDIA's trial terms collect content "to improve … AI models"), Inkling 2
Small, Flint, Cohere North Mini Code (trial terms), Gemma via Google AI Studio,
ERNIE, Dots, LFM, and Kilo `kilo-auto/free`. Groq, SambaNova and Cloudflare
don't train, but their free limits (8K TPM, 20 requests/day, 10k neurons/day)
can't hold a 50k-token call.

Zro's paid plans are poor value. Its Flash rate is $0.30 in / $1.10 out / $0.01
cache read ([models](https://zro.moonmath.ai/docs/models)), about 2.6x DeepSeek
off-peak per builder request. Pro's $40 budget for $20 still comes out worse
than DeepSeek direct. Use only the free plan.

- **If one of these joins the chain:**
  - Put the free route first.
  - Treat 429 as a short cooldown, honouring `Retry-After`.
  - Treat 402, 404 and "no endpoints" as the promo having ended: drop the route
    until the next daily discovery.
  - Every switch re-reads the context uncached. On a free route that costs nothing.

Gone in 2026: GitHub Models (retired 2026-07-30), Chutes' free tier, SambaNova
Cloud and Hugging Face free inference
([tracker](https://mvalentsev.github.io/awesome-free-ai-coding/providers/)).

Rules that matter: OpenRouter's limits are in
[api-reference/limits](https://openrouter.ai/docs/api-reference/limits), and
its training switch, separate for free and paid models, is in
[privacy/logging](https://openrouter.ai/docs/guides/privacy/logging). Gemini's
free terms say "Do not submit sensitive, confidential, or personal information
to the Unpaid Services" ([terms](https://aistudio.google.com/docs/terms)).

## Privacy, by default setting

No training by default: OpenCode Go (US/EU regions, the default), Chutes,
Synthetic, Ollama Cloud, Command Code (where its provider allows), and OpenRouter
itself, though not every provider behind it.

Training unless you opt out: DeepSeek API (China), Mistral Vibe and
Experiment, ChatGPT Plus (the "Improve the model for everyone" toggle also
covers Codex; OpenAI's page answered 403, so the default is unverified).

Trains with no real opt-out, or has no policy we could find: Alibaba Coding Plan,
Kimi consumer terms (opt-out by support ticket, China), MiniMax, and Gemini free.

Quotes and links:
[OpenCode Zen](https://opencode.ai/docs/zen/) ·
[Chutes](https://chutes.ai/privacy) ·
[Synthetic](https://synthetic.new/policies/privacy) ·
[Ollama](https://docs.ollama.com/cloud) ·
[Command Code](https://commandcode.ai/privacy) ·
[OpenRouter](https://openrouter.ai/privacy) ·
[Mistral](https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training) ·
[Alibaba](https://help.aliyun.com/en/model-studio/coding-plan) ·
[Kimi](https://www.kimi.com/help/others/data-usage) ·
[Z.ai Team Plan](https://docs.z.ai/devpack/teamplan) ·
[OpenAI](https://help.openai.com/en/articles/5722486-how-do-i-opt-out-of-my-content-being-used-to-improve-model-performance).

## Builder models, late 2026

Aggregator numbers ([Morph](https://www.morphllm.com/best-open-source-coding-model-2026),
checked 2026-10-29; [Artificial Analysis](https://artificialanalysis.ai/models/open-source)).
Most are vendor-reported, from each lab's own harness, so they are not
comparable across rows.

| Model | Terminal-Bench 2.1 | Other | $/1M in / out |
|---|---:|---|---|
| DeepSeek V4.1 Flash | 90.6 (vendor) | DeepSWE 74.2; AA index 33 | 0.12 / 0.80 |
| Kimi K3 | 88.3 | FrontierSWE 81.2 | 2.50 / 14 |
| GLM-5.3 | 88.2 | FrontierSWE 78.1 | 1.19 / 6 |
| Qwen3.8 (hosted Max) | 86.6 | SWE-bench Pro 67.7% | not open weight |
| MiniMax M3 | 66.0 | SWE-bench Pro 59.0% | |

Flash is the cheapest, and it may also be the strongest builder. GLM-5.3 is the
natural second model, and it sits in both the Go and GOAT pools. We found no
sourced report of a subscription serving quantized weights. The one measured
complaint is speed: GLM 5.2 on Z.ai's coding endpoint ran at 12–55 tok/s
([test](https://akitaonrails.com/en/2026/06/14/llm-benchmark-kimi-2-7-code-glm-5-2-minimax-m3-local/)).

## Not checked

- Synthetic's quantization page.
- Kimi and Z.ai Pro prices from the vendors themselves.
- Measured tok/s and cache hit rate on Go versus DeepSeek's API.

## Decided 2026-11-16

- **Zro free plan goes first in the `cloud` chain**, key
  `op://Infra/zro free api key/credential`. Live on 2026-11-16 as `cloud` and
  `cloud-zro`: 2 calls at once per key, 99% cache hits on a repeated prompt, daily
  allowance still unmeasured (home-lab `docs/llm-gateway.md` → Zro).
- **Command Code GOAT, a one-month trial** after Go, with `x-cmd-zdr: 1` on and key
  `op://Infra/commandcode goat api key/credential`. **Flash keeps the $100 under
  ZDR:** on 2026-11-16, $0.56 of ZDR Flash read 3% of the $20 5-hour limit, where
  the $4 default would have read 14%. Even at $20 it would have been worth keeping,
  at half DeepSeek's list price and with no training. Review at renewal on Dec 16,
  using the GOAT and DS API usage. The $1 Go plan is no cheaper test: it is "the only
  plan without API access" and answers 403 `upgrade_required`
  ([provider docs](https://commandcode.ai/docs/provider)).
- **No DeepInfra.** Greg dropped it on 2026-11-16; DeepSeek's API stays the paid tail.
- **Order:** Zro, GOAT, Go, Luna, DeepSeek. At DeepSeek's peak, Luna moves before GOAT:
  GOAT and Go draw their dollar allowances at the doubled peak price, and Luna's limits ignore
  the hour. DeepSeek stays last at every hour, since it doubles too. Routing on DeepSeek's
  half price alone saves nothing, because the plans meter at the same ratio. Built in home-lab
  [#181](https://github.com/GregHilston/home-lab/pull/181).
