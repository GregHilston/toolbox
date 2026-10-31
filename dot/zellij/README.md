# Zellij — named sessions, and staying usable inside vim

Installed everywhere tmux is; tmux is still the default multiplexer. Config is
stow-managed at `dot/zellij/`, keybinds deliberately shaped like our tmux ones, and
`dot/zellij/.config/zellij/config.kdl`'s header comment owns the details.

**Learning the keys:** the bottom row is zellij's stock status-bar, listing what
the current mode accepts (press `Ctrl-b` to see the Tmux-mode keys), and
`Ctrl-b ?` opens zellij-forgot, a searchable list of every binding.

**Named sessions:** `zj <name>` (a zsh function in `dot/zsh/.zshrc`) attaches to that
session or creates it, from inside a session or out. It is the one verb for tmux's
`new -s` / `a -t` pair, and it tolerates that syntax — `zj a -t foo` works. Bare `zj`
lists, `zjk <name>` kills. Native equivalents: `zellij -s <name>` only creates and
errors if the name exists; `zellij attach -c <name>` is the attach-or-create; from
*inside* a session neither works, because zellij refuses to nest — that needs
`zellij action switch-session <name>`.

**Inside vim:** the autolock plugin puts zellij in Locked mode whenever the focused
pane runs `nvim|vim|git|fzf|zoxide|atuin`, so those tools keep `Ctrl-h/j/k/l`. Locked
mode passes every unbound key to the pane, so a locked pane used to have no way to
change tab. `Ctrl-b` (and `Alt-<hjkl>`/`Alt-<arrows>`) is bound in Locked mode too, on
the grounds that tmux's prefix is never swallowed either.

**Clipboard:** a plain drag copies. zellij captures the mouse, so the selection is
its own rather than Ghostty's, and its `copy_on_select` goes out over OSC 52 — which
did not reach the clipboard here. `copy_command` bypasses that and pipes to
`bin/clipboard-copy.sh`, which picks the tool per host because this file is stowed to
macOS, NixOS and Termux alike.

That wrapper writes OSC 52 to `$SSH_TTY` when it sees one, rather than copying on the
far end where a headless box has no clipboard at all. So a selection made in a zellij
on dungeon rides the connection back and lands on moria's clipboard — what zellij does
for itself when `copy_command` is unset. `Shift`-drag still works everywhere too, and
is Ghostty's own way past a mouse-capturing app.

**Nested in tmux, `Ctrl-b` never arrives.** tmux's prefix is `Ctrl-b` too, so it eats
the key and zellij looks frozen — no detach, no tab switching, no way out. `Ctrl-b
Ctrl-b` sends one through (tmux's `send-prefix`), `Ctrl-q` quits zellij outright, and
from any other pane `zellij --session <name> action detach` frees it without losing
the session.

`Ctrl-g` is **not** a force-unlock: autolock re-locks within `reaction_seconds`
(0.3s) because the pane still runs a trigger command. `Alt-z` is — it disables the
plugin first; `Alt-z` again hands control back. Config changes need a detach and
reattach if the running session does not pick them up.
