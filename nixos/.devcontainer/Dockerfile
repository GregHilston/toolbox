FROM nixos/nix:latest

# Enable flakes
RUN mkdir -p /etc/nix && \
    echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# Install just and zsh (justfile uses zsh as shell, git-minimal already in base image)
RUN nix profile install nixpkgs#just nixpkgs#zsh

# Create symlinks so just can find zsh
RUN mkdir -p /bin && ln -sf $(which zsh) /bin/zsh

WORKDIR /workspaces/nixos
