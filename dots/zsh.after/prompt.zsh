function preexec() {
    timer=${timer:-$SECONDS}
}

function precmd() {
    if [ $timer ]; then
        timer_show=$(($SECONDS - $timer))
        export RPROMPT="%F{cyan}${timer_show}s %{$reset_color%}"
        unset timer
    fi
}
