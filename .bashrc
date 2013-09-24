#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
PS1='[\u@\h \W]\$ '

alias ll='ls -l'
alias la='ls -la'
alias vi='vim'
alias battery='acpi'

# Terminal transparency 
[ -n "$XTERM_VERSION" ] && transset-df -a >/dev/null
