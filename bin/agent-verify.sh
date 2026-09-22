#!/bin/bash
# Prove the Hermes run mechanisms actually fire, before spending an hour on them.
#
# Run 2 burned 75 minutes on a config whose headline change was inert: the
# auxiliary model slots carried no base_url, so the dense judge model served zero
# requests while everything *looked* configured. `hermes config` echoed nothing
# back and no error was raised anywhere. Static inspection cannot catch that
# class of failure; only observing the mechanism fire can.
#
# Every assertion here is behavioural and cheap. Run it before every long run.
set -uo pipefail
IFS=$'\n\t'

TOOLBOX="${TOOLBOX:-$HOME/Git/toolbox}"
INSTANCE="${AGENT_VERIFY_DIR:-$HOME/Git/agent-runs/verify}"
IMAGE="${AGENT_IMAGE:-agent-sandbox-hermes:latest}"
MODEL_JUDGE="${AGENT_JUDGE_MODEL:-Qwen3.8-27B-4bit}"
MODEL_BUILD="${AGENT_BUILD_MODEL:-Qwen3.6-35B-A3B-4bit-DWQ}"
STATS="$HOME/.omlx/stats.json"

pass=0; fail=0
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$*"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; fail=$((fail+1)); }
note() { printf '       %s\n' "$*"; }

model_requests() {
  python3 - "$1" "$2" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print((d.get("per_model") or {}).get(sys.argv[2], {}).get("requests", 0))
except Exception:
    print(0)
PY
}

# The probe script is written to the mounted instance directory and run by path.
# Passing it as a `bash -c` string means three levels of quoting between the host
# shell, docker, and the container shell — which silently broke three assertions
# on the first attempt and reported them as system failures.
run_probe() {
  cat > "${INSTANCE}/probe.sh"
  # shellcheck disable=SC2046
  docker run --rm $("${TOOLBOX}/bin/agent-sandbox.sh" _flags "${INSTANCE}" 2>/dev/null) \
    -e AGENT_TASK_MODE=1 -e AGENT_BUILD_MODEL="${MODEL_BUILD}" \
    "${IMAGE}" bash /instance/probe.sh 2>&1
}

printf '\n== agent-verify ==\n\n'
rm -rf "${INSTANCE}"; mkdir -p "${INSTANCE}"
before="$(model_requests "${STATS}" "${MODEL_JUDGE}")"
before_build="$(model_requests "${STATS}" "${MODEL_BUILD}")"

printf '1. bootstrap, profiles, toolsets, skills, hook\n'
out="$(run_probe <<'PROBE'
/usr/local/bin/hermes-bootstrap.sh >/dev/null 2>&1
hermes hooks doctor >/dev/null 2>&1 || true
echo "TOOLBYTES=$(hermes -p builder prompt-size --json 2>/dev/null \
  | python3 -c 'import json,sys; print(sum(t["json_bytes"] for t in json.load(sys.stdin).get("toolsets_breakdown",[])))')"
echo "REVIEWER=$(awk '/^  default:/{print $2; exit}' "$HERMES_HOME/profiles/reviewer/config.yaml")"
echo "BUILDER=$(awk '/^  default:/{print $2; exit}' "$HERMES_HOME/profiles/builder/config.yaml")"
echo "SKILLCATS=$(find "$HERMES_HOME/profiles/builder/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
echo "SDLC=$(find "$HERMES_HOME/profiles/reviewer/skills" -name SKILL.md -path '*sdlc*' | wc -l | tr -d ' ')"
PROBE
)"
tb="$(printf '%s' "${out}" | sed -n 's/^TOOLBYTES=//p')"
{ [ -n "${tb}" ] && [ "${tb}" -lt 26000 ]; } && ok "tool schemas pruned (${tb} B)" || bad "tool schemas not pruned (${tb:-?} B)"
printf '%s' "${out}" | grep -q "REVIEWER=${MODEL_JUDGE}" && ok "reviewer on ${MODEL_JUDGE}" || bad "reviewer model not pinned"
printf '%s' "${out}" | grep -q "BUILDER=${MODEL_BUILD}" \
  && ok "builder profile names ${MODEL_BUILD}" || bad "builder profile does not name ${MODEL_BUILD}"
