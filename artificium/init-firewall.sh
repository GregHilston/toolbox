#!/bin/bash
# Default-deny egress for the Artificium sandbox: the open internet is allowed,
# every private network is not, and oMLX is reached through a single hole.
#
# Runs as root before the agent exists, then the entrypoint drops to a non-root
# user with no_new_privileges, so nothing the agent does can undo these rules.
set -euo pipefail
IFS=$'\n\t'

OMLX_HOST="${OMLX_HOST:-omlx.host}"
OMLX_PORT="${OMLX_PORT:-8000}"

# Addresses that MUST be unreachable, and that MUST answer when the rules are
# absent -- otherwise the assertion passes for the wrong reason and the safety
# net is decorative. The launcher verifies each one answers from the host before
# it ever starts this container; see artificium-sandbox.sh verify_probes.
BLOCKED_PROBES="${BLOCKED_PROBES:-}"

DENY_V4=(
  10.0.0.0/8 172.16.0.0/12 192.168.0.0/16
  169.254.0.0/16 100.64.0.0/10 198.18.0.0/15
  224.0.0.0/4 240.0.0.0/4
)
# fd7a:115c:a1e0::/48 is Tailscale's ULA. The v4 deny list covers 100.64/10 and
# would miss every tailnet peer reachable over its v6 address.
DENY_V6=(
  fd7a:115c:a1e0::/48 fc00::/7 fe80::/10 ::1/128
)

log() { printf 'firewall: %s\n' "$*" >&2; }
die() { printf 'firewall: FATAL: %s\n' "$*" >&2; exit 1; }

# The default route, not a hostname. `.host` is a live public gTLD, so a missing
# --add-host would have DNS answer with a stranger's address and this script
# would obligingly punch a hole to it.
gateway="$(ip route show default | awk '/default/ {print $3; exit}')"
[ -n "${gateway}" ] || die "no default route; cannot locate the container gateway"
case "${gateway}" in
  10.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*|192.168.*|198.1[89].*|198.19.*) ;;
  *) die "default gateway ${gateway} is not a private address; refusing" ;;
esac

# The name is still what the agent connects to, so the two must agree.
named="$(getent hosts "${OMLX_HOST}" | awk '{print $1; exit}' || true)"
[ -n "${named}" ] || die "cannot resolve ${OMLX_HOST}; run with --add-host=${OMLX_HOST}:host-gateway"
[ "${named}" = "${gateway}" ] \
  || die "${OMLX_HOST} resolves to ${named} but the gateway is ${gateway}; refusing"
log "oMLX at ${gateway}:${OMLX_PORT}"

iptables -F
iptables -X
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Rule order is the whole design. Everything accepted before the deny list is a
# hole the deny list never sees, so only three named tuples go above it.
iptables -A OUTPUT -o lo -j ACCEPT

while read -r ns; do
  [ -n "${ns}" ] || continue
  # An IPv6 resolver would make iptables error out and, being fail-closed, kill
  # the container. v6 is dropped wholesale anyway.
  case "${ns}" in *:*) log "skipping IPv6 resolver ${ns}"; continue ;; esac
  case "${ns}" in
    10.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*|192.168.*)
      log "WARNING: resolver ${ns} is a private address; this hole reaches a LAN device on :53" ;;
  esac
  iptables -A OUTPUT -d "${ns}" -p udp --dport 53 -j ACCEPT
  iptables -A OUTPUT -d "${ns}" -p tcp --dport 53 -j ACCEPT
  log "DNS allowed to ${ns}"
done < <(awk '/^nameserver/ {print $2}' /etc/resolv.conf)

iptables -A OUTPUT -d "${gateway}/32" -p tcp --dport "${OMLX_PORT}" -j ACCEPT

# DROP rather than REJECT: a rejection makes scanning the home network fast and
# informative, a silent drop makes it slow and useless.
for net in "${DENY_V4[@]}"; do
  iptables -A OUTPUT -d "${net}" -j DROP
done

# ESTABLISHED only, and below the deny list. RELATED above it would let a
# conntrack helper -- nf_conntrack_ftp and a PORT command naming a LAN address --
# create an expectation that is accepted before the deny list can see it.
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED -j ACCEPT
iptables -A OUTPUT -j ACCEPT

# IPv6 is dropped outright. Left open it is a trivial detour around every rule
# above. No `|| true` anywhere: a failure here must stop the run, not log a
# success line over the top of it.
command -v ip6tables >/dev/null 2>&1 || die "ip6tables missing; cannot close IPv6"
ip6tables -F
ip6tables -X
ip6tables -P INPUT DROP
ip6tables -P FORWARD DROP
ip6tables -P OUTPUT DROP
ip6tables -A INPUT -i lo -j ACCEPT
ip6tables -A OUTPUT -o lo -j ACCEPT
for net in "${DENY_V6[@]}"; do
  ip6tables -A OUTPUT -d "${net}" -j DROP
done
log "IPv6 egress dropped"

# A firewall that is not asserted is a firewall that is assumed.
#
# Assert the ruleset itself first: it tests the rules rather than the network's
# current mood, and cannot be fooled by a target that merely happens to be down.
for net in "${DENY_V4[@]}"; do
  iptables -C OUTPUT -d "${net}" -j DROP 2>/dev/null || die "missing deny rule for ${net}"
done
for net in "${DENY_V6[@]}"; do
  ip6tables -C OUTPUT -d "${net}" -j DROP 2>/dev/null || die "missing v6 deny rule for ${net}"
done
ip6tables -S | grep -q -- '-P OUTPUT DROP' || die "IPv6 OUTPUT policy is not DROP"
log "PASS ruleset matches intent"

# Then assert behaviour. curl exits 7 on a TCP reset and 28 on a timeout; only
# 28 means the packet was swallowed. Treating any non-zero exit as "blocked"
# would score a refused connection -- one that reached the host -- as a pass.
blocked() {
  local url="$1" timeout="$2" code
  curl -s -o /dev/null -m "${timeout}" "${url}" && return 1
  code=$?
  [ "${code}" -eq 28 ]
}

curl -s -o /dev/null -m 8 "http://${OMLX_HOST}:${OMLX_PORT}/v1/models" \
  || die "oMLX unreachable at ${OMLX_HOST}:${OMLX_PORT} -- is the server running?"
log "PASS oMLX reachable"

curl -s -o /dev/null -m 15 "https://example.com" || die "no internet egress; this run needs it"
log "PASS internet reachable"

if curl -6 -s -o /dev/null -m 8 "https://ipv6.google.com"; then
  die "IPv6 egress is open"
fi
log "PASS IPv6 egress closed"

[ -n "${BLOCKED_PROBES}" ] || die "BLOCKED_PROBES is empty; the launcher must supply verified targets"
IFS=',' read -r -a probes <<< "${BLOCKED_PROBES}"
for target in "${probes[@]}"; do
  blocked "http://${target}/" 6 \
    || die "private address ${target} was not silently dropped -- refusing to start the agent"
  log "PASS ${target} blocked"
done

log "all assertions passed"
