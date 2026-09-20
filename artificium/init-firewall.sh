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

# Probes that MUST fail. moria's own LAN and tailnet addresses serving the very
# port we allow through the gateway -- if either answers, the rules are wrong in
# the one way that matters.
BLOCKED_PROBES="${BLOCKED_PROBES:-192.168.1.1:80,192.168.1.234:8000,100.115.155.85:8000}"

log() { printf 'firewall: %s\n' "$*" >&2; }
die() { printf 'firewall: FATAL: %s\n' "$*" >&2; exit 1; }

omlx_ip="$(getent hosts "${OMLX_HOST}" | awk '{print $1; exit}')" \
  || die "cannot resolve ${OMLX_HOST}; run with --add-host=${OMLX_HOST}:host-gateway"
[ -n "${omlx_ip}" ] || die "cannot resolve ${OMLX_HOST}; run with --add-host=${OMLX_HOST}:host-gateway"
log "oMLX at ${omlx_ip}:${OMLX_PORT}"

iptables -F
iptables -X
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# The container's own resolvers, whatever the runtime handed us. Before the
# private-range denials, because Docker and OrbStack both put theirs inside one.
while read -r ns; do
  [ -n "${ns}" ] || continue
  iptables -A OUTPUT -d "${ns}" -p udp --dport 53 -j ACCEPT
  iptables -A OUTPUT -d "${ns}" -p tcp --dport 53 -j ACCEPT
  log "DNS allowed to ${ns}"
done < <(awk '/^nameserver/ {print $2}' /etc/resolv.conf)

iptables -A OUTPUT -d "${omlx_ip}/32" -p tcp --dport "${OMLX_PORT}" -j ACCEPT

# DROP rather than REJECT: a rejection makes scanning the home network fast and
# informative, a silent drop makes it slow and useless.
for net in \
  10.0.0.0/8 \
  172.16.0.0/12 \
  192.168.0.0/16 \
  169.254.0.0/16 \
  100.64.0.0/10 \
  198.18.0.0/15 \
  224.0.0.0/4 \
  240.0.0.0/4
do
  iptables -A OUTPUT -d "${net}" -j DROP
done

iptables -A OUTPUT -j ACCEPT

# IPv6 is dropped outright. Left open it is a trivial detour around every rule
# above, and nothing this agent needs is v6-only.
if command -v ip6tables >/dev/null 2>&1; then
  ip6tables -F 2>/dev/null || true
  ip6tables -P INPUT DROP 2>/dev/null || true
  ip6tables -P FORWARD DROP 2>/dev/null || true
  ip6tables -P OUTPUT DROP 2>/dev/null || true
  ip6tables -A INPUT -i lo -j ACCEPT 2>/dev/null || true
  ip6tables -A OUTPUT -o lo -j ACCEPT 2>/dev/null || true
  log "IPv6 egress dropped"
fi

# A firewall that is not asserted is a firewall that is assumed. Any failure
# here stops the agent from ever starting.
probe() { curl -s -o /dev/null -m "$2" "$1"; }

probe "http://${OMLX_HOST}:${OMLX_PORT}/v1/models" 8 \
  || die "oMLX unreachable at ${OMLX_HOST}:${OMLX_PORT} -- is the server running?"
log "PASS oMLX reachable"

probe "https://example.com" 15 || die "no internet egress; this run needs it"
log "PASS internet reachable"

IFS=',' read -r -a blocked <<< "${BLOCKED_PROBES}"
for target in "${blocked[@]}"; do
  if probe "http://${target}/" 4; then
    die "private address ${target} is REACHABLE -- refusing to start the agent"
  fi
  log "PASS ${target} blocked"
done

log "all assertions passed"
