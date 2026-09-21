#!/bin/bash
# One-time setup of the Hermes arm: config, profiles, kanban board, task graph.
# Idempotent — safe to re-run, and it re-runs on every container start so a
# restart repairs anything half-written.
set -euo pipefail
IFS=$'\n\t'

SEED=/opt/agent-seed
WORKSPACE=/instance/workspace

log() { printf 'bootstrap: %s\n' "$*" >&2; }
die() { printf 'bootstrap: FATAL: %s\n' "$*" >&2; exit 1; }

[ -n "${HERMES_HOME:-}" ] || die "HERMES_HOME is not set"
mkdir -p "${HERMES_HOME}"

# journal_mode must be right before the first database is opened, so the config
# is seeded before any hermes command runs.
if [ ! -f "${HERMES_HOME}/config.yaml" ]; then
  cp "${SEED}/config.yaml" "${HERMES_HOME}/config.yaml"
  log "seeded config.yaml"
fi

for role in builder researcher reviewer; do
  if ! hermes profile list 2>/dev/null | grep -qE "^\s*[^ ]*\b${role}\b"; then
    # --no-skills: the image bundles 58 skills (airtable, powerpoint, notion…)
    # and each one is prefill on every turn of every worker. The role's SOUL.md
    # is what this profile knows.
    hermes profile create "${role}" --no-skills \
      --description "$(head -1 "${SEED}/profiles/${role}/SOUL.md" | sed 's/^# //')" \
      >/dev/null 2>&1 || die "could not create profile ${role}"
    log "created profile ${role}"
  fi
  install -m 0644 "${SEED}/profiles/${role}/SOUL.md" \
    "${HERMES_HOME}/profiles/${role}/SOUL.md"
  # `profile create` snapshots the root model block into the profile, so a
  # correction to the root config does not reach an already-created profile.
  # Re-stamp it every boot; this is the difference between a worker that runs
  # and one that exits 0 having done nothing.
  profile_config="${HERMES_HOME}/profiles/${role}/config.yaml"
  if [ -f "${profile_config}" ]; then
    sed -i 's|provider: custom:omlx|provider: "custom"|' "${profile_config}"
  fi
done

# The key is read from .env, not only from the process environment.
if [ -n "${OMLX_API_KEY:-}" ]; then
  printf 'OMLX_API_KEY=%s\n' "${OMLX_API_KEY}" > "${HERMES_HOME}/.env"
  chmod 600 "${HERMES_HOME}/.env"
fi

hermes kanban init >/dev/null 2>&1 || true

# The task graph. Deliberately small: the point of the first cards is to prove
# the loop turns, not to front-load a plan the agent should be making itself.
# Each card's body IS its acceptance criteria — goal mode judges against it.
if [ "$(hermes kanban list --json 2>/dev/null | jq 'length' 2>/dev/null || echo 0)" = "0" ]; then
  log "seeding the task graph"

  research_id="$(hermes kanban create \
    "Establish one Vermont business source end to end" \
    --body "Pick the single most promising source named in BRIEF.md. Establish: its endpoint, auth, rate limits, licence, what robots.txt permits, and the exact shape of one real response. Save that response under data/raw/. Write findings to research/. DONE WHEN: a real response is saved on disk and the findings file names the endpoint, the licence and at least five fields the source actually returns." \
    --assignee researcher --workspace "dir:${WORKSPACE}" \
    --goal --goal-max-turns 20 --json | jq -r '.id')"

  build_id="$(hermes kanban create \
    "Build the vertical slice against that source" \
    --body "Using the saved response as a fixture, build the package described in ENGINEERING.md far enough to ingest that one source end to end: domain types, the adapter's DTO and mapper, a port, a repository, and a CLI. DONE WHEN: 'uv run vt-smb build' exits 0 on a clean data/ and 'uv run pytest' passes with at least one mapper test running against the recorded fixture." \
    --assignee builder --parent "${research_id}" --workspace "dir:${WORKSPACE}" \
    --goal --goal-max-turns 40 --json | jq -r '.id')"

  hermes kanban create \
    "Widen to the remaining sources" \
    --body "Add the other sources from BRIEF.md behind the same port, one adapter package each, and implement the join: name normalisation, address matching, and the rule for when two records are one business. DONE WHEN: every added adapter has a mapper test against a recorded fixture, the dedup logic has its own tests in tests/unit/domain, and 'uv run vt-smb build' still exits 0." \
    --assignee builder --parent "${build_id}" --workspace "dir:${WORKSPACE}" \
    --goal --goal-max-turns 60 --json >/dev/null

  log "seeded 3 cards"
fi

hermes kanban list 2>&1 | tail -10 >&2
