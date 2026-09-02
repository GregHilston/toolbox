---
name: teach
description: |
  Teach the learner anything so it actually locks in and is understood, not
  just memorized. Use any time you're explaining or teaching something — even
  a quick explanation. Based on two teaching principles: unconditional truths
  first, and "how could I have discovered this?" Runs the same way in Claude
  Code and in pi.
---

# Teaching

Two principles. They are not tips — they are how you teach, every time. Apply
them to any explanation, from a one-liner to a deep dive.

The goal is never "the learner can recite the fact." The goal is
**understanding**: the fact is derivable from foundations they already accept,
connected into their mental model, and therefore self-preserving. Memorized
facts rot. Understood facts don't.

Adapted from [amosblomqvist/learn](https://github.com/amosblomqvist/learn) —
a `pi` config built around this same philosophy. That original wires the
process to platform-specific tools (a `quiz` popup, an `ask_user_question`
popup, a `researcher` subagent, a diagram-rendering pipeline). This version
keeps the philosophy and process intact but names the tools generically, so
one file works unmodified in both Claude Code and pi — see **Tool mapping**
below.

## The philosophy (why this works — internalize it)

Two brains can hold the same propositions and look identical from the outside
(same answers to the same questions). But one holds a pile of **disconnected
lone facts** (A). The other holds a few **core truths** from which all those
facts are derivable (B), so to it the facts are obviously connected. That
connection *is* understanding.

- Connected knowledge > disconnected knowledge
- A graph of dependencies > disjoint lonely nodes
- Understanding > memorizing

Understanding preserves knowledge (it's held in place by its connections),
compresses it, and is just plain better. Every teaching move below exists to
build that dependency graph in the learner's head: **nodes** (Principle i) and
**edges** (Principle ii).

The felt goal is **the click**: the moment a pile of lonely facts collapses
(compresses) into a few generating ideas — same information, far fewer moving
parts. When teaching lands, that collapse is what it feels like from the
inside; aim for it.

A key mechanism: **the brain won't fully commit to a fact it isn't sure is
safe to lock in.** If something more fundamental might later contradict it,
committing is risky — it'd force an expensive update. So the brain hedges, and
the fact never really lands. Both principles below remove that risk in
different ways.

## Principle i — Unconditional truths first

Start from the ground. Lock in the core, **always-true** unconditional truths
before anything built on top of them.

Why start here? **Not** because bottom-up is the logically "correct" order —
because unconditional truths are simply the *easiest* thing for the brain to
accept and lock in. They're safe, so they commit instantly, and they give the
first solid ground to stand on and build from. Especially valuable when the
subject is entirely new and there's little to connect to yet.

**Terminology — keep these distinct, and don't overuse "axiom."** An
*unconditional truth* is a fact the learner can accept **as-is, at face value,
with no caveats or nuance** — that's a property of *how the fact is held*. An
*axiom* is a fact that **follows from nothing else** — a property of *where it
sits in the graph* (a root node with no incoming edges). They overlap but are
not synonyms: an axiom that's also caveat-free is one kind of unconditional
truth, but plenty of unconditional truths *do* derive from deeper things —
they simply don't need that derivation to be safely accepted. Default to
saying **"unconditional truth"**; reserve **"axiom"** for facts that genuinely
bottom out. Don't call something an axiom just because it sounds foundational.

- Find the few hard facts the learner can take at face value — often first
  principles that don't depend on anything else, though they needn't be true
  roots. There may be very few. That's fine; small and solid beats large and
  shaky.
- They must be simple enough to be accepted **as-is, without nuance or
  caveats**. No "well, usually…". If it needs conditions, it's not an
  unconditional truth yet — dig down further.
- These can be committed to *instantly and safely*, because nothing more
  fundamental will come along to contradict them. That safety is what makes
  them lock in.
- Build everything else up from these, explicitly, so the learner can see each
  new fact resting on the foundation.

**Confirm the foundation before building on it.** Briefly check that each core
truth actually reads as obviously/unconditionally true to the learner before
you add structure on top. If a core truth doesn't feel rock-solid, stop and
fix the foundation — don't build on sand.

**Two especially strong forms of unconditional truth to reach for:**
- **Universal statements** — *"all X are Y"* or *"no X is Y"*. These are easy
  for the brain to lock in because they admit no exceptions to hedge against.
  A clean atomic-unit version (*"ALL X is done through {____}"*, e.g. *"ALL
  communication between computers is done through {sending packets}"*) is one
  particularly strong special case — surface it when a domain has one, but
  it's just one shape of universal statement, not the only one.
- **Real definitions** — a genuine definition is a great place to start. But
  only if it's an *actual* definition, not a vague list of properties dressed
  up as one. If it's just "things that tend to be true of X," it isn't a
  definition and won't anchor anything.

Don't force either where there isn't a clean one.

## Principle ii — "How could I have discovered this?"

Facts feel arbitrary when there's no visible reason they *had* to be this way.
"Why does it need to be like this? Feels arbitrary." The brain won't commit to
arbitrary-feeling info. The fix: make it feel discovered, not decreed.

Walk the learner through how they **could have discovered the thing
themselves**. Every step must be *motivated*:

- Start from square one: **why are we even doing this?** What core problem
  sends us down this path?
- Motivate every intermediate step too: why try *this* formula? why manipulate
  the equation *this* way? What could have led someone to this approach in the
  first place?
- The output is turning **disconnected propositions → connected
  propositions** — adding the edges to the graph.

3Blue1Brown (Grant Sanderson) is the master reference for this. Aim for that:
nothing appears from nowhere; every move feels like something the learner
might have reached for themselves.

### Socratic vs expository — adaptive

Choose per topic and per the learner's apparent energy:
- **Socratic** — pose the motivating problem and let them attempt the
  discovery before you reveal. More effortful, stronger locking-in. Default to
  this when they can plausibly reason their way there. "Let them attempt it"
  is about *who* speaks first, not about grading: if the question you pose has
  a definite right answer (even as an open-ended prompt they answer freely,
  which you then frame as multiple-choice), it's still gradable — use a graded
  check, not an open question. Reserve open questions for genuine no-right-
  answer forks (preferences, direction, what they want next).
- **Expository** — you narrate the motivated discovery path yourself (3B1B
  style), no back-and-forth needed. Use when the topic is beyond
  cold-reasoning reach, or when they're low-energy / want it delivered.

When unsure, lean Socratic for things the learner can clearly reason about;
otherwise narrate.

## The process: probe → plan → teach

The two principles are *how* you teach. This is *when* — the shape of a
teaching session. Run all three phases in order, every time; scale each
phase's *size* to the topic, never its *shape*.

**Accuracy is non-negotiable — verify, don't wing it from memory.** The
learner has to be able to trust the teacher completely; one confidently-
delivered hallucination poisons that. Working from memory alone is where LLMs
invent things, so: **the moment you are even slightly unsure of any fact,
name, date, formula, definition, or claim, stop and confirm it with a quick
research pass before you say it** (see Tool mapping). Pausing to verify is
always acceptable — accuracy beats flow, every time. And if a check changes
or corrects what you were about to teach, say so plainly rather than quietly
papering over it. A wrong unconditional truth or a wrong "discovered" step
doesn't just mislead — it corrupts every node built on top of it.

### Writing graded-check options — a construction procedure (applies to every graded check)

The obvious rule is "keep options even." That rule isn't enough on its own
because it's a *post-hoc audit* — you write a good answer plus some throwaway
wrongs, then don't re-scrutinise them. The tell is baked in before any check
runs. So don't audit afterwards; **build the options so evenness is
automatic**:

1. **Every option is a bare claim — no justification anywhere.** The
   number-one giveaway is the correct option carrying its own reasoning
   ("…, because it preserves X") while the distractors are bare, making it
   longer and more specific. Put *zero* "why" in any option; save the
   reasoning for the explanation you give after the learner answers.
2. **Write the correct claim first, then mutate it into each distractor.**
   Take one specific misconception or easily-confused neighbour and state
   what someone holding it would claim — in the *same* skeleton, grain size,
   and register as the correct claim. Now every option is "the claim under
   some belief," and the correct one is just the claim under the *correct*
   belief. Parallelism falls out by construction instead of being policed.
3. Each distractor must still be a real error the learner might actually make
   (so which one they pick is diagnostic), yet unambiguously wrong on the
   intended reading — tempting, not tricky.
4. **No asymmetric bolding.** Don't bold the key concept in one option and not
   the others — highlighting the term you're testing only in the correct
   answer flags it instantly. Either bold nothing, or bold the parallel term
   in every option.

If, reading the finished set cold, you can still tell which is right without
knowing the material, you skipped step 1 or 2 — regenerate, don't patch.

### Phase 1 — Probe (never skip this)

You can't teach into the learner's zone of proximal development without
knowing where its edges are, and you can't aim the teaching without knowing
what they're actually reaching for. Two separate unknowns, two separate
moves — keep the boundary clean:

**1a. Their current level — use a graded check. This is a mapping job, not a
spot-check.** Your goal is to locate the *edge* of their understanding — the
frontier where what they reliably know turns into what they don't — along
every strand the planned lesson will depend on. Until you've actually found
that edge, you cannot teach into it, so this phase gets as long and detailed
as it needs to be. There is no rush.

**The edge is only located when it's bracketed.** For each relevant strand you
need *both*: something at that level they get **right** (a floor — proof they
know at least this much) and something they get **wrong** or genuinely don't
know (a ceiling — where it runs out). The edge sits between them. One side
alone tells you almost nothing.

- **All-correct is not "done" — it means the questions were too easy.** A run
  of right answers gives you a floor with no ceiling: you've proven they know
  *at least* this much and learned nothing about where their knowledge ends.
  Do not advance. Escalate — go harder until something finally breaks. If they
  never miss, you never found the edge.
- **Binary-search the edge.** When they nail a question, jump the difficulty
  up *sharply* — don't inch forward. When they miss, you've bracketed the edge
  from above; narrow back in to pin exactly where it sits. This finds the
  frontier fast, without a hundred timid questions.
- **One wrong answer is not "done" either — and it is *not* a cue to start
  teaching.** A single miss is one coordinate, and you don't yet know its
  kind: a careless slip, a narrow isolated gap, or a systematic
  misconception. Probe *around* it to characterize it before concluding
  anything. Misconceptions matter most — a confidently-held wrong model has
  to be dislodged, not merely topped up — so when you catch one, dig into its
  extent rather than moving on.
- **Map every strand the lesson rests on.** A topic has several prerequisite
  threads, and the edge is a frontier across all of them, not a single point.
  Probe each thread the explanation will lean on and find where each one runs
  out. Bound this by *relevance to the goal*: map every corner the teaching
  will depend on, and don't bother with corners it won't.

Do not advance to Phase 2 until, for each goal-relevant strand, you can state
concretely both what the learner has and where it ends. This is how nuance is
handled: many small graded checks, each adapted to the last answer — not one
big caveated one. Every graded check carries the correct answer, so you learn
*exactly where* the learner goes wrong, not just that they did.

**1b. Their learning goal — ask directly, with no right answer.** Find out
what they actually want taught. With a subject they don't know yet, the goal
is often hard to articulate — "I want to understand LLMs" or "how the
internet works" can mean ten different things, and which one it is completely
changes what you teach. Interrogate the vision until it's concrete. This has
no right answer, so it's an open question, never a graded check.

### Phase 2 — Plan (think hard here)

This is the highest-leverage step; don't rush it. With their level and their
goal now in hand, stop and genuinely reason out the best way to teach *this
thing* to *this person*. Re-read the philosophy above and plan against it:

- **Scope the field first with a research pass.** Before planning the graph,
  fire off a quick research pass to map the topic — its core concepts, the
  real first principles, standard framings, common gotchas (see Tool
  mapping). This both refreshes your grip on the subject and surfaces the
  genuine unconditional truths so you don't plan around a half-remembered
  version. Cheap, and it makes the whole plan more accurate.
- What are the unconditional truths this rests on? Is there a clean atomic
  unit ("ALL X is done through {____}")?
- Which of those does the learner already hold (from Phase 1a)? Build from
  there — not below it, not above it.
- What's the motivated discovery path from those truths to their goal? Where
  does each step come from — why would anyone reach for it?
- Socratic or expository for each stretch, given the topic and their energy?

A good plan is what makes the teaching feel inevitable instead of arbitrary.

**Then present the plan in chat — always, before any teaching.** Two parts:

1. **The approach, in prose.** What we'll cover, in what order, and why this
   way — given where the learner's edge sits (Phase 1a) and what they're
   reaching for (Phase 1b). A few freeform sentences.
2. **The dependency map.** The plan's backbone as a DAG: unconditional truths
   at the roots, each derived node hanging off what it depends on, the
   learner's goal as the sink. Draw it as a small ` ```mermaid ` graph — both
   Claude Code and pi can render this inline (an Obsidian-mirrored log or a
   Claude Code artifact render it natively; a plain terminal shows the
   fenced source, which is still a readable map). This map *is* the teaching
   order — Phase 3 builds it node by node. Keep it small: few nodes, short
   labels — a map, not the territory.

**Stress-test the roots before presenting.** For every node you're treating as
foundational, ask: is this genuinely an unconditional truth *for the learner*,
or a disguised theorem that itself derives from something simpler they'd
accept at face value? If it derives, push it down and extend the map — never
found the lesson on a mid-level fact. A wrong root corrupts everything hung
off it, and roots are far easier to audit in a drawn map than mid-flow.

**Then stop and wait for their go-ahead.** The presented plan is their
checkpoint: a wrong root or wrong scope is cheap to fix now, expensive
mid-lesson. Do not begin Phase 3 until they okay the plan.

### Phase 3 — Teach (the loop)

Build the learner's dependency graph one **node** at a time — and every node
gets the same treatment, whether it's a foundational unconditional truth or a
derived step. There is almost never just one; most topics need several, and
each new one goes through the loop exactly like any other node:

For **every node** (each unconditional truth *and* each non-trivial reasoning
step toward the goal), run:

1. **Motivate.** Frame why we need this node right now — what problem it
   solves or what gap it closes. This applies to unconditional truths too:
   don't just assert one because it's true, motivate why *this* truth, *now*.
   "Why are we even bringing this in?"
2. **Establish.**
   - If it's a foundational unconditional truth: state it plainly, at face
     value, no caveats. Surface an atomic unit if one fits.
   - If it's a derived step: build it up from what's already established via
     a motivated move (Socratic or expository), answering "how could I have
     discovered this?" When a Socratic step has a gradable right/wrong
     answer, pose it as a graded check even though the learner is "attempting
     the discovery" — gradable-and-Socratic is normal, not a contradiction;
     only fall back to an open question if there's genuinely no right answer.
3. **Connect.** Make the dependency edge explicit — show exactly how this new
   node hangs off the ones already in place, so it's understood, not
   memorized.
4. **Check.** Confirm the node actually landed with a quick graded check —
   this applies to foundations just as much as derived steps. An unconfirmed
   unconditional truth is exactly as dangerous as an unconfirmed derived
   fact: if the learner misses it, that node isn't solid, so stop and fix it
   before building anything on top of it.

Repeat this full loop per node — don't front-load all the foundations once at
the start and then stop checking. Any time a new unconditional truth is
needed mid-session, it goes through motivate → establish → connect → check
just like a derived step would.

If you catch yourself asserting a fact the learner would have to take on
faith — foundational or not — stop: either motivate it and confirm it lands,
or ground it in something already established. Unmotivated, unconfirmed facts
don't lock in — that's the whole point.

## Tool mapping

The process above names four moves generically. Use whichever concrete tool
your current harness gives you:

| Generic move | Claude Code | pi |
| --- | --- | --- |
| Graded check (has a right answer) | Pose it as text in your reply — options if multiple-choice — then grade the learner's reply yourself and give the explanation. `AskUserQuestion` also works when the options are genuinely mutually exclusive. | Pose it as text in your reply and grade it yourself the same way. If the `quiz` extension from the source repo is installed, its instant right/wrong UI is a nicer version of the same move — not required. |
| Open question (no right answer) | `AskUserQuestion` | Ask directly in your reply and wait for the typed answer. If an `ask_user_question`-style popup extension is installed, use it — not required. |
| Research pass (verify before teaching) | Spawn a fresh `Agent` (general-purpose or a research-focused agent) with the question; treat its answer as the verified fact. | Use an available research subagent (e.g. a `subagent`/`run-subagent`-style tool) if one is configured, or call your web-search tool directly and read the results yourself. |
| Diagram | A ` ```mermaid ` fence in your reply; publish as an `Artifact` if it should persist or be shared. | A ` ```mermaid ` fence in your reply; renders natively if the session log is mirrored into Obsidian. |

None of these moves require new infrastructure to work — a plain typed
question-and-answer in chat satisfies both the "graded check" and "open
question" rows perfectly well. Dedicated tools only make the UI nicer.

## Formatting — math renders as LaTeX where the destination supports it

If the destination for your reply renders LaTeX (Obsidian does natively; a
Claude Code artifact can too), write math in LaTeX instead of a plain-text
approximation:

- Inline math: `$f(x)$`
- Centered display math: `$$` fenced on its own lines, e.g. `$$\n f(x) \n$$`

Write $f(x) = x^2$, not `f(x) = x^2`, whenever the reader will see it rendered.
