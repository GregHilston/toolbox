# The Hermes arm of the harness comparison. Same cage as the Artificium arm:
# default-deny egress installed by root, then a non-root agent for the rest of
# the container's life.
#
# Pinned to v2026.9.14, NOT the v2026.8.31 that home-lab/hermes runs. That
# release's notes open by describing how v0.21.0 made state.db fragile, and two
# of the named second-writer paths (cron's lifecycle guard, the dashboard's
# writable handle) are exactly what a long unattended run exercises.
FROM nousresearch/hermes-agent:v2026.9.14

ARG UID=501
ARG GID=20

# Debian trixie. The base carries neither iptables nor gosu.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dnsutils \
    gosu \
    iproute2 \
    iptables \
    jq \
    ripgrep \
    sqlite3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${GID}" artificium 2>/dev/null || true \
    && useradd --uid "${UID}" --gid "${GID}" --create-home --shell /bin/bash artificium \
    && mkdir -p /instance \
    && chown "${UID}:${GID}" /instance

COPY shared/init-firewall.sh hermes/entrypoint.sh /usr/local/sbin/
COPY hermes/bootstrap.sh /usr/local/bin/hermes-bootstrap.sh
COPY hermes/hooks/require-green.sh /usr/local/bin/require-green.sh
COPY hermes/agent-block.yaml /opt/agent-seed/agent-block.yaml
COPY hermes/hooks-block.yaml /opt/agent-seed/hooks-block.yaml
COPY hermes/config.yaml /opt/agent-seed/config.yaml
COPY hermes/profiles/ /opt/agent-seed/profiles/
COPY seed/ /opt/agent-seed/
RUN chmod 0755 /usr/local/sbin/init-firewall.sh /usr/local/sbin/entrypoint.sh \
      /usr/local/bin/hermes-bootstrap.sh /usr/local/bin/require-green.sh

# HERMES_HOME on the bind mount, so the kanban board, the profiles and the work
# all survive a restart and stay readable from the host.
# --accept-hooks / HERMES_ACCEPT_HOOKS allowlists the pre_tool_call gate. Without
# it `hermes hooks doctor` reports "not allowlisted — hook will NOT fire at
# runtime", and the gate silently does nothing.
ENV HERMES_ACCEPT_HOOKS=1 \
    HERMES_HOME=/instance/home \
    HOME=/home/artificium \
    UV_LINK_MODE=copy
# The uv cache is an image layer and the venv is on the bind mount, so uv can
# never hardlink between them; unset, it says so on every command it runs.

# An offline run has no PyPI, and the card's own DONE WHEN criteria are
# `uv run pytest` and `uv run vt-smb build` — which the completion gate also
# runs. With a cold cache both spend 50s retrying and then fail, so an offline
# card is unsatisfiable by construction; two iterations were lost to this and
# read as packaging failures. Resolve and download the seeded dependency set at
# build time, and ship the lock beside the pyproject so nothing re-resolves.
USER artificium
RUN mkdir -p /tmp/warm/src/vt_smb /tmp/warm/tests \
    && cp /opt/agent-seed/project/pyproject.toml /tmp/warm/ \
    && touch /tmp/warm/src/vt_smb/__init__.py \
    && cd /tmp/warm \
    && UV_PYTHON_DOWNLOADS=never uv lock \
    && UV_PYTHON_DOWNLOADS=never uv sync --frozen \
    && rm -rf /tmp/warm/.venv
USER root
RUN cp /tmp/warm/uv.lock /opt/agent-seed/project/uv.lock && rm -rf /tmp/warm

WORKDIR /instance/workspace

ENTRYPOINT ["/usr/local/sbin/entrypoint.sh"]
# Bootstrap runs as the agent user on every start, so a restart repairs a
# half-written setup, then execs the dispatcher as PID 1's child.
# `hermes gateway run` in the foreground, NOT `hermes kanban daemon`: the
# standalone daemon is deprecated and refuses to start without --force, because
# the dispatcher now lives inside the gateway and the two race for claims.
CMD ["bash", "-c", "/usr/local/bin/hermes-bootstrap.sh && exec hermes gateway run --accept-hooks"]
