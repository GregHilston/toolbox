# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Path to your oh-my-zsh installation.
export ZSH=~/.oh-my-zsh

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion. Case
# sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Auto-correction
ENABLE_CORRECTION="true"

# Show dots while waiting for completion
COMPLETION_WAITING_DOTS="true"

# History settings
# https://unix.stackexchange.com/a/273863/180341
HISTFILE="$HOME/.zsh_history"
HISTSIZE=100000
SAVEHIST=100000
setopt BANG_HIST                 # Treat the '!' character specially during expansion.
setopt EXTENDED_HISTORY          # Write the history file in the ":start:elapsed;command" format.
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits.
setopt SHARE_HISTORY             # Share history between all sessions.
setopt HIST_EXPIRE_DUPS_FIRST    # Expire duplicate entries first when trimming history.
setopt HIST_IGNORE_DUPS          # Don't record an entry that was just recorded again.
setopt HIST_IGNORE_ALL_DUPS      # Delete old recorded entry if new entry is a duplicate.
setopt HIST_FIND_NO_DUPS         # Do not display a line previously found.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_SAVE_NO_DUPS         # Don't write duplicate entries in the history file.
setopt HIST_REDUCE_BLANKS        # Remove superfluous blanks before recording entry.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.
setopt HIST_BEEP                 # Beep when accessing nonexistent history.

# Plugins
plugins=(git
  docker
  colored-man-pages
  colorize
  github
  virtualenv
  pip
  python
  brew
  macos
  zsh-syntax-highlighting
  zsh-autosuggestions
  web-search
  jsontools
  dotenv
)

source $ZSH/oh-my-zsh.sh

# VS Code shell integration (remote SSH and native terminal)
if [[ -n "$VSCODE_IPC_HOOK_CLI" ]] || [[ "$TERM_PROGRAM" == "vscode" ]]; then
  if command -v code &>/dev/null; then
    . "$(code --locate-shell-integration-path zsh 2>/dev/null)" 2>/dev/null || true
  fi
fi

# ── Environment ──────────────────────────────────────────────────────

HOSTNAME=$(hostname)

# Toolbox
TOOLBOX_HOME=~/Git/toolbox
export TOOLBOX_HOME=$TOOLBOX_HOME
export PATH=$PATH:$TOOLBOX_HOME/bin

# Editor
export VISUAL=nvim
export EDITOR="$VISUAL"

# Displays which virtual environment you're working on
export VIRTUAL_ENV_DISABLE_PROMPT=

# ── PATH additions ──────────────────────────────────────────────────

export PATH="$PATH:$HOME/.local/bin"
export PATH="$HOME/Apps:$PATH"

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
# Also try brew-installed nvm (macOS)
if command -v brew &>/dev/null && [ -s "$(brew --prefix nvm)/nvm.sh" ]; then
  source "$(brew --prefix nvm)/nvm.sh"
fi

# Go
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$GOPATH/bin

# Poetry
export PATH="$PATH:$HOME/.poetry/bin"
export PATH="$PATH:$HOME/.local/share/pypoetry/venv/bin"

# pyenv
if command -v pyenv >/dev/null 2>&1; then
    export PYENV_ROOT="$HOME/.pyenv"
    if [[ ":$PATH:" != *":$PYENV_ROOT/bin:"* ]]; then
        export PATH="$PYENV_ROOT/bin:$PATH"
    fi
    eval "$(pyenv init --path)"
    if command -v pyenv virtualenv-init >/dev/null 2>&1; then
        eval "$(pyenv virtualenv-init -)"
    fi
fi

# direnv
if command -v direnv &>/dev/null; then
  eval "$(direnv hook zsh)"
fi

# uv / rustup — added by their installers, loads cargo/uv onto PATH
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"

# libpq (Postgres CLI tools)
if [ -d "/opt/homebrew/opt/libpq/bin" ]; then
  export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
fi

# LM Studio CLI
if [ -d "$HOME/.lmstudio/bin" ]; then
  export PATH="$PATH:$HOME/.lmstudio/bin"
fi

# Screenlayout (xrandr scripts on Linux)
if [ -d "$HOME/.screenlayout" ]; then
  export PATH="$HOME/.screenlayout:$PATH"
fi

# ── Aliases ──────────────────────────────────────────────────────────

alias vim="nvim"
alias vi="nvim"
alias v="nvim"
alias e="exit"
alias c="clear"
alias lg="lazygit"
alias cat="bat"
alias htop="btop"
alias python='/usr/bin/python3'
alias night="redshift.sh"
alias audio="pavucontrol"

# Clipboard (pbcopy on macOS, xclip on Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
  alias clip="pbcopy <"
else
  alias clip="xclip -sel clip <"
fi

# ── Script aliases ───────────────────────────────────────────────────
# All scripts live in $TOOLBOX_HOME/bin (on PATH). These are convenience aliases.

alias git-all-history="git-all-history.sh"
alias git-commit-undo="git-commit-undo.sh"
alias youtube-to-audio="youtube-to-audio.sh"
alias search-string="search-string.sh"
alias search-file="search-file.sh"
alias docker-clear-containers="docker-clear-containers.sh"
alias docker-clear-images="docker-clear-images.sh"
alias docker-clear-volumes="docker-clear-volumes.sh"
alias docker-clear-networks="docker-clear-networks.sh"
alias localclaude="localclaude.sh"

# ── GitHub CLI ───────────────────────────────────────────────────────

alias ghpr="gh pr view --web"
alias ghprc="gh pr create --web"
alias ghprl="gh pr list"
alias ghis="gh issue view --web"
alias ghisc="gh issue create --web"
alias ghisl="gh issue list"
alias ghrepo="gh repo view --web"

# ── Git ──────────────────────────────────────────────────────────────

alias gdiff="git diff"
alias gshow="git show --ext-diff"
alias glog="git log --ext-diff -p"

# Capture the output of a command so it can be retrieved with ret
# https://stackoverflow.com/a/58598185/1983957
cap() {
    tee /tmp/capture.out
}

# Return the output of the most recent command that was captured by cap
ret() {
    command cat /tmp/capture.out
}

# ── Completions ──────────────────────────────────────────────────────

autoload bashcompinit && bashcompinit

# fzf
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# ngrok
if command -v ngrok &>/dev/null; then
  eval "$(ngrok completion)"
fi

# ── Powerlevel10k ────────────────────────────────────────────────────

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# ── Machine-local ────────────────────────────────────────────────────
# ~/.zshrc.local is generated by nix (nixos/modules/programs/tui/zsh/default.nix)
# and sourced here for nix-only additions. Safe no-op on non-nix machines.
[ -f ~/.zshrc.local ] && source ~/.zshrc.local