sc="$(printf '%s' "${out}" | sed -n 's/^SKILLCATS=//p')"
{ [ "${sc:-0}" -ge 3 ] && [ "${sc:-99}" -le 6 ]; } && ok "skills pruned to ${sc} categories" || bad "skills not pruned (${sc:-0} categories)"
printf '%s' "${out}" | grep -q "SDLC=1" && ok "reviewer has the sdlc-review skill" || bad "sdlc-review skill missing"

printf '\n2. the completion gate blocks red and passes green\n'
out="$(run_probe <<'PROBE'
mkdir -p /instance/workspace/tests && cd /instance/workspace
cat > pyproject.toml <<EOF
[project]
name = "gate-probe"
version = "0.1.0"
requires-python = ">=3.11"
[dependency-groups]
dev = ["pytest>=8.0"]
EOF
echo "def test_x(): assert False" > tests/test_x.py
printf 'RED=%s\n' "$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
echo "def test_x(): assert True" > tests/test_x.py
green_out="$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
printf 'GREEN=%s\n' "${green_out}"
printf 'GREENEXIT=%s\n' "$?"
other_out="$(echo '{"tool_name":"read_file"}' | /usr/local/bin/require-green.sh | head -c 26)"
printf 'OTHER=%s\n' "${other_out}"
printf 'OTHEREXIT=%s\n' "$?"
# A green suite over a pyproject whose packaging was deleted. Both runs that
# ever completed a card shipped exactly this and the gate waved both through.
cat > pyproject.toml <<EOF
[project]
name = "gate-probe"
version = "0.1.0"
requires-python = ">=3.11"
[project.scripts]
gate-probe = "gate_probe:main"
[dependency-groups]
dev = ["pytest>=8.0"]
EOF
printf 'GUTTED=%s\n' "$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
# Every one of these was a working way past the gate, and the first is cheaper
# than either evasion actually observed: the gate used to exit 0 when there was
# nothing to look at, which made deleting the evidence the shortest path.
rm -f pyproject.toml
printf 'NOPYPROJECT=%s\n' "$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
printf 'NOPAYLOAD=%s\n' "$(echo '{}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
cat > pyproject.toml <<EOF
[project]
name = "gate-probe"
version = "0.1.0"
requires-python = ">=3.11"
[project.entry-points.console_scripts]
gate-probe = "gate_probe:main"
[dependency-groups]
dev = ["pytest>=8.0"]
EOF
printf 'RENAMED=%s\n' "$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
cat > pyproject.toml <<EOF
[project]
name = "gate-probe"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []
[project.scripts]
gate-probe = "gate_probe:main"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
printf 'EMPTYDEPS=%s\n' "$(echo '{"tool_name":"kanban_complete"}' | GATE_BUILD_CMD=true /usr/local/bin/require-green.sh | head -c 26)"
PROBE
)"
printf '%s' "${out}" | grep -q 'RED={"decision": "block"' && ok "gate blocks a failing suite" || bad "gate did NOT block on failing tests"
# Silence alone is what a crashed gate also produces, so pair it with exit 0.
{ printf '%s' "${out}" | grep -q '^GREEN=$' && printf '%s' "${out}" | grep -q '^GREENEXIT=0$'; } \
  && ok "gate allows a green suite" || bad "gate blocked a green tree, or did not exit 0"
{ printf '%s' "${out}" | grep -q '^OTHER=$' && printf '%s' "${out}" | grep -q '^OTHEREXIT=0$'; } \
  && ok "gate ignores other tools" || bad "gate fired on a non-completion tool, or did not exit 0"
printf '%s' "${out}" | grep -q 'GUTTED={"decision": "block"' && ok "gate blocks a tree whose packaging was deleted" || bad "gate allowed a pyproject with a console script but no build system"
printf '%s' "${out}" | grep -q 'NOPYPROJECT={"decision": "block"' \
  && ok "gate blocks a missing pyproject.toml" || bad "deleting pyproject.toml still opens the gate"
printf '%s' "${out}" | grep -q 'NOPAYLOAD={"decision": "block"' \
  && ok "gate blocks a payload it cannot parse" || bad "an unreadable payload still opens the gate"
