# Sandbox for https://github.com/officialgr/agent-artificium, whose README states
# plainly that it is NOT A SAFE PRODUCT: no sandbox, no approval layer, and an
# agent that can rewrite its own code and its own API key. Every safety property
# comes from this container, never from the agent's configuration.
#
# Shaped after claude-code/Dockerfile, and after the firewall the official Claude
# Code devcontainer ships but that one omits.
FROM python:3.11-slim

ARG ARTIFICIUM_REPO=https://github.com/officialgr/agent-artificium.git
ARG ARTIFICIUM_REF=6c391f33a6b3cb94da27cc6d151192ad2aabfecb

# UID/GID of the host user, so bind-mounted files are owned by you, not root.
ARG UID=501
ARG GID=20

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dnsutils \
    git \
    gosu \
    iproute2 \
    iptables \
    jq \
    less \
    procps \
    ripgrep \
    sqlite3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Artificium is stdlib-only, so the image carries no Python dependencies. The
# agent installs whatever its own projects need with uv, from PyPI.
RUN git clone "${ARTIFICIUM_REPO}" /opt/artificium-dist \
    && git -C /opt/artificium-dist checkout --quiet "${ARTIFICIUM_REF}" \
    && rm -rf /opt/artificium-dist/.git

# The group may already exist under another name -- macOS's default GID 20 is
# `dialout` here -- so the user's primary group is addressed by id, never by the
# name `artificium`, which groupadd may well have failed to create.
# Artificium tells the model to emit `<tool_call>` blocks as plain text and
# parses them itself. That tag is also Qwen's native tool-call token, and oMLX
# parses tool calls out of every response unconditionally — so the server eats
# the block first and, because the doubled tags defeat its parser, hands back
# tool_calls with empty names and a content field with the call removed.
# Artificium then reports "empty answer (tool_calls)" and never lands a single
# tool call.
#
# life_loop.py's TAG_PATTERN already accepts a bare `<tool>` tag as an alias, so
# moving the prompt pack onto it costs no code change and dodges the collision
# entirely. This is the smallest adaptation that makes the harness usable here.
RUN sed -i 's|<tool_call>|<tool>|g; s|</tool_call>|</tool>|g' \
      /opt/artificium-dist/artificium-code/prompts/always/tool_protocol.md \
      /opt/artificium-dist/artificium-code/prompts/tools/core_tools.md \
      /opt/artificium-dist/artificium-code/prompts/events/tool_call_repair.md \
    && grep -q "<tool>" /opt/artificium-dist/artificium-code/prompts/always/tool_protocol.md

RUN groupadd --gid "${GID}" artificium 2>/dev/null || true \
    && useradd --uid "${UID}" --gid "${GID}" --create-home --shell /bin/bash artificium \
    && mkdir -p /instance /reference \
    && chown "${UID}:${GID}" /instance

COPY shared/init-firewall.sh artificium/entrypoint.sh /usr/local/sbin/
COPY artificium/omlx-shim.py /usr/local/bin/omlx-shim.py
COPY seed/ /opt/artificium-seed/
RUN chmod 0755 /usr/local/sbin/init-firewall.sh /usr/local/sbin/entrypoint.sh /usr/local/bin/omlx-shim.py

# PATH is deliberately NOT overridden. iptables, ip6tables and gosu all live in
# /usr/sbin, and dropping it costs the firewall and the privilege drop -- the
# IPv6 block worst of all, because its `command -v` guard would skip it in
# silence rather than fail.
ENV ARTIFICIUM_ROOT=/instance \
    HOME=/home/artificium

WORKDIR /instance

ENTRYPOINT ["/usr/local/sbin/entrypoint.sh"]
CMD ["python3", "/instance/artificium.py", "run", "--verbose"]
