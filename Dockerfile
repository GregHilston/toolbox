FROM ubuntu:20.04

RUN useradd --system --create-home --shell /bin/bash --gid sudo --uid 1001 testuser
WORKDIR /home/testuser
USER testuser

# keeps the container alive
CMD tail -f /dev/null