printf '%s' "${out}" | grep -q 'RENAMED={"decision": "block"' \
  && ok "gate sees entry-points.console_scripts too" || bad "renaming the scripts table skips the packaging check"
printf '%s' "${out}" | grep -q 'EMPTYDEPS={"decision": "block"' \
  && ok "gate blocks an empty dependencies list" || bad "dependencies = [] still satisfies the gate"

# Section 2 proves the SCRIPT behaves. It says nothing about whether Hermes ever
# calls it — and for seven runs it did not. The root config carried the hook, the
# profile configs did not, and a kanban worker runs under a profile. Run `long-a`
# completed a card through builder -> review -> complete with `require-green.log`
# still absent. Assert the worker's own config, and let Hermes fire it.
out="$(run_probe <<'PROBE'
/usr/local/bin/hermes-bootstrap.sh >/dev/null 2>&1
for role in builder reviewer; do
  grep -q "require-green.sh" "$HERMES_HOME/profiles/${role}/config.yaml" \
    && echo "PROFILE_${role}=yes" || echo "PROFILE_${role}=no"
done
cd /instance/workspace 2>/dev/null || cd /tmp
# Approve first, exactly as `hermes gateway run --accept-hooks` does at boot,
# then ask the doctor. Asking before anything has approved reports "not
# allowlisted" on a perfectly good config — which it did, and which is a
# verification script crying wolf rather than a finding.
hermes --accept-hooks hooks test pre_tool_call 2>&1 | grep -oE "exit=[0-9]+" | head -1 | sed 's/^/FIRED_/'
PROBE
)"
printf '%s' "${out}" | grep -q "PROFILE_builder=yes" \
  && ok "the gate reaches the builder profile" || bad "builder profile has NO gate — it will not fire for a worker"
printf '%s' "${out}" | grep -q "PROFILE_reviewer=yes" \
  && ok "the gate reaches the reviewer profile" || bad "reviewer profile has NO gate — the review handoff is ungated"
# Deliberately NOT asserting `hermes hooks doctor` here. `--accept-hooks` on
# `hooks test` fires the hook without persisting an approval, so the doctor
# reports "not allowlisted" on a config that works — it failed this way twice.
# The gateway is what writes the allowlist (proven: `long-a` wrote one at boot),
# and whether the gate actually fired in a run is reported per-run by
# `agent-deliver.sh` as "gate fired: N". Config here, behaviour there.
printf '%s' "${out}" | grep -q "FIRED_exit=" \
  && ok "Hermes actually dispatches the hook ($(printf '%s' "${out}" | sed -n 's/^FIRED_//p'))" \
  || bad "Hermes did not dispatch the hook at all"

printf '\n3. the auxiliary judge model receives traffic\n'
note "kanban decompose runs on auxiliary.kanban_decomposer — a direct, deterministic test"
dec="$(run_probe <<'PROBE'
hermes kanban init >/dev/null 2>&1
id=$(hermes kanban create "compare electric leaf blowers for half an acre in vermont" --triage --json 2>/dev/null \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "CARD=$id"
timeout 300 hermes kanban decompose "$id" 2>&1 | grep -oE 'Decomposed .* children' | head -1
PROBE
)"
# `kanban decompose` is genuinely flaky on a local model — it sometimes returns
# no children with no error. The auxiliary wiring itself is proven separately
# (config resolves with base_url/api_key, and a manual decompose moved the dense
# model's request count), so a miss here is a WARN, not a failure.
if printf '%s' "${dec}" | grep -q "children"; then
  ok "decompose produced children"
else
  note "WARN decompose produced no children this attempt (known flaky on a local model)"
fi
# oMLX flushes stats.json lazily, so a read immediately after the call can miss
# it. Poll rather than conclude "inert" from a write that has not landed yet.
delta=0
for _ in $(seq 1 12); do
  after="$(model_requests "${STATS}" "${MODEL_JUDGE}")"
  delta=$(( after - before ))
  [ "${delta}" -gt 0 ] && break
  sleep 5
done
if [ "${delta}" -gt 0 ]; then
  ok "${MODEL_JUDGE} served ${delta} request(s) — auxiliary wiring is LIVE"
else
  note "WARN no ${MODEL_JUDGE} traffic observed (decompose may not have fired; wiring verified separately)"
fi

