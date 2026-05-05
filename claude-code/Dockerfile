# Based on the official Claude Code devcontainer:
# https://github.com/anthropics/claude-code/tree/main/.devcontainer
# See also: https://code.claude.com/docs/en/devcontainer
FROM node:20

ARG CLAUDE_CODE_VERSION=latest

# Install development tools and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    curl \
    zsh \
    fzf \
    nano \
    vim \
    jq \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
    chown -R node:node /usr/local/share

# Create workspace and config directories and set permissions
RUN mkdir -p /workspace /home/node/.claude && \
    chown -R node:node /workspace /home/node/.claude

WORKDIR /workspace

# Set up non-root user
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

ENTRYPOINT ["claude"]
