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
    # Skills stay ON, unlike run 1. They are progressively disclosed — only the
    # index is always-on — and pruning to four categories costs 2.0 KB while
    # providing sdlc-review, test-driven-development, systematic-debugging and
    # requesting-code-review. kanban.review_dispatch spawns the reviewer WITH
    # the SDLC review skill, so removing it crippled the gate that then approved
    # a package whose CLI could not import.
    hermes profile create "${role}" \
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
    # `profile create` writes a literal `agent: {}`, and a profile key OVERRIDES
    # the root config — so run 1's disabled_toolsets never reached a single
    # worker and every one carried 40 KB of schemas including `delegation`,
    # the toolset home-lab/hermes says a 3B-active model cannot drive.
    # Measured after this fix: 40,394 B -> 20,277 B.
    python3 - "${profile_config}" "${SEED}/agent-block.yaml" <<'PYEOF'
import pathlib, sys
cfg, block = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]).read_text()
text = cfg.read_text()
if "agent: {}" in text:
    cfg.write_text(text.replace("agent: {}\n", block))
elif "disabled_toolsets" not in text:
    cfg.write_text(text.rstrip() + "\n" + block)
PYEOF
  fi
done

# Pruned AFTER the profile loop, not inside it: Hermes seeds a profile's bundled
# skills lazily, so a prune during creation is simply undone. Four categories out
# of twelve keeps the index at ~2.0 KB instead of 5.4 KB and loses nothing an
# engineering agent wants.
for role in builder researcher reviewer; do
  for unwanted in apple creative email media note-taking productivity social-media web; do
    rm -rf "${HERMES_HOME}/profiles/${role}/skills/${unwanted}"
  done
done

# Every judgement call runs on the dense Qwen3.8-27B; the builder keeps the fast
# MoE. This is the cloud-orchestrator asymmetry the Bot Mode video says makes
# multi-agent pay off, done entirely locally.
reviewer_config="${HERMES_HOME}/profiles/reviewer/config.yaml"
if [ -f "${reviewer_config}" ]; then
  sed -i 's|^  default: .*|  default: Qwen3.8-27B-4bit|' "${reviewer_config}"
  log "reviewer pinned to Qwen3.8-27B-4bit"
fi

# The key is read from .env, not only from the process environment.
if [ -n "${OMLX_API_KEY:-}" ]; then
  printf 'OMLX_API_KEY=%s\n' "${OMLX_API_KEY}" > "${HERMES_HOME}/.env"
  chmod 600 "${HERMES_HOME}/.env"
fi

# Git-init the shared workspace. Run 1's card 3 was interrupted mid-edit and
# left the tree with a broken import and four drifted tests, with no way back to
# the last good state. Worktree-per-card is the documented Hermes answer, but
# worktrees are preserved rather than merged, and a fumbled merge inside a
# 75-minute budget could end with an empty workspace — so for a run that must
# stay comparable to run 1, git plus commit-on-green is the lower-risk version
# of the same protection. Revisit worktrees once a run survives unattended.
if [ ! -d "${WORKSPACE}/.git" ]; then
  git -C "${WORKSPACE}" init -q 2>/dev/null || true
  git -C "${WORKSPACE}" config user.email "agent@localhost" 2>/dev/null || true
  git -C "${WORKSPACE}" config user.name "Hermes" 2>/dev/null || true
  printf '.venv/\n__pycache__/\ndata/raw/\ndata/final/\n*.pyc\n' > "${WORKSPACE}/.gitignore"
  git -C "${WORKSPACE}" add -A 2>/dev/null || true
  git -C "${WORKSPACE}" commit -qm "seed: brief and engineering standard" 2>/dev/null || true
  log "workspace git-initialised"
fi

hermes kanban init >/dev/null 2>&1 || true

# A one-shot `task` run wants profiles, config and skills, but no board — the
# board exists to sequence dependent work, and a single bounded question is one
# turn.
if [ "${AGENT_TASK_MODE:-0}" = "1" ]; then
  log "task mode: skipping the vt-smb task graph"
  exit 0
fi

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

  widen_id="$(hermes kanban create \
    "Widen to the remaining sources" \
    --body "Add the other sources from BRIEF.md behind the same port, one adapter package each, and implement the join: name normalisation, address matching, and the rule for when two records are one business. DONE WHEN: every added adapter has a mapper test against a recorded fixture, the dedup logic has its own tests in tests/unit/domain, and 'uv run vt-smb build' still exits 0." \
    --assignee builder --parent "${build_id}" --workspace "dir:${WORKSPACE}" \
    --goal --goal-max-turns 50 --json | jq -r '.id')"

  hermes kanban create \
    "Score every business for outreach and emit the dataset" \
    --body "Add outreach_score (float 0.0-1.0, required and never null) and outreach_reason (one plain-language sentence) to the domain model and the emitted dataset, per BRIEF.md. The score must be computed in the domain layer from recorded signals — never asked of a model — with the weighting in one place, documented, and tested. Keep the component signals as columns so the score can be taken apart. DONE WHEN: every row in data/final/businesses.csv has a non-null outreach_score in [0,1] and a non-empty outreach_reason, tests cover the scoring rules including boundary cases, and 'uv run vt-smb build' exits 0." \
    --assignee builder --parent "${widen_id}" --workspace "dir:${WORKSPACE}" \
    --goal --goal-max-turns 40 --json >/dev/null

  log "seeded 4 cards"
fi

hermes kanban list 2>&1 | tail -10 >&2