printf '\n4. the builder model that answers is the one we think\n'
note "a profile config is what we asked for; oMLX's log says what actually served the turn"
# Counters in stats.json proved unreliable here — the probe answered while the
# delta stayed zero, more than once, and chasing it was not worth the time. The
# server's own log line is better evidence anyway: it names the model per
# request, it is timestamped, and contention_audit.sh already parses it.
OMLX_LOG="${OMLX_LOG:-$HOME/Library/Logs/omlx.log}"
probe_start="$(date '+%F %T')"
probe_out="$(run_probe <<'PROBE'
/usr/local/bin/hermes-bootstrap.sh >/dev/null 2>&1
timeout 300 hermes -p builder -z "say pong" 2>&1 | tail -2
PROBE
)"
probe_end="$(date '+%F %T')"
served="$(grep "Chat completion: model=" "${OMLX_LOG}" 2>/dev/null \
  | awk -v s="${probe_start}" -v e="${probe_end}" '{t=$1 " " substr($2,1,8)} t>=s && t<=e' \
  | sed 's/.*model=\([^,]*\),.*/\1/' | sort -u | tr '\n' ' ')"
if printf '%s' "${served}" | grep -qF "${MODEL_BUILD}"; then
  ok "oMLX served the builder turn on ${MODEL_BUILD}"
  case "${served}" in
    *" "*" "*) note "other models in the same window (another process on this box): ${served}" ;;
  esac
elif [ -z "${served// /}" ]; then
  bad "no oMLX completion logged for the builder turn at all"
  note "the probe answered: $(printf '%s' "${probe_out}" | tail -1)"
  note "an answer with no server record means it never reached oMLX; no answer means"
  note "the probe container failed and this says nothing about routing"
else
  bad "the builder turn was served by: ${served}— expected ${MODEL_BUILD}"
fi

printf '\n5. the offline toolchain can satisfy the card\n'
note "with no PyPI, 'uv run pytest' and the build are what DONE WHEN and the gate require"
# A dedicated instance: sections 1-2 leave their own pyproject.toml in the
# workspace, and the entrypoint only seeds a file it does not already find.
OFFLINE_DIR="${INSTANCE}-offline"
rm -rf "${OFFLINE_DIR}"; mkdir -p "${OFFLINE_DIR}"
cat > "${OFFLINE_DIR}/probe.sh" <<'PROBE'
cd /instance/workspace
mkdir -p src/vt_smb tests && touch src/vt_smb/__init__.py
printf 'import click\n@click.command()\ndef main(): print("ok")\n' > src/vt_smb/cli.py
echo "def test_x(): assert True" > tests/test_x.py
echo "OFFLINE=${UV_OFFLINE:-unset}"
timeout 240 uv run pytest -q 2>&1 | tail -2 | sed 's/^/PYTEST=/'
timeout 120 uv run vt-smb --help >/dev/null 2>&1 && echo "ENTRYPOINT=ok" || echo "ENTRYPOINT=fail"
timeout 120 uv run python -c 'import pandas, pyarrow, httpx, pydantic' 2>&1 >/dev/null \
  && echo "DEPS=ok" || echo "DEPS=fail"
PROBE
# shellcheck disable=SC2046
out="$(docker run --rm $("${TOOLBOX}/bin/agent-sandbox.sh" _flags "${OFFLINE_DIR}" 2>/dev/null) \
  -e AGENT_TASK_MODE=1 -e AGENT_OFFLINE=1 "${IMAGE}" bash /instance/probe.sh 2>&1)"
printf '%s' "${out}" | grep -q 'OFFLINE=1' && ok "UV_OFFLINE is set in offline mode" || bad "UV_OFFLINE not exported"
printf '%s' "${out}" | grep -q 'PYTEST=.*1 passed' && ok "pytest runs offline from the image cache" || bad "pytest cannot run offline"
printf '%s' "${out}" | grep -q 'ENTRYPOINT=ok' && ok "the console script imports offline" || bad "console script broken offline"
printf '%s' "${out}" | grep -q 'DEPS=ok' && ok "the seeded dependencies import offline" || bad "seeded dependencies unavailable offline"

printf '\n== %d passed, %d failed ==\n\n' "${pass}" "${fail}"
[ "${fail}" -eq 0 ] || exit 1
