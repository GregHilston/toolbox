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

RUN groupadd --gid "${GID}" artificium 2>/dev/null || true \
    && useradd --uid "${UID}" --gid "${GID}" --create-home --shell /bin/bash artificium \
    && mkdir -p /instance /reference \
    && chown "${UID}:${GID}" /instance

COPY init-firewall.sh entrypoint.sh /usr/local/sbin/
COPY seed/ /opt/artificium-seed/
RUN chmod 0755 /usr/local/sbin/init-firewall.sh /usr/local/sbin/entrypoint.sh

ENV ARTIFICIUM_ROOT=/instance \
    HOME=/home/artificium \
    PATH=/usr/local/bin:/usr/bin:/bin

WORKDIR /instance

ENTRYPOINT ["/usr/local/sbin/entrypoint.sh"]
CMD ["python3", "/instance/artificium.py", "run", "--verbose"]
