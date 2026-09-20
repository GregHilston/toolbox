# vt-smb — how this project is built

These are standards, not suggestions. Depart from them where the domain argues
for it, but write the argument into memory when you do.

The point of all of it is one thing: this project will be read, extended and
debugged months from now by someone who has forgotten it. Every rule below earns
its place by making that easier. A rule that does not is ceremony — say so and
drop it.

## Layout

```
pyproject.toml            uv-managed; console script `vt-smb`
src/vt_smb/
  domain/                 entities and value objects. Pure.
  application/            use cases: build_dataset, refresh_dataset, assess_websites
  ports/                  Protocols the application depends on
  adapters/               one package per external source
    vtsos/                client.py · dto.py · mapper.py
    socrata/              client.py · dto.py · mapper.py
    overpass/             client.py · dto.py · mapper.py
    web/                  the website prober
    http/                 shared cached, rate-limited client
    storage/              parquet/csv/sqlite repository
  cli.py
tests/
  unit/domain/            pure, fast, no I/O
  unit/adapters/          mappers against recorded fixtures
  integration/            hits real sources; marked, opt-in, not in the default run
  fixtures/               recorded raw responses
data/
  raw/                    content-addressed cache of every response ever fetched
  interim/
  final/                  the dataset
```

**Dependencies point one way: `adapters → application → domain`.** `domain/`
imports nothing from the rest of the project and no I/O library — no `httpx`, no
`pandas`, no `pydantic`. If you find yourself wanting one there, the thing you
are writing is not domain logic.

## Domain models

**Parse, don't validate.** A type is constructed from untrusted input, validates
once in its constructor, and is thereafter trusted everywhere. `PhoneNumber`
cannot hold `"call us!"`. `WebsiteUrl` cannot hold a Facebook URL — that is a
`SocialProfile`, and the distinction is one of the most valuable signals in the
dataset, so the type system should be the thing that keeps them apart. Once you
hold the type, nothing downstream re-checks it, and no function needs a defensive
`if`.

**The test for introducing a type.** Ask: *does this rule out a state that would
otherwise cause a bug or a wrong business decision?*

- `PhoneNumber`, `EmailAddress`, `WebsiteUrl`, `Zip`, `County`, `NaicsCode` —
  yes. Each has a wrong-but-plausible string form, each is mixed up with its
  neighbours in practice, and each getting through wrong corrupts an outreach
  list.
- A review count, a page weight in bytes, a retry limit — no. There is no
  invalid `int` here worth a class. Leave them `int`.

Wrapping every primitive is how this style gets a bad name. Wrap the ones that
bite.

**Entity or value object — decide deliberately, because here it is load-bearing.**

- `Business` is an **entity**. Two registry rows and an OSM node can be the same
  business with three different phone numbers and two spellings of the name.
  Identity is `BusinessId`, not field equality. That means deduplication and
  merging are *domain logic with tests*, not an afterthought in a dataframe.
  This is the hardest and most valuable code in the project. Give it a home.
- `Address`, `PhoneNumber`, `WebsiteAssessment`, `Provenance` are **value
  objects**: frozen, equal by value, no identity, freely shared and replaced.

Use `@dataclass(frozen=True)` with validation in `__post_init__`. Pydantic is for
parsing at the edge, not for domain types — a domain type that knows how to
deserialise itself has an I/O concern in it.

**Make absence explicit and typed.** Most fields will be missing for most
businesses; that is the nature of the data. `owner: Owner | None` is a fact about
the world. What must never happen is a missing value and an unknown value looking
the same when they mean different things — "we looked and there is no website"
is a strong signal, "we have not looked yet" is not a signal at all. If that
distinction matters for a field, model it.

## DTOs

**One DTO package per external source, and DTOs never leave it.**

- `adapters/<source>/dto.py` mirrors *that source's wire shape*, with that
  source's names and that source's warts. Frozen. Pydantic here is a good fit.
- `adapters/<source>/mapper.py` converts DTO → domain. Every quirk of that source
  lives in the mapper: its date formats, its sentinel values, its three spellings
  of "Burlington", its habit of putting a phone number in the address field.
- Nothing outside the adapter package imports a DTO. The application layer has
  never heard of the Secretary of State's JSON.

That boundary is the whole return on the pattern. When a source changes its
format, exactly one file changes, and exactly one test file tells you whether
you got it right. Without it, source quirks leak across the codebase and every
one of them becomes permanent.

Do **not** add a DTO for an internal function call. A DTO is for a wire format
you do not control. Passing domain objects between your own layers is correct.

## Ports

`ports/` holds `typing.Protocol` definitions — `BusinessSource`,
`WebsiteProber`, `BusinessRepository`. The application depends on these; adapters
satisfy them structurally, with no base class to inherit and no registration.
Tests substitute a hand-written fake in three lines and need no mocking
framework. If a test needs `unittest.mock.patch` to reach into a module, that is
a design signal, not a testing problem.

## Testing

- `tests/unit/domain/` — pure and fast. Validation, merge rules, scoring.
- `tests/unit/adapters/` — mappers against **recorded fixtures**, which are the
  same cached responses `data/raw/` collects. Record a real response once, then
  test against it forever.
- `tests/integration/` — hits the real network. Marked, opt-in, never in the
  default run. These are for confirming a source still behaves, not for CI.

The merge and normalisation rules are where the bugs will be, and they are pure
functions of their inputs. That is the best possible situation for testing;
exploit it.

## Tooling

`uv` for everything. `ruff` for lint and format. `mypy --strict` over `domain/`
and `application/` — they are pure, so strict costs nothing there and catches a
great deal. `pytest`.

## Comments

Comments carry *why*, never *what*. A comment earns its place by holding a
non-obvious constraint, a deliberate deviation, or the reason the obvious simpler
version is wrong — "the registry returns `0001-01-01` for 'never filed'" is worth
a line forever. Default to none, and never narrate a change in code; that belongs
in the commit message.
